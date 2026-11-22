#!/usr/bin/env python3
"""Independent material/contact, actuation and reward probes on consumed scenes."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'training'))
import numpy as np
from kessel_training.contracts import LoaderConfig
from kessel_training.environment import LoaderEnv,SceneConfig
from kessel_training.reference_audit import trace
from kessel_training.rewards import UNITS,calculate


def execute(output):
    started=time.perf_counter();cycles=[]
    for family in ('legacy','rubble','steep'):
        for substeps in (1,5,10):
            row=trace(SceneConfig(randomise=True,pile_family=family),207600,replace(LoaderConfig(),substeps=substeps))
            cycles.append({'family':family,'configured_substeps':substeps,'effective_substeps':max(substeps,5),**{k:row[k] for k in ('outcome','delivered_kg','spilled_kg','cycle_s','max_mass_residual_kg','independent_max_state_error')}})
    actuators=[]
    for axis,name in enumerate(('drive','articulation','boom','bucket')):
        for sign in (-1,1):
            env=LoaderEnv(1,seed=207600)
            for _ in range(30):
                if (env.terminated|env.truncated).any():break
                action=np.zeros((1,4));action[0,axis]=sign;env.step(action)
            actuators.append({'axis':name,'command':sign,'speed_m_s':float(env.speed[0]),'joints_rad':env.joints[0].tolist(),
                              'reason':str(env.reason[0]),'decisions':int(env.steps[0])})
    # Incremental reward counterexamples. Pickup alone has no credit.
    rewards=[]
    for name,changes in [('idle_60s',{'elapsed_s':60}),('delivery_2000kg',{'delivered_kg':2000,'elapsed_s':40}),
                         ('spill_2000kg',{'spilled_kg':2000,'elapsed_s':40}),('collision',{'collision_count':1}),
                         ('pickup_only',{}),('high_effort_delivery',{'delivered_kg':2000,'elapsed_s':40,'effort_proxy_j':2e6})]:
        terms={k:np.array([changes.get(k,0.)]) for k in UNITS};value,detail=calculate(terms)
        rewards.append({'probe':name,'reward':float(value[0]),'terms':changes})
    result={'kind':'simulator-extension-audit-v1','seed':207600,'source':'consumed nominal scene; not new held-out evidence',
            'cycles':cycles,'actuators':actuators,'reward_probes':rewards,'wall_s':time.perf_counter()-started,
            'limits':['height-field contact; no granular fracture or calibrated hydraulics',
                      'substep sensitivity is a discretisation diagnostic, not proof of physical fidelity',
                      'reward ranking does not prove a reward-only optimiser can find complete cycles']}
    output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);execute(p.parse_args().output)
