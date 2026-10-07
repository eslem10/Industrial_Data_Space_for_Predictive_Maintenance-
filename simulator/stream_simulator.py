"""Common deterministic sensor stream used by backfill and live simulation."""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", "data")).expanduser()
if not DATA_DIR.is_absolute():
    DATA_DIR = PROJECT_ROOT / DATA_DIR
FEATURES = ["temperature", "vibration", "pressure", "humidity", "energy_consumption"]
FACTORY_MEANS = {
    "F1": (55.0, 0.35, 3.4, 55.0, 6.5),
    "F2": (75.0, 0.45, 3.7, 65.0, 7.5),
    "F3": (68.0, 0.70, 3.8, 48.0, 8.5),
}


def generate_measurement(factory_id, timestamp_index=0, rng=None):
    if factory_id not in FACTORY_MEANS:
        raise ValueError("Factory must be F1, F2, or F3")
    rng = rng or np.random.default_rng()
    means = FACTORY_MEANS[factory_id]
    drift = 1.2 * np.sin(timestamp_index / 900 + int(factory_id[-1]))
    values = np.array(means, dtype=np.float64)
    scales = np.array([7.0, 0.13, 0.55, 8.0, 1.2])
    values += rng.normal(0, scales) + drift
    risk = np.dot((values[[0, 1, 2, 4]] - np.array(means)[[0, 1, 2, 4]]) / scales[[0, 1, 2, 4]], [0.3, 0.3, 0.2, 0.2])
    probability = 1 / (1 + np.exp(-(risk * 2 - 3.4)))
    state = "failure" if rng.random() < probability else "normal"
    if state == "failure":
        values += rng.normal([10, 0.5, 1.0, 0, 2.0], [3, 0.15, 0.3, 1, 0.5])
    values = np.maximum(values, 0)
    return {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "factory_id": factory_id,
        **{feature: round(float(value), 3) for feature, value in zip(FEATURES, values)},
        "state": state,
    }


def write_latest(factory_id, measurement):
    path = DATA_DIR / f"factory_{factory_id[-1]}" / "latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(measurement, ensure_ascii=False) + "\n", encoding="utf-8")


def run_backfill(factory_name, count=12000, step_seconds=60, reset=True):
    factory_id = f"F{factory_name[-1]}"
    if count < 1 or step_seconds < 1:
        raise ValueError("count and step_seconds must be positive")
    output = DATA_DIR / factory_name / "sensor_data.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    import csv
    mode = "w" if reset else "a"
    with output.open(mode, newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["timestamp", "factory_id", *FEATURES, "state"])
        if reset:
            writer.writeheader()
        rng = np.random.default_rng(20261003 + int(factory_id[-1]))
        latest = None
        for index in range(count):
            measurement = generate_measurement(factory_id, index, rng)
            measurement["timestamp"] = (datetime(2026, 1, 1) + timedelta(seconds=index * step_seconds)).isoformat()
            writer.writerow(measurement)
            latest = measurement
    if latest:
        write_latest(factory_id, latest)


def run_realtime(factory_name):
    factory_id = f"F{factory_name[-1]}"
    interval = float(os.environ.get("INTERVAL", "2"))
    if interval <= 0:
        raise ValueError("INTERVAL must be positive")
    rng = np.random.default_rng(20261003 + int(factory_id[-1]))
    index = 0
    while True:
        measurement = generate_measurement(factory_id, index, rng)
        write_latest(factory_id, measurement)
        index += 1
        time.sleep(interval)
