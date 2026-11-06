import json

import pytest

from kessel_training import checkpoints
from kessel_training.telemetry import scan
from kessel_training.train import Trainer, TrainConfig


def test_append_only_training_events_reconcile_resume_curves_and_checkpoints(tmp_path):
    trainer=Trainer(TrainConfig(num_envs=2, rollout_steps=3, updates=4, checkpoint_every=1))
    first=trainer.run(tmp_path,until_update=2);prefix=(tmp_path/"events.jsonl").read_bytes()
    resumed=Trainer.resume(tmp_path/"checkpoint-000002-final.pt");report=resumed.run(tmp_path)
    assert (tmp_path/"events.jsonl").read_bytes().startswith(prefix)
    events=scan(tmp_path/"events.jsonl");updates=[e["payload"] for e in events if e["kind"]=="rollout"]
    assert [r["counters"]["rollouts"] for r in updates]==[1,2,3,4]
    assert report["telemetry"]["final_counters"]==report["counters"]
    assert [r["metrics"] for r in updates]==report["learning_curve"]
    assert updates[-1]["counters"]["environment_steps"]==24
    for event in events:
        if event["kind"]=="checkpoint":
            p=tmp_path/event["payload"]["file"]
            assert checkpoints.sha256(p)==event["payload"]["checkpoint_sha256"]
    from kessel_training.audit_run import audit
    assert audit(tmp_path)["counters"] == report["counters"]
    old=Trainer.resume(tmp_path/"checkpoint-000001.pt")
    with pytest.raises(ValueError,match="counters differ"):old.run(tmp_path)


def test_telemetry_mutation_is_detected(tmp_path):
    trainer=Trainer(TrainConfig(num_envs=1,rollout_steps=1,updates=1));trainer.run(tmp_path)
    path=tmp_path/"events.jsonl";rows=path.read_text().splitlines();data=json.loads(rows[1])
    data["payload"]["counters"]["environment_steps"]=999;rows[1]=json.dumps(data);path.write_text("\n".join(rows)+"\n")
    with pytest.raises(ValueError,match="hash differs"):scan(path)
