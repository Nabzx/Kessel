"""Two-frame observations and held-out curriculum gates, separate from legacy runs."""
import numpy as np
import torch
from torch import nn
from .policy import ActorCritic
from .curriculum import STAGES


def flat(observation):
    return np.concatenate((observation['proprio'],observation['local_height_m'].reshape(-1,25),observation['range_valid'].reshape(-1,25)),axis=1)


class HistoryEnv:
    def __init__(self,base):
        self.base=base;self.previous=np.zeros((base.num_envs,65),dtype=np.float64)
    def __getattr__(self,name):return getattr(self.base,name)
    def observe(self):return {**self.base.observe(),'previous':self.previous.copy()}
    def clear_history(self,mask=None):
        selected=np.ones(self.num_envs,dtype=bool) if mask is None else np.asarray(mask)
        if selected.shape!=(self.num_envs,) or selected.dtype!=bool:raise ValueError('history reset mask must be boolean')
        self.previous[selected]=0
    def reset(self,**kwargs):
        _,info=self.base.reset(**kwargs);self.clear_history(kwargs.get('mask'));return self.observe(),info
    def step(self,actions):
        previous=flat(self.base.observe());_,reward,term,trunc,info=self.base.step(actions)
        self.previous[:]=previous
        return self.observe(),reward,term,trunc,info


class HistoryActorCritic(ActorCritic):
    feature_size=130
    def __init__(self,hidden=64):
        super().__init__(hidden)
        for network in (self.actor,self.critic):
            network[0]=nn.Linear(130,hidden);nn.init.orthogonal_(network[0].weight,2**.5);nn.init.zeros_(network[0].bias)
    def encode(self,observation):
        if set(observation)!={'proprio','local_height_m','range_valid','previous'}:raise ValueError('history observation contract differs')
        current=super().encode({k:v for k,v in observation.items() if k!='previous'})
        previous=torch.as_tensor(observation['previous'],dtype=torch.float32)
        if previous.shape!=(len(current),65):raise ValueError('previous observation shape differs')
        encoded=super().encode({'proprio':previous[:,:15],'local_height_m':previous[:,15:40].reshape(-1,5,5),'range_valid':previous[:,40:].reshape(-1,5,5)})
        return torch.cat((current,encoded),dim=1)
    def description(self):return {**super().description(),'features':130,'history_frames':2,'history_reset':'masked zeros; no feature-encoding side effect'}


class CurriculumBridge:
    """Keep training-window and held-out retention evidence separate."""
    def __init__(self):self.history=[];self.records=[]
    def gate(self,stage,episodes,heldout):
        self.history.extend(bool(e.get('stage_success',False)) for e in episodes if e.get('stage')==stage)
        self.history=self.history[-32:]
        expected=STAGES[:STAGES.index(stage)+1]
        valid=all(name in heldout and heldout[name]['valid_starts'] and heldout[name]['evaluations']>=2 for name in expected)
        train_rate=sum(self.history)/len(self.history) if self.history else 0
        current=heldout.get(stage,{}).get('success_rate',0)
        retention=all(heldout.get(name,{}).get('success_rate',0)>=.5 for name in expected[:-1])
        passed=len(self.history)==32 and train_rate>=.7 and valid and current>=.7 and retention
        row={'stage':stage,'training_episodes':len(self.history),'training_success_rate':train_rate,'heldout':heldout,'retention_passed':retention,'passed':passed}
        self.records.append(row);return row
    def advance(self,env,episodes,heldout,rollout):
        row=self.gate(env.stage,episodes,heldout)
        if not row['passed'] or env.stage=='complete':return None
        samples=[{'stage':env.stage,'stage_success':x} for x in self.history]
        event=env.consider_advancement(samples,rollout)
        if event:self.history=[]
        return event
