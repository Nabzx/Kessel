"""Learned local motion/material heads with explicit reference-specific priors."""
import numpy as np
import torch
from torch import nn

from kessel_training.contracts import LoaderConfig
from kessel_training.kinematics import advance, components, footprints
from kessel_training.wm_state import INDEX, TARGET_FLOORS, delta_target


def sample_height(state,points):
    ij = np.floor((points-state[:,79:81])/.5).astype(int)
    valid = ((ij >= 0)&(ij < 8)).all(axis=1)
    grid = state[:,15:79].reshape(-1,8,8)
    return np.where(valid,grid[np.arange(len(state)),np.clip(ij[:,0],0,7),np.clip(ij[:,1],0,7)],0.)


def local_features(state,action):
    g = components(state[:,:3],state[:,4:7]); receiver = state[:,88:90]-g["mouth"]
    front = sample_height(state,g["front"]); mouth = sample_height(state,g["mouth"])
    present = state[:,101] > .5
    fore = np.where(present,np.maximum(0,state[:,97]-g["mouth"][:,0]),12.)
    rear = np.where(present,np.maximum(0,state[:,0]-1.9-state[:,98]),12.)
    return np.column_stack((state[:,3]/2,state[:,4]/.6,state[:,5]/1.1,state[:,6],state[:,7]/3500,
        np.sin(state[:,2]),np.cos(state[:,2]),state[:,83],state[:,84]/.1,state[:,85]/36000,action,
        front/1.5,mouth/1.5,state[:,14],state[:,11]/10,state[:,INDEX["step_index"]]/state[:,INDEX["max_steps"]],fore/12,rear/12,state[:,96]/.1,
        state[:,8]/2000,receiver[:,0]/15,receiver[:,1]/5)).astype(np.float32)


def cell_features(state,action):
    n = len(state); geometry = components(state[:,:3],state[:,4:7]); mouth = geometry["mouth"]
    gx,gy = np.meshgrid((np.arange(8)+.5)*.5,(np.arange(8)+.5)*.5,indexing="ij")
    centres = np.stack((gx.ravel(),gy.ravel()),axis=1)[None]+state[:,None,79:81]
    difference = centres-mouth[:,None]; yaw = state[:,2]+state[:,4]
    along = difference[...,0]*np.cos(yaw[:,None])+difference[...,1]*np.sin(yaw[:,None])
    across = -difference[...,0]*np.sin(yaw[:,None])+difference[...,1]*np.cos(yaw[:,None])
    height = state[:,15:79]; bottom = geometry["bucket_height"]
    available = np.minimum(np.maximum(height-bottom[:,None],0),.7)
    broadcast = lambda value:np.broadcast_to(value[:,None],(n,64))
    values = (height/1.5,available/.7,along/2,across/2,broadcast(bottom/2),broadcast(state[:,7]/3500),
              broadcast(state[:,3]/2),broadcast(state[:,5]/1.1),broadcast(state[:,6]),
              broadcast(action[:,0]),broadcast(action[:,2]),broadcast(action[:,3]))
    return np.stack(values,axis=-1).astype(np.float32)


def swept_collision(current,proposed):
    old = footprints(current[:,:3],current[:,4:7]); new = footprints(proposed[:,:3],proposed[:,4:7])
    rear = (proposed[:,2]-current[:,2]+np.pi)%(2*np.pi)-np.pi
    front = rear+proposed[:,4]-current[:,4]
    padding = np.stack((rear,front,front),axis=1)**2+1e-10
    low = np.minimum(old.min(axis=2),new.min(axis=2))-padding[...,None]
    high = np.maximum(old.max(axis=2),new.max(axis=2))+padding[...,None]
    wall = ((low[...,0] < -11)|(high[...,0] > 18)|(low[...,1] < -current[:,None,86])|(high[...,1] > current[:,None,86])).any(axis=1)
    roof = np.maximum(np.maximum(.35+2*np.sin(current[:,5]),.35+2*np.sin(proposed[:,5]))+.6,1.9) > current[:,87]
    obstacle = ((low[...,0] <= current[:,None,98])&(high[...,0] >= current[:,None,97])&
                (low[...,1] <= current[:,None,100])&(high[...,1] >= current[:,None,99])).any(axis=1)&(current[:,101] > .5)
    return wall|roof|obstacle


