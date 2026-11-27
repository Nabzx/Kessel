"""Rank-checked linear imitation. Tactical planning and braking stay conventional."""
import numpy as np
import torch
from torch import nn

from kessel_training import checkpoints

COLUMNS = ((0,1,2),(3,),(4,),(5,))


class LinearFeedback(nn.Module):
    def __init__(self):
        super().__init__(); self.network = nn.Linear(6,4,bias=False,dtype=torch.float64)
        nn.init.zeros_(self.network.weight); self.calls = 0
    def forward(self,features): return self.network(features).clamp(-1,1)
    @torch.no_grad()
    def action(self,features):
        x = np.asarray(features,dtype=np.float64)
        if x.ndim != 2 or x.shape[1] != 6 or not np.isfinite(x).all(): raise ValueError("six finite current feedback features required")
        self.calls += len(x)
        return self(torch.as_tensor(x)).numpy()


def fit(features,labels):
    x = np.asarray(features,dtype=np.float64); y = np.asarray(labels,dtype=np.float64)
    if x.ndim != 2 or x.shape[1] != 6 or y.shape != (len(x),4) or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("invalid imitation feature/label data")
    if (abs(y) > 1+1e-12).any(): raise ValueError("labels exceed the normalised action contract")
    model = LinearFeedback(); ranks = []; residuals = []; counts = []
    with torch.no_grad():
        for head,columns in enumerate(COLUMNS):
            usable = abs(y[:,head]) < 1-1e-8
            design = x[usable][:,columns]; target = y[usable,head]
            rank = int(np.linalg.matrix_rank(design))
            if rank != len(columns): raise ValueError("rank-deficient unsaturated actuator labels")
            coefficients,_,_,_ = np.linalg.lstsq(design,target,rcond=None)
            model.network.weight[head,list(columns)] = torch.as_tensor(coefficients)
            ranks.append(rank); residuals.append(float(abs(design@coefficients-target).max())); counts.append(int(usable.sum()))
    prediction = model.action(x); error = float(abs(prediction-y).max())
    if error > 1e-10: raise ValueError("declared linear hypothesis does not reproduce training labels")
    model.eval(); model.calls = 0
    return model,{"kind":"learned-linear-feedback-v1","input_features":["speed_error_m_s","bounded_integral","target_direction",
        "articulation_error_rad","boom_error_rad","bucket_error_rad"],"columns":[list(c) for c in COLUMNS],
        "ranks":ranks,"unsaturated_rows":counts,"max_unsaturated_residual":residuals,"max_training_action_error":error,
        "weight_matrix":model.network.weight.detach().numpy().tolist(),"least_squares_solves":4,"optimiser_updates":0,
        "planner":"conventional progress/traction/lane/setpoint memory","brake":"conventional bootstrap law; not fitted"}


def save(path,model,metadata):
    return checkpoints.save(path,{"kind":"learned-linear-feedback-v1","weights":model.state_dict(),"fit":metadata})


def load(path):
    payload = checkpoints.load(path)
    if payload["kind"] != "learned-linear-feedback-v1": raise ValueError("feedback checkpoint kind differs")
    model = LinearFeedback(); model.load_state_dict(payload["weights"]); model.eval()
    if not torch.isfinite(model.network.weight).all(): raise ValueError("non-finite feedback weights")
    return model,payload["fit"]
