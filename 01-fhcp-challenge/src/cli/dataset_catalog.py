"""Build a graph-only catalog with the existing strict parser; no tours are read."""

import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from src.graphs import read_hcp

ROOT = Path(__file__).resolve().parents[2]


def build_catalog(root=ROOT, count=1001):
    original = json.loads((root / 'docs/decisions/fhcp-instances.json').read_text(encoding='utf-8'))
    entries = []
    for number in range(1, count + 1):
        member = f'graph{number}.hcp'
        payload = (root / 'data/raw/FHCPCS' / member).read_bytes()
        graph = read_hcp(BytesIO(payload))
        entries.append({'id': f'graph{number}', 'archive_member': member,
                        'sha256': sha256(payload).hexdigest(), 'size_bytes': len(payload),
                        'dimension': graph.vertex_count(), 'edge_count': graph.edge_count()})
    return {'manifest_version': 1, 'purpose': 'Full graph-only catalog; original M6 selection unchanged',
            'archives': {'graphs': original['archives']['graphs']}, 'instances': entries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists; it will not be replaced.')
    catalog = build_catalog()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(catalog, stream, indent=2)
        stream.write('\n')
    print(f'{len(catalog["instances"])} graphs parsed and indexed: {args.output}')


if __name__ == '__main__':
    main()
