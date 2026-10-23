import numpy as np
from datetime import datetime, timedelta, timezone
from app.cnn.model import BUCKETS, METRICS, build_heatmap, synth


def test_heatmap_shape_and_range():
    now = datetime.now(timezone.utc)
    series = {"cpu": [(now - timedelta(minutes=m), 50.0) for m in range(0, 600, 5)]}
    h = build_heatmap(series, now)
    assert h.shape == (len(METRICS), BUCKETS) and 0 <= h.min() and h.max() <= 1
    assert h[0].max() == 0.5


def test_synth_classes_differ():
    rng = np.random.default_rng(0)
    assert synth("idle", rng).mean() < synth("normal", rng).mean()


def test_blast_radius():
    from app.agents.terraform import blast_radius_from_plan
    plan = {"resource_changes": [
        {"change": {"actions": ["create"]}}, {"change": {"actions": ["delete", "create"]}},
        {"change": {"actions": ["no-op"]}}]}
    r = blast_radius_from_plan(plan)
    assert r["create"] == 1 and r["replace"] == 1 and r["score"] == 4
