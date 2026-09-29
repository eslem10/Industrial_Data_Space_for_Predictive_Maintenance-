"""Shared, deterministic feature scaling for every federated participant.

These fixed reference values keep feature units comparable without fitting a
scaler on one factory's private data. Change them only as a coordinated update
for the server and every client.
"""

import numpy as np


FEATURES = ["temperature", "vibration", "pressure", "humidity", "energy_consumption"]
LABEL = "state"
FEATURE_MEANS = np.array([70.0, 0.5, 5.0, 50.0, 10.0], dtype=np.float32)
FEATURE_SCALES = np.array([20.0, 0.5, 2.0, 20.0, 5.0], dtype=np.float32)


def scale_features(values):
    values = np.asarray(values, dtype=np.float32)
    return (values - FEATURE_MEANS) / FEATURE_SCALES
