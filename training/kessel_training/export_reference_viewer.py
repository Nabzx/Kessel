"""Full conventional reference cycles with independent action/state replay."""
import argparse
from dataclasses import asdict,replace
import hashlib,json
from pathlib import Path
import numpy as np
from .contracts import canonical_json
from .controller import ReferenceController
from .environment import LoaderEnv
from .evaluate import source_identity
from .export_viewer import row,forecasts,ROOT
from .scenarios import family
from .viewer_bundle import validate,UNITS
from .wm_state import STATE_NAMES,pack
from .world_model import load_model

PHASES=('Approach','Scoop','Retract','Haul','Tip')


def export_episode(scene,seed=100000):
    env=LoaderEnv(1,seed=seed,scene=scene);controller=ReferenceController(1);records=[];timeline=[{'t_s':0.,'kind':'Approach','index':0}];last_phase=0;seen=set()
    while True:
        record=row(env);action=controller.act(env.observe());phase=int(controller.phase[0]);record['phase']=PHASES[phase]
        if phase!=last_phase:timeline.append({'t_s':record['t_s'],'kind':PHASES[phase],'index':len(records)});last_phase=phase
        _,reward,term,trunc,info=env.step(action);transfer={k:float(info['transfer'][k][0]) for k in ('loaded_kg','delivered_kg','spilled_kg')};events=[k for k,v in transfer.items() if v>0]
        for key in events:
            if key not in seen:timeline.append({'t_s':float(env.elapsed[0]),'kind':{'loaded_kg':'Pickup','delivered_kg':'Deposition','spilled_kg':'Spill'}[key],'index':len(records)+1,'kg':transfer[key]});seen.add(key)
        record.update(action=action[0].tolist(),reward=float(reward[0]),reward_terms={k:float(v[0]) for k,v in info['reward_terms'].items()},reward_weighted={k:float(v[0]) for k,v in info['reward_description']['weighted'].items()},events=events,transfer=transfer);records.append(record)
        if (term|trunc).any():break
    final=row(env);final.update(events=[str(env.reason[0])],phase=PHASES[int(controller.phase[0])],transfer=None);records.append(final);timeline.append({'t_s':final['t_s'],'kind':str(env.reason[0]),'index':len(records)-1})
    replay=LoaderEnv(1,seed=seed,scene=scene);max_error=0.;max_mass=0.
    for current,following in zip(records,records[1:]):
        np.testing.assert_allclose(pack(replay)[0],current['state'],rtol=0,atol=1e-10);replay.step([current['action']]);max_error=max(max_error,float(np.abs(pack(replay)[0]-following['state']).max()));max_mass=max(max_mass,abs(float(replay.pile.mass()[0]+replay.payload[0]+replay.delivered[0]+replay.spilled[0]-replay.pile.initial_mass[0])))
    if max_error>1e-9 or max_mass>1e-7:raise ValueError('independent action replay failed')
    return {'id':scene.pile_family,'name':{'legacy':'Baseline','rubble':'Rubble','steep':'Steep'}[scene.pile_family],'seed':seed,'stream_id':0,'scene':asdict(scene),'scenario_sha256':env.scenario_identity()[0],'policy':None,'terminated':bool(term[0]),'truncated':bool(trunc[0]),'outcome':str(env.reason[0]),'steps':len(records)-1,'metrics':{k:v[0].item() for k,v in info['metrics'].items()},'records':records,'timeline':timeline,'playback_seconds':14.,'action_replay':{'decisions':len(records)-1,'max_state_absolute_error':max_error,'max_mass_residual_kg':max_mass,'states_sha256':hashlib.sha256(canonical_json([r['state'] for r in records]).encode()).hexdigest()}}


def export(output):
    source=source_identity()
    if source['training_dirty']:raise ValueError('commit training sources before export')
    evidence=ROOT/'docs/phase-11/world-followup-evidence';study=json.loads((evidence/'report.json').read_text());choice=min(study['models'],key=lambda k:min(r['validation_normalised_mse'] for r in study['models'][k]['fit']['history']));selected=study['models'][choice];model,identity=load_model(evidence/selected['path']);scene,_=family('standard');episodes=[]
    for name in ('legacy','rubble','steep'):
        ep=export_episode(replace(scene,pile_family=name));forecasts(ep,model);episodes.append(ep)
    settings=ReferenceController(1).settings();config_sha=hashlib.sha256(canonical_json(settings).encode()).hexdigest()
    bundle={'schema_version':'1.1','source_mode':'recorded_synthetic','run_id':'reference-cycle-v1','agent':{'kind':'reference_controller','learned':False,'configuration':settings,'configuration_sha256':config_sha},'export_source':source,'units':UNITS,'state_names':STATE_NAMES,'action_names':['acceleration','articulation rate','boom rate','bucket rate'],'run':{'configuration':settings,'configuration_sha256':config_sha,'source':source,'counters':{'environment_steps':0},'training_wall_s':None},'learning_curve':[],'world_model':{'kind':'raw_neural_ensemble','model_sha256':identity['model_sha256'],'training_source':identity['training']['source'],'members':3,'selection':'lowest held-out validation normalised one-step MSE among predeclared variants; no test selection','selected_variant':choice,'envelope_method':'Final-step conditional member endpoints; not calibrated confidence or cumulative covariance'},'presentation':{'replay_seconds':42,'terminal_hold_s':1,'selection':'First declared held-out seed 100000, predeclared baseline/rubble/steep families, every decision retained; no outcome selection','limitations':'Conventional reference controller, not a learned policy. Raw forecasts can violate physics. Synthetic reference material accounting; no deployed performance claim.'},'episodes':episodes}
    counts=validate(bundle);output=Path(output);output.write_text(json.dumps(bundle,separators=(',',':'),allow_nan=False)+'\n');entry={'run_id':bundle['run_id'],'url':str(output.relative_to(ROOT)),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'bytes':output.stat().st_size,'source_mode':'recorded_synthetic'}
    if entry['bytes']>8*1024*1024:raise ValueError('playback budget exceeded')
    index_path=output.parent/'index.json';index=json.loads(index_path.read_text());index['experiments']=[e for e in index['experiments'] if e['run_id']!=bundle['run_id']]+[entry];index_path.write_text(json.dumps(index,indent=2)+'\n');return {**counts,'entry':entry,'source':source,'selected_model_variant':choice,'episodes':[{k:v for k,v in e.items() if k not in ('records','timeline')} for e in episodes]}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--report',type=Path,required=True);args=parser.parse_args();report=export(args.output);args.report.write_text(json.dumps(report,indent=2)+'\n')
