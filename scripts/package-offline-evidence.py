#!/usr/bin/env python3
"""Package the completed CPU export comparison and standalone inference files."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]


def package(source,output):
    if output.exists():raise FileExistsError(output)
    manifest=json.loads((source/"manifest.json").read_text());comparison=json.loads((source/"comparison.json").read_text())
    if manifest["source"]["training_dirty"] or manifest["runtime"]["ORT_DISABLE_TELEMETRY"]!="1":raise ValueError("study was not frozen/offline")
    if len(comparison["variants"])!=5 or comparison["unsupported"]:raise ValueError("review unsupported variants before packaging")
    output.mkdir(parents=True)
    for path in sorted(source.iterdir()):
        if path.is_file() and path.suffix in (".json",".onnx",".pt",".sha256"):shutil.copyfile(path,output/path.name)
    shutil.copyfile(ROOT/"training/kessel_training/offline_runtime.py",output/"offline_runtime.py")
    (output/"requirements.txt").write_text(f"numpy=={manifest['runtime']['numpy']}\nonnxruntime=={manifest['runtime']['onnxruntime']}\n")
    (output/"README.md").write_text('''# Offline CPU actor package

The fidelity reference is `teacher-fp32.onnx`. `offline_runtime.py` needs only
the pinned NumPy and ONNX Runtime requirements. It disables runtime telemetry
before initialisation and uses one CPU thread. No PyTorch, training process,
network service or browser inference is required.

```python
from offline_runtime import OfflinePolicy
policy = OfflinePolicy("teacher-fp32.onnx", expected_sha256="<hash from files.json>")
action = policy.act(observation)
```

`observation` contains `(N,15)` raw `proprio`, `(N,5,5)` height metres and
`(N,5,5)` binary `range_valid`. The graph includes physical preprocessing and
bounded deterministic actions. See `package.json` for layout, units and
synthetic actuator request rates. Hash checking is mandatory for a selected
package; replace the example hash with the retained file hash.

Teacher/student float32 and dynamic-int8 files are separate experiments.
The student imitates the teacher; quantisation changes numerical precision.
All variants achieved zero full synthetic delivery cycles. Matching zero
success cannot validate useful loading performance. This package is research
evidence and has no machine-control or NVIDIA deployment qualification.
''')
    files=[{"path":str(p.relative_to(output)),"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size} for p in sorted(output.iterdir()) if p.is_file()]
    (output/"files.json").write_text(json.dumps({"source_mode":"recorded_synthetic","recommended_fidelity_reference":"teacher-fp32.onnx","files":files},indent=2)+"\n")
    return {"files":len(files),"bytes":sum(e["bytes"] for e in files)}


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--source",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();print(json.dumps(package(a.source,a.output)))