def flux_context(state,action,proposed):
    old = components(state[:,:3],state[:,4:7]); new = components(proposed[:,:3],proposed[:,4:7])
    gx,gy = np.meshgrid((np.arange(8)+.5)*.5,(np.arange(8)+.5)*.5,indexing="ij")
    centres = np.stack((gx.ravel(),gy.ravel()),axis=1)[None]+state[:,None,79:81]
    masks = []
    for pose,g in ((state,old),(proposed,new)):
        d = centres-g["mouth"][:,None]; yaw = pose[:,2]+pose[:,4]
        along = d[...,0]*np.cos(yaw[:,None])+d[...,1]*np.sin(yaw[:,None])
        across = -d[...,0]*np.sin(yaw[:,None])+d[...,1]*np.cos(yaw[:,None])
        masks.append((abs(along) <= .75)&(abs(across) <= .9))
    bottom = np.minimum(old["bucket_height"],new["bucket_height"])
    available = np.minimum(np.maximum(state[:,15:79]-bottom[:,None],0),.7)*state[:,None,81]*.25
    travel = np.maximum(0,np.sum((new["mouth"]-old["mouth"])*old["front_forward"],axis=1))
    curl = np.maximum(0,proposed[:,6]-state[:,6])
    activity = np.clip(travel/.6+curl*1.5,0,1)
    return available*activity[:,None]*(masks[0]|masks[1])


def decode(state,action,acceleration,fraction):
    """Known kinematics/bounds/events/accounting; no environment transition call."""
    out = state.copy(); pose = state[:,:3].copy(); joints = state[:,4:7].copy(); speed = state[:,3].copy()
    dt = state[:,96]
    # All frozen reference data use the same 0.1 s actuation interval.
    if not np.allclose(dt,.1,atol=1e-12,rtol=0): raise ValueError("structured predictor requires 0.1-second state context")
    collision = np.zeros(len(state),dtype=bool); elapsed = np.zeros(len(state)); wheels = np.zeros((len(state),4))
    # Five known kinematic increments preserve the declared swept-envelope
    # resolution. Acceleration and extraction still come from fitted heads.
    for _ in range(5):
        active = ~collision; previous = out.copy(); old_pose = pose.copy(); old_joints = joints.copy()
        advance(pose,speed,joints,wheels,action*active[:,None],np.clip(acceleration,-1.5,1.5)*active,LoaderConfig(),.02)
        out[:,:3] = pose; out[:,3] = speed; out[:,4:7] = joints
        hit = swept_collision(previous,out)&active
        front = components(out[:,:3],out[:,4:7])["front"]
        blocked = (sample_height(state,front) > .5)&(speed > 0)&active
        rollback = hit|blocked|~active
        pose[rollback] = old_pose[rollback]; speed[rollback] = 0
        joints[hit|~active] = old_joints[hit|~active]
        out[:,:3] = pose; out[:,3] = speed; out[:,4:7] = joints
        elapsed += .02*active; collision |= hit
    capacity = flux_context(state,action,out); removed = capacity*np.clip(fraction,0,1)
    removed[collision] = 0
    total = removed.sum(axis=1); room = np.minimum(np.maximum(3500-state[:,7],0),1200*dt)
    removed *= np.minimum(1,room/np.maximum(total,1e-12))[:,None]; gain = removed.sum(axis=1)
    out[:,15:79] = state[:,15:79]-removed/(state[:,None,81]*.25)
    available_load = state[:,7]+gain; survival = np.ones(len(state))
    # Explicit known release-rate prior, including within-decision curl changes.
    for step in range(1,6):
        curl = np.clip(state[:,6]+action[:,3]*.5*dt*step/5,-.7,1.)
        survival *= 1-3*dt/5*np.clip((-curl-.2)/.5,0,1)
    release = available_load*(1-survival); release[collision] = 0
    mouth = components(out[:,:3],out[:,4:7])["mouth"]
    inside = (abs(mouth-state[:,88:90]) <= state[:,90:92]).all(axis=1)
    delivery = np.where(inside,release,0); spill = release-delivery
    out[:,7] = available_load-release; out[:,8] = state[:,8]+delivery; out[:,9] = state[:,9]+spill
    out[:,10] = state[:,10]+elapsed; out[:,INDEX["step_index"]] = state[:,INDEX["step_index"]]+1
    immobile = (abs(action[:,0]) > .4)&(abs(out[:,3]) < .03)&(np.max(abs(out[:,4:7]-state[:,4:7]),axis=1)/dt < .01)&~collision
    out[:,11] = np.where(immobile,state[:,11]+dt,0.)
    requested = action[:,0]*np.minimum(22000,28000/np.maximum(abs(state[:,3]),.5))
    grip = state[:,83]*(10500+state[:,7])*9.81*np.cos(state[:,84]); drive = np.clip(requested,-grip,grip)
    slip = np.maximum(abs(requested)-grip,0)/np.maximum(abs(requested),1)
    distance = np.linalg.norm(out[:,:2]-state[:,:2],axis=1)
    effort = abs(drive)*np.maximum(distance,abs(action[:,0])*.01*dt)+abs(out[:,4:7]-state[:,4:7]).sum(axis=1)*1500
    out[:,12] = state[:,12]+effort; out[:,13] = state[:,13]+slip*dt; out[:,14] = slip
    stuck = out[:,11]+1e-12 >= state[:,INDEX["stuck_limit_s"]]
    success = out[:,8] >= state[:,INDEX["success_kg"]]
    terminal = collision|success|stuck
    truncated = (out[:,INDEX["step_index"]] >= state[:,INDEX["max_steps"]])&~terminal
    contact = (sample_height(state,components(state[:,:3],state[:,4:7])["mouth"]) > .35+2*np.sin(state[:,5]))|(gain > 1e-6)
    reward = (delivery-spill)/3500-.002*elapsed-3e-8*effort-.02*slip*dt-5*collision
    events = np.column_stack((terminal,truncated,contact,collision)).astype(float)
    return out,reward,events


