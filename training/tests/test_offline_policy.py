from pathlib import Path
import os
os.environ["ORT_DISABLE_TELEMETRY"] = "1"

import numpy as np
import pytest

pytest.importorskip("onnxruntime")
pytest.importorskip("onnx")
from kessel_training.environment import LoaderEnv
from kessel_training.offline_policy import export_actor, torch_actions
from kessel_training.offline_runtime import OfflinePolicy, flatten_observation, requested_actuator_rates
from kessel_training.policy import ActorCritic, configure_cpu


def test_onnx_actor_matches_raw_preprocessing_masks_and_saturation_boundaries(tmp_path):
    configure_cpu(4);policy=ActorCritic(16);path=tmp_path/"actor.onnx";export_actor(policy,path)
    runtime=OfflinePolicy(path);flat=flatten_observation(LoaderEnv(3).observe())
    boundary=np.zeros((6,65),dtype=np.float32);boundary[:,:40]=np.asarray([-1e4,-5,-1,0,5,1e4])[:,None];boundary[:,40:]=np.arange(25)%2
    data=np.vstack((flat,boundary));np.testing.assert_allclose(runtime.infer_flat(data),torch_actions(policy,data),rtol=1e-5,atol=1e-6)
    assert runtime.session.get_providers()==["CPUExecutionProvider"]
    with pytest.raises(ValueError,match="hash differs"):OfflinePolicy(path,"bad")
    bad=data.copy();bad[0,40]=0.5
    with pytest.raises(ValueError,match="binary"):runtime.infer_flat(bad)
    with pytest.raises(ValueError,match="finite"):runtime.infer_flat(np.full((1,65),np.nan))
    np.testing.assert_allclose(requested_actuator_rates([1,-1,1,-1]),[1.5,-0.35,0.25,-0.5])


def test_quantised_matmul_really_uses_int8_weights_and_executes_on_cpu(tmp_path):
    from kessel_training.offline_experiment import quantise
    configure_cpu(8);policy=ActorCritic(16);fp=tmp_path/"actor.onnx";qp=tmp_path/"actor-int8.onnx"
    export_actor(policy,fp);report=quantise(fp,qp)
    assert report["int8_weight_matrices"]==3
    values=flatten_observation(LoaderEnv(4).observe());actual=OfflinePolicy(qp).infer_flat(values)
    assert np.isfinite(actual).all() and actual.shape==(4,4)
    assert np.max(np.abs(actual-torch_actions(policy,values)))<0.01


def test_onnx_closed_loop_uses_identical_reference_scenes(tmp_path):
    from kessel_training.environment import SceneConfig
    from kessel_training.evaluation import evaluate_controller
    from kessel_training.offline_policy import EvaluationAdapter
    configure_cpu(8);policy=ActorCritic(16);fp=tmp_path/"actor.onnx";export_actor(policy,fp)
    kwargs=dict(split="test",count=2,seed_offset=6600,scene_override=SceneConfig(max_steps=3))
    reference=evaluate_controller(policy,**kwargs);actual=evaluate_controller(EvaluationAdapter(fp),**kwargs)
    for p,q in zip(reference["cases"],actual["cases"]):
        assert p["scenario_sha256"]==q["scenario_sha256"] and p["reason"]==q["reason"]
        assert abs(p["delivered_kg"]-q["delivered_kg"])<1e-8
        assert abs(p["effort_proxy_j"]-q["effort_proxy_j"])<1e-3


def test_student_imitation_keeps_teacher_frozen_and_selects_actual_validation_loss():
    import json
    import torch
    from kessel_training.offline_experiment import distil, DEFAULT_PLAN
    configure_cpu(8);teacher=ActorCritic(32);before={k:v.clone() for k,v in teacher.state_dict().items()}
    plan=json.loads(DEFAULT_PLAN.read_text());plan.update(student_epochs=2,student_batch=4)
    train={"observation":flatten_observation(LoaderEnv(8,seed=3).observe())}
    validation={"observation":flatten_observation(LoaderEnv(4,seed=100003).observe())}
    student,report=distil(teacher,train,validation,plan)
    assert student.hidden==16 and report["optimiser_updates"]==4
    assert report["selected_epoch"]==min(report["history"],key=lambda r:r["current_validation_action_mse"])["epoch"]
    for k,v in before.items():torch.testing.assert_close(v,teacher.state_dict()[k],rtol=0,atol=0)


def test_packaged_standalone_runtime_executes_without_pytorch_and_matches_teacher():
    import json
    import subprocess
    import sys
    root=Path(__file__).resolve().parents[2];evidence=root/"docs/phase-11/offline-policy-evidence"
    manifest=json.loads((evidence/"files.json").read_text())
    digest=next(f["sha256"] for f in manifest["files"] if f["path"]=="teacher-fp32.onnx")
    from kessel_training.evaluation import load_policy
    teacher,_=load_policy(root/"docs/phase-11/rl-evidence/policies/policy-7.pt")
    runtime=OfflinePolicy(evidence/"teacher-fp32.onnx",digest)
    values=flatten_observation(LoaderEnv(4,seed=206600).observe())
    np.testing.assert_allclose(runtime.infer_flat(values),torch_actions(teacher,values),rtol=1e-5,atol=1e-6)
    code='''import importlib.util,sys,numpy as np
spec=importlib.util.spec_from_file_location("standalone",sys.argv[1]);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
runtime=module.OfflinePolicy(sys.argv[2],sys.argv[3]);x=np.zeros((1,65),dtype=np.float32);x[:,40:]=1
assert runtime.infer_flat(x).shape==(1,4)
assert "torch" not in sys.modules
assert module.os.environ["ORT_DISABLE_TELEMETRY"]=="1"
'''
    subprocess.run([sys.executable,"-I","-c",code,str(evidence/"offline_runtime.py"),str(evidence/"teacher-fp32.onnx"),digest],check=True,capture_output=True,text=True)
