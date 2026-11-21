"""Reaudit final-test non-use; prior registration is allowed, policy traces are not."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import subprocess
import zipfile

from . import reserve_scenarios as old
from .full_cycle import FINAL_TEST, VALIDATION
from .five_stage import FiveStageEnv
from .scenarios import family
from .wm_state import pack


def reserve(root, output):
    root, output = Path(root), Path(output)
    if output.exists():
        raise FileExistsError(output)
    original_path = root/'docs/phase-11/retraction-pilot-evidence/reservation.json'
    original = json.loads(original_path.read_text())
    baseline = json.loads(subprocess.check_output(['git', 'show',
        '07c5615:docs/phase-11/retraction-pilot-evidence/files.json'], cwd=root, text=True))
    allowed_digests = {}
    for name in ('reservation.json', 'consumption.json'):
        data = (original_path.parent/name).read_bytes()
        digest = old.sha(data)
        if digest != baseline[name]:
            raise ValueError('prior registration/non-use declaration changed')
        allowed_digests[digest] = name
    consumption = json.loads((original_path.parent/'consumption.json').read_text())
    if consumption['final_test'] != {'role': 'reserved_initialised_only_no_policy_evaluation', 'seeds': FINAL_TEST}:
        raise ValueError('prior final-test role differs')
    allowed_digest = old.sha(original_path.read_bytes())
    finals = [r for r in original['identities'] if r['split'] == 'final_test']
    if [r['seed'] for r in finals] != FINAL_TEST:
        raise ValueError('final seed registration differs')
    identities = old.identities
    try:
        old.identities = lambda: finals
        with tempfile.TemporaryDirectory() as temporary:
            audit_path = Path(temporary)/'audit.json'
            try:
                old.reserve(root, audit_path)
            except ValueError:
                pass  # Classify only the prior registration below; all else fails.
            audit = json.loads(audit_path.read_text())
    finally:
        old.identities = identities
    inventory = audit['archive_inventory']
    allowed_locations = {location for digest in allowed_digests
                         for location in inventory.get(digest, {}).get('locations', [])}
    disallowed = [h for h in audit['hits'] if h['location'] not in allowed_locations]
    fingerprints = {v for r in finals for start in r['starts'].values()
                    for k, v in start.items() if k.endswith('sha256')}
    zip_inventory, zip_hits, errors = [], [], list(audit['failures'])
    seen = set()
    for directory in ('docs/phase-11', 'training', 'data'):
        for path in sorted((root/directory).rglob('*.zip')):
            if '.venv' in path.parts:
                continue
            try:
                with zipfile.ZipFile(path) as archive:
                    for name in archive.namelist():
                        if not name.endswith(('.json', '.json.gz', '.jsonl', '.pt', '.npz')):
                            continue
                        data = archive.read(name); digest = old.sha(data)
                        location = path.relative_to(root).as_posix()+':'+name
                        zip_inventory.append({'location': location, 'sha256': digest})
                        if digest in seen or digest in allowed_digests:
                            continue
                        seen.add(digest)
                        hits = old.inspect(data, name, set(FINAL_TEST), fingerprints)
                        if hits:
                            zip_hits.append({'location': location, 'hits': hits})
            except Exception as error:
                errors.append({'location': str(path), 'error': str(error)})
    for row in finals:
        env = FiveStageEnv(1, seed=row['seed'], scene=family('standard')[0], stage='complete', shaping=False)
        if old.sha(pack(env)[0].astype('<f8').tobytes()) != row['starts']['complete']['state_float64_sha256']:
            raise ValueError('full-cycle final initial state differs from registration')
    result = {'kind': 'full-cycle-reservation-v1',
        'final_test_verified_unused': not disallowed and not zip_hits and not errors,
        'validation_seeds': VALIDATION, 'validation_role': 'consumed validation reused for selection and retention, never fresh-test evidence',
        'final_test_seeds': FINAL_TEST, 'prior_registration_sha256': allowed_digest, 'allowed_prior_documents': allowed_digests,
        'allowed_prior_registration_locations': sorted(allowed_locations),
        'archive_audit': audit, 'zip_inventory': zip_inventory, 'disallowed_hits': disallowed+zip_hits,
        'errors': errors, 'scope': 'available local Git refs/history, local raw archives and ZIP members; unrecorded external runs cannot be ruled out',
        'final_initial_identities': finals}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2)+'\n')
    if not result['final_test_verified_unused']:
        raise ValueError('final test audit failed; inspect audit, do not start study')
    print('Final-test audit passed:', len(inventory), 'unique archive blobs;', len(zip_inventory), 'ZIP members')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    reserve(Path(__file__).resolve().parents[2], args.output)
