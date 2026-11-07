"""Measured state/observation dynamics repairs; imposed constraints stay explicit."""
from dataclasses import asdict
import copy
import hashlib
import time
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from .evaluate import source_identity
from .followup_data import coverage,EVENTS
from .policy import configure_cpu
from .wm_data import Normaliser,logical_hash
from .wm_state import INDEX,PILE_END,TARGET_FLOORS,delta_target
from .world_model import ModelConfig,DynamicsEnsemble


def torch_decode(state,changes):
    dynamic=state[:,:PILE_END]+changes[:,:PILE_END]
    yaw=torch.atan2(dynamic[:,2].sin(),dynamic[:,2].cos())
    dynamic=torch.cat((dynamic[:,:2],yaw[:,None],dynamic[:,3:]),dim=1)
    step=INDEX['step_index']
    context=torch.cat((state[:,PILE_END:step],state[:,step:step+1]+1,state[:,step+1:]),dim=1)
    return torch.cat((dynamic,context),dim=1)


def mass_residual(states):
    density=states[:,INDEX['density_kg_m3']]
    return states[:,15:PILE_END].sum(1)*.25*density+states[:,7:10].sum(1)-states[:,INDEX['initial_mass_kg']]


def fit_state(train,validation,episodes,*,material=False,multistep=False,epochs=40):
    config=ModelConfig(hidden=64,epochs=epochs);started=time.perf_counter()
    inputs=np.column_stack((train['state'],train['action']));targets=delta_target(train['state'],train['next_state'],train['reward'])
    xn,yn=Normaliser.fit(inputs),Normaliser.fit(targets,TARGET_FLOORS);model=DynamicsEnsemble(config,xn,yn)
    states=torch.as_tensor(train['state'],dtype=torch.float64);actions=torch.as_tensor(train['action'],dtype=torch.float64);ys=torch.as_tensor(yn.scale);ym=torch.as_tensor(yn.mean)
    xmean=torch.as_tensor(xn.mean);xscale=torch.as_tensor(xn.scale);labels=torch.as_tensor(train['events'],dtype=torch.float32)
    target=torch.as_tensor(yn.transform(targets),dtype=torch.float32);next_states=torch.as_tensor(train['next_state'],dtype=torch.float64)
    event_weight=((len(labels)-labels.sum(0))/labels.sum(0).clamp_min(1)).clamp(1,200)
    _,sampling=coverage(train);sampling=sampling/sampling.sum();episode_indices=np.asarray(train['episode_id']);step_indices=np.asarray(train['step']);histories=[];best=None;best_score=float('inf');updates=0
    vx=torch.as_tensor(xn.transform(np.column_stack((validation['state'],validation['action']))),dtype=torch.float32).clamp(-10,10);vy=torch.as_tensor(yn.transform(delta_target(validation['state'],validation['next_state'],validation['reward'])),dtype=torch.float32)
    optimisers=[torch.optim.Adam(m.parameters(),lr=.001) for m in model.models]
    bootstraps=[]
    for seed in config.seeds:
        rng=np.random.default_rng(seed);chosen=rng.integers(0,len(episodes),len(episodes));indices=np.concatenate([np.arange(episodes[i]['start'],episodes[i]['stop']) for i in chosen]);weights=sampling[indices];weights/=weights.sum();bootstraps.append((rng,indices,weights,chosen.tolist()))
    for epoch in range(1,epochs+1):
        losses=[]
        for member,optimiser,(rng,pool,weights,_) in zip(model.models,optimisers,bootstraps):
            for _ in range(max(1,int(np.ceil(len(pool)/256)))):
                batch=rng.choice(pool,min(256,len(pool)),replace=True,p=weights);current=states[batch];total=0;active=np.ones(len(batch),dtype=bool)
                max_horizon=4 if multistep else 1
                for h in range(1,max_horizon+1):
                    future=batch+h-1;safe=np.minimum(future,len(states)-1);active &= (future<len(states))&(episode_indices[safe]==episode_indices[batch])&(step_indices[safe]==step_indices[batch]+h-1)
                    if not active.any():break
                    features=((torch.cat((current,actions[safe]),1)-xmean)/xscale).clamp(-10,10).float();prediction,logits=member(features);changes=prediction.double()*ys+ym;following=torch_decode(current,changes)
                    if multistep and h==3:current=following;continue
                    selected=torch.from_numpy(active.copy());step_loss=F.mse_loss(prediction[selected],target[safe][selected]) if h==1 else F.mse_loss(((following[selected,:PILE_END]-next_states[safe][selected,:PILE_END])/ys[:PILE_END]).float()/h,torch.zeros_like(following[selected,:PILE_END],dtype=torch.float32))
                    step_loss=step_loss+.1*F.binary_cross_entropy_with_logits(logits[selected],labels[safe][selected],pos_weight=event_weight)
                    if material:
                        step_loss=step_loss+(mass_residual(following[selected])/100).square().mean().float()+F.relu(-following[selected,7:10]/100).square().mean().float()+F.relu(-following[selected,15:PILE_END]/.01).square().mean().float()
                    total=total+step_loss/max_horizon;current=following
                if not torch.isfinite(total):raise FloatingPointError('non-finite multistep/material loss')
                optimiser.zero_grad();total.backward();torch.nn.utils.clip_grad_norm_(member.parameters(),1,error_if_nonfinite=True);optimiser.step();updates+=1;losses.append(float(total.detach()))
        with torch.no_grad():
            predicted=torch.stack([m(vx)[0] for m in model.models]).mean(0);score=float(F.mse_loss(predicted,vy))
        if score<best_score:best_score=score;best=copy.deepcopy(model.state_dict());best_epoch=epoch
        histories.append({'epoch':epoch,'train_loss':float(np.mean(losses)),'validation_normalised_mse':score})
    model.load_state_dict(best)
    report={'source':source_identity(),'configuration':asdict(config),'normalisers_fitted_on':'training_only','training_dataset_sha256':logical_hash(train,episodes),
        'material_loss':{'enabled':material,'conservation_residual_scale_kg':100,'projection':False},'horizons_trained':[1,2,4] if multistep else [1],
        'episode_bootstraps':[{'seed':s,'episode_draws':b[3]} for s,b in zip(config.seeds,bootstraps)],'balanced_regime_sampling':coverage(train)[0],
        'selected_epoch':best_epoch,'selection':'lowest validation one-step normalised MSE; first tie','history':histories,'optimiser_updates':updates,'training_wall_s':time.perf_counter()-started}
    return model,report


