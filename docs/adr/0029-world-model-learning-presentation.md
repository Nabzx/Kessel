# ADR-0029: World-model learning presentation

Status: Accepted

The authored-only assumption for future learning content is superseded in
part by [ADR-0031](0031-synthetic-learning-and-presentation-boundary.md).
The current replay and its labels remain unchanged.

## Decision

The technical viewer is an optional branch entered with Explore the world
model. It illustrates a loader learning to scoop and haul ore. It shows
observations, policy actions, predicted outcomes and a reward signal, then
compares an early failed checkpoint with an improved one. A short replay
represents 2.4 million authored episodes in eight seconds. It does not train
2.4 million policies or run actual neural inference in the browser.

Separate the learned dynamics model from the policy. A world model predicts
how observations/state change under actions. Reinforcement learning improves
a policy using the predicted consequences and rewards. Distillation trains a
smaller policy for onboard compute. The deployed machine uses local sensors
and control; returning deployment data improves future training when a link
becomes available. A 3D geometric mine is context for this explanation, not
itself proof of a learned dynamics model.

Use a new original rigged loader with the compact LH203 envelope as a
reference: 7.1 x 1.5 x 1.9 m, 3.5 t rated payload. It is not a Sandvik digital
twin or branded manufacturer asset. The existing excavator remains the loading
machine in the main mine. Both assets retain their own ownership/credits.

All episode counts, rewards, predicted states and policy checkpoints are
scripted and labelled illustrative. No live-training claim is made.

## Sources

- https://danijar.com/project/dreamerv3/
- https://arxiv.org/abs/1511.06295
- https://www.mining.sandvik/en/products/equipment/loaders/lh203-underground-lhd/
