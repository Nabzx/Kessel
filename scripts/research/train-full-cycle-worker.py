#!/usr/bin/env python3
"""Run independent frozen-plan training configurations; final tests remain centralised."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import signal
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'training'))
from kessel_training import full_cycle as fc
from kessel_training import checkpoints


def work(study, names):
    plan = json.loads((study/'plan.json').read_text())
    source = fc.source_identity()
    if source['training_dirty'] or source['package_sha256'] != plan['source']['package_sha256']:
        raise ValueError('worker requires the exact frozen clean training package')
    by_name = {f'{c["method"]}-{c["seed"]}': c for c in plan['configurations']}
    for name in names:
        cfg = fc.Config(**by_name[name]); directory = study/name
        run = fc.CycleRun.resume(directory) if (directory/'latest.json').exists() else fc.CycleRun(directory, cfg, plan['reservation_sha256'])
        if run.reservation_sha != plan['reservation_sha256'] or asdict(run.config) != by_name[name]:
            raise ValueError('worker configuration or reservation differs')
        if run.log is None:
            run.source = plan['source']
        run.train()
        (study/f'worker-{name}.json').write_text(json.dumps(run.report(),indent=2)+'\n')
        print('Worker frozen',name,run.status,run.counters,flush=True)
        if fc.STOP:
            break


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study',type=Path,required=True)
    parser.add_argument('--runs',nargs='+',required=True)
    args=parser.parse_args()
    def stop(*_):fc.STOP=True
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    work(args.study,args.runs)
