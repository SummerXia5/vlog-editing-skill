#!/usr/bin/env python3
"""Static FCPXML lint only; does not certify DTD validity, timing semantics or FCP import."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
from urllib.parse import urlparse, unquote
import xml.etree.ElementTree as ET


def check(path, allow_missing=False):
    errors, warnings = [], []
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        return {'static_ok': False, 'errors': [str(exc)], 'warnings': [], 'native_import_verified': False}
    if root.tag != 'fcpxml':
        errors.append('Expected fcpxml root')
    if not root.get('version'):
        errors.append('Missing FCPXML version')
    resources = root.find('resources')
    ids = [] if resources is None else [n.get('id') for n in resources if n.get('id')]
    if len(ids) != len(set(ids)):
        errors.append('Duplicate resource IDs')
    known = set(ids) | {n.get('id') for n in root.iter('text-style-def')}
    local_files = set()
    for node in root.iter():
        if node.get('ref') and node.get('ref') not in known:
            errors.append(f'Unresolved ref {node.get("ref")} on {node.tag}')
        for name in ('start', 'offset', 'duration', 'frameDuration'):
            value = node.get(name)
            if value is None:
                continue
            try:
                if not value.endswith('s'):
                    raise ValueError('Expected rational seconds')
                number = Fraction(value[:-1])
                if name == 'duration' and number < 0:
                    raise ValueError('Negative duration')
                if name == 'frameDuration' and number <= 0:
                    raise ValueError('Non-positive frame duration')
            except (ValueError, ZeroDivisionError):
                errors.append(f'Invalid {node.tag}.{name}: {value}')
        # Check asset media only: effect/title src/uid can use built-in identifiers.
        if node.tag not in ('asset', 'media-rep') or not node.get('src'):
            continue
        uri = node.get('src')
        parsed = urlparse(uri)
        media_path = unquote(parsed.path)
        if Path(media_path).suffix.lower() == '.lrv':
            errors.append(f'Analysis proxy referenced in delivery: {uri}')
        if parsed.scheme == 'file' and parsed.netloc in ('', 'localhost'):
            file = Path(media_path)
            local_files.add(str(file))
            if not file.is_absolute():
                errors.append(f'File URI is not absolute: {uri}')
            elif not file.is_file():
                (warnings if allow_missing else errors).append(f'Missing media: {file}')
        else:
            warnings.append(f'Non-local or unsupported media URI needs verification: {uri}')
    sequences = list(root.iter('sequence'))
    if not sequences:
        warnings.append('No project sequence: this may be an event-only import')
    return {'static_ok': not errors, 'resource_count': len(ids), 'sequence_count': len(sequences),
            'local_file_count': len(local_files), 'errors': sorted(set(errors)),
            'warnings': sorted(set(warnings)), 'dtd_verified': False,
            'source_bounds_verified': False, 'native_import_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fcpxml', type=Path)
    parser.add_argument('--allow-missing', action='store_true')
    args = parser.parse_args()
    report = check(args.fcpxml, args.allow_missing)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['static_ok'] else 1)


if __name__ == '__main__':
    main()
