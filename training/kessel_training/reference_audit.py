"""Independent reference, contact-step, reset and material evidence. No learned claim."""
import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from .contracts import LoaderConfig, canonical_json
from .controller import ReferenceController
from .dynamics import clearance
from .environment import LoaderEnv, SceneConfig
from .kinematics import components, footprints
from .scenarios import family
from .wm_state import pack


def initial_status(env):
    reasons=clearance(env.pose,env.joints,env.pose,env.joints,env.half_width,
                      env.scene.ceiling_m,env.scene.obstacles)
    return [{"valid":not bool(reason),"classification":"invalid_start" if reason else "valid_start",
             "reason":str(reason)} for reason in reasons]


def trace(scene,seed=100000,loader=None):
    env=LoaderEnv(1,seed=seed,scene=scene,loader=loader)
    status=initial_status(env)[0]
    if not status['valid']:
        return {"seed":seed,"scene":asdict(scene),"reset":status,"records":[],"outcome":"invalid_start"}
    control=ReferenceController(1);records=[];events=[];max_mass=0.;previous=0
    started=time.perf_counter()
    while True:
        before=pack(env)[0].copy();action=control.act(env.observe())
        geometry=components(env.pose,env.joints)
        _,reward,term,trunc,info=env.step(action)
        after=pack(env)[0].copy()
        mass=float(env.pile.mass()[0]+env.payload[0]+env.delivered[0]+env.spilled[0])
        residual=mass-float(env.pile.initial_mass[0]);max_mass=max(max_mass,abs(residual))
        transfer={k:float(info['transfer'][k][0]) for k in ('loaded_kg','delivered_kg','spilled_kg')}
        # Events belong to the completed physical interval, not the pre-action row.
        if int(control.phase[0])!=previous:
            events.append({"t_s":float(before[10]),"kind":"controller_phase","phase":int(control.phase[0])});previous=int(control.phase[0])
        for key,value in transfer.items():
            if value>0:events.append({"t_s":float(env.elapsed[0]),"kind":key,"kg":value})
        records.append({"t_s":float(before[10]),"next_t_s":float(after[10]),"state":before.tolist(),
            "next_state":after.tolist(),"action":action[0].tolist(),"reward":float(reward[0]),
            "transfer":transfer,"mass_residual_kg":residual,
            "geometry":{k:v[0].tolist() for k,v in geometry.items()},
            "footprints_xy_m":footprints(np.asarray([before[:3]]),np.asarray([before[[4,5,6]]]))[0].tolist()})
        if (term|trunc).any():break
    # A second instance executes the exported actions without the controller.
    replay=LoaderEnv(1,seed=seed,scene=scene,loader=loader);max_state=0.
    for row in records:
        max_state=max(max_state,float(np.abs(pack(replay)[0]-row['state']).max()))
        replay.step(np.asarray([row['action']]))
        max_state=max(max_state,float(np.abs(pack(replay)[0]-row['next_state']).max()))
    if max_state>1e-9 or max_mass>1e-7:raise AssertionError('independent replay or ledger failed')
    events.append({"t_s":float(env.elapsed[0]),"kind":str(env.reason[0])})
    return {"source_mode":"recorded_synthetic","controller":"observation_only_reference",
        "learned_policy":False,"seed":seed,"scene":asdict(scene),"loader":asdict(env.loader),
        "reset":status,"outcome":str(env.reason[0]),"terminated":bool(term[0]),"truncated":bool(trunc[0]),
        "delivered_kg":float(env.delivered[0]),"spilled_kg":float(env.spilled[0]),
        "carried_kg":float(env.payload[0]),"cycle_s":float(env.elapsed[0]),"max_mass_residual_kg":max_mass,
        "independent_max_state_error":max_state,"records":records,"events":events,
        "state_sha256":hashlib.sha256(canonical_json([r['next_state'] for r in records]).encode()).hexdigest(),
        "wall_s":time.perf_counter()-started}


def run(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    scene,_=family('standard');results=[]
    for name in ('legacy','low','ridge','rubble','steep'):
        for seed in (100000,100001):
            row=trace(replace(scene,pile_family=name),seed)
            path=output/f'{name}-{seed}.json';path.write_text(json.dumps(row,separators=(',',':'))+'\n')
            results.append({k:v for k,v in row.items() if k not in ('records','events')})
    step_rows=[]
    for step in (.05,.1,.2):
        config=replace(LoaderConfig(),decision_s=step)
        for name,command in [('forward',[.4,0,0,0]),('reverse',[-.4,0,0,0]),('turn',[.2,.25,0,0]),('boom',[0,0,.2,0]),('curl',[0,0,0,.2])]:
            env=LoaderEnv(1,seed=100000,loader=config)
            for _ in range(round(2/step)):env.step([command])
            step_rows.append({'decision_s':step,'case':name,'pose':env.pose[0].tolist(),'joints':env.joints[0].tolist(),'speed':float(env.speed[0])})
        row=trace(scene,100000,config)
        step_rows.append({'decision_s':step,'case':'full_contact_cycle',**{k:row[k] for k in ('outcome','delivered_kg','spilled_kg','cycle_s','max_mass_residual_kg')}})
    reset_rows=[]
    for name in ('standard','low_grip','occluded','blocked'):
        scene,_=family(name)
        for seed in range(100000,100008):
            env=LoaderEnv(1,seed=seed,scene=scene)
            reset_rows.append({'family':name,'seed':seed,**initial_status(env)[0]})
    invalid=LoaderEnv(1,scene=SceneConfig(obstacles=((-1,1,-1,1),)))
    reset_rows.append({'family':'deliberately_invalid',**initial_status(invalid)[0]})
    # Browser audit includes straight, reverse, turning, scoop and roof-contact poses.
    fixtures=[]
    for name,pose,joints in [('straight',[0,0,0],[0,0,-.1]),('reverse',[2,0,0],[0,.35,.8]),('turn',[1,-.4,.7],[.3,.2,.5]),('scoop',[4.4,0,0],[0,-.1,-.3]),('high_boom',[1,0,-.3],[-.2,.6,.1])]:
        p=np.array([pose],float);j=np.array([joints],float)
        fixtures.append({'name':name,'pose':pose,'joints':joints,'geometry':{k:v[0].tolist() for k,v in components(p,j).items()},'footprints':footprints(p,j)[0].tolist()})
    (output/'geometry-fixtures.json').write_text(json.dumps(fixtures,indent=2)+'\n')
    report={'schema':'reference-audit-v1','source_mode':'recorded_synthetic','units':{'distance':'m','angle':'rad','mass':'kg','time':'s'},'limits':'Synthetic cell-centre contact and swept AABBs; not granular or calibrated machine physics. No learned success claim.','reference_cases':results,'integration':step_rows,'resets':reset_rows,'chosen_decision_s':.1,'physics_step_max_s':.02}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);args=p.parse_args();print(json.dumps(run(args.output)))
