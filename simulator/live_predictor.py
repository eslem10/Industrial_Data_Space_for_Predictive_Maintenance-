"""Predict failures from the latest shared simulator measurements."""

import json
import os
import sys
from pathlib import Path

import numpy as np
import tensorflow as tf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from federated.preprocessing import FEATURES, scale_features

DATA_DIR = Path(os.environ.get("DATA_DIR", PROJECT_ROOT / "data")).expanduser()
if not DATA_DIR.is_absolute():
    DATA_DIR = PROJECT_ROOT / DATA_DIR
MODEL_PATH = Path(os.environ.get("MODEL_PATH", PROJECT_ROOT / "federated" / "global_model.keras")).expanduser()
ALERT_THRESHOLD = float(os.environ.get("ALERT_THRESHOLD", "0.5"))
MODEL = None


def predict(measurement):
    missing = [feature for feature in FEATURES if feature not in measurement]
    if missing:
        raise ValueError(f"Missing sensor measurements: {', '.join(missing)}")
    try:
        values = np.asarray([[float(measurement[feature]) for feature in FEATURES]], dtype=np.float32)
    except (TypeError, ValueError) as error:
        raise ValueError("Sensor measurements must be numeric") from error
    global MODEL
    if MODEL is None:
        if not MODEL_PATH.is_file():
            raise FileNotFoundError(f"Global model not found: {MODEL_PATH}")
        MODEL = tf.keras.models.load_model(MODEL_PATH, compile=False)
    return float(MODEL.predict(scale_features(values), verbose=0).reshape(-1)[0])


def main():
    alerts_path = DATA_DIR / "alerts.json"
    alerts = []
    for number in range(1, 4):
        latest_path = DATA_DIR / f"factory_{number}" / "latest.json"
        if not latest_path.is_file():
            continue
        measurement = json.loads(latest_path.read_text(encoding="utf-8"))
        probability = predict(measurement)
        if probability >= ALERT_THRESHOLD:
            alerts.append({
                "timestamp": measurement["timestamp"],
                "factory_id": measurement["factory_id"],
                "probability": probability,
            })
    alerts_path.write_text(json.dumps(alerts[-50:], indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
