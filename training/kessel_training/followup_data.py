"""Declared contact/failure corpus and onboard range impairment. Communications is separate."""
from collections import deque
from dataclasses import asdict,dataclass,replace
import hashlib
import json
from pathlib import Path
import numpy as np
from .controller import ReferenceController
from .environment import LoaderEnv,SceneConfig,PROPRIO_NAMES
from .followup_policy import flat
from .kinematics import components
from .reference_audit import initial_status
from .scenarios import scenario_seed
from .wm_data import logical_hash,write_archive
from .wm_state import pack,STATE_NAMES

EVENTS=('contact','collision','success','stuck','truncation')

@dataclass(frozen=True)
class SensorProfile:
    range_latency_steps:int=0
    dropout:float=0
    occlusion:float=0
    range_noise_m:float=0
    communications_available:bool=False
    def __post_init__(self):
        if not isinstance(self.communications_available,bool):raise ValueError('communications flag must be boolean')
        if isinstance(self.range_latency_steps,bool) or not isinstance(self.range_latency_steps,int) or not 0<=self.range_latency_steps<=10:raise ValueError('range latency must be 0..10 decisions')
        if not all(np.isfinite(x) for x in (self.dropout,self.occlusion,self.range_noise_m)):raise ValueError('non-finite sensor profile')
        if not 0<=self.dropout<=1 or not 0<=self.occlusion<=1 or self.range_noise_m<0:raise ValueError('invalid sensor profile')


class SensorEnv:
    """Delay the range crop; local odometry/encoders and actuation stay onboard."""
    def __init__(self,base,profile=None):
        self.base=base;self.profile=profile or SensorProfile();self.queues=[deque(maxlen=self.profile.range_latency_steps+1) for _ in range(base.num_envs)]
        self.rng=[None]*base.num_envs;self.cached=base.observe();self.last_t=np.zeros(base.num_envs);self._refresh(np.ones(base.num_envs,dtype=bool),reset=True)
    def __getattr__(self,name):return getattr(self.base,name)
    def observe(self):return {k:v.copy() for k,v in self.cached.items()}
    def _refresh(self,mask,reset=False):
        obs=self.base.observe();self.cached['proprio'][mask]=obs['proprio'][mask]
        for i in np.flatnonzero(mask):
            if reset:
                self.queues[i].clear();self.rng[i]=np.random.default_rng(np.random.SeedSequence([int(self.seeds[i]),int(self.stream_ids[i]),int(self.episode_index[i]),8817]));self.last_t[i]=self.elapsed[i]
            self.queues[i].append((obs['local_height_m'][i].copy(),obs['range_valid'][i].copy(),float(self.elapsed[i])))
            ready=len(self.queues[i])>self.profile.range_latency_steps;drop=self.rng[i].random()<self.profile.dropout
            if ready and not drop:
                height,valid,t=self.queues[i][0];noise=self.rng[i].normal(0,self.profile.range_noise_m,(5,5));visible=self.rng[i].random((5,5))>=self.profile.occlusion
                valid=valid.astype(bool)&visible;self.cached['local_height_m'][i]=np.where(valid,np.maximum(0,height+noise),0);self.cached['range_valid'][i]=valid;self.last_t[i]=t
            else:self.cached['local_height_m'][i]=0;self.cached['range_valid'][i]=0
            self.cached['proprio'][i,11]=max(0,self.elapsed[i]-self.last_t[i]);self.cached['proprio'][i,12]=int(ready and not drop)
    def reset(self,**kwargs):
        _,info=self.base.reset(**kwargs);mask=kwargs.get('mask');mask=np.ones(self.num_envs,dtype=bool) if mask is None else mask;self._refresh(mask,reset=True);return self.observe(),info
    def step(self,actions):
        _,reward,term,trunc,info=self.base.step(actions);self._refresh(np.ones(self.num_envs,dtype=bool));info['sensor_profile']=asdict(self.profile);info['communications_available']=self.profile.communications_available
        return self.observe(),reward,term,trunc,info


def observation_inventory():
    return {'schema':'observability-v1','inputs':[
        {'name':name,'status':'synthetic_onboard_estimate','availability':'local; independent of communications','note':'receiver displacement assumes a preloaded local target map; odometry is not GPS'} for name in PROPRIO_NAMES]+[
        {'name':'local_height_m[5,5]','status':'synthetic_local_range','units':'m','availability':'delayed/dropout profile; masked invalid cells'},
        {'name':'range_valid[5,5]','status':'onboard_validity','units':'binary','availability':'local sensor frame'}],
        'privileged_baseline_only':list(STATE_NAMES),'excluded_inputs':['future states','future observations','held-out scene identities','communication status as a substitute for sensing'],
        'observable_model':'predicts local observation features, reward and events; does not invent full hidden-pile mass or learned pixel perception'}


