"""Standalone NumPy/ONNX Runtime CPU actor. No training or PyTorch dependency."""

import hashlib
from pathlib import Path

import numpy as np
import onnxruntime as ort


def flatten_observation(observation):
    if set(observation)!={"proprio","local_height_m","range_valid"}:raise ValueError("local observation fields required")
    p=np.asarray(observation["proprio"],dtype=np.float32);h=np.asarray(observation["local_height_m"],dtype=np.float32);v=np.asarray(observation["range_valid"],dtype=np.float32)
    if p.ndim!=2 or p.shape[1]!=15 or h.shape!=(len(p),5,5) or v.shape!=h.shape:raise ValueError("invalid observation shape")
    return np.column_stack((p,h.reshape(len(p),25),v.reshape(len(p),25)))


class OfflinePolicy:
    def __init__(self,path,expected_sha256=None):
        path=Path(path)
        self.sha256=hashlib.sha256(path.read_bytes()).hexdigest()
        if expected_sha256 is not None and self.sha256!=expected_sha256:raise ValueError("offline model hash differs")
        options=ort.SessionOptions();options.intra_op_num_threads=1;options.inter_op_num_threads=1
        options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
        self.session=ort.InferenceSession(str(path),sess_options=options,providers=["CPUExecutionProvider"])
        if self.session.get_inputs()[0].name!="observation" or self.session.get_outputs()[0].name!="action":raise ValueError("unsupported actor graph")

    def infer_flat(self,values):
        values=np.asarray(values,dtype=np.float32)
        if values.ndim!=2 or values.shape[0]<1 or values.shape[1]!=65 or not np.isfinite(values).all():raise ValueError("finite N by 65 observation required")
        if not np.isin(values[:,40:],(0,1)).all():raise ValueError("range validity must be binary")
        action=self.session.run(["action"],{"observation":values})[0]
        if action.shape!=(len(values),4) or not np.isfinite(action).all() or (np.abs(action)>1).any():raise ValueError("invalid offline action")
        return action

    def act(self,observation):return self.infer_flat(flatten_observation(observation))


def requested_actuator_rates(action):
    """Synthetic acceleration request and joint rates, before traction/limits."""
    action=np.asarray(action,dtype=np.float64)
    if action.shape[-1:]!=(4,) or not np.isfinite(action).all() or (np.abs(action)>1).any():raise ValueError("bounded four-action array required")
    return action*np.array([1.5,0.35,0.25,0.5])
