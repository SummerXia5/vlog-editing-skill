"""Render configured text to transparent ProRes with a shared typographic baseline."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from media_utils import frac, rgba_movie


def title_frame(spec, index, base):
    w, h = spec['width'], spec['height']
    im = Image.new('RGBA', (w, h))
    d = ImageDraw.Draw(im)
    count = spec['frames']
    fade = max(0, int(spec.get('fade_frames', 6)))
    alpha = min(1, (index + 1) / fade, (count - index) / fade) if fade else 1
    for line in spec['lines']:
        fontpath = (base / line['font']).resolve(strict=True)
        f = ImageFont.truetype(str(fontpath), line['size'], index=line.get('font_index', 0))
        x, baseline = line['x'], line['baseline']
        color = tuple(line.get('color', [255, 255, 255])) + (round(255 * alpha),)
        tracking = line.get('tracking', 0)
        if tracking:
            for char in line['text']:
                d.text((x, baseline), char, font=f, fill=color, anchor='ls')
                x += d.textlength(char, font=f) + tracking
        else:
            d.text((x, baseline), line['text'], font=f, fill=color, anchor='ls')
    return im


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('config', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--ffmpeg')
    a = p.parse_args()
    spec = json.loads(a.config.read_text())
    if min(spec['width'], spec['height'], spec['frames']) <= 0 or frac(spec['fps']) <= 0:
        raise ValueError('Invalid dimensions, duration or frame rate')
    # Validate font access and first frame before opening the encoder.
    first = title_frame(spec, 0, a.config.parent)
    def frames():
        yield first
        for i in range(1, spec['frames']):
            yield title_frame(spec, i, a.config.parent)
    rgba_movie(frames(), a.output, spec['width'], spec['height'], spec['fps'], a.ffmpeg)


if __name__ == '__main__':
    main()
