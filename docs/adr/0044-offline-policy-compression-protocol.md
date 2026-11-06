# ADR-0044: Offline policy compression protocol

Status: Accepted

## Decision

Export the frozen final seed-7 actor from the completed RL study. Package its
fixed physical preprocessing, bounded tanh action mapping, units and actuator
rates in an offline CPU ONNX package, separate from published browser assets.
Set `ORT_DISABLE_TELEMETRY=1` before runtime initialisation and disable telemetry
through the runtime API; offline inference must not start background uploads.
Compare deterministic actions with PyTorch on nominal, masked and boundary
observations. Measure cold session creation/first inference, warm inference,
file size and actual host/runtime identity. No NVIDIA measurements are implied.

Test one 16-unit student distilled from this fixed teacher using the existing
8,192-row world-model training observations and validation-only checkpoint
selection on 2,048 rows. Fix seed 71, 60 epochs, batch 256, Adam learning rate
0.001, action MSE. This is imitation of a fixed policy, not new RL or task
improvement. Do not train or select on held-out data.

Compare teacher/student float32 ONNX and dynamic signed-int8 MatMul variants
with the direct uncompressed PyTorch teacher. Keep unsupported operators and
regressions in the report. Quantisation changes numerical precision;
distillation changes architecture and learned weights. Neither can preserve
useful loading performance that the teacher has not demonstrated.

Use four identical fresh test scenes per standard/low-grip/occluded/blocked
family at test seed offset 6600 for every variant. Report action error, bytes,
latency, material delivered, complete cycles and failures. A task with zero
teacher success cannot validate compression quality through success parity
alone. Choose a conservative research export based on action fidelity and
measured runtime/size, with no real-machine recommendation.

Refs: #251, #252.

Sources: [ONNX Runtime quantisation](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html),
[CPU sessions](https://onnxruntime.ai/docs/api/python/api_summary.html),
[PyTorch ONNX export](https://docs.pytorch.org/docs/2.15/onnx.html).

Runtime behaviour: [official telemetry controls](https://github.com/microsoft/onnxruntime/blob/main/docs/Privacy.md).
