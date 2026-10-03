"""Transcode a finished SDR export or explicit source window; verify full decode + hash."""
import argparse
import subprocess
from pathlib import Path
from media_utils import dump, ffmpeg, frac, new_output, probe, sha256


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--ffmpeg')
    p.add_argument('--long-edge', type=int, default=960)
    p.add_argument('--crf', type=int, default=23)
    p.add_argument('--start', default='0')
    p.add_argument('--duration', help='Optional source-window duration, seconds')
    p.add_argument('--sdr-confirmed', action='store_true', required=True,
                   help='Only set after verifying SDR input; this tool does not tone-map HDR')
    a = p.parse_args()
    if a.long_edge < 16 or a.long_edge % 2 or not 0 <= a.crf <= 51:
        raise ValueError('Even long-edge >=16 and CRF 0..51 required')
    meta = probe(a.source)
    if not meta['video'] or meta['video']['color_transfer'] in (16, 18):
        raise ValueError('Requires SDR video. Tone-map PQ/HLG in a color-managed pipeline first.')
    source_duration = frac(meta['duration_seconds'])
    start = frac(a.start)
    duration = frac(a.duration) if a.duration else source_duration-start
    if start < 0 or duration <= 0 or start+duration > source_duration:
        raise ValueError('Requested source window out of bounds')
    output = new_output(a.output)
    receipt = new_output(str(output)+'.json')
    binary = ffmpeg(a.ffmpeg)
    command = [binary, '-v', 'error', '-n', '-ss', str(float(start)), '-i', str(a.source),
               '-t', str(float(duration)), '-map', '0:v:0', '-map', '0:a:0?',
               '-vf', f'scale={a.long_edge}:{a.long_edge}:force_original_aspect_ratio=decrease:force_divisible_by=2,setsar=1',
               '-c:v', 'libx264', '-crf', str(a.crf), '-preset', 'medium', '-pix_fmt', 'yuv420p',
               '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', str(output)]
    subprocess.run(command, check=True)
    subprocess.run([binary, '-v', 'error', '-xerror', '-i', str(output),
                    '-map', '0:v:0', '-map', '0:a:0?', '-f', 'null', '-'], check=True)
    result = probe(output)
    tolerance = max(frac('1/10'), 2/frac(result['video']['fps']))
    if abs(frac(result['duration_seconds'])-duration) > tolerance:
        raise ValueError('Preview duration mismatch; do not deliver without inspection')
    dump(receipt, {'source': meta, 'source_in_seconds': str(start), 'source_out_seconds': str(start+duration),
                   'preview': result, 'sha256': sha256(output), 'full_decode_verified': True,
                   'visual_review': False, 'audio_audition': False,
                   'hosted': False, 'browser_download_verified': False})
    print(output)


if __name__ == '__main__':
    main()
