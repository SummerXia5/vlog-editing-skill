"""Integration tests with synthetic media; no personal footage or cloud services."""
import hashlib
import http.client
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import Engine
from server import StudioServer
from store import Store

FFMPEG = os.environ.get('STUDIO_FFMPEG', 'ffmpeg')


class StudioTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.source = cls.root/'original.mp4'
        subprocess.run([FFMPEG, '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=180x320:rate=30',
                        '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000', '-t', '2',
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac',
                        '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
                        str(cls.source)], check=True)
        cls.source_bytes = cls.source.read_bytes()
        cls.engine = Engine(cls.root/'data', FFMPEG)
        cls.server = StudioServer(('127.0.0.1', 0), cls.engine)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        c = http.client.HTTPConnection('127.0.0.1', cls.server.server_port)
        c.request('GET', '/')
        res = c.getresponse(); cls.cookie = res.getheader('Set-Cookie').split(';')[0]; res.read(); c.close()

    @classmethod
    def tearDownClass(cls):
        cls.engine.q.join()
        cls.server.shutdown(); cls.server.server_close(); cls.tmp.cleanup()

    def request(self, method, path, data=None, headers=None, authenticated=True):
        base = {'Origin': self.server.origin, 'X-Studio-Request': '1'}
        if authenticated:
            base['Cookie'] = self.cookie
        body = data if isinstance(data, bytes) else json.dumps(data).encode() if data is not None else None
        base.update(headers or {})
        c = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=30)
        c.request(method, path, body, base); response = c.getresponse()
        result = (response.status, dict(response.getheaders()), response.read()); c.close(); return result

    def post(self, path, data):
        status, _, body = self.request('POST', path, data)
        return status, json.loads(body)

    def project(self):
        status, data = self.post('/api/projects', {'name': 'Synthetic test', 'brief': 'No private footage'})
        self.assertEqual(status, 201)
        return data['id']

    def upload(self, project, name='VID_001.mp4', content=None):
        status, _, body = self.request('POST', f'/api/projects/{project}/upload',
                                      self.source_bytes if content is None else content, {'X-Filename': name})
        self.assertIn(status, (200, 201), body)
        self.engine.q.join()
        return json.loads(body)

    def test_auth_origin_host_and_path_boundaries(self):
        self.assertEqual(self.request('GET', '/api/state', authenticated=False)[0], 403)
        self.assertEqual(self.request('POST', '/api/projects', {'name':'x'}, {'Origin':'https://evil.example'})[0],403)
        self.assertEqual(self.request('GET', '/', headers={'Host':'evil.example'})[0],403)
        p=self.project()
        self.assertEqual(self.request('POST',f'/api/projects/{p}/upload',b'x',{'X-Filename':'../escape.mp4'})[0],400)
        self.assertEqual(self.request('POST',f'/api/projects/{p}/upload',b'x',{'X-Filename':'bad.svg'})[0],400)
        self.assertEqual(self.request('GET','/api/exports/../../etc/passwd')[0],404)

    def test_upload_review_export_download_and_persistence(self):
        p=self.project(); original=self.upload(p); proxy=self.upload(p,'LRV_001.LRV')
        duplicate=self.upload(p)
        self.assertTrue(duplicate['duplicate'])
        self.assertEqual(len(self.engine.store.list('asset',p)),2)
        status,job=self.post(f'/api/projects/{p}/preview',{'asset_id':proxy['id'],'sdr_confirmed':True})
        self.assertEqual(status,202);self.engine.q.join()
        self.assertEqual(self.engine.store.get(job['id'])['status'],'succeeded')
        status,headers,part=self.request('GET',f'/api/assets/{proxy["id"]}/preview',headers={'Range':'bytes=0-99'})
        self.assertEqual(status,206);self.assertEqual(len(part),100)
        self.assertTrue(headers['Content-Range'].startswith('bytes 0-99/'))
        self.assertEqual(self.request('GET',f'/api/assets/{proxy["id"]}/preview',headers={'Range':'bytes=999999999-'})[0],416)
        data={'asset_id':proxy['id'],'original_id':original['id'],'in_seconds':0.2,'out_seconds':1.2,
              'tc_start':'0','sdr_confirmed':True,'reviewed':True,'audio_reviewed':True,
              'alignment_confirmed':True,'chapter':'Trip','category':'reaction','note':'Synthetic tone'}
        self.assertEqual(self.post(f'/api/projects/{p}/selects',dict(data,alignment_confirmed=False))[0],400)
        self.assertEqual(self.post(f'/api/projects/{p}/selects',dict(data,out_seconds=500))[0],400)
        self.assertEqual(self.post(f'/api/projects/{p}/selects',dict(data,audio_reviewed=False))[0],400)
        self.assertEqual(self.post(f'/api/projects/{p}/selects',dict(data,tc_start=''))[0],400)
        other=self.project()
        self.assertEqual(self.post(f'/api/projects/{other}/selects',data)[0],400)
        self.assertEqual(self.post(f'/api/projects/{p}/selects',data)[0],201)
        status,job=self.post(f'/api/projects/{p}/export',{'style':'playful','shape':'portrait'})
        self.assertEqual(status,202);self.engine.q.join()
        finished=self.engine.store.get(job['id']);self.assertEqual(finished['status'],'succeeded',finished)
        export=self.engine.store.list('export',p)[0]
        xml=ET.parse(self.engine.path(export['xml']))
        sources=[r.attrib['src'] for r in xml.iter('media-rep')]
        self.assertTrue(all(s.endswith('VID_001.mp4') for s in sources))
        self.assertFalse(export['receipt']['native_fcp_import'])
        status,headers,video=self.request('GET',f'/api/exports/{export["id"]}/preview?download=1')
        self.assertEqual(status,200);self.assertIn('attachment',headers['Content-Disposition'])
        self.assertEqual(hashlib.sha256(video).hexdigest(),export['receipt']['preview_sha256'])
        self.assertAlmostEqual(export['duration'],1.0,delta=0.15)
        self.assertEqual(self.request('GET',f'/api/exports/{export["id"]}/package')[0],200)
        reopened=Store(self.root/'data')
        self.assertEqual(len(reopened.list('select',p)),1)
        self.assertEqual(self.source.read_bytes(),self.source_bytes)
        self.assertEqual(self.engine.path(original['path']).read_bytes(),self.source_bytes)

    def test_failed_media_and_retry_are_honest(self):
        p=self.project();asset=self.upload(p,'invalid.mp4',b'not video')
        job=self.engine.store.list('job',p)[0]
        self.assertEqual(job['status'],'failed')
        status,retry=self.post(f'/api/projects/{p}/retry',{'job_id':job['id']})
        self.assertEqual(status,202);self.engine.q.join()
        self.assertNotEqual(retry['id'],job['id'])
        self.assertEqual(self.engine.store.get(retry['id'])['status'],'failed')
        self.assertEqual(self.engine.store.list('export',p),[])


if __name__=='__main__':
    unittest.main(verbosity=2)
