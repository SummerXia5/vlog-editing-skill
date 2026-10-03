"""Synthetic integration test: no personal media, FCP import or publication needed."""
import argparse
import copy
import json
import math
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from media_utils import frac, probe, sha256
from render_route import Route, motion


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ffmpeg', required=True)
    p.add_argument('--font', required=True, help='Installed font path (prefer CJK)')
    p.add_argument('--dtd')
    p.add_argument('--report', type=Path, required=True)
    args = p.parse_args()
    checks = []
    if args.report.exists():
        raise ValueError('Report exists')
    def run(script, *extra, fail=False):
        result = subprocess.run([sys.executable, str(SCRIPTS/script), *map(str, extra)],
                                capture_output=True, text=True)
        if fail:
            assert result.returncode != 0, result.stdout
        elif result.returncode:
            raise RuntimeError(result.stderr)
        return result
    with tempfile.TemporaryDirectory(prefix='vlog-tools-test-') as temporary:
        root = Path(temporary)
        source = root/'原片.mp4'
        subprocess.run([args.ffmpeg, '-v', 'error', '-n', '-f', 'lavfi', '-i',
                        'testsrc2=size=160x240:rate=30000/1001:duration=3.003',
                        '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000:duration=3.003',
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac',
                        '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
                        str(source)], check=True)
        original_hash = sha256(source)
        proxy = root/'原片.LRV'
        proxy.write_bytes(source.read_bytes())
        run('review_media.py', proxy, '--compare-original', source, '--times', '0', '1', '2',
            '--output', root/'review')
        review = json.loads((root/'review/review.json').read_text())
        assert review['pair_check']['duration_delta_seconds'] == '0'
        assert review['audio_audition'] is False
        assert review['pair_check']['visual_alignment_verified'] is False
        checks.append('proxy/original timed samples and honest unverified review state')

        title = {'width': 160, 'height': 240, 'frames': 30, 'fps': '30000/1001',
                 'lines': [{'text': '一路向北', 'font': args.font, 'size': 20,
                            'x': 10, 'baseline': 130, 'tracking': 3}]}
        (root/'title.json').write_text(json.dumps(title))
        run('render_title.py', root/'title.json', '--output', root/'title.mov', '--ffmpeg', args.ffmpeg)
        assert 'a' in probe(root/'title.mov')['video']['pixel_format']
        import av
        with av.open(str(root/'title.mov')) as c:
            frame = next(c.decode(video=0)).to_ndarray(format='rgba')
            assert frame[0, 0, 3] == 0
        checks.append('transparent ProRes title with CJK tracking')

        from PIL import Image, ImageDraw
        Image.new('RGBA', (160, 240), '#224d40').save(root/'map.png')
        sprite = Image.new('RGBA', (20, 30))
        ImageDraw.Draw(sprite).polygon([(10, 0), (20, 30), (0, 30)], fill='white')
        sprite.save(root/'sprite.png')
        points = [[20, 200], [20, 200], [40, 160], [80, 100], [100, 30]]
        route = {'background': 'map.png', 'sprite': 'sprite.png', 'sprite_size': 18,
                 'frames': 30, 'fps': '30000/1001', 'points_px': points,
                 'route_source': 'synthetic test geometry, not a real destination',
                 'geography_verified': True}
        (root/'route.json').write_text(json.dumps(route))
        run('render_route.py', root/'route.json', '--output', root/'route.mov', '--ffmpeg', args.ffmpeg)
        rows = motion(Route(points), 90)
        assert rows[0]['position'] == tuple(points[0]) and rows[-1]['position'] == tuple(points[-1])
        assert all(b['distance'] >= a['distance'] for a, b in zip(rows, rows[1:]))
        north = motion(Route([[0, 100], [0, 0]]), 30)
        east = motion(Route([[0, 0], [100, 0]]), 30)
        assert abs(north[0]['heading_degrees']) < 1e-6
        assert abs(east[0]['heading_degrees'] + 90) < 1e-6
        checks.append('route endpoints, monotone distance, duplicate points, north/east sprite headings')

        manifest = {'schema_version': 1, 'project_id': 'Synthetic Test',
                    'sequence': {'width': 160, 'height': 240, 'fps': '30000/1001',
                                 'color_space': '1-1-1 (Rec. 709)'},
                    'assets': {'camera': {'path': '原片.mp4', 'kind': 'original', 'tc_start': '3600',
                                          'color_space': '1-1-1 (Rec. 709)'},
                               'title': {'path': 'title.mov', 'kind': 'generated', 'tc_start': '0',
                                         'color_space': '1-1-1 (Rec. 709)'}},
                    'timelines': [{'name': 'TEST_MASTER', 'kind': 'master',
                                   'clips': [{'id': 'A', 'asset': 'camera', 'in': 15, 'frames': 45,
                                              'audio_enabled': False,
                                              'overlays': [{'asset': 'title', 'at': 5, 'in': 0, 'frames': 30}]},
                                             {'id': 'B', 'asset': 'camera', 'in': 0, 'frames': 30}],
                                   'audio': [{'asset': 'camera', 'at': 20, 'in': 0, 'frames': 40,
                                              'gain_db': -12, 'role': 'music'}]}]}
        manifest['timelines'].append({'name': 'TEST_SELECTS', 'kind': 'selects',
                                      'clips': [{'id': 'S1', 'asset': 'camera', 'in': 0, 'frames': 60}]})
        path = root/'compile.json'
        path.write_text(json.dumps(manifest))
        dtd_args = ['--dtd', args.dtd] if args.dtd else []
        run('build_fcpxml.py', path, '--output', root/'fcp', *dtd_args)
        xml = ET.parse(root/'fcp/TEST_MASTER.fcpxml')
        clip = xml.find('.//spine/asset-clip')
        fd = frac('1001/30000')
        assert frac(clip.get('start')) == 3600+15*fd
        assert frac(clip.find('video').get('offset')) == 3600+20*fd
        assert frac(clip.find('audio').get('offset')) == 3600+35*fd
        assert frac(xml.find('.//sequence').get('duration')) == 75*fd
        checks.append('29.97 rational timing, nonzero TC, repeated sources, connected graphics/audio, selects/master')
        if args.dtd:
            checks.append('Apple FCPXML 1.10 DTD for both timelines')
        bads = []
        b = copy.deepcopy(manifest); b['assets']['camera']['path'] = '原片.LRV'; bads.append(b)
        b = copy.deepcopy(manifest); b['timelines'][0]['clips'][0]['frames'] = 1000; bads.append(b)
        b = copy.deepcopy(manifest); b['timelines'][0]['clips'][0]['speed'] = 2; bads.append(b)
        b = copy.deepcopy(manifest); del b['assets']['camera']['tc_start']; bads.append(b)
        for b in bads:
            path.write_text(json.dumps(b))
            run('build_fcpxml.py', path, '--output', root/'invalid', fail=True)
            assert not (root/'invalid').exists()
        path.write_text(json.dumps(manifest))
        run('build_fcpxml.py', path, '--output', root/'fcp', fail=True)
        checks.append('reject LRV, out-of-bounds ranges, unsupported speed, missing TC, overwrite')

        run('make_preview.py', source, '--output', root/'preview.mp4', '--ffmpeg', args.ffmpeg,
            '--sdr-confirmed', '--long-edge', '240', '--start', '0.5', '--duration', '1')
        receipt = json.loads((root/'preview.mp4.json').read_text())
        assert receipt['sha256'] == sha256(root/'preview.mp4') and receipt['full_decode_verified']
        assert not receipt['hosted'] and not receipt['audio_audition']
        assert sha256(source) == original_hash
        checks.append('H264/AAC source-window preview, full decode/hash, originals unchanged')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps({'passed': True, 'checks': checks, 'native_fcp_import': False,
                                       'publication_tested': False}, indent=2)+'\n')
    print(args.report.read_text())


if __name__ == '__main__':
    main()