def setup_episode(split,index,kind,*,pile_family='legacy'):
    seed=scenario_seed(split,index);scene=SceneConfig(randomise=True,max_steps=400,pile_family=pile_family)
    if kind=='blocked':scene=replace(scene,obstacles=((6.,6.1,-4.2,4.2),))
    if kind=='stuck':scene=replace(scene,friction=.00001,stuck_s=.5,randomise=False)
    if kind in ('contact_static','spill','prepared_delivery'):scene=replace(scene,max_steps=32)
    env=LoaderEnv(1,seed=seed,scene=scene);controller=ReferenceController(1);prepared=kind in ('contact_static','close_scoop','spill','prepared_delivery')
    if kind in ('contact_static','close_scoop'):
        env.pose[0,0]=env.pile.origin[0,0]-4.2;env.joints[0]=(0,-.1,-.1)
        if kind=='close_scoop':controller.phase[0]=1
    if kind in ('spill','prepared_delivery'):
        payload=2200 if kind=='prepared_delivery' else 1500;mass=env.pile.mass()[0];env.pile.height[0]*=(mass-payload)/mass;env.payload[0]=payload;env.peak_load[0]=payload;env.joints[0]=(0,.35,-.7)
        if kind=='prepared_delivery':env.pose[0,0]=env.receiver[0,0]-1.8-1.6-1.2*np.cos(.35)
    env.initial_pose[:]=env.pose;env._assert_finite();env._update_observations(np.ones(1,dtype=bool),reset=True)
    if not initial_status(env)[0]['valid']:raise ValueError('invalid targeted collection reset')
    profile=SensorProfile(range_latency_steps=2,dropout=.25,occlusion=.15,range_noise_m=.01) if kind=='impaired_range' else SensorProfile()
    return SensorEnv(env,profile),controller,{'split':split,'seed':seed,'kind':kind,'pile_family':pile_family,'prepared_start':prepared,'initial_payload_kg':float(env.payload[0]),'initial_state_sha256':hashlib.sha256(pack(env).tobytes()).hexdigest(),'sensor_profile':asdict(profile)}


def collect_targeted(split,budget,*,seed_offset=0,kinds=None,pile_family='legacy'):
    if split not in ('train','validation','test') or isinstance(budget,bool) or not isinstance(budget,int) or budget<1:raise ValueError('invalid collection split/budget')
    allowed=('reference','blocked','contact_static','close_scoop','spill','prepared_delivery','stuck','impaired_range')
    kinds=allowed if kinds is None else tuple(kinds)
    if not kinds or any(k not in allowed for k in kinds):raise ValueError('unknown collection stratum')
    rows=[];episodes=[];number=0
    while len(rows)<budget:
        kind=kinds[number%len(kinds)];env,controller,identity=setup_episode(split,seed_offset+number,kind,pile_family=pile_family);start=len(rows);episode_id=len(episodes)
        while len(rows)<budget:
            obs=env.observe();state=pack(env)[0];action=np.zeros((1,4)) if kind in ('contact_static','spill','prepared_delivery') else np.array([[1,0,0,0]]) if kind=='stuck' else controller.act(obs)
            geometry=components(env.pose,env.joints);contact=bool(env.pile.sample(geometry['mouth'])[0]>geometry['bucket_height'][0])
            following,reward,term,trunc,info=env.step(action);collision=bool(env.collision_time[0]>=0);reason=str(env.reason[0]);transfer=sum(float(info['transfer'][k][0]) for k in ('loaded_kg','delivered_kg','spilled_kg'))
            regime=3 if collision or reason=='stuck' else 2 if transfer>1e-6 else 1 if contact else 0
            rows.append({'state':state,'action':action[0],'next_state':pack(env)[0],'observation':flat(obs)[0],'next_observation':flat(following)[0],'reward':float(reward[0]),
                'events':np.array([term[0],trunc[0],contact or transfer>1e-6,collision]),'event_targets':np.array([contact or transfer>1e-6,collision,reason=='success',reason=='stuck',trunc[0]]),
                'episode_id':episode_id,'step':int(env.steps[0]-1),'regime':regime,'physical_dt_s':float(env.elapsed[0]-state[10])})
            if (term|trunc).any():break
        episodes.append({**identity,'id':episode_id,'start':start,'stop':len(rows),'reason':str(env.reason[0]) or 'collection_budget','collection_boundary':not bool((term|trunc)[0])});number+=1
    arrays={key:np.asarray([r[key] for r in rows]) for key in rows[0]}
    for value in arrays.values():
        if not np.isfinite(value).all():raise ValueError('non-finite collected row')
    return arrays,episodes


def coverage(arrays):
    counts=np.bincount(arrays['regime'].astype(int),minlength=4);weights=1/np.maximum(1,counts[arrays['regime'].astype(int)]);weights/=weights.mean()
    return {'rows':len(weights),'regime_names':['free','contact_without_transfer','material_transfer','collision_or_stuck'],'regime_counts':counts.tolist(),
        'natural_corpus_fractions':(counts/len(weights)).tolist(),'balanced_sampling_weights':[float(len(weights)/(4*max(1,n))) for n in counts],
        'event_names':EVENTS,'event_counts':arrays['event_targets'].sum(axis=0).tolist(),'note':'Natural frequency means this declared unbalanced synthetic corpus, not actual mine operation frequency.'},weights


def save_data(root,name,arrays,episodes):
    root=Path(root);root.mkdir(parents=True,exist_ok=True);write_archive(root/(name+'.npz'),arrays);report,_=coverage(arrays)
    manifest={'schema':'targeted-corpus-v1','logical_sha256':logical_hash(arrays,episodes),'episodes':episodes,'coverage':report,'observability':observation_inventory()}
    (root/(name+'.json')).write_text(json.dumps(manifest,indent=2)+'\n');return manifest
