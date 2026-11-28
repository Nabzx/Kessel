"""Observation-only residual forecasts. No privileged state or simulator transition."""
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from kessel_training import checkpoints

P_SCALE = np.array([10,5,1,1,2,.6,1.1,1,3500,15,5,.2,1,1,1.],dtype=float)
FLOORS = np.array([.005,.005,.001,.001,.01,.001,.001,.001,1,.01,.01,.02,1,1,.01])


def flatten(observation):
    if set(observation) != {"proprio","local_height_m","range_valid"}: raise ValueError("only numeric sensor observations are accepted")
    p = np.asarray(observation["proprio"],dtype=float); height = np.asarray(observation["local_height_m"],dtype=float); mask = np.asarray(observation["range_valid"],dtype=float)
    if p.ndim != 2 or p.shape[1] != 15 or not len(p) or height.shape != (len(p),5,5) or mask.shape != height.shape: raise ValueError("sensor batch shape differs")
    if not all(np.isfinite(v).all() for v in (p,height,mask)) or (height < 0).any() or not np.isin(mask,(0,1)).all() or not np.isin(p[:,12],(0,1)).all() or (p[:,11] < 0).any(): raise ValueError("finite valid sensor channels required")
    fresh = (p[:,12] == 1)&(p[:,11] <= .2+1e-9); mask = mask*fresh[:,None,None]
    return np.concatenate((p,height.reshape(-1,25)*mask.reshape(-1,25),mask.reshape(-1,25)),axis=1)


def observations(flat): return {"proprio":flat[:,:15],"local_height_m":flat[:,15:40].reshape(-1,5,5),"range_valid":flat[:,40:65].reshape(-1,5,5)}


def features(current,action,previous,previous_action,present):
    current = np.asarray(current,dtype=float); previous = np.asarray(previous,dtype=float)
    action = np.asarray(action,dtype=float); previous_action = np.asarray(previous_action,dtype=float); present = np.asarray(present,dtype=bool)
    n = len(current)
    if current.shape != (n,65) or previous.shape != (n,65) or action.shape != (n,4) or previous_action.shape != (n,4) or present.shape != (n,): raise ValueError("causal feature shape differs")
    if not all(np.isfinite(v).all() for v in (current,previous,action,previous_action)) or (abs(action) > 1).any() or (abs(previous_action) > 1).any(): raise ValueError("finite normalised actions and sensors required")
    current = current.copy(); previous = previous.copy(); origin = current[:,:2].copy()
    current[:,:2] = 0; previous[:,:2] -= origin; current[:,13] = previous[:,13] = 0
    scale = np.r_[P_SCALE,np.full(25,1.5),np.ones(25)]
    previous = previous/scale; previous[~present] = 0; previous_action = previous_action.copy(); previous_action[~present] = 0
    encoded = np.column_stack((current/scale,action,previous,previous_action,present)).astype(np.float32)
    if not np.isfinite(encoded).all() or (abs(encoded) > 1e6).any(): raise ValueError("sensor features exceed numerical envelope")
    return encoded


class Member(nn.Module):
    def __init__(self):
        super().__init__(); self.network = nn.Sequential(nn.Linear(139,128),nn.SiLU(),nn.Linear(128,128),nn.SiLU(),nn.Linear(128,65))
        nn.init.zeros_(self.network[-1].weight); nn.init.zeros_(self.network[-1].bias)
    def forward(self,x): return self.network(x)


class SensorModel(nn.Module):
    def __init__(self,proprio_scale,height_scale):
        super().__init__(); self.members = nn.ModuleList()
        for seed in (101,211,307): torch.manual_seed(seed); self.members.append(Member())
        self.register_buffer("proprio_scale",torch.as_tensor(proprio_scale,dtype=torch.float64)); self.register_buffer("height_scale",torch.as_tensor(height_scale,dtype=torch.float64))

    @torch.no_grad()
    def predict(self,observation,action,previous_observation=None,previous_action=None,history_present=None):
        current = flatten(observation); n = len(current)
        previous = np.zeros_like(current) if previous_observation is None else flatten(previous_observation)
        past_action = np.zeros((n,4)) if previous_action is None else np.asarray(previous_action,dtype=float)
        present = np.full(n,previous_observation is not None) if history_present is None else np.asarray(history_present,dtype=bool)
        x = features(current,action,previous,past_action,present); tensor = torch.as_tensor(x)
        outputs = []
        for member in self.members:
            raw = member(tensor).numpy().astype(float); p = current[:,:15]+raw[:,:15]*self.proprio_scale.numpy()
            norm = np.linalg.norm(p[:,2:4],axis=1); p[:,2:4] /= np.maximum(norm,1e-8)[:,None]
            p[:,8] = np.clip(p[:,8],0,3500); p[:,11] = np.maximum(0,p[:,11]); p[:,12] = torch.sigmoid(torch.as_tensor(raw[:,12])).numpy()
            p[:,13] = current[:,13]+.1; p[:,14] = np.clip(p[:,14],0,1)
            height = np.maximum(0,current[:,15:40]+raw[:,15:40]*self.height_scale.numpy())
            validity = torch.sigmoid(torch.as_tensor(raw[:,40:65])).numpy()
            outputs.append(np.column_stack((p,height,validity)))
        stack = np.stack(outputs); mean = stack.mean(axis=0); mean[:,2:4] /= np.maximum(np.linalg.norm(mean[:,2:4],axis=1),1e-8)[:,None]
        uncertainty = stack.std(axis=0); current_mask = current[:,40:65]
        square = (uncertainty[:,0]/.05)**2+(uncertainty[:,1]/.05)**2+(uncertainty[:,4]/.05)**2+(uncertainty[:,8]/50)**2
        square += ((uncertainty[:,15:40]/.05)**2*current_mask).sum(axis=1)
        score = np.sqrt(square/(4+current_mask.sum(axis=1)))
        usable = (current[:,12] == 1)&(current[:,11] <= .2+1e-9)&(current_mask.sum(axis=1) >= 5)
        return {"observation":mean,"disagreement":score,"input_usable":usable,"source":"sensor_observation_residual_ensemble",
                "known_priors":["nonnegative height","unit heading","rated load range","0.1-second scheduled clock"],"privileged_inputs":False}


