"""Shared, deterministic feature scaling for every federated participant."""

import numpy as np


FEATURES = ["temperature", "vibration", "pressure", "humidity", "energy_consumption"]
LABEL = "state"
FEATURE_MEANS = np.array([70.0, 0.5, 5.0, 50.0, 10.0], dtype=np.float32)
FEATURE_SCALES = np.array([20.0, 0.5, 2.0, 20.0, 5.0], dtype=np.float32)


def scale_features(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float32)
    return (values - FEATURE_MEANS) / FEATURE_SCALES
