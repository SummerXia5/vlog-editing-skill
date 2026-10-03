#!/usr/bin/env python3
"""Read-only file inventory. Does not decode media or verify proxy synchronization."""
import argparse
import hashlib
import json
from pathlib import Path

VIDEO = {'.lrv', '.mp4', '.mov', '.m4v', '.mts', '.m2ts', '.insv'}
AUX = {'.wav', '.mp3', '.m4a', '.aac', '.jpg', '.jpeg', '.png', '.heic'}


def inventory(root):
    rows, errors = [], []
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or path.suffix.lower() not in VIDEO | AUX:
            continue
        try:
            if not path.is_file():
                continue
            stat = path.stat()
        except OSError as exc:
            errors.append({'path': str(path), 'error': str(exc)})
            continue
        rel = str(path.relative_to(root))
        rows.append({'clip_id': hashlib.sha256(str(path).encode()).hexdigest()[:16],
                     'path': str(path), 'relative_path': rel, 'extension': path.suffix.lower(),
                     'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns,
                     'review_status': 'unreviewed'})
    originals = {}
    for row in rows:
        if row['extension'] in {'.mp4', '.mov', '.m4v'}:
            originals.setdefault(Path(row['path']).stem.casefold(), []).append(row['path'])
    pairs = []
    for row in rows:
        if row['extension'] != '.lrv':
            continue
        stem = Path(row['path']).stem.casefold()
        keys = {stem}
        if stem.startswith('lrv_'):
            keys.add('vid_' + stem[4:])
        candidates = sorted({p for key in keys for p in originals.get(key, [])})
        pairs.append({'proxy_clip_id': row['clip_id'], 'lrv': row['path'],
                      'candidate_originals': candidates,
                      'status': 'unmatched' if not candidates else 'candidate_unverified' if len(candidates) == 1 else 'ambiguous',
                      'evidence': 'filename_only', 'timing_verified': False})
    return {'schema_version': 1, 'source_root': str(root), 'media_opened': False,
            'files': rows, 'proxy_candidates': pairs, 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    root, output = args.source.expanduser().resolve(), args.output.expanduser().resolve()
    if not root.is_dir():
        parser.error('Source must be an accessible directory')
    if output.is_relative_to(root):
        parser.error('Write the inventory outside the original source directory')
    if output.exists():
        parser.error('Output already exists; choose a new versioned filename')
    data = inventory(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({'files': len(data['files']), 'proxy_candidates': len(data['proxy_candidates']),
                      'errors': len(data['errors']), 'output': str(output)}))


if __name__ == '__main__':
    main()
