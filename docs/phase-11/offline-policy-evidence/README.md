# Offline CPU actor package

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
