"""Animate a supplied map route at arc-length speed, without altering its geography."""
import argparse
import bisect
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw
from media_utils import dump, new_output, rgba_movie


class Route:
    def __init__(self, points):
        self.points, self.arc = [], []
        for x, y in points:
            point = (float(x), float(y))
            if not all(math.isfinite(v) for v in point):
                raise ValueError('Non-finite route point')
            if not self.points:
                self.points.append(point)
                self.arc.append(0.)
            else:
                delta = math.dist(point, self.points[-1])
                if delta > 1e-6:
                    self.points.append(point)
                    self.arc.append(self.arc[-1] + delta)
        if len(self.points) < 2:
            raise ValueError('Route needs two distinct points')

    def sample(self, distance):
        distance = max(0, min(self.arc[-1], distance))
        j = min(len(self.arc) - 1, max(1, bisect.bisect_right(self.arc, distance)))
        t = (distance - self.arc[j-1]) / (self.arc[j] - self.arc[j-1])
        return tuple(a + (b-a)*t for a, b in zip(self.points[j-1], self.points[j]))

    def prefix(self, distance):
        return self.points[:bisect.bisect_left(self.arc, distance)] + [self.sample(distance)]


def motion(route, count, lookahead=20):
    if count < 2 or lookahead <= 0:
        raise ValueError('Need >=2 frames and positive heading lookahead')
    rows, previous = [], None
    for i in range(count):
        t = i / (count-1)
        ease = t*t*t*(t*(t*6-15)+10)
        distance = ease * route.arc[-1]
        a, b = route.sample(distance-lookahead), route.sample(distance+lookahead)
        # PIL positive rotation is counterclockwise; input sprite faces screen-up.
        angle = math.degrees(math.atan2(-(b[0]-a[0]), -(b[1]-a[1])))
        if previous is not None:
            angle = previous + (angle - previous + 180) % 360 - 180
        previous = angle
        rows.append({'frame': i, 'distance': distance, 'position': route.sample(distance),
                     'heading_degrees': angle})
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('config', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--ffmpeg')
    a = p.parse_args()
    spec = json.loads(a.config.read_text())
    if not spec.get('route_source') or not spec.get('geography_verified'):
        raise ValueError('Supply route_source and geography_verified=true after actual map verification')
    base = a.config.parent
    bg = Image.open(base / spec['background']).convert('RGBA')
    car = Image.open(base / spec['sprite']).convert('RGBA')
    car.thumbnail((spec.get('sprite_size', 100), spec.get('sprite_size', 100)))
    # A fixed padded rotation canvas prevents changing icon bounds from jittering its anchor.
    side = math.ceil(math.hypot(*car.size)) + 4
    sprite = Image.new('RGBA', (side, side))
    sprite.alpha_composite(car, ((side-car.width)//2, (side-car.height)//2))
    route = Route(spec['points_px'])
    if any(not (0 <= x < bg.width and 0 <= y < bg.height) for x, y in route.points):
        raise ValueError('Route outside the supplied map canvas')
    rows = motion(route, spec['frames'], spec.get('heading_lookahead_px', 20))
    report = new_output(str(a.output) + '.motion.json')
    def frames():
        for row in rows:
            im = bg.copy()
            points = route.prefix(row['distance'])
            if len(points) > 1:
                ImageDraw.Draw(im).line(points, fill=spec.get('route_color', '#e8cf86'),
                                        width=spec.get('route_width', 5), joint='curve')
            rotated = sprite.rotate(row['heading_degrees'], Image.Resampling.BICUBIC)
            x, y = row['position']
            im.alpha_composite(rotated, (round(x-side/2), round(y-side/2)))
            yield im
    rgba_movie(frames(), a.output, bg.width, bg.height, spec['fps'], a.ffmpeg)
    dump(report, {'route_source': spec['route_source'], 'geometry_modified': False, 'frames': rows})


if __name__ == '__main__':
    main()
