#!/usr/bin/env python3
"""Offline prototype: five owned JSON files -> the existing static dashboard.
No network, Git operation, deployment, routine change, or pending-data ingestion.
The existing literal-only parser is used once to preserve the published baseline.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

BASELINE_BLOB = 'f72b8a4e69bfea39c71747b5c7300e070b765d07'
# Exact 27-record snapshot only; --init rejects a different input blob.
ASSIGNMENT = {1: [0,1,2,3,4,5,6,26], 2: [11,14,17],
              3: [10,12,13,15,16,23,24,25], 4: [7,8,9,19], 5: [18,20,21,22]}
FIELDS = 'name url priority type location deadline value fee simplicity career eligibility maxWorks lifetime action verified'.split()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result or key in {'__proto__', 'constructor', 'prototype'}:
            raise ValueError(f'Duplicate or forbidden JSON key: {key}')
        result[key] = value
    return result


def load_json(path: Path):
    def invalid(value):
        raise ValueError(f'Non-finite JSON number: {value}')
    return json.loads(path.read_text(encoding='utf-8'),
                      object_pairs_hook=unique_object, parse_constant=invalid)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'


def identity(record):
    return (' '.join(record['name'].split()).casefold(), record['url'].rstrip('/'))


def validate(record):
    if not isinstance(record, dict):
        raise ValueError('Each opportunity must be an object')
    for field in FIELDS:
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ValueError(f'Missing text field: {field}')
    if record['priority'] not in {'A1','A2','B','C','Écarté'}:
        raise ValueError('Invalid priority')
    url = urlsplit(record['url'])
    if url.scheme != 'https' or not url.hostname or url.username or url.password:
        raise ValueError('Source URL must be HTTPS without credentials')
    # Legacy published records lack tags; the unchanged UI derives them.
    for field in ('discipline', 'tags'):
        values = record.get(field, [] if field == 'tags' else None)
        if not isinstance(values, list) or not all(isinstance(v,str) and v.strip() for v in values):
            raise ValueError(f'Invalid {field} array')
        if field == 'discipline' and not values:
            raise ValueError('Empty discipline array')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', record['verified']):
        raise ValueError('Verification date must use YYYY-MM-DD')
    encoded(record)


def initialize(root: Path):
    """One-time, exact-snapshot split. Never overwrite an existing source folder."""
    raw = (root / 'data.js').read_bytes()
    blob = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if blob != BASELINE_BLOB:
        raise ValueError('Baseline changed: re-read main and review allocation before migration')
    folder = root / 'opportunities'
    if folder.exists():
        raise ValueError('opportunities already exists; initialization will not overwrite it')
    sys.path.insert(0, str(root / 'tools'))
    from merge_opportunities import LiteralParser
    records = LiteralParser(raw.decode('utf-8')).records()[0]
    if len(records) != 27 or sorted(i for group in ASSIGNMENT.values() for i in group) != list(range(27)):
        raise ValueError('Unexpected baseline allocation')
    for record in records:
        validate(record)
    folder.mkdir()
    owners = []
    for axis, indices in ASSIGNMENT.items():
        (folder / f'axis{axis}.json').write_text(encoded([records[i] for i in indices]), encoding='utf-8')
        owners.extend({'key': list(identity(records[i])), 'axis':axis, 'order':i} for i in indices)
    (folder / '_baseline.json').write_text(encoded({'sourceBlob':blob, 'owners':owners}), encoding='utf-8')


def build(root: Path, output: Path):
    """Validate all five inputs before writing any public artifact."""
    folder = root / 'opportunities'
    manifest = load_json(folder / '_baseline.json')
    indexed = {}
    names, urls = set(), set()
    for axis in range(1, 6):
        records = load_json(folder / f'axis{axis}.json')
        if not isinstance(records, list):
            raise ValueError(f'axis{axis}.json must contain an array')
        for record in records:
            validate(record)
            key = identity(record)
            if key in indexed or key[0] in names or key[1] in urls:
                raise ValueError(f'Duplicate opportunity: {record["name"]}')
            indexed[key] = (axis, record)
            names.add(key[0]); urls.add(key[1])
    order = {}
    for entry in manifest['owners']:
        key = tuple(entry['key'])
        if key not in indexed or indexed[key][0] != entry['axis']:
            raise ValueError(f'Published baseline record missing or moved: {key[0]}')
        order[key] = entry['order']
    if not indexed:
        raise ValueError('Refusing an empty dashboard')
    keys = sorted(indexed, key=lambda key:(order.get(key, 10**9), key))
    records = [indexed[key][1] for key in keys]
    data = 'window.DIANE_OPPORTUNITIES = ' + encoded(records).rstrip() + ';\n'
    data = data.replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    version = hashlib.sha256(data.encode()).hexdigest()[:16]
    source = (root / 'index.html').read_text(encoding='utf-8')
    page, count = re.subn(r'(<script\s+src=[\"\'])data\.js[^\"\']*',
                          lambda m:m[1]+'data.js?v='+version, source)
    if count != 1:
        raise ValueError('Expected exactly one existing data.js script reference')
    allowed = {'index.html','data.js','.nojekyll'}
    if output.resolve() == root.resolve():
        raise ValueError('Output must not replace the source repository')
    if output.exists() and any(p.name not in allowed for p in output.iterdir()):
        raise ValueError('Output contains unrelated files; refusing to overwrite it')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'data.js').write_text(data, encoding='utf-8')
    (output / 'index.html').write_text(page, encoding='utf-8')
    (output / '.nojekyll').write_text('', encoding='utf-8')
    return records, version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--init', action='store_true')
    parser.add_argument('--output', type=Path, default=Path('_site'))
    args = parser.parse_args()
    try:
        if args.init:
            initialize(args.root)
        records, version = build(args.root, args.output)
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, f'Build refused: {exc}\n')
    print(f'{len(records)} opportunities; data version {version}; local output {args.output}')


if __name__ == '__main__':
    main()
