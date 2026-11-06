"""Export deterministic actor weights and their exact preprocessing as ONNX."""

import numpy as np
import onnx
from onnx import helper, numpy_helper, TensorProto
import torch

from .offline_runtime import OfflinePolicy, flatten_observation


def export_actor(policy,path):
    scales=np.concatenate((policy.proprio_scale.detach().numpy(),np.full(25,float(policy.height_scale)),np.ones(25))).astype(np.float32)
    initialisers=[numpy_helper.from_array(scales,"physical_scales"),numpy_helper.from_array(np.array(-5,dtype=np.float32),"low"),numpy_helper.from_array(np.array(5,dtype=np.float32),"high")]
    nodes=[helper.make_node("Div",["observation","physical_scales"],["scaled"]),helper.make_node("Clip",["scaled","low","high"],["features"])]
    previous="features"
    for i,index in enumerate((0,2,4)):
        layer=policy.actor[index];weight=f"weight_{i}";bias=f"bias_{i}"
        initialisers.extend((numpy_helper.from_array(layer.weight.detach().numpy().T.copy(),weight),numpy_helper.from_array(layer.bias.detach().numpy().copy(),bias)))
        out="action" if i==2 else f"hidden_{i}"
        nodes.extend((helper.make_node("MatMul",[previous,weight],[f"matmul_{i}"]),helper.make_node("Add",[f"matmul_{i}",bias],[f"biased_{i}"]),helper.make_node("Tanh",[f"biased_{i}"],[out])))
        previous=out
    graph=helper.make_graph(nodes,"kessel-offline-actor",[helper.make_tensor_value_info("observation",TensorProto.FLOAT,["batch",65])],
        [helper.make_tensor_value_info("action",TensorProto.FLOAT,["batch",4])],initialisers)
    model=helper.make_model(graph,opset_imports=[helper.make_opsetid("",18)],producer_name="Kessel");model.ir_version=10
    helper.set_model_props(model,{"normalisation":"fixed_physical_scales_v1","action_units":"normalised [-1,1]","frame":"x-forward/y-left/z-up","scope":"synthetic research; no machine-control qualification"})
    onnx.checker.check_model(model,full_check=True);onnx.save(model,str(path))
    return model


@torch.no_grad()
def torch_actions(policy,flat):
    from .imagination import observation_from_flat
    return policy.actor(policy.encode(observation_from_flat(flat))).tanh().numpy()


class EvaluationAdapter:
    def __init__(self,path):self.runtime=OfflinePolicy(path)
    def encode(self,observation):return flatten_observation(observation)
    def sample(self,features,deterministic=True):
        if not deterministic:raise ValueError("offline evaluation exports deterministic actors")
        return {"action":torch.from_numpy(self.runtime.infer_flat(features))}
