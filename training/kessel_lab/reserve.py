"""Reserve the ADR-0062 base seeds before any policy query."""
import argparse
import json
from pathlib import Path
import tempfile
import zipfile
from kessel_training import reserve_scenarios as audit
from .runtime import ROOT


def reserve(output):
    audit.RANGES = {'calibration': (108400, 108408), 'shift_test': (206200, 206208)}
    seeds = set(range(108400,108408)) | set(range(206200,206208))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp)/'base.json'
        try: audit.reserve(ROOT, path)
        except ValueError: pass
        base = json.loads(path.read_text())
    inventory = []; hits = []; errors = []
    fingerprints = {v for row in base['identities'] for start in row['starts'].values() for k,v in start.items() if k.endswith('sha256')}
    for directory in ('docs/phase-11', 'training', 'data'):
        for path in sorted((ROOT/directory).rglob('*.zip')):
            if '.venv' in path.parts: continue
            try:
                with zipfile.ZipFile(path) as z:
                    for name in z.namelist():
                        if not name.endswith(('.json','.json.gz','.jsonl','.npz','.pt')): continue
                        data = z.read(name); found = audit.inspect(data,name,seeds,fingerprints)
                        inventory.append({'path': path.relative_to(ROOT).as_posix()+':'+name,'sha256':audit.sha(data)})
                        if found: hits.append({'path':inventory[-1]['path'],'hits':found})
            except Exception as error: errors.append({'path':str(path),'error':str(error)})
    result = {'verified':base['reservation_verified'] and not hits and not errors,'base':base,
              'zip_inventory':inventory,'zip_hits':hits,'zip_errors':errors}
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists(): raise FileExistsError(output)
    output.write_text(json.dumps(result,indent=2)+'\n')
    if not result['verified']: raise ValueError('audit rejected the proposed ranges')
    print('Reserved 16 bases:',base['unique_blobs'],'blobs;',len(inventory),'ZIP members',flush=True)

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);reserve(p.parse_args().output)