class ObservationModel(nn.Module):
    def __init__(self,mean,scale,target_mean,target_scale,hidden=64):
        super().__init__();self.net=nn.Sequential(nn.Linear(69,hidden),nn.SiLU(),nn.Linear(hidden,hidden),nn.SiLU(),nn.Linear(hidden,71))
        for name,value in [('input_mean',mean),('input_scale',scale),('target_mean',target_mean),('target_scale',target_scale)]:self.register_buffer(name,torch.as_tensor(value,dtype=torch.float32))
    def forward(self,observation,action):
        x=torch.cat((observation,action),1);out=self.net(((x-self.input_mean)/self.input_scale).clamp(-10,10));delta=out[:,:41]*self.target_scale+self.target_mean
        return torch.cat((observation[:,:40]+delta[:,:40],out[:,41:66].sigmoid()),1),delta[:,40],out[:,66:]
    @torch.no_grad()
    def predict(self,observation,action):
        obs,reward,events=self(torch.as_tensor(observation,dtype=torch.float32),torch.as_tensor(action,dtype=torch.float32))
        return {'observation':obs.numpy(),'reward':reward.numpy(),'events':events.sigmoid().numpy(),'hidden_material_state':'unobserved; no full-state reconstruction is claimed'}


def fit_observable(train,validation,epochs=40):
    configure_cpu(101);started=time.perf_counter();xn=Normaliser.fit(np.column_stack((train['observation'],train['action'])));yn=Normaliser.fit(np.column_stack((train['next_observation'][:,:40]-train['observation'][:,:40],train['reward'])),np.array([.005]*40+[.001]))
    model=ObservationModel(xn.mean,xn.scale,yn.mean,yn.scale);optimiser=torch.optim.Adam(model.parameters(),lr=.001);rng=np.random.default_rng(101);obs=torch.as_tensor(train['observation'],dtype=torch.float32);action=torch.as_tensor(train['action'],dtype=torch.float32);following=torch.as_tensor(train['next_observation'],dtype=torch.float32);events=torch.as_tensor(train['event_targets'],dtype=torch.float32);reward=torch.as_tensor(train['reward'],dtype=torch.float32);history=[];_,weights=coverage(train);weights/=weights.sum()
    for epoch in range(1,epochs+1):
        losses=[]
        for _ in range(max(1,int(np.ceil(len(obs)/256)))):
            indices=rng.choice(len(obs),min(256,len(obs)),p=weights);pred,r,event=model(obs[indices],action[indices]);valid=following[indices,40:]
            # Missing range values are not treated as observed empty space.
            continuous=(pred[:,:40]-following[indices,:40])/model.target_scale[:40];continuous[:,15:40]*=valid
            loss=continuous.square().mean()+.1*F.mse_loss(r,reward[indices])+.1*F.binary_cross_entropy(pred[:,40:].clamp(1e-6,1-1e-6),valid)+.1*F.binary_cross_entropy_with_logits(event,events[indices])
            if not torch.isfinite(loss):raise FloatingPointError('non-finite observable model')
            optimiser.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1,error_if_nonfinite=True);optimiser.step();losses.append(float(loss.detach()))
        history.append({'epoch':epoch,'loss':float(np.mean(losses))})
    return model,{'source':source_identity(),'input':'65 current onboard observation features plus four actions; no privileged state or future inputs','output':'next local observation, reward, five events; full hidden-pile mass unavailable','epochs':epochs,'history':history,'training_wall_s':time.perf_counter()-started,'normalisers_fitted_on':'training_only'}


