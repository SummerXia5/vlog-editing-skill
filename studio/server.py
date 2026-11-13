#!/usr/bin/env python3
"""Single-user loopback alpha. Not a public Internet deployment server."""
import argparse
import hashlib
import json
import mimetypes
import os
import re
import secrets
import socket
import threading
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from engine import Engine, STYLES
from store import uid

STATIC = Path(__file__).parent / 'static'
EXTENSIONS = {'.mp4', '.mov', '.lrv', '.m4v'}
MAX_FILE = 2 * 1024**3
MAX_STORAGE = 20 * 1024**3


class StudioServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, engine):
        if address[0] != '127.0.0.1':
            raise ValueError('This alpha may only bind to 127.0.0.1')
        self.engine = engine
        self.token = secrets.token_urlsafe(32)
        self.upload_lock = threading.Lock()
        super().__init__(address, Handler)
        self.origin = f'http://127.0.0.1:{self.server_port}'


class Handler(BaseHTTPRequestHandler):
    server_version = 'VlogStudio/0.1'

    def setup(self):
        super().setup()
        self.connection.settimeout(60)

    def log_message(self, fmt, *args):
        # No filenames, query strings, cookies, or file paths in request logs.
        pass

    def headers_common(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")

    def send_json(self, value, code=200):
        body = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(code)
        self.headers_common()
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        try:
            cookies = SimpleCookie(self.headers.get('Cookie', ''))
            token = cookies['studio_session'].value if 'studio_session' in cookies else ''
            return secrets.compare_digest(token, self.server.token)
        except Exception:
            return False

    def guard(self, write=False):
        if self.headers.get('Host') != urlsplit(self.server.origin).netloc:
            raise PermissionError('Invalid Host; use the printed 127.0.0.1 URL')
        if not self.authorized():
            raise PermissionError('Open the local Studio page first')
        if write and (self.headers.get('Origin') != self.server.origin or
                      self.headers.get('X-Studio-Request') != '1'):
            raise PermissionError('Same-origin Studio request required')

    def body_json(self):
        n = int(self.headers.get('Content-Length', '0'))
        if not 0 < n <= 1024 * 128:
            raise ValueError('Invalid JSON body length')
        result = json.loads(self.rfile.read(n))
        if not isinstance(result, dict):
            raise ValueError('Object body required')
        return result

    def do_GET(self):
        try:
            self.get()
        except PermissionError as e:
            self.send_json({'error': str(e)}, 403)
        except (ValueError, KeyError, FileNotFoundError) as e:
            self.send_json({'error': str(e)}, 400)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            self.send_json({'error': 'Unexpected server error. Check local setup.'}, 500)

    def get(self):
        path = urlsplit(self.path).path
        if self.headers.get('Host') != urlsplit(self.server.origin).netloc:
            raise PermissionError('Invalid Host')
        if path in ('/', '/app.js', '/style.css'):
            target = STATIC / ('index.html' if path == '/' else path[1:])
            self.send_file(target, cookie=(path == '/'))
            return
        self.guard()
        engine = self.server.engine
        if path == '/api/state':
            self.send_json({'projects': engine.store.list('project'), 'styles': STYLES,
                            'mode': 'local-alpha', 'max_file_bytes': MAX_FILE,
                            'capabilities': {'ai_review': False, 'billing': False, 'hosting': False}})
        elif re.fullmatch(r'/api/projects/[a-f0-9]{32}', path):
            self.send_json(engine.project(path.split('/')[-1]))
        elif re.fullmatch(r'/api/assets/[a-f0-9]{32}/(preview|poster)', path):
            _, _, _, asset_id, kind = path.split('/')
            asset = engine.store.get(asset_id, 'asset')
            self.send_file(engine.path(asset[kind]))
        elif re.fullmatch(r'/api/exports/[a-f0-9]{32}/(preview|package|xml)', path):
            _, _, _, export_id, kind = path.split('/')
            export = engine.store.get(export_id, 'export')
            query = parse_qs(urlsplit(self.path).query)
            self.send_file(engine.path(export[kind]), download=(kind != 'preview' or 'download' in query))
        else:
            self.send_json({'error': 'Not found'}, 404)

    def send_file(self, path, download=False, cookie=False):
        if not path.is_file():
            raise FileNotFoundError('File not ready')
        size, start, end = path.stat().st_size, 0, path.stat().st_size - 1
        partial = self.headers.get('Range')
        if partial:
            match = re.fullmatch(r'bytes=(\d*)-(\d*)', partial)
            if not match or not any(match.groups()):
                self.send_response(416); self.send_header('Content-Range', f'bytes */{size}'); self.end_headers(); return
            a, b = match.groups()
            if a:
                start, end = int(a), min(int(b) if b else size-1, size-1)
            else:
                start = max(0, size-int(b))
            if start > end or start >= size:
                self.send_response(416); self.send_header('Content-Range', f'bytes */{size}'); self.end_headers(); return
        self.send_response(206 if partial else 200)
        self.headers_common()
        self.send_header('Content-Type', mimetypes.guess_type(path.name)[0] or 'application/octet-stream')
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(end-start+1))
        if partial:
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        if download:
            self.send_header('Content-Disposition', f'attachment; filename="{path.name}"')
        if cookie:
            self.send_header('Set-Cookie', f'studio_session={self.server.token}; HttpOnly; SameSite=Strict; Path=/')
        self.end_headers()
        with path.open('rb') as f:
            f.seek(start)
            remaining = end-start+1
            while remaining > 0:
                b = f.read(min(1024*1024, remaining))
                if not b:
                    break
                self.wfile.write(b)
                remaining -= len(b)

    def do_POST(self):
        try:
            self.guard(write=True)
            self.post()
        except PermissionError as e:
            self.send_json({'error': str(e)}, 403)
        except (ValueError, KeyError, FileNotFoundError) as e:
            self.send_json({'error': str(e)}, 400)
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            pass
        except Exception:
            self.send_json({'error': 'Unexpected server error. Your existing media is unchanged.'}, 500)

    def post(self):
        engine = self.server.engine
        path = urlsplit(self.path).path
        if path == '/api/projects':
            data = self.body_json()
            name = str(data.get('name', '')).strip()[:100]
            if not name:
                raise ValueError('Project name is required')
            record = engine.store.put('project', '', {'name': name, 'brief': str(data.get('brief', ''))[:4000]})
            self.send_json(record, 201)
            return
        match = re.fullmatch(r'/api/projects/([a-f0-9]{32})/(upload|selects|preview|export|retry|remove-select)', path)
        if not match:
            self.send_json({'error': 'Not found'}, 404); return
        project, action = match.groups()
        engine.store.get(project, 'project')
        if action == 'upload':
            self.upload(project)
            return
        data = self.body_json()
        if action == 'selects':
            self.send_json(engine.save_select(project, data), 201)
        elif action == 'preview':
            engine.asset(data['asset_id'], project)
            self.send_json(engine.enqueue(project, 'preview', data), 202)
        elif action == 'export':
            selects = engine.store.list('select', project)
            if not selects or len(selects) > 150:
                raise ValueError('Choose between 1 and 150 reviewed selects')
            if data.get('style') not in STYLES or data.get('shape') not in ('portrait', 'landscape'):
                raise ValueError('Choose an available plan and aspect ratio')
            if sum(s['frames'] for s in selects) > 30*60*30:
                raise ValueError('This alpha supports rough cuts up to 30 minutes')
            self.send_json(engine.enqueue(project, 'export', dict(data, selects=selects)), 202)
        elif action == 'retry':
            old = engine.store.get(data['job_id'], 'job')
            if old['project_id'] != project or old['status'] != 'failed':
                raise ValueError('Only failed jobs in this project may be retried')
            self.send_json(engine.enqueue(project, old['task'], old['payload']), 202)
        elif action == 'remove-select':
            select = engine.store.get(data['select_id'], 'select')
            if select['project_id'] != project:
                raise ValueError('Select belongs to another project')
            engine.store.delete(select['id'], 'select')
            self.send_json({'removed': True})

    def upload(self, project):
        engine = self.server.engine
        name = unquote(self.headers.get('X-Filename', ''))
        if not name or '/' in name or '\\' in name or any(ord(c) < 32 for c in name) or len(name) > 180:
            raise ValueError('Provide a simple filename')
        if Path(name).suffix.lower() not in EXTENSIONS:
            raise ValueError('Upload MP4, MOV, M4V or LRV video')
        length = int(self.headers.get('Content-Length', '0'))
        if not 0 < length <= MAX_FILE or self.headers.get('Transfer-Encoding'):
            raise ValueError('Each upload must be between 1 byte and 2 GiB')
        with self.server.upload_lock:
            usage = sum(p.stat().st_size for p in engine.root.rglob('*') if p.is_file())
            if usage + length > MAX_STORAGE:
                raise ValueError('Local alpha storage limit (20 GiB) reached')
            directory = engine.root/'uploads'/project/uid()
            directory.mkdir(parents=True)
            partial, dest = directory/'upload.part', directory/name
            h = hashlib.sha256()
            try:
                with partial.open('xb') as f:
                    left = length
                    while left:
                        block = self.rfile.read(min(left, 1024*1024))
                        if not block:
                            raise ValueError('Upload interrupted; retry this file')
                        f.write(block); h.update(block); left -= len(block)
                digest = h.hexdigest()
                duplicate = next((a for a in engine.store.list('asset', project)
                                  if a['sha256'] == digest and a['name'] == name), None)
                if duplicate:
                    partial.unlink(); directory.rmdir()
                    self.send_json(dict(duplicate, duplicate=True)); return
                os.replace(partial, dest)
                asset = engine.store.put('asset', project, {'project_id': project, 'name': name,
                    'path': str(dest.relative_to(engine.root)), 'sha256': digest, 'bytes': length,
                    'is_proxy': dest.suffix.lower() == '.lrv', 'status': 'pending', 'review_status': 'unreviewed'})
                engine.enqueue(project, 'inspect', {'asset_id': asset['id']})
                self.send_json(asset, 201)
            except Exception:
                if partial.exists():
                    partial.unlink()
                raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=Path.home()/'.vlog-studio')
    parser.add_argument('--port', type=int, default=4318)
    parser.add_argument('--ffmpeg', default='ffmpeg')
    args = parser.parse_args()
    engine = Engine(args.data, args.ffmpeg)
    server = StudioServer(('127.0.0.1', args.port), engine)
    print('Vlog Editing Studio · local alpha · ' + server.origin, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == '__main__':
    main()
