"""Compile original-media cuts, connected graphics and audio to FCPXML 1.10 + CSV.

All in/frames/at values use the sequence frame grid. Asset tc_start is an explicit
rational number of seconds, independent of container PTS. Unsupported edits fail.
"""
import argparse
import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from media_utils import dump, frac, probe, stamp


def only(obj, keys, context):
    unexpected = set(obj) - set(keys.split())
    if unexpected:
        raise ValueError(f'Unsupported {context} fields: {sorted(unexpected)}')


def integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'Expected integer >= {minimum}: {value}')
    return value


def build(manifest, output, dtd=None):
    manifest, output = Path(manifest).resolve(), Path(output).resolve()
    data = json.loads(manifest.read_text())
    only(data, 'schema_version project_id sequence assets timelines', 'manifest')
    if data['schema_version'] != 1:
        raise ValueError('Unknown compilation schema')
    if output.exists():
        raise ValueError(f'Output version already exists: {output}')
    seq = data['sequence']
    only(seq, 'width height fps color_space', 'sequence')
    fps = frac(seq['fps'])
    if fps <= 0 or min(integer(seq['width'], 1), integer(seq['height'], 1)) <= 0:
        raise ValueError('Invalid sequence')
    fd = 1 / fps
    if not seq.get('color_space'):
        raise ValueError('Explicit sequence color_space required')
    metadata, asset_specs = {}, data['assets']
    for key, spec in asset_specs.items():
        only(spec, 'path kind tc_start color_space', 'asset')
        path = (manifest.parent / spec['path']).resolve(strict=True)
        if path.suffix.lower() == '.lrv':
            raise ValueError('LRV proxies may not be used as editing resources')
        if spec['kind'] not in ('original', 'generated'):
            raise ValueError('Asset kind must be original or generated')
        frac(spec['tc_start'])  # Required; no silent timecode=0 assumption.
        meta = probe(path)
        if meta['video'] and not spec.get('color_space'):
            raise ValueError('Specify each video asset color_space after inspection')
        metadata[key] = meta
    if not data['timelines']:
        raise ValueError('No timelines')
    results = []
    names = set()
    for timeline in data['timelines']:
        only(timeline, 'name kind clips audio', 'timeline')
        name = timeline['name']
        if not name or Path(name).name != name or '/' in name or '\\' in name or name in names:
            raise ValueError('Unique filename-safe timeline names required')
        names.add(name)
        if timeline['kind'] not in ('selects', 'master'):
            raise ValueError('Timeline kind must be selects or master')
        if not timeline['clips']:
            raise ValueError('Empty timeline')
        root = ET.Element('fcpxml', version='1.10')
        resources = ET.SubElement(root, 'resources')
        ET.SubElement(resources, 'format', id='r1', width=str(seq['width']),
                      height=str(seq['height']), frameDuration=stamp(fd),
                      colorSpace=seq['color_space'])
        refs = {}
        for index, (key, meta) in enumerate(metadata.items(), 1):
            spec = asset_specs[key]
            ref = f'r{index*2}'
            refs[key] = ref
            attrs = dict(id=ref, name=Path(meta['path']).name,
                         start=stamp(spec['tc_start']), duration=stamp(meta['duration_seconds']))
            if meta['video']:
                video = meta['video']
                fmt = f'r{index*2+1}'
                ET.SubElement(resources, 'format', id=fmt, width=str(video['width']),
                              height=str(video['height']), frameDuration=stamp(1/frac(video['fps'])),
                              colorSpace=spec['color_space'])
                attrs.update(hasVideo='1', format=fmt)
            if meta['audio']:
                audio = meta['audio']
                attrs.update(hasAudio='1', audioSources='1', audioChannels=str(audio['channels']),
                             audioRate=str(audio['sample_rate']))
            asset = ET.SubElement(resources, 'asset', **attrs)
            ET.SubElement(asset, 'media-rep', kind='original-media', src=Path(meta['path']).as_uri())
        library = ET.SubElement(root, 'library')
        event = ET.SubElement(library, 'event', name=data['project_id'])
        project = ET.SubElement(event, 'project', name=name)
        total = sum(integer(c['frames'], 1) for c in timeline['clips'])
        sequence = ET.SubElement(project, 'sequence', format='r1', duration=stamp(total*fd),
                                 tcStart='0s', tcFormat='NDF', audioLayout='stereo', audioRate='48k')
        ET.SubElement(sequence, 'note').text = 'Draft generated from compilation manifest; native FCP import unverified.'
        spine = ET.SubElement(sequence, 'spine')
        rows, ids, cursor, first_node, first_start = [], set(), 0, None, None

        def bounds(item):
            key = item['asset']
            meta = metadata[key]
            relative = integer(item.get('in', 0)) * fd
            duration = integer(item['frames'], 1) * fd
            if relative + duration > frac(meta['duration_seconds']):
                raise ValueError(f'Source range exceeds duration: {key}')
            return key, frac(asset_specs[key]['tc_start']) + relative, duration

        def row(item, kind, at, start, duration):
            key = item['asset']
            rows.append({'instance_id': item.get('id', ''), 'kind': kind, 'asset': key,
                         'path': metadata[key]['path'], 'source_in_seconds': str(integer(item.get('in', 0))*fd),
                         'source_out_seconds': str(integer(item.get('in', 0))*fd+duration),
                         'source_timecode_start_seconds': str(start), 'timeline_in_seconds': str(at),
                         'timeline_out_seconds': str(at+duration), 'role': item.get('role', ''),
                         'gain_db': item.get('gain_db', 0), 'note': item.get('note', '')})

        for clip in timeline['clips']:
            only(clip, 'id asset in frames audio_enabled gain_db conform overlays note', 'clip')
            if not clip.get('id') or clip['id'] in ids:
                raise ValueError('Unique clip id required per timeline')
            ids.add(clip['id'])
            key, start, duration = bounds(clip)
            if not metadata[key]['video']:
                raise ValueError('Primary storyline clips need video')
            conform = clip.get('conform', 'fit')
            if conform not in ('fit', 'fill', 'none'):
                raise ValueError('Unsupported conform; use fit or explicitly planned fill/none')
            node = ET.SubElement(spine, 'asset-clip', ref=refs[key], name=clip['id'],
                                 offset=stamp(cursor*fd), start=stamp(start), duration=stamp(duration),
                                 srcEnable='all' if clip.get('audio_enabled', True) else 'video')
            if clip.get('note'):
                ET.SubElement(node, 'note').text = clip['note']
            ET.SubElement(node, 'adjust-conform', type=conform)
            if 'gain_db' in clip:
                ET.SubElement(node, 'adjust-volume', amount=f"{float(clip['gain_db'])}dB")
            if first_node is None:
                first_node, first_start = node, start
            for overlay in clip.get('overlays', []):
                only(overlay, 'id asset in frames at lane role note', 'overlay')
                okey, ostart, oduration = bounds(overlay)
                at = integer(overlay.get('at', 0))*fd
                if at+oduration > duration or not metadata[okey]['video']:
                    raise ValueError('Overlay must have video and fit its parent duration')
                ov = ET.SubElement(node, 'video', ref=refs[okey], name=overlay.get('id', okey),
                                   offset=stamp(start+at), start=stamp(ostart), duration=stamp(oduration),
                                   lane=str(integer(overlay.get('lane', 1), 1)), role=overlay.get('role', 'titles'))
                if overlay.get('note'):
                    ET.SubElement(ov, 'note').text = overlay['note']
                ET.SubElement(ov, 'adjust-conform', type='fit')
                row(overlay, 'overlay', cursor*fd+at, ostart, oduration)
            row(clip, 'picture', cursor*fd, start, duration)
            cursor += clip['frames']
        for index, audio in enumerate(timeline.get('audio', []), 1):
            only(audio, 'id asset in frames at role gain_db note', 'audio')
            key, start, duration = bounds(audio)
            at = integer(audio.get('at', 0))*fd
            if at+duration > total*fd or not metadata[key]['audio']:
                raise ValueError('Audio needs an audio stream and must fit the sequence')
            node = ET.SubElement(first_node, 'audio', ref=refs[key], name=audio.get('id', key),
                                 lane=str(-index), offset=stamp(first_start+at), start=stamp(start),
                                 duration=stamp(duration), role=audio.get('role', 'music'))
            if audio.get('note'):
                ET.SubElement(node, 'note').text = audio['note']
            ET.SubElement(node, 'adjust-volume', amount=f"{float(audio.get('gain_db', 0))}dB")
            row(audio, 'audio', at, start, duration)
        ET.indent(root)
        xml = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        if dtd:
            from lxml import etree
            with Path(dtd).open('rb') as handle:
                validator = etree.DTD(handle)
            if not validator.validate(etree.fromstring(xml)):
                raise ValueError(str(validator.error_log))
        results.append((name, xml, rows, total))
    # Validate every timeline before writing any deliverable.
    output.mkdir(parents=True, exist_ok=False)
    for name, xml, rows, total in results:
        (output / (name+'.fcpxml')).write_bytes(xml)
        with (output / (name+'.csv')).open('x', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    dump(output/'build.json', {'schema_version': 1, 'manifest': data, 'media_probes': metadata,
                              'dtd_validated': bool(dtd), 'native_import_verified': False,
                              'render_verified': False,
                              'timelines': [{'name': n, 'frames': f} for n, _, _, f in results]})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--dtd', type=Path)
    a = p.parse_args()
    build(a.manifest, a.output, a.dtd)


if __name__ == '__main__':
    main()
