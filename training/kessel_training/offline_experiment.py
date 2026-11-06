"""Bounded distillation/quantisation study with fixed teacher and fresh task cases."""

import os
os.environ["ORT_DISABLE_TELEMETRY"] = "1"

import argparse
import copy
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time

import numpy as np
import onnx
import onnxruntime as ort
ort.disable_telemetry_events()
from onnxruntime.quantization import quantize_dynamic, QuantType
from onnxruntime.quantization.shape_inference import quant_pre_process
import torch

from . import checkpoints
from .contracts import canonical_json
from .evaluation import evaluate_controller, load_policy
from .evaluate import source_identity
from .offline_policy import export_actor, torch_actions, EvaluationAdapter
from .offline_runtime import OfflinePolicy
from .policy import ActorCritic, configure_cpu
from .wm_data import load_partition, assert_disjoint
from .wm_experiment import write

ROOT=Path(__file__).resolve().parents[2]
DEFAULT_PLAN=Path(__file__).parent.parent/"experiments/offline-policy-study-v1.json"


def distil(teacher,train,validation,plan):
    configure_cpu(plan["student_seed"]);student=ActorCritic(plan["student_hidden"])
    x=torch.from_numpy(train["observation"].astype(np.float32));vx=torch.from_numpy(validation["observation"].astype(np.float32))
    from .imagination import observation_from_flat
    with torch.no_grad():
        features=teacher.encode(observation_from_flat(x));vfeatures=teacher.encode(observation_from_flat(vx))
        targets=teacher.actor(features).tanh();vtargets=teacher.actor(vfeatures).tanh()
    optimiser=torch.optim.Adam(student.actor.parameters(),lr=plan["student_learning_rate"])
    generator=torch.Generator().manual_seed(plan["student_seed"]+1)
    best=float("inf");best_weights=None;selected=0;history=[];updates=0;started=time.perf_counter()
    for epoch in range(1,plan["student_epochs"]+1):
        order=torch.randperm(len(x),generator=generator);losses=[]
        for ids in order.split(plan["student_batch"]):
            loss=(student.actor(features[ids]).tanh()-targets[ids]).square().mean()
            if not torch.isfinite(loss):raise ValueError("non-finite student loss")
            optimiser.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(student.actor.parameters(),1,error_if_nonfinite=True);optimiser.step()
            updates+=1;losses.append(float(loss.detach()))
        with torch.no_grad():score=float((student.actor(vfeatures).tanh()-vtargets).square().mean())
        if score<best:best=score;best_weights=copy.deepcopy(student.actor.state_dict());selected=epoch
        history.append({"epoch":epoch,"training_action_mse":float(np.mean(losses)),"current_validation_action_mse":score,"best_validation_action_mse":best})
    student.actor.load_state_dict(best_weights)
    return student,{"history":history,"selected_epoch":selected,"optimiser_updates":updates,"training_wall_s":time.perf_counter()-started,
        "training_rows":len(x),"validation_rows":len(vx),"objective":"teacher deterministic action MSE; no RL/environment update"}


def quantise(source,target):
    prepared=source.with_name(source.stem+"-shapes.onnx")
    quant_pre_process(str(source),str(prepared),skip_optimization=True)
    quantize_dynamic(str(prepared),str(target),weight_type=QuantType.QInt8,op_types_to_quantize=["MatMul"])
    model=onnx.load(str(target));count=sum(t.data_type==onnx.TensorProto.INT8 and len(t.dims)==2 for t in model.graph.initializer)
    if count!=3:raise ValueError("not all three actor matrices were quantised")
    return {"int8_weight_matrices":count,"operators":sorted({n.op_type for n in model.graph.node}),"preprocessed_sha256":hashlib.sha256(prepared.read_bytes()).hexdigest()}


def latency(fn,values,plan):
    for _ in range(plan["latency_warmups"]):fn(values)
    times=[]
    for _ in range(plan["latency_repetitions"]):
        started=time.perf_counter_ns();fn(values);times.append((time.perf_counter_ns()-started)/1000)
    return {"batch":1,"repetitions":len(times),"median_us":float(np.median(times)),"p95_us":float(np.quantile(times,0.95)),"min_us":min(times)}


