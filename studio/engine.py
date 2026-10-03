"""Local alpha: explicit review decisions -> reproducible editable rough cut.

No automatic dialogue understanding, AI selection, cloud upload, or FCP rendering.
"""
import json
import math
import queue
import shutil
import subprocess
import sys
import threading
import time
import zipfile
from fractions import Fraction
from pathlib import Path

from store import Store, uid

SKILL = Path(__file__).resolve().parents[1] / 'vlog-editing'
sys.path.insert(0, str(SKILL / 'scripts'))
from media_utils import probe, sha256
from build_fcpxml import build

STYLES = {
    'journal': {'name': '旅行手记', 'description': '按你确认的章节和顺序展开，保留体验与互动。'},
    'cinematic': {'name': '风景长诗', 'description': '风景标签优先；保留片段完整长度，不自动快切。'},
    'playful': {'name': '轻快 Vlog', 'description': '互动标签优先；不改对白内容、不自动截断反应。'},
}


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, timeout=900)
    if result.returncode:
        raise ValueError('Media processing failed: ' + result.stderr.decode(errors='replace')[-700:])


class Engine:
    def __init__(self, root, ffmpeg):
        self.store = Store(root)
        self.root = self.store.root
        self.ffmpeg = shutil.which(ffmpeg)
        if not self.ffmpeg:
            raise ValueError('FFmpeg executable not found')
        self.q = queue.Queue()
        self.lock = threading.RLock()
        for job in self.store.list('job'):
            if job['status'] == 'running':
                job.update(status='failed', error='Application restarted during this job. Retry to create a new version.')
                self.store.put('job', job['project_id'], job, job['id'])
            elif job['status'] == 'queued':
                self.q.put(job['id'])
        threading.Thread(target=self.worker, daemon=True).start()

    def enqueue(self, project, task, payload):
        self.store.get(project, 'project')
        job = self.store.put('job', project, {'project_id': project, 'task': task,
                            'payload': payload, 'status': 'queued', 'created_at': time.time()})
        self.q.put(job['id'])
        return job

    def worker(self):
        while True:
            job_id = self.q.get()
            job = self.store.get(job_id, 'job')
            job.update(status='running', started_at=time.time())
            self.store.put('job', job['project_id'], job, job_id)
            try:
                result = getattr(self, 'job_' + job['task'])(job)
                job.update(status='succeeded', result=result)
            except Exception as exc:
                job.update(status='failed', error=str(exc)[:1000])
            job['finished_at'] = time.time()
            self.store.put('job', job['project_id'], job, job_id)
            self.q.task_done()

    def project(self, project_id):
        return dict(self.store.get(project_id, 'project'),
                    assets=self.store.list('asset', project_id),
                    selects=self.store.list('select', project_id),
                    jobs=self.store.list('job', project_id),
                    exports=self.store.list('export', project_id))

    def asset(self, asset_id, project):
        asset = self.store.get(asset_id, 'asset')
        if asset['project_id'] != project:
            raise ValueError('Asset belongs to another project')
        return asset

    def path(self, relative):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError('Invalid storage path')
        return path

    def job_inspect(self, job):
        asset = self.asset(job['payload']['asset_id'], job['project_id'])
        meta = probe(self.path(asset['path']))
        if not meta['video']:
            raise ValueError('A video stream is required')
        meta.pop('path', None)
        asset.update(metadata=meta, duration=float(Fraction(meta['duration_seconds'])), status='ready')
        self.store.put('asset', job['project_id'], asset, asset['id'])
        return {'asset_id': asset['id']}

    def check_sdr(self, asset, confirmed):
        if asset.get('status') != 'ready':
            raise ValueError('Wait for media inspection')
        if asset['metadata']['video']['color_transfer'] in (16, 18):
            raise ValueError('HDR/PQ/HLG requires a reviewed SDR conversion before this alpha can render it')
        if confirmed is not True:
            raise ValueError('Confirm this media is SDR before rendering')

    def job_preview(self, job):
        asset = self.asset(job['payload']['asset_id'], job['project_id'])
        self.check_sdr(asset, job['payload'].get('sdr_confirmed'))
        dest = self.root / 'previews' / (job['id'] + '.mp4')
        dest.parent.mkdir(exist_ok=True)
        # Explicit preview request only; no full original decoding on upload.
        run([self.ffmpeg, '-v', 'error', '-n', '-i', str(self.path(asset['path'])),
             '-vf', 'scale=640:640:force_original_aspect_ratio=decrease:force_divisible_by=2',
             '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '25', '-pix_fmt', 'yuv420p',
             '-c:a', 'aac', '-b:a', '96k', '-movflags', '+faststart', '-threads', '2', str(dest)])
        run([self.ffmpeg, '-v', 'error', '-i', str(dest), '-f', 'null', '-'])
        poster = dest.with_suffix('.jpg')
        run([self.ffmpeg, '-v', 'error', '-n', '-i', str(dest), '-frames:v', '1', str(poster)])
        asset.update(preview=str(dest.relative_to(self.root)), poster=str(poster.relative_to(self.root)))
        self.store.put('asset', job['project_id'], asset, asset['id'])
        return {'asset_id': asset['id']}

    def save_select(self, project, data):
        asset = self.asset(data['asset_id'], project)
        source = self.asset(data.get('original_id') or asset['id'], project)
        if source['is_proxy']:
            raise ValueError('Select an uploaded original for this LRV')
        if asset.get('status') != 'ready' or source.get('status') != 'ready':
            raise ValueError('Media inspection must finish first')
        fps = Fraction(30)
        start, end = float(data['in_seconds']), float(data['out_seconds'])
        if not all(math.isfinite(t) for t in (start, end)):
            raise ValueError('Invalid range')
        first, last = round(start * fps), round(end * fps)
        limit = min(asset['duration'], source['duration'])
        if first < 0 or last <= first or Fraction(last, 30) > Fraction(str(limit)):
            raise ValueError('IN/OUT must fit the source duration and contain at least one frame')
        if asset['is_proxy']:
            if abs(asset['duration'] - source['duration']) > 0.1:
                raise ValueError('Proxy/original duration mismatch exceeds 100 ms; manual conformance required')
            if data.get('alignment_confirmed') is not True:
                raise ValueError('Confirm visual timeline alignment; matching duration alone is not proof')
        tc = str(data.get('tc_start', ''))
        try:
            if Fraction(tc) < 0:
                raise ValueError()
        except (ValueError, ZeroDivisionError):
            raise ValueError('Provide verified source timecode as rational seconds, or explicitly 0 if none')
        if data.get('reviewed') is not True:
            raise ValueError('Review the selected motion before saving')
        if source['metadata']['audio'] and data.get('audio_reviewed') is not True:
            raise ValueError('Listen to the selected audio before saving')
        self.check_sdr(source, data.get('sdr_confirmed'))
        category = data.get('category', 'experience')
        if category not in ('experience', 'reaction', 'scenery', 'detail'):
            raise ValueError('Unknown category')
        row = {'project_id': project, 'asset_id': asset['id'], 'original_id': source['id'],
               'in': first, 'frames': last-first, 'tc_start': tc, 'category': category,
               'chapter': str(data.get('chapter', '旅程'))[:120], 'note': str(data.get('note', ''))[:2000],
               'reviewed': True, 'audio_reviewed': bool(data.get('audio_reviewed')),
               'sdr_confirmed': True, 'alignment_confirmed': bool(data.get('alignment_confirmed')),
               'order': len(self.store.list('select', project))}
        return self.store.put('select', project, row)

    def job_export(self, job):
        project_id = job['project_id']
        # Snapshot is captured when requested, never read a changing timeline during export.
        decisions = job['payload']['selects']
        if not decisions:
            raise ValueError('Add at least one reviewed select')
        style = job['payload']['style']
        if style not in STYLES:
            raise ValueError('Unknown plan')
        if style != 'journal':
            preferred = 'scenery' if style == 'cinematic' else 'reaction'
            decisions = sorted(decisions, key=lambda s: s['category'] != preferred)
        shape = job['payload'].get('shape', 'portrait')
        if shape not in ('portrait', 'landscape'):
            raise ValueError('Unknown aspect ratio')
        width, height = (1080, 1920) if shape == 'portrait' else (1920, 1080)
        out = self.root / 'exports' / job['id']
        out.mkdir(parents=True, exist_ok=False)
        assets, clips = {}, []
        for s in decisions:
            a = self.asset(s['original_id'], project_id)
            self.check_sdr(a, s['sdr_confirmed'])
            if sha256(self.path(a['path'])) != a['sha256']:
                raise ValueError('Uploaded source changed; re-ingest before export')
            key = 'asset_' + a['id']
            if key in assets and Fraction(assets[key]['tc_start']) != Fraction(s['tc_start']):
                raise ValueError('Conflicting source timecodes for the same original; correct the reviewed selects')
            assets[key] = {'path': str(self.path(a['path'])), 'kind': 'original',
                           'tc_start': s['tc_start'], 'color_space': '1-1-1 (Rec. 709)'}
            clips.append({'id': s['id'], 'asset': key, 'in': s['in'], 'frames': s['frames'],
                          'conform': 'fit', 'note': s['chapter'] + ': ' + s['note']})
        spec = {'schema_version': 1, 'project_id': project_id,
                'sequence': {'width': width, 'height': height, 'fps': '30', 'color_space': '1-1-1 (Rec. 709)'},
                'assets': assets, 'timelines': [{'name': 'VLOG_ROUGH_CUT', 'kind': 'master', 'clips': clips}]}
        manifest = out / 'compile.json'
        manifest.write_text(json.dumps(spec, ensure_ascii=False, indent=2))
        build(manifest, out / 'fcp')
        small_w, small_h = (360, 640) if shape == 'portrait' else (640, 360)
        segments = []
        for i, c in enumerate(clips):
            source = assets[c['asset']]['path']
            a = self.asset(c['asset'].removeprefix('asset_'), project_id)
            seg = out / f'segment-{i:04d}.mp4'
            # FFmpeg duration options require decimal seconds, unlike XML rational times.
            seconds = f'{float(Fraction(c["frames"], 30)):.9f}'
            cmd = [self.ffmpeg, '-v', 'error', '-n', '-ss', f'{c["in"]/30:.9f}', '-i', source]
            if not a['metadata']['audio']:
                cmd += ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo']
            cmd += ['-map', '0:v:0', '-map', '0:a:0' if a['metadata']['audio'] else '1:a:0',
                    '-t', seconds, '-vf', f'scale={small_w}:{small_h}:force_original_aspect_ratio=decrease:force_divisible_by=2,pad={small_w}:{small_h}:(ow-iw)/2:(oh-ih)/2,fps=30,setsar=1',
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '24', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-ar', '48000', '-ac', '2', '-af', 'apad', '-threads', '2', str(seg)]
            run(cmd)
            segments.append(seg)
        concat = out / 'concat.txt'
        concat.write_text(''.join(f"file '{p.name}'\n" for p in segments))
        preview = out / 'preview.mp4'
        run([self.ffmpeg, '-v', 'error', '-n', '-f', 'concat', '-safe', '1', '-i', str(concat),
             '-c', 'copy', '-movflags', '+faststart', str(preview)])
        run([self.ffmpeg, '-v', 'error', '-i', str(preview), '-f', 'null', '-'])
        expected = sum(c['frames'] for c in clips)/30
        actual = float(Fraction(probe(preview)['duration_seconds']))
        if abs(actual-expected) > 0.15:
            raise ValueError('Preview duration verification failed')
        receipt = {'job_id': job['id'], 'style': style, 'ordering': 'tag-based template, not AI planning',
                   'sources': [{'name': self.asset(s['original_id'], project_id)['name'],
                                'sha256': self.asset(s['original_id'], project_id)['sha256']} for s in decisions],
                   'duration_seconds': actual, 'preview_sha256': sha256(preview),
                   'preview_full_decode': True, 'native_fcp_import': False,
                   'automatic_transcription': False, 'cloud_published': False,
                   'reviewed_selects': decisions}
        (out / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2))
        (out / 'READ_ME.txt').write_text('Editable rough cut alpha. No music, generated graphics, or final grade added.\n'
            'FCPXML references uploaded originals on this machine. Relink original files by name on another Mac.\n'
            'The MP4 is a straight-cut review render, not a verified Final Cut export. Native import remains unverified.\n')
        package = out / 'edit-package.zip'
        with zipfile.ZipFile(package, 'x', zipfile.ZIP_DEFLATED) as z:
            for p in [manifest, out/'receipt.json', out/'READ_ME.txt', *sorted((out/'fcp').glob('*'))]:
                z.write(p, str(p.relative_to(out)))
        for p in segments:
            p.unlink()  # Generated temporary segments only; uploaded sources remain unchanged.
        record = self.store.put('export', project_id, {'project_id': project_id, 'job_id': job['id'],
            'style': style, 'duration': actual, 'created_at': time.time(),
            'preview': str(preview.relative_to(self.root)), 'package': str(package.relative_to(self.root)),
            'xml': str((out/'fcp/VLOG_ROUGH_CUT.fcpxml').relative_to(self.root)), 'receipt': receipt})
        return {'export_id': record['id']}
