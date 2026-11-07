"""Replay every declared curriculum seed on the first test scene, retaining failures."""
import argparse,gzip,hashlib,json
from dataclasses import asdict
from pathlib import Path
import numpy as np
from . import checkpoints
from .environment import LoaderEnv
from .evaluate import source_identity
from .export_viewer import row,forecasts,ROOT
from .followup_study import load_policy
from .scenarios import family
from .viewer_bundle import UNITS,validate
from .wm_state import pack,STATE_NAMES
from .world_model import load_model


def export(output):
    source=source_identity()
    if source['training_dirty']:raise ValueError('commit training sources before export')
    evidence=ROOT/'docs/phase-11/policy-followup-evidence';study=json.loads((evidence/'report.json').read_text());reference=json.loads((ROOT/'data/experiments/reference-v1.json').read_text());wm=reference['world_model'];wstudy=json.loads((ROOT/'docs/phase-11/world-followup-evidence/report.json').read_text());model,_=load_model(ROOT/'docs/phase-11/world-followup-evidence'/wstudy['models'][wm['selected_variant']]['path']);episodes=[];scene,_=family('standard')
    runs=[next(r for r in study['runs'] if r['method']=='bridged_curriculum' and r['seed']==seed) for seed in (7,19,41)]
    for run in runs:
        selected=run['selected'];policy,_=load_policy(evidence/selected['path']);trace=next(t for t in run['traces'] if t['seed']==200000);retained=json.loads(gzip.decompress((evidence/trace['path']).read_bytes()));raw_records=retained['records'] if isinstance(retained,dict) else retained
        env=LoaderEnv(1,seed=200000,scene=scene);records=[];max_error=0.
        for kept in raw_records[:-1]:
            max_error=max(max_error,float(np.max(np.abs(pack(env)[0]-kept['state']))));record=row(env);action=policy.sample(policy.encode(env.observe()),deterministic=True)['action'].detach().numpy();np.testing.assert_allclose(action[0],kept['action'],rtol=0,atol=1e-7);_,reward,term,trunc,info=env.step(action);transfer={k:float(info['transfer'][k][0]) for k in ('loaded_kg','delivered_kg','spilled_kg')};record.update(action=action[0].tolist(),reward=float(reward[0]),reward_terms={k:float(v[0]) for k,v in info['reward_terms'].items()},reward_weighted={k:float(v[0]) for k,v in info['reward_description']['weighted'].items()},events=[k for k,v in transfer.items() if v>0],transfer=transfer);records.append(record)
        final=row(env);max_error=max(max_error,float(np.abs(pack(env)[0]-raw_records[-1]['state']).max()));final['events']=[str(env.reason[0])];records.append(final)
        if max_error>1e-9:raise ValueError('retained curriculum replay differs')
        counters={'environment_steps':run['counters']['online_reference_decisions'],'completed_episodes':run['counters']['completed_episodes'],'rollouts':selected['rollout'],'optimiser_updates':run['counters']['optimiser_updates'],'nominal_simulated_s':run['counters']['online_reference_decisions']*.1}
        curve=[{'environment_steps':r['online_reference_decisions'],'mean_step_reward':r['mean_step_reward'],'rollout':r['rollout']} for r in run['curve']]
        ep={'id':f"seed-{run['seed']}",'name':f"Seed {run['seed']}",'training_seed':run['seed'],'seed':200000,'stream_id':0,'scene':asdict(scene),'scenario_sha256':env.scenario_identity()[0],'policy':{'checkpoint_sha256':selected['sha256'],'source_checkpoint_sha256':selected['sha256'],'training_counters':counters},'terminated':bool(term[0]),'truncated':bool(trunc[0]),'outcome':str(env.reason[0]),'steps':len(records)-1,'metrics':{k:v[0].item() for k,v in info['metrics'].items()},'learning_curve':curve,'records':records,'playback_seconds':8,'action_replay':{'decisions':len(records)-1,'max_state_absolute_error':max_error}};forecasts(ep,model);episodes.append(ep)
    config={'method':'bridged_curriculum','seeds':[7,19,41],'reference_decisions_per_run':4096};config_sha=hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()
    bundle={'schema_version':'1.1','source_mode':'recorded_synthetic','run_id':'curriculum-followup-v1','agent':{'kind':'learned_policy'},'export_source':source,'units':UNITS,'state_names':STATE_NAMES,'action_names':['acceleration','articulation rate','boom rate','bucket rate'],'run':{'configuration':config,'configuration_sha256':config_sha,'source':study['source'],'counters':episodes[0]['policy']['training_counters'],'training_wall_s':runs[0]['training_wall_s']},'learning_curve':episodes[0]['learning_curve'],'world_model':wm,'presentation':{'replay_seconds':24,'terminal_hold_s':.7,'selection':'Post-hoc curriculum illustration, not an efficacy estimate: all three predeclared training seeds, first declared test seed 200000, validation-selected checkpoints. Other methods and the second test scene are retained in the policy study. No favourable test-seed selection.','limitations':'Partial pickup only. Every displayed learned policy hits a wall and delivers zero ore. No full learned cycle; business figures illustrative.'},'episodes':episodes}
    counts=validate(bundle);output=Path(output).resolve();output.write_text(json.dumps(bundle,separators=(',',':'),allow_nan=False)+'\n');entry={'run_id':bundle['run_id'],'url':str(output.relative_to(ROOT)),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'bytes':output.stat().st_size,'source_mode':'recorded_synthetic'};index_path=output.parent/'index.json';index=json.loads(index_path.read_text());index['experiments']=[e for e in index['experiments'] if e['run_id']!=bundle['run_id']]+[entry];index_path.write_text(json.dumps(index,indent=2)+'\n');return {'source':source,'entry':entry,**counts,'selection':bundle['presentation']['selection']}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--report',type=Path,required=True);args=parser.parse_args();args.report.write_text(json.dumps(export(args.output),indent=2)+'\n')