def boundary_inputs(teacher):
    scales=np.concatenate((teacher.proprio_scale.numpy(),np.full(25,float(teacher.height_scale)),np.ones(25))).astype(np.float32)
    rows=[]
    for value in (-20,-5,-1,0,1,5,20):
        for mask in (0,1):
            row=scales*value;row[40:]=mask;rows.append(row)
    return np.asarray(rows,dtype=np.float32)


def run(dataset_directory,output,plan_path=DEFAULT_PLAN):
    plan=json.loads(Path(plan_path).read_text());source=source_identity();output=Path(output)
    if source["training_dirty"]:raise ValueError("commit inference study sources first")
    output.mkdir(parents=True,exist_ok=False)
    teacher,teacher_identity=load_policy(ROOT/plan["teacher"])
    train,tm=load_partition(dataset_directory,"train");validation,vm=load_partition(dataset_directory,"validation");test,test_manifest=load_partition(dataset_directory,"test")
    assert_disjoint([(train,tm["episodes"]),(validation,vm["episodes"]),(test,test_manifest["episodes"])])
    if len(train["reward"])!=plan["training_observations"] or len(validation["reward"])!=plan["validation_observations"]:raise ValueError("distillation corpus budget differs")
    write(output/"plan.json",plan)
    try:cpu=subprocess.check_output(["sysctl","-n","machdep.cpu.brand_string"],text=True).strip() if platform.system()=="Darwin" else platform.processor()
    except (OSError, subprocess.CalledProcessError):cpu=platform.machine()
    write(output/"manifest.json",{"source":source,"plan_sha256":hashlib.sha256(canonical_json(plan).encode()).hexdigest(),
        "teacher":teacher_identity,"datasets":{"train":tm["logical_sha256"],"validation":vm["logical_sha256"],"test":test_manifest["logical_sha256"]},
        "runtime":{"cpu":cpu,"platform":platform.platform(),"python":platform.python_version(),"torch":str(torch.__version__),"numpy":np.__version__,"onnx":onnx.__version__,"onnxruntime":ort.__version__,"providers":["CPUExecutionProvider"],"threads":1,"ORT_DISABLE_TELEMETRY":"1"}})
    started=time.perf_counter();student,distillation=distil(teacher,train,validation,plan);write(output/"distillation.json",distillation)
    checkpoints.save(output/"teacher-actor.pt",{"artefact_kind":"deterministic-actor","hidden":teacher.hidden,"actor":teacher.actor.state_dict(),
        "proprio_scale":teacher.proprio_scale,"height_scale":teacher.height_scale,"teacher_sha256":teacher_identity["checkpoint_sha256"],"source":source})
    checkpoints.save(output/"student.pt",{"artefact_kind":"distilled-actor","hidden":student.hidden,"actor":student.actor.state_dict(),
        "teacher_sha256":teacher_identity["checkpoint_sha256"],"source":source,"normalisation":"fixed_physical_scales_v1"})
    models={};unsupported=[]
    for name,policy in (("teacher",teacher),("student",student)):
        fp32=output/f"{name}-fp32.onnx";export_actor(policy,fp32);models[f"onnx_{name}_fp32"]={"path":fp32,"quantisation":None}
        path=output/f"{name}-int8.onnx"
        try:models[f"onnx_{name}_int8"]={"path":path,"quantisation":quantise(fp32,path)}
        except Exception as error:unsupported.append({"variant":f"onnx_{name}_int8","stage":"quantisation","error":f"{type(error).__name__}: {error}"})
    nominal=test["observation"].astype(np.float32);boundary=boundary_inputs(teacher)
    teacher_nominal=torch_actions(teacher,nominal);teacher_boundary=torch_actions(teacher,boundary)
    results=[];evaluations=[]
    reference_latency=latency(lambda data:torch_actions(teacher,data),nominal[:1],plan)
    results.append({"variant":"pytorch_teacher","latency":reference_latency,"file_bytes":(output/"teacher-actor.pt").stat().st_size,
        "size_scope":"actor-only PyTorch weights and preprocessing; original actor+critic source checkpoint separately retained", "nominal_action_max_abs_error":0,"boundary_action_max_abs_error":0})
    for name in plan["variants"]:
        if name=="pytorch_teacher":
            policy=teacher;identity=teacher_identity
        elif name in models:
            item=models[name];path=item["path"]
            try:
                cold=[];first=[]
                for _ in range(plan["cold_session_repetitions"]):
                    begin=time.perf_counter_ns();runtime=OfflinePolicy(path);cold.append((time.perf_counter_ns()-begin)/1000)
                    begin=time.perf_counter_ns();runtime.infer_flat(nominal[:1]);first.append((time.perf_counter_ns()-begin)/1000)
                actual=runtime.infer_flat(nominal);edge=runtime.infer_flat(boundary)
                results.append({"variant":name,"model_sha256":runtime.sha256,"file_bytes":path.stat().st_size,"quantisation":item["quantisation"],
                    "nominal_action_max_abs_error":float(np.abs(actual-teacher_nominal).max()),"nominal_action_mae":float(np.abs(actual-teacher_nominal).mean()),
                    "boundary_action_max_abs_error":float(np.abs(edge-teacher_boundary).max()),
                    "latency":latency(runtime.infer_flat,nominal[:1],plan),"cold_session_median_us":float(np.median(cold)),"first_inference_median_us":float(np.median(first)),
                    "cold_scope":"new CPU session, libraries already imported and OS cache not flushed; hash validation included"})
                policy=EvaluationAdapter(path);identity={"checkpoint_sha256":runtime.sha256,"format":"onnx","variant":name,"teacher_identity":teacher_identity}
            except Exception as error:
                unsupported.append({"variant":name,"stage":"CPU inference","error":f"{type(error).__name__}: {error}"});continue
        else:continue
        for family in plan["evaluation_families"]:
            evaluation=evaluate_controller(policy,split=plan["evaluation_split"],count=plan["evaluation_cases"],family_name=family,identity=identity,seed_offset=plan["evaluation_seed_offset"])
            evaluations.append({"variant":name,"evaluation":evaluation})
        print(json.dumps({"variant":name,"event":"evaluated"}),flush=True)
    write(output/"comparison.json",{"variants":results,"evaluations":evaluations,"unsupported":unsupported,
        "training_wall_s":distillation["training_wall_s"],"experiment_wall_s":time.perf_counter()-started,
        "interpretation":"Zero teacher success cannot validate useful loading preservation. Quantisation and distillation are separate interventions; no deployment qualification.",
        "recommendation":"Retain float32 teacher ONNX as the fidelity reference. Student/int8 variants remain experimental; no useful-task-performance recommendation."})
    write(output/"package.json",{"schema_version":"1.0","source_mode":"recorded_synthetic","teacher":teacher_identity,
        "input":{"name":"observation","shape":["N",65],"layout":"15 proprio, 25 row-major height metres, 25 binary validity","normalisation":"embedded fixed_physical_scales_v1, clip [-5,5]"},
        "output":{"name":"action","shape":["N",4],"units":"normalised [-1,1]","names":["acceleration request","articulation rate","boom rate","bucket rate"],"synthetic_requested_rate_limits":[1.5,0.35,0.25,0.5],"rate_units":["m/s^2","rad/s","rad/s","rad/s"]},
        "runtime":"Standalone offline_runtime.py with NumPy and ONNX Runtime CPU; no PyTorch for inference", "calibrated_for_real_machine":False})
    print(json.dumps({"event":"complete","output":str(output)}),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--datasets",type=Path,required=True);parser.add_argument("--output",type=Path,required=True);parser.add_argument("--plan",type=Path,default=DEFAULT_PLAN)
    args=parser.parse_args();run(args.datasets,args.output,args.plan)
