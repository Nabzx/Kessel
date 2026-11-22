#!/usr/bin/env python3
"""Synthetic mixed-rate observation/shadow-proposal recording with measured costs."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'training'))
from kessel_lab.runtime import Run,checkpoint
from kessel_lab.observations import adapt,CONTRACT
from kessel_lab.recorder import Recorder,scan
from kessel_training.policy import configure_cpu
import numpy as np


def execute(output):
    configure_cpu(7);run=Run('nominal',19000,'phase_memory-7');actor,sha=checkpoint('phase_memory-7')
    latencies=[];adapt_us=[];masked=0
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'shadow.jsonl';identity={'run':'synthetic-shadow-19000','clock':'synthetic-monotonic',
                 'checkpoint_sha256':sha,'calibration':'synthetic-rig-1','mode':'observation-and-shadow-proposals'}
        log=Recorder(path,identity)
        for sequence in range(100):
            obs=run.env.observe();use=100.+float(run.env.elapsed[0]);channels={}
            for name,values in obs.items():
                delay=.3 if name!='proprio' and 30<=sequence<40 else .02 if name=='proprio' else .05
                channels[name]={'values':values[0].tolist(),'capture_s':use-delay,'delivery_s':use-.005,'sensor_id':'synthetic-'+name}
            packet={'clock':identity['clock'],'calibration':identity['calibration'],'frame':CONTRACT['frame'],
                    'sequence':sequence,'channels':channels}
            start=time.perf_counter_ns();adapted,meta=adapt(packet,clock=identity['clock'],calibration=identity['calibration'],use_time_s=use)
            adapt_us.append((time.perf_counter_ns()-start)/1000);masked+=int(not adapted['range_valid'].any())
            action=actor.act(adapted)[0].tolist()
            start=time.perf_counter_ns();log.append('observation',sequence,{'packet':packet,'alignment':meta})
            log.append('proposal',sequence,{'action':action,'checkpoint_sha256':sha,'applied_to_machine':False})
            latencies.append((time.perf_counter_ns()-start)/1000)
            run.step() # Reference physics advances independently of the shadow proposal.
        size=path.stat().st_size;before=path.read_bytes();path.write_bytes(before+b'{"power_loss":')
        log=Recorder(path,identity,recover=True)
        assert path.read_bytes()==before and len(scan(path,identity=identity))==201
        quota_log=Recorder(path,identity,quota_bytes=size+512)
        try:quota_log.append('observation',100,{'oversize':'x'*2048})
        except BufferError:pass
        else:raise AssertionError('quota accepted oversized data')
        assert path.read_bytes()==before
        output.mkdir(parents=True,exist_ok=False);(output/'shadow.jsonl').write_bytes(before)
        result={'source':'synthetic mixed-rate shadow probe; no hardware connection','decisions':100,'records':201,
                'range_stale_decisions':masked,'log_bytes':size,'bytes_per_decision':size/100,
                'estimated_mb_per_hour_at_10hz':size/100*36000/1e6,
                'fsync_pair_us':{'median':float(np.median(latencies)),'p95':float(np.quantile(latencies,.95))},
                'alignment_us':{'median':float(np.median(adapt_us)),'p95':float(np.quantile(adapt_us,.95))},
                'explicit_tail_recovery':True,'quota_preserves_records':True,'applied_machine_commands':0,
                'sha256':hashlib.sha256(before).hexdigest(),
                'limits':'Local filesystem fsync measurement, not sudden-power-loss hardware qualification; no image or raw-range storage.'}
        (output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);execute(p.parse_args().output)
