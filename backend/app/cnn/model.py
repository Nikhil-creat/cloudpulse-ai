"""Metrics -> 2D heatmap -> CNN classifier (normal | cost_spike | idle | intrusion)."""
import io
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

METRICS = ["cpu", "memory", "net_in", "net_out", "disk_io", "cost_hourly", "auth_failures", "api_calls"]
REF_MAX = {"cpu": 100, "memory": 100, "net_in": 1e9, "net_out": 1e9, "disk_io": 5e8,
           "cost_hourly": 50, "auth_failures": 200, "api_calls": 5000}
CLASSES = ["normal", "cost_spike", "idle", "intrusion"]
BUCKETS = 96  # 24h at 15-minute resolution
WEIGHTS = Path(__file__).resolve().parents[2] / "models" / "cnn.pt"


def build_heatmap(series: dict, end: datetime | None = None) -> np.ndarray:
    """series: {metric: [(datetime, value), ...]} -> float32 array (len(METRICS), BUCKETS) in [0,1]."""
    end = end or datetime.now(timezone.utc)
    start = end - timedelta(hours=24)
    out = np.zeros((len(METRICS), BUCKETS), dtype=np.float32)
    for i, m in enumerate(METRICS):
        sums, cnts = np.zeros(BUCKETS), np.zeros(BUCKETS)
        for ts, val in series.get(m, []):
            if start <= ts < end:
                b = min(int((ts - start).total_seconds() // 900), BUCKETS - 1)
                sums[b] += val
                cnts[b] += 1
        row = np.divide(sums, cnts, out=np.zeros(BUCKETS), where=cnts > 0)
        last = 0.0
        for b in range(BUCKETS):  # forward-fill gaps
            if cnts[b] == 0:
                row[b] = last
            last = row[b]
        out[i] = np.clip(row / REF_MAX[m], 0, 1)
    return out


def to_png(heat: np.ndarray, scale: int = 8) -> bytes:
    from PIL import Image
    g = (heat * 255).astype(np.uint8)
    rgb = np.stack([g, (g * 0.55).astype(np.uint8), 255 - g], axis=-1)
    img = Image.fromarray(rgb).resize((BUCKETS * scale, len(METRICS) * scale), Image.NEAREST)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _net():
    import torch.nn as nn

    class HeatmapCNN(nn.Module):
        def __init__(self, n_classes=len(CLASSES)):
            super().__init__()
            def block(i, o):
                return nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(), nn.MaxPool2d(2))
            self.features = nn.Sequential(block(1, 16), block(16, 32), nn.Conv2d(32, 64, 3, padding=1),
                                          nn.ReLU(), nn.AdaptiveAvgPool2d((2, 4)))
            self.head = nn.Sequential(nn.Flatten(), nn.Linear(64 * 8, 64), nn.ReLU(), nn.Dropout(0.2),
                                      nn.Linear(64, n_classes))

        def forward(self, x):
            return self.head(self.features(x))

    return HeatmapCNN()


def synth(kind: str, rng: np.random.Generator) -> np.ndarray:
    """Synthetic training patterns used for bootstrapping before real labelled incidents exist."""
    t = np.linspace(0, 4 * np.pi, BUCKETS)
    h = rng.normal(0.05, 0.02, (len(METRICS), BUCKETS)).clip(0, 1).astype(np.float32)
    if kind == "idle":
        return (h * 0.5).clip(0, 1)
    h[0] += 0.35 + 0.2 * np.sin(t)       # diurnal cpu
    h[1] += 0.45
    h[4] += 0.2 + 0.1 * np.sin(t + 1)
    h[7] += 0.3 + 0.15 * np.sin(t)
    if kind == "cost_spike":
        s = rng.integers(55, 80)
        h[5, s:] += rng.uniform(0.5, 0.9)
        h[0, s:] += 0.3
    elif kind == "intrusion":
        s = rng.integers(50, 85)
        h[6, s:s + 12] += rng.uniform(0.6, 1.0)
        h[3, s:s + 12] += rng.uniform(0.5, 0.9)
    return h.clip(0, 1)


class AnomalyClassifier:
    def __init__(self, weights: Path = WEIGHTS):
        import torch
        self.torch, self.net = torch, _net()
        self.loaded = weights.exists()
        if self.loaded:
            self.net.load_state_dict(torch.load(weights, map_location="cpu"))
        self.net.eval()

    def predict(self, heat: np.ndarray) -> dict:
        x = self.torch.from_numpy(heat).float()[None, None]
        with self.torch.no_grad():
            p = self.torch.softmax(self.net(x), dim=1)[0].numpy()
        i = int(p.argmax())
        return {"label": CLASSES[i], "confidence": float(p[i]),
                "probs": {c: float(v) for c, v in zip(CLASSES, p)}, "trained": self.loaded}
