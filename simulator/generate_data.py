"""Generate overlapping, reproducible synthetic predictive-maintenance data."""

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "data"
SAMPLES_PER_FACTORY = 12_000
FAILURE_RATE = 0.06
SEED = 20260929

PROFILES = {
    "F1": {"temperature": (55, 7), "vibration": (0.35, 0.13), "pressure": (3.4, 0.55), "humidity": (55, 8), "energy_consumption": (6.5, 1.2)},
    "F2": {"temperature": (75, 8), "vibration": (0.45, 0.16), "pressure": (3.7, 0.65), "humidity": (65, 9), "energy_consumption": (7.5, 1.4)},
    "F3": {"temperature": (68, 8), "vibration": (0.70, 0.20), "pressure": (3.8, 0.70), "humidity": (48, 7), "energy_consumption": (8.5, 1.6)},
}
FEATURES = list(next(iter(PROFILES.values())))
RISK_WEIGHTS = np.array([0.30, 0.30, 0.20, 0.20])


def calibrated_intercept(risk, target_rate):
    """Find a logistic intercept whose average failure probability is target_rate."""
    low, high = -20.0, 5.0
    for _ in range(80):
        middle = (low + high) / 2
        mean_probability = np.mean(1 / (1 + np.exp(-(middle + risk))))
        if mean_probability < target_rate:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def generate_factory_data(factory_id, num_samples, rng, start_time):
    profile = PROFILES[factory_id]
    values = {}
    standardized = []
    for feature, (mean, std) in profile.items():
        # Mild drift and correlated sensor noise make the series less artificial.
        drift = 1.2 * np.sin(np.arange(num_samples) / 900 + int(factory_id[-1]))
        common_noise = rng.normal(0, 0.18, num_samples)
        measurements = rng.normal(mean + drift, std, num_samples)
        measurements += common_noise * std
        values[feature] = measurements
        if feature != "humidity":
            standardized.append((measurements - mean) / std)

    risk = 3.0 * np.sum(np.vstack(standardized).T * RISK_WEIGHTS, axis=1)
    # Unobserved factors and label uncertainty prevent a clean sensor threshold.
    risk += rng.normal(0, 0.75, num_samples)
    intercept = calibrated_intercept(risk, FAILURE_RATE)
    probability = 1 / (1 + np.exp(-(intercept + risk)))
    is_failure = rng.random(num_samples) < probability

    # Add occasional measurement faults independently of the machine state.
    for feature, (_, std) in profile.items():
        faulty = rng.random(num_samples) < 0.01
        values[feature][faulty] += rng.normal(0, 2.5 * std, faulty.sum())

    frame = pd.DataFrame({
        "timestamp": [start_time + timedelta(minutes=i) for i in range(num_samples)],
        "factory_id": factory_id,
        **{feature: np.round(np.maximum(values[feature], 0), 3) for feature in FEATURES},
        "state": np.where(is_failure, "failure", "normal"),
    })
    return frame


def main():
    rng = np.random.default_rng(SEED)
    start_time = datetime.now().replace(microsecond=0)
    print("Generating new overlapping synthetic sensor data...")
    for number in range(1, 4):
        factory_id = f"F{number}"
        factory_dir = OUTPUT_DIR / f"factory_{number}"
        factory_dir.mkdir(parents=True, exist_ok=True)
        frame = generate_factory_data(factory_id, SAMPLES_PER_FACTORY, rng, start_time)
        csv_path = factory_dir / "sensor_data.csv"
        frame.to_csv(csv_path, index=False)
        failures = int((frame["state"] == "failure").sum())
        print(f"{csv_path}: {len(frame)} rows, {failures} failures ({failures / len(frame):.2%})")
    print("Done. Existing factory CSV files have been replaced.")


if __name__ == "__main__":
    main()
