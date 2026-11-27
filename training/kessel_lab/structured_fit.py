"""Fixed-budget training of local heads; known decoder priors are not fitted."""
import numpy as np
import torch
from torch.nn import functional as F

from kessel_training import checkpoints
from kessel_training.policy import configure_cpu
from kessel_training.wm_state import TARGET_FLOORS, delta_target
from .structured_model import StructuredModel, cell_features, flux_context, local_features, sample_height
from kessel_training.kinematics import components


def fit(data,episodes,budget):
    configure_cpu(7,threads=1)
    state = data["state"]; following = data["next_state"]; action = data["action"]
    targets = delta_target(state,following,data["reward"])
    scale = np.maximum(targets.std(axis=0),TARGET_FLOORS)
    model = StructuredModel(scale)
    local = torch.as_tensor(local_features(state,action)); cells = cell_features(state,action)
    acceleration = (following[:,3]-state[:,3])/.1
    front = components(state[:,:3],state[:,4:7])["front"]
    constrained = (sample_height(state,front) > .5)&(abs(following[:,3]) < .03)&(following[:,11] > state[:,11])
    motion_valid = (abs(acceleration) <= 1.50001)&~constrained
    capacity = flux_context(state,action,following)
    removed = np.maximum(0,state[:,15:79]-following[:,15:79])*state[:,None,81]*.25
    eligible = capacity > 1e-6
    raw_fraction = np.divide(removed,capacity,out=np.zeros_like(removed),where=eligible)
    fraction = np.clip(raw_fraction,0,1).astype(np.float32)
    flat_cells = torch.as_tensor(cells.reshape(-1,12)); cell_target = torch.as_tensor(fraction.ravel())
    cell_weight = torch.as_tensor(np.minimum((capacity.ravel()/25)**2,20).astype(np.float32))
    acc_target = torch.as_tensor(np.clip(acceleration/1.5,-1,1),dtype=torch.float32)
    events = torch.as_tensor(data["events"],dtype=torch.float32); histories = []
    for member,seed in zip(model.members,(101,211,307)):
        rng = np.random.default_rng(seed); drawn = rng.integers(0,len(episodes),len(episodes))
        pool = np.concatenate([np.arange(episodes[i]["start"],episodes[i]["stop"]) for i in drawn])
        motion_pool = pool[motion_valid[pool]]
        cell_ids = (pool[:,None]*64+np.arange(64)).ravel()
        cell_pool = cell_ids[eligible.ravel()[cell_ids]]
        positive = cell_pool[fraction.ravel()[cell_pool] > 1e-6]
        zero = cell_pool[fraction.ravel()[cell_pool] <= 1e-6]
        if not len(motion_pool) or not len(positive) or not len(zero): raise ValueError("bootstrap lacks motion/material coverage")
        optimiser = torch.optim.Adam(member.parameters(),lr=.002); history = []
        for update in range(750):
            budget.charge("updates")
            motion_rows = rng.choice(motion_pool,256,replace=True); event_rows = rng.choice(pool,256,replace=True)
            cell_rows = np.concatenate((rng.choice(positive,256,replace=True),rng.choice(zero,256,replace=True)))
            motion_loss = F.mse_loss(member.motion(local[motion_rows,:22]).squeeze(-1).tanh(),acc_target[motion_rows])
            fraction_prediction = member.cells(flat_cells[cell_rows]).squeeze(-1).sigmoid()
            cell_loss = ((fraction_prediction-cell_target[cell_rows]).square()*cell_weight[cell_rows]).mean()
            event_loss = F.binary_cross_entropy_with_logits(member.events(local[event_rows]),events[event_rows],pos_weight=torch.tensor([5.,1.,1.,5.]))
            total = motion_loss+cell_loss+.1*event_loss
            if not torch.isfinite(total): raise FloatingPointError("nonfinite structured-head loss")
            optimiser.zero_grad(); total.backward()
            for module in (member.motion,member.cells,member.events): torch.nn.utils.clip_grad_norm_(module.parameters(),1.,error_if_nonfinite=True)
            optimiser.step()
            history.append({"update":update+1,"motion":float(motion_loss.detach()),"material":float(cell_loss.detach()),"events":float(event_loss.detach())})
        histories.append({"seed":seed,"episode_draws":drawn.tolist(),"history":history})
    model.eval()
    return model,{"kind":"structured-local-dynamics-v1","members":3,"member_seeds":[101,211,307],"updates_per_member":750,
        "optimiser_updates":2250,"input_scaling":"declared physical constants; no validation fitting",
        "target_scaling":"training-only standard deviation with frozen physical floors","target_scale":scale.tolist(),
        "effective_motion_rows":int(motion_valid.sum()),"event_training_rows":len(state),"eligible_cell_targets":int(eligible.sum()),
        "fraction_targets_clipped":int((raw_fraction[eligible] > 1).sum()),"bootstrap_histories":histories,
        "priors":["kinematics","joint/speed bounds","swept geometric collision","nonnegative material flux",
                  "throughput and bucket capacity","release accounting","event and reward rules"],
        "learned":["local acceleration","shared local extraction factors","separately reported event logits"]}


def save(path,model,report):
    return checkpoints.save(path,{"kind":"structured-local-dynamics-v1","weights":model.state_dict(),"training":report})


def load(path):
    payload = checkpoints.load(path)
    if payload["kind"] != "structured-local-dynamics-v1": raise ValueError("structured checkpoint kind differs")
    model = StructuredModel(payload["training"]["target_scale"]); model.load_state_dict(payload["weights"]); model.eval()
    if not all(torch.isfinite(p).all() for p in model.parameters()): raise ValueError("invalid structured weights")
    return model,payload["training"]
