"""Probe a selected file; extract timed frames without claiming human review."""
import argparse
import json
from pathlib import Path
from media_utils import dump, frac, probe


def sample(path, output, times):
    import av
    rows = []
    with av.open(str(path)) as c:
        s = c.streams.video[0]
        origin = (s.start_time or 0) * s.time_base
        for i, requested in enumerate(times):
            target = origin + frac(requested)
            c.seek(int(target / s.time_base), stream=s, backward=True)
            for frame in c.decode(s):
                if frame.pts is None:
                    continue
                actual = frame.pts * frame.time_base
                if actual + s.time_base / 2 >= target:
                    name = f'frame_{i:03d}.jpg'
                    im = frame.to_image()
                    im.thumbnail((960, 960))
                    im.save(output / name, quality=90)
                    rows.append({'requested_seconds': str(requested),
                                 'actual_seconds': str(actual - origin), 'image': name})
                    break
            else:
                raise ValueError(f'No frame at {requested} seconds')
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--times', nargs='+', default=['0', '1'])
    p.add_argument('--compare-original', type=Path,
                   help='Explicit opt-in to probe/sample this candidate original')
    a = p.parse_args()
    sources = [a.source] + ([a.compare_original] if a.compare_original else [])
    metadata = [probe(s) for s in sources]
    times = [frac(t) for t in a.times]
    if any(t < 0 or t >= frac(m['duration_seconds']) for m in metadata for t in times):
        raise ValueError('Requested sample outside source duration')
    a.output.mkdir(parents=True, exist_ok=False)
    report = {'review_status': 'sampled_stills_only', 'human_motion_review': False,
              'audio_audition': False, 'sources': []}
    for i, (path, meta) in enumerate(zip(sources, metadata)):
        folder = a.output / str(i)
        folder.mkdir()
        report['sources'].append({'metadata': meta, 'samples': sample(path, folder, times)})
    if len(metadata) == 2:
        difference = abs(frac(metadata[0]['duration_seconds']) - frac(metadata[1]['duration_seconds']))
        report['pair_check'] = {'duration_delta_seconds': str(difference),
                                'visual_alignment_verified': False,
                                'pairing_status': 'candidate_needs_visual_comparison'}
    dump(a.output / 'review.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