class EventModel(nn.Module):
    def __init__(self,mean,scale):
        super().__init__();self.register_buffer('mean',torch.as_tensor(mean,dtype=torch.float32));self.register_buffer('scale',torch.as_tensor(scale,dtype=torch.float32));self.net=nn.Sequential(nn.Linear(106,64),nn.SiLU(),nn.Linear(64,64),nn.SiLU(),nn.Linear(64,len(EVENTS)))
    def forward(self,x):return self.net(((x-self.mean)/self.scale).clamp(-10,10))
    @torch.no_grad()
    def predict(self,state,action):return self(torch.as_tensor(np.column_stack((state,action)),dtype=torch.float32)).sigmoid().numpy()


def fit_events(train,epochs=40):
    configure_cpu(211);started=time.perf_counter();inputs=np.column_stack((train['state'],train['action']));normal=Normaliser.fit(inputs);model=EventModel(normal.mean,normal.scale);x=torch.as_tensor(inputs,dtype=torch.float32);y=torch.as_tensor(train['event_targets'],dtype=torch.float32);positive=((len(y)-y.sum(0))/y.sum(0).clamp_min(1)).clamp(1,200);optimiser=torch.optim.Adam(model.parameters(),lr=.001);rng=np.random.default_rng(211);history=[]
    for epoch in range(1,epochs+1):
        losses=[]
        for start in range(0,len(x),256):
            index=rng.integers(0,len(x),min(256,len(x)));loss=F.binary_cross_entropy_with_logits(model(x[index]),y[index],pos_weight=positive)
            if not torch.isfinite(loss):raise FloatingPointError('non-finite event model')
            optimiser.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1,error_if_nonfinite=True);optimiser.step();losses.append(float(loss.detach()))
        history.append({'epoch':epoch,'loss':float(np.mean(losses))})
    return model,{'source':source_identity(),'event_names':EVENTS,'input':'privileged current state/action baseline; separate from onboard observation model','class_weights':positive.tolist(),'history':history,'training_wall_s':time.perf_counter()-started}
