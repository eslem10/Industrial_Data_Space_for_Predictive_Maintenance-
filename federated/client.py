import json
import os
from pathlib import Path
import sys

import flwr as fl
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

try:
    from .preprocessing import FEATURES, LABEL, scale_features
except ImportError:
    from preprocessing import FEATURES, LABEL, scale_features


EDC_WEIGHTS_DIR = Path(__file__).resolve().parent.parent / "edc-connectors" / "weights"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", PROJECT_ROOT / "data")).expanduser()
if not DATA_DIR.is_absolute():
    DATA_DIR = PROJECT_ROOT / DATA_DIR
SERVER_ADDRESS = os.environ.get("SERVER_ADDRESS", "127.0.0.1:8080")
SEED = 42



def create_model() -> tf.keras.Model:
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(len(FEATURES),)),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dense(16, activation="relu"),
        tf.keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    return model


def stratified_split(features, labels, test_fraction=0.2):
    rng = np.random.default_rng(SEED)
    train_indices = []
    test_indices = []
    for label in np.unique(labels):
        indices = np.flatnonzero(labels == label)
        if len(indices) < 2:
            raise ValueError("Each class must contain at least two rows")
        rng.shuffle(indices)
        test_count = min(len(indices) - 1, max(1, round(len(indices) * test_fraction)))
        test_indices.extend(indices[:test_count])
        train_indices.extend(indices[test_count:])
    rng.shuffle(train_indices)
    rng.shuffle(test_indices)
    train_indices = np.asarray(train_indices, dtype=int)
    test_indices = np.asarray(test_indices, dtype=int)
    return (
        scale_features(features[train_indices]),
        scale_features(features[test_indices]),
        labels[train_indices],
        labels[test_indices],
    )


def load_factory_data(factory_name: str):
    if factory_name not in {"factory_1", "factory_2", "factory_3"}:
        raise ValueError("Factory must be factory_1, factory_2, or factory_3")

    csv_path = DATA_DIR / factory_name / "sensor_data.csv"
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    required = FEATURES + [LABEL]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"{csv_path}: missing columns: {', '.join(missing)}")

    df = df[required].dropna()
    unknown_labels = sorted(set(df[LABEL]) - {"normal", "failure"})
    if unknown_labels:
        raise ValueError(f"{csv_path}: unknown states: {unknown_labels}")

    y = df[LABEL].map({"normal": 0, "failure": 1}).to_numpy(dtype=np.float32)
    if len(df) < 4 or len(np.unique(y)) != 2:
        raise ValueError(f"{csv_path}: at least four valid rows and two classes are required")
    return stratified_split(df[FEATURES].to_numpy(dtype=np.float32), y)


def export_round_weights(factory_name: str, round_number: int, weights) -> None:
    output_dir = EDC_WEIGHTS_DIR / factory_name
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"round_{round_number:03d}.json"
    payload = {
        "factory_id": factory_name,
        "round": round_number,
        "weights": [layer.tolist() for layer in weights],
    }
    output_path.write_text(json.dumps(payload), encoding="utf-8")
    print(f"[{factory_name}] exported round {round_number} weights to {output_path}")


class FactoryClient(fl.client.NumPyClient):
    def __init__(self, factory_name: str):
        self.factory_name = factory_name
        self.round = 0
        self.model = create_model()
        self.X_train, self.X_test, self.y_train, self.y_test = load_factory_data(factory_name)
        counts = np.bincount(self.y_train.astype(int), minlength=2)
        sample_count = len(self.y_train)
        self.class_weights = {
            label: sample_count / (2.0 * count)
            for label, count in enumerate(counts)
            if count > 0
        }

    def get_parameters(self, config):
        return self.model.get_weights()

    def fit(self, parameters, config):
        self.model.set_weights(parameters)
        history = self.model.fit(
            self.X_train,
            self.y_train,
            epochs=5,
            batch_size=32,
            class_weight=self.class_weights,
            verbose=0,
        )
        updated_weights = self.model.get_weights()

        self.round += 1
        export_round_weights(self.factory_name, self.round, updated_weights)

        return updated_weights, len(self.X_train), {
            "train_loss": float(history.history["loss"][-1])
        }

    def evaluate(self, parameters, config):
        self.model.set_weights(parameters)
        evaluation = self.model.evaluate(self.X_test, self.y_test, verbose=0)
        loss = float(evaluation[0] if isinstance(evaluation, (list, tuple)) else evaluation)
        probabilities = self.model.predict(self.X_test, verbose=0).ravel()
        predictions = (probabilities >= 0.5).astype(int)
        metrics = {
            "accuracy": float(accuracy_score(self.y_test, predictions)),
            "precision": float(precision_score(self.y_test, predictions, zero_division=0)),
            "recall": float(recall_score(self.y_test, predictions, zero_division=0)),
            "f1": float(f1_score(self.y_test, predictions, zero_division=0)),
        }
        print(f"[{self.factory_name}] {metrics}")
        return loss, len(self.y_test), metrics


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python client.py factory_1")
    factory_name = sys.argv[1]
    client = FactoryClient(factory_name)
    print(f"Client {factory_name} ready; connecting to {SERVER_ADDRESS}")
    fl.client.start_client(server_address=SERVER_ADDRESS, client=client.to_client())


if __name__ == "__main__":
    main()