def fit(data,episodes,budget):
    current = data["observation"]; target = data["next_observation"]
    delta = target[:,:15]-current[:,:15]; pscale = np.maximum(delta.std(axis=0),FLOORS); pscale[12:14] = 1
    hscale = np.maximum((target[:,15:40]-current[:,15:40]).std(axis=0),.01)
    model = SensorModel(pscale,hscale); x = torch.as_tensor(features(current,data["action"],data["previous_observation"],data["previous_action"],data["history_present"]))
    y = torch.as_tensor(delta/pscale,dtype=torch.float32); heights = torch.as_tensor((target[:,15:40]-current[:,15:40])/hscale,dtype=torch.float32)
    masks = torch.as_tensor(target[:,40:65],dtype=torch.float32); fresh = torch.as_tensor(target[:,12],dtype=torch.float32)
    pids = [i for i in range(15) if i not in (12,13)]; histories = []
    for member,seed in zip(model.members,(101,211,307)):
        rng = np.random.default_rng(seed); drawn = rng.integers(0,len(episodes),len(episodes))
        pool = np.concatenate([np.arange(episodes[i]["start"],episodes[i]["stop"]) for i in drawn if episodes[i]["stop"] > episodes[i]["start"]])
        optimiser = torch.optim.Adam(member.parameters(),lr=.001); history = []
        for step in range(750):
            budget.charge("updates"); rows = rng.choice(pool,256,replace=True); raw = member(x[rows])
            ploss = F.mse_loss(raw[:,pids],y[rows][:,pids])
            hloss = ((raw[:,15:40]-heights[rows]).square()*masks[rows]).sum()/masks[rows].sum().clamp_min(1)
            vloss = F.binary_cross_entropy_with_logits(raw[:,40:65],masks[rows]); floss = F.binary_cross_entropy_with_logits(raw[:,12],fresh[rows])
            loss = ploss+hloss+.25*vloss+.1*floss
            if not torch.isfinite(loss): raise FloatingPointError("nonfinite sensor loss")
            optimiser.zero_grad(); loss.backward(); nn.utils.clip_grad_norm_(member.parameters(),1.,error_if_nonfinite=True); optimiser.step()
            history.append({"update":step+1,"proprio":float(ploss.detach()),"height":float(hloss.detach()),"validity":float(vloss.detach()),"freshness":float(floss.detach())})
        histories.append({"seed":seed,"episode_draws":drawn.tolist(),"history":history})
    model.eval()
    return model,{"kind":"sensor_residual_ensemble_v1","input_dimension":139,"target_dimension":65,"proprio_scale":pscale.tolist(),"height_scale":hscale.tolist(),
                  "normalisation":"training only; physical feature constants","updates":2250,"members":histories,"privileged_inputs":False,"simulator_queries":0}


def save(path,model,metadata): return checkpoints.save(path,{"kind":"sensor_residual_ensemble_v1","weights":model.state_dict(),"metadata":metadata})


def load(path):
    payload = checkpoints.load(path)
    if payload["kind"] != "sensor_residual_ensemble_v1": raise ValueError("sensor checkpoint kind differs")
    metadata = payload["metadata"]; model = SensorModel(metadata["proprio_scale"],metadata["height_scale"])
    model.load_state_dict(payload["weights"]); model.eval()
    if not all(torch.isfinite(p).all() for p in model.parameters()): raise ValueError("nonfinite sensor weights")
    return model,metadata
