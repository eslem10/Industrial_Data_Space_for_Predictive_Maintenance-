import sys
from pathlib import Path

import flwr as fl
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

from preprocessing import FEATURES, LABEL, scale_features


def create_model() -> tf.keras.Model:
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(len(FEATURES),)),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dense(16, activation="relu"),
        tf.keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    return model


def load_factory_data(factory_name: str):
    if factory_name not in {"factory_1", "factory_2", "factory_3"}:
        raise ValueError("Factory must be factory_1, factory_2, or factory_3")

    csv_path = Path(__file__).resolve().parent.parent / "data" / factory_name / "sensor_data.csv"
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
    if len(df) < 2 or len(np.unique(y)) < 2:
        raise ValueError(f"{csv_path}: at least two valid rows and two classes are required")

    X_train, X_test, y_train, y_test = train_test_split(
        df[FEATURES].to_numpy(dtype=np.float32),
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )
    return scale_features(X_train), scale_features(X_test), y_train, y_test


class FactoryClient(fl.client.NumPyClient):
    def __init__(self, factory_name: str):
        self.factory_name = factory_name
        self.model = create_model()
        self.X_train, self.X_test, self.y_train, self.y_test = load_factory_data(factory_name)

    def get_parameters(self, config):
        return self.model.get_weights()

    def fit(self, parameters, config):
        self.model.set_weights(parameters)
        self.model.fit(self.X_train, self.y_train, epochs=5, batch_size=32, verbose=0)
        return self.model.get_weights(), len(self.X_train), {}

    def evaluate(self, parameters, config):
        self.model.set_weights(parameters)
        loss, _ = self.model.evaluate(self.X_test, self.y_test, verbose=0)
        probabilities = self.model.predict(self.X_test, verbose=0).ravel()
        predictions = (probabilities >= 0.5).astype(int)
        metrics = {
            "accuracy": float(accuracy_score(self.y_test, predictions)),
            "precision": float(precision_score(self.y_test, predictions, zero_division=0)),
            "recall": float(recall_score(self.y_test, predictions, zero_division=0)),
            "f1": float(f1_score(self.y_test, predictions, zero_division=0)),
        }
        print(f"[{self.factory_name}] {metrics}")
        return float(loss), len(self.y_test), metrics


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python client.py factory_1")
    factory_name = sys.argv[1]
    client = FactoryClient(factory_name)
    print(f"Client {factory_name} ready; connecting to 127.0.0.1:8080")
    fl.client.start_client(server_address="127.0.0.1:8080", client=client.to_client())


if __name__ == "__main__":
    main()
