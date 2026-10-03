"""Shared media primitives. No source mutation or implicit uploads."""
import hashlib
import json
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path


def frac(value):
    return Fraction(str(value).removesuffix('s'))


def stamp(value):
    value = frac(value)
    return f'{value.numerator}/{value.denominator}s'


def new_output(path):
    path = Path(path).resolve()
    if path.exists():
        raise ValueError(f'Refusing to overwrite: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def dump(path, value):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def ffmpeg(value=None):
    found = shutil.which(value or 'ffmpeg')
    if not found:
        raise ValueError('Install FFmpeg or supply --ffmpeg /path/to/ffmpeg')
    return found


def probe(path):
    import av
    path = Path(path).resolve(strict=True)
    with av.open(str(path)) as c:
        video = next(iter(c.streams.video), None)
        audio = next(iter(c.streams.audio), None)
        stream = video or audio
        if stream is None:
            raise ValueError(f'No audio/video stream: {path}')
        duration = (Fraction(stream.duration) * stream.time_base
                    if stream.duration is not None else
                    Fraction(c.duration, av.time_base) if c.duration is not None else None)
        if duration is None or duration <= 0:
            raise ValueError(f'Missing finite duration: {path}')
        stat = path.stat()
        return {
            'path': str(path), 'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns,
            'duration_seconds': str(duration),
            'container_timecode': c.metadata.get('timecode'),
            'video': None if video is None else {
                'width': video.width, 'height': video.height,
                'fps': str(video.average_rate or video.guessed_rate),
                'stream_start_seconds': str((video.start_time or 0) * video.time_base),
                'time_base': str(video.time_base), 'codec': video.codec_context.name,
                'pixel_format': video.codec_context.format.name,
                'color_primaries': int(video.codec_context.color_primaries),
                'color_transfer': int(video.codec_context.color_trc),
                'timecode': video.metadata.get('timecode'),
            },
            'audio': None if audio is None else {
                'channels': audio.codec_context.channels,
                'sample_rate': audio.codec_context.sample_rate,
                'codec': audio.codec_context.name,
            },
        }


def rgba_movie(frames, output, width, height, fps, executable):
    """Transparent ProRes 4444; caller supplies full-size RGBA Pillow frames."""
    output = new_output(output)
    cmd = [ffmpeg(executable), '-v', 'error', '-n', '-f', 'rawvideo',
           '-pix_fmt', 'rgba', '-s', f'{width}x{height}', '-r', str(fps), '-i', '-',
           '-an', '-c:v', 'prores_ks', '-profile:v', '4', '-pix_fmt', 'yuva444p10le',
           '-threads', '2', '-color_primaries', 'bt709', '-color_trc', 'bt709',
           '-colorspace', 'bt709', str(output)]
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for frame in frames:
            if frame.mode != 'RGBA' or frame.size != (width, height):
                raise ValueError('Frame format/size mismatch')
            process.stdin.write(frame.tobytes())
        process.stdin.close()
        if process.wait():
            raise RuntimeError('FFmpeg encoding failed; partial output is not a deliverable')
    except BaseException:
        process.kill()
        process.wait()
        raise
