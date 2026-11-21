"""Reserve new observation/phase-study scenes before collection, including ZIP audits."""
import argparse
import json
from pathlib import Path
import tempfile
import zipfile
from . import reserve_scenarios as old
from .phase_study import VALIDATION, FINAL


def reserve(output):
    root = Path(__file__).resolve().parents[2]
    if output.exists():
        raise FileExistsError(output)
    original_ranges = old.RANGES
    try:
        old.RANGES = {'validation':(VALIDATION[0], VALIDATION[-1]+1), 'final_test':(FINAL[0], FINAL[-1]+1)}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'reservation.json'
            try:
                old.reserve(root,path)
            except ValueError:
                pass
            audit = json.loads(path.read_text())
    finally:
        old.RANGES = original_ranges
    fingerprints={v for row in audit['identities'] for start in row['starts'].values() for key,v in start.items() if key.endswith('sha256')}
    zip_hits=[];zip_errors=[];inventory=[];seen=set()
    for folder in ('docs/phase-11','training','data'):
        for path in sorted((root/folder).rglob('*.zip')):
            if '.venv' in path.parts:continue
            try:
                with zipfile.ZipFile(path) as archive:
                    for name in archive.namelist():
                        if not name.endswith(('.json','.json.gz','.jsonl','.pt','.npz')):continue
                        data=archive.read(name);digest=old.sha(data)
                        inventory.append({'location':path.relative_to(root).as_posix()+':'+name,'sha256':digest})
                        if digest in seen:continue
                        seen.add(digest);hits=old.inspect(data,name,set(VALIDATION+FINAL),fingerprints)
                        if hits:zip_hits.append({'location':str(path)+':'+name,'hits':hits})
            except Exception as error:zip_errors.append({'path':str(path),'error':str(error)})
    result={'kind':'phase-imitation-reservation-v1','verified':audit['reservation_verified'] and not zip_hits and not zip_errors,
        'archive_audit':audit,'zip_inventory':inventory,'zip_hits':zip_hits,'zip_errors':zip_errors,
        'validation':VALIDATION,'final':FINAL,'scope':'available local refs/history, local data/docs/training raw archives and ZIP members; excludes unrecorded external runs'}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n')
    if not result['verified']:raise ValueError('fresh scene audit failed; do not train')
    print('Fresh audit passed',len(audit['archive_inventory']),'blobs',len(inventory),'ZIP members',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);reserve(p.parse_args().output)
