"""Client Flower: chaque usine garde et traite ses donnees localement."""

import os
import sys
from pathlib import Path

import flwr as fl
import numpy as np
import pandas as pd
import tensorflow as tf

from preprocessing import FEATURES, LABEL, scale_features


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", PROJECT_ROOT / "data")).expanduser()
SERVER_ADDRESS = os.environ.get("SERVER_ADDRESS", "127.0.0.1:8080")
SEED = 42


def create_model():
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(len(FEATURES),)),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dense(16, activation="relu"),
        tf.keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy")
    return model


def stratified_split(features, labels, test_fraction=0.2):
    """Separe localement les classes en conservant leur proportion."""
    rng = np.random.default_rng(SEED)
    train_indices = []
    test_indices = []
    for label in np.unique(labels):
        indices = np.flatnonzero(labels == label)
        if len(indices) < 2:
            raise ValueError("Chaque classe doit contenir au moins deux lignes.")
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


def load_factory_data(factory_name):
    if factory_name not in {"factory_1", "factory_2", "factory_3"}:
        raise ValueError("Nom usine attendu: factory_1, factory_2 ou factory_3")

    csv_path = DATA_DIR / factory_name / "sensor_data.csv"
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV introuvable: {csv_path}")
    frame = pd.read_csv(csv_path)
    missing = [column for column in FEATURES + [LABEL] if column not in frame.columns]
    if missing:
        raise ValueError(f"{csv_path}: colonnes manquantes: {', '.join(missing)}")
    frame = frame[FEATURES + [LABEL]].dropna()
    unknown = sorted(set(frame[LABEL]) - {"normal", "failure"})
    if unknown:
        raise ValueError(f"{csv_path}: etats inconnus: {unknown}")

    features = frame[FEATURES].to_numpy(dtype=np.float32)
    labels = frame[LABEL].map({"normal": 0, "failure": 1}).to_numpy(dtype=np.float32)
    if len(frame) < 4 or len(np.unique(labels)) != 2:
        raise ValueError(f"{csv_path}: il faut assez de lignes valides des deux classes")
    return stratified_split(features, labels)


def binary_metrics(labels, predictions):
    """Calcule les indicateurs de panne sans dependance supplementaire."""
    true_positive = int(np.sum((labels == 1) & (predictions == 1)))
    false_positive = int(np.sum((labels == 0) & (predictions == 1)))
    false_negative = int(np.sum((labels == 1) & (predictions == 0)))
    accuracy = float(np.mean(labels == predictions))
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "accuracy": accuracy,
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
    }


class FactoryClient(fl.client.NumPyClient):
    def __init__(self, factory_name):
        self.factory_name = factory_name
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
        metrics = {"train_loss": float(history.history["loss"][-1])}
        return self.model.get_weights(), len(self.X_train), metrics

    def evaluate(self, parameters, config):
        self.model.set_weights(parameters)
        loss = self.model.evaluate(self.X_test, self.y_test, verbose=0)
        probabilities = self.model.predict(self.X_test, verbose=0).ravel()
        predictions = (probabilities >= 0.5).astype(np.float32)
        metrics = binary_metrics(self.y_test, predictions)
        print(f"[{self.factory_name}] loss={float(loss):.4f}, {metrics}")
        return float(loss), len(self.y_test), metrics


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python client.py factory_1")
    factory_name = sys.argv[1]
    client = FactoryClient(factory_name)
    print(f"Client {factory_name} pret, connexion a {SERVER_ADDRESS}")
    fl.client.start_client(server_address=SERVER_ADDRESS, client=client.to_client())


if __name__ == "__main__":
    main()
