import json
from pathlib import Path

import numpy as np
from sklearn.metrics import precision_recall_curve

root = Path(__file__).resolve().parents[2]
experiment = root / "artifacts/models/demo-20261005-233045"
history = json.loads((experiment / "history.json").read_text(encoding="utf-8"))
with np.load(experiment / "test-predictions.npz") as predictions:
    curves = []
    for name in ("logistic", "lstm"):
        precision, recall, _ = precision_recall_curve(
            (predictions["y"] != 0).astype(int), predictions[name]
        )
        curves.append({"name": name, "x": recall.tolist(), "y": precision.tolist()})
payload = {
    "loss": [
        {"name": "train", "x": list(range(1, 51)), "y": history["loss"]},
        {"name": "validation", "x": list(range(1, 51)), "y": history["val_loss"]},
    ],
    "pr": curves,
}
(Path(__file__).parent / "chart-data.json").write_text(
    json.dumps(payload, ensure_ascii=False), encoding="utf-8"
)
