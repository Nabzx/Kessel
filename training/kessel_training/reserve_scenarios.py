"""Audit available local archives and Git history before reserving pilot scenes."""

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess

import numpy as np
import torch

from .inspect_prerequisites import stage_environment
from .reference_audit import initial_status
from .wm_state import pack

RANGES = {'validation': (108000, 108016), 'pilot_test': (208900, 208916), 'final_test': (209900, 209932)}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def identities():
    rows = []
    for split, (first, stop) in RANGES.items():
        for seed in range(first, stop):
            entry = {'split': split, 'seed': seed, 'starts': {}}
            for stage in ('retract', 'complete'):
                env = stage_environment(stage, seed)
                if not initial_status(env)[0]['valid']:
                    raise ValueError('reserved scenario starts in collision')
                state = pack(env)[0]
                entry['starts'][stage] = {'state_float64_sha256': sha(state.astype('<f8').tobytes()),
                                          'state_float32_sha256': sha(state.astype('<f4').tobytes()),
                                          'pile_sha256': sha(env.pile.height[0].astype('<f8').tobytes()),
                                          'pile_float32_sha256': sha(env.pile.height[0].astype('<f4').tobytes()),
                                          'initial_payload_kg': float(env.payload[0])}
            rows.append(entry)
    return rows


def inspect(data, name, seeds, fingerprints):
    """Safe decoding only. A seed/initial-state hit is consumption, not success."""
    if name.endswith('.gz'):
        data = gzip.decompress(data)
    if name.endswith('.pt'):
        value = torch.load(io.BytesIO(data), map_location='cpu', weights_only=True)
    elif name.endswith('.npz'):
        with np.load(io.BytesIO(data), allow_pickle=False) as archive:
            value = {key: archive[key] for key in archive.files}
    elif name.endswith('.jsonl'):
        value = [json.loads(line) for line in data.splitlines() if line.strip()]
    else:
        value = json.loads(data)
    hits = []
    stack = [('', value)]
    while stack:
        key, item = stack.pop()
        if isinstance(item, torch.Tensor):
            item = item.detach().cpu().numpy()
        if isinstance(item, np.ndarray):
            if 'seed' in key.lower():
                for seed in np.unique(item):
                    if int(seed) in seeds:
                        hits.append({'kind': 'seed', 'value': int(seed), 'key': key})
            if item.ndim >= 1 and item.shape[-1] == 102 and item.dtype.kind == 'f':
                for row in item.reshape(-1, 102):
                    for dtype in ('<f8', '<f4'):
                        for kind, values in [('initial_state', row), ('pile', row[15:79])]:
                            digest = sha(values.astype(dtype).tobytes())
                            if digest in fingerprints:
                                hits.append({'kind': kind, 'value': digest, 'key': key})
            if item.ndim >= 2 and item.shape[-2:] == (8, 8) and item.dtype.kind == 'f':
                for pile in item.reshape(-1, 64):
                    for dtype in ('<f8', '<f4'):
                        digest = sha(pile.astype(dtype).tobytes())
                        if digest in fingerprints:
                            hits.append({'kind': 'pile', 'value': digest, 'key': key})
        elif isinstance(item, dict):
            stack.extend((str(k), v) for k, v in item.items())
        elif isinstance(item, (tuple, list)):
            if 'seed' in key.lower() and all(isinstance(v, (int, float)) for v in item):
                hits.extend({'kind': 'seed', 'value': int(v), 'key': key} for v in item if v in seeds)
            elif key in ('state', 'states', 'initial_state') and len(item) == 102 and all(isinstance(v, (int, float)) for v in item):
                array = np.asarray(item)
                for dtype in ('<f8', '<f4'):
                    for kind, values in [('initial_state', array), ('pile', array[15:79])]:
                        digest = sha(values.astype(dtype).tobytes())
                        if digest in fingerprints:
                            hits.append({'kind': kind, 'value': digest, 'key': key})
            elif item and isinstance(item[0], (dict, tuple, list, str)):
                stack.extend((key, v) for v in item)
        elif isinstance(item, int) and 'seed' in key.lower() and item in seeds:
            hits.append({'kind': 'seed', 'value': item, 'key': key})
        elif isinstance(item, str) and item in fingerprints:
            hits.append({'kind': 'initial_fingerprint', 'value': item, 'key': key})
    return hits


def reserve(root, output):
    root, output = Path(root), Path(output)
    if output.exists():
        raise FileExistsError('reservation output exists')
    rows = identities()
    seeds = {r['seed'] for r in rows}
    fingerprints = {v for row in rows for start in row['starts'].values() for k, v in start.items() if k.endswith('sha256')}
    all_ids = [start['state_float64_sha256'] for row in rows for start in row['starts'].values()]
    if len(all_ids) != len(set(all_ids)):
        raise ValueError('reserved initial identities overlap')
    history = subprocess.check_output(['git', 'rev-list', '--objects', '--all', '--', 'data', 'docs/phase-11', 'training'], cwd=root, text=True)
    candidates = []
    suffixes = ('.json', '.json.gz', '.jsonl', '.npz', '.pt')
    for line in history.splitlines():
        parts = line.split(' ', 1)
        if len(parts) == 2 and parts[1].endswith(suffixes):
            candidates.append(('git:' + parts[0], parts[1], lambda oid=parts[0]: subprocess.check_output(['git', 'cat-file', 'blob', oid], cwd=root)))
    for directory in ('data', 'docs/phase-11', 'training'):
        for path in sorted((root / directory).rglob('*')):
            if path.is_file() and '.venv' not in path.parts and path.name.endswith(suffixes):
                candidates.append((path.relative_to(root).as_posix(), path.name, path.read_bytes))
    blobs, failures, hits = {}, [], []
    for location, name, read in candidates:
        try:
            data = read()
            digest = sha(data)
            if digest in blobs:
                blobs[digest]['locations'].append(location)
                continue
            found = inspect(data, name, seeds, fingerprints)
            blobs[digest] = {'format': next(s for s in ('.json.gz', '.jsonl', '.json', '.npz', '.pt') if name.endswith(s)), 'locations': [location]}
            if found:
                hits.append({'location': location, 'hits': found})
        except Exception as error:
            failures.append({'location': location, 'error': str(error)})
    report = {'schema': 'scenario-reservation-v1', 'reservation_verified': not hits and not failures,
              'scope': 'All available local refs and local data/docs/training archives; not unretained external runs.',
              'history_listing_sha256': sha(history.encode()), 'unique_blobs': len(blobs), 'archive_inventory': blobs,
              'hits': hits, 'failures': failures, 'identities': rows,
              'generator_review': {'scenario_seed': 'immutable disjoint seed ranges; episode/stream random generators are deterministic',
                                   'old_schedules': 'Explicit realised seeds in all historical manifests plus raw initial-state fingerprints. OOD offsets 3000+, fresh offsets 6000/9000 and strides are inspected without assuming they imply non-use.',
                                   'remaining_limits': 'An unrecorded external experiment cannot be ruled out. This certificate covers available artefacts and exact/f32 initial-state matches only.'}}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    if hits or failures:
        raise ValueError(f'reservation audit failed: {len(hits)} consumed matches, {len(failures)} unreadable archives; inspect report')
    print(json.dumps({'reserved_seeds': len(rows), 'unique_blobs': len(blobs), 'output': str(output)}))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    reserve(Path(__file__).resolve().parents[2], args.output)