class Member(nn.Module):
    def __init__(self):
        super().__init__()
        self.motion = nn.Sequential(nn.Linear(22,64),nn.SiLU(),nn.Linear(64,64),nn.SiLU(),nn.Linear(64,1))
        self.cells = nn.Sequential(nn.Linear(12,32),nn.SiLU(),nn.Linear(32,32),nn.SiLU(),nn.Linear(32,1))
        self.events = nn.Sequential(nn.Linear(25,32),nn.SiLU(),nn.Linear(32,32),nn.SiLU(),nn.Linear(32,4))


class StructuredModel(nn.Module):
    def __init__(self,target_scale):
        super().__init__(); self.members = nn.ModuleList()
        for seed in (101,211,307):
            torch.manual_seed(seed); self.members.append(Member())
        self.register_buffer("target_scale",torch.as_tensor(target_scale,dtype=torch.float64))
    @torch.no_grad()
    def predict(self,states,actions,ablation=False,learned_events=False):
        state = np.asarray(states,dtype=np.float64); action = np.asarray(actions,dtype=np.float64)
        if state.ndim != 2 or state.shape[1] != 102 or action.shape != (len(state),4) or not np.isfinite(state).all() or not np.isfinite(action).all():
            raise ValueError("finite state/action batches required")
        if (abs(action) > 1+1e-12).any(): raise ValueError("normalised actions required")
        x = torch.as_tensor(local_features(state,action)); cells = torch.as_tensor(cell_features(state,action))
        following = []; rewards = []; events = []; neural_events = []
        for member in self.members:
            acceleration = member.motion(x[:,:22]).squeeze(-1).tanh().numpy()*1.5
            fraction = member.cells(cells).squeeze(-1).sigmoid().numpy()
            if ablation: acceleration[:] = 0; fraction[:] = 0
            out,reward,event = decode(state,action,acceleration,fraction)
            following.append(out); rewards.append(reward); events.append(event); neural_events.append(member.events(x).sigmoid().numpy())
        mean = np.mean(following,axis=0); reward = np.mean(rewards,axis=0)
        changes = np.stack([delta_target(state,out,r) for out,r in zip(following,rewards)])
        normal = changes/self.target_scale.numpy()[None,None,:]
        return {"next_state":mean,"reward":reward,"events":np.mean(neural_events if learned_events else events,axis=0),
                "learned_events":np.mean(neural_events,axis=0),"disagreement":np.sqrt(normal.var(axis=0).mean(axis=1)),
                "input_envelope":np.max(abs(x.numpy()),axis=1),"predictor_kind":"learned_local_heads_with_explicit_kinematic_flux_event_priors"}
