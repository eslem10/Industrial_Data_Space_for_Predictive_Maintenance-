import sys
from pathlib import Path

import flwr as fl
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

from preprocessing import FEATURES, LABEL, scale_features


def create_model():
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(len(FEATURES),)),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dense(16, activation="relu"),
        tf.keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    return model


def load_factory_data(factory_name):
    if factory_name not in {"factory_1", "factory_2", "factory_3"}:
        raise ValueError("Nom usine attendu: factory_1, factory_2 ou factory_3")

    csv_path = Path(__file__).resolve().parent.parent / "data" / factory_name / "sensor_data.csv"
    if not csv_path.is_file():
        raise FileNotFoundError(f"CSV introuvable: {csv_path}")
    df = pd.read_csv(csv_path)
    missing = [column for column in FEATURES + [LABEL] if column not in df.columns]
    if missing:
        raise ValueError(f"{csv_path}: colonnes manquantes: {', '.join(missing)}")
    df = df[FEATURES + [LABEL]].dropna()
    unknown = sorted(set(df[LABEL]) - {"normal", "failure"})
    if unknown:
        raise ValueError(f"{csv_path}: états inconnus: {unknown}")

    y = df[LABEL].map({"normal": 0, "failure": 1}).to_numpy(dtype=np.float32)
    if len(df) < 2 or len(np.unique(y)) < 2:
        raise ValueError(f"{csv_path}: il faut au moins deux classes et deux lignes valides")
    X_train, X_test, y_train, y_test = train_test_split(
        df[FEATURES].to_numpy(dtype=np.float32), y,
        test_size=0.2, random_state=42, stratify=y,
    )
    return scale_features(X_train), X_test, y_train, y_test


class FactoryClient(fl.client.NumPyClient):
    def __init__(self, factory_name):
        self.factory_name = factory_name
        self.model = create_model()
        self.X_train, self.X_test_raw, self.y_train, self.y_test = load_factory_data(factory_name)
        self.X_test = scale_features(self.X_test_raw)

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


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python client.py factory_1")
    factory_name = sys.argv[1]
    client = FactoryClient(factory_name)
    print(f"Client {factory_name} prêt, connexion au serveur 127.0.0.1:8080")
    fl.client.start_client(server_address="127.0.0.1:8080", client=client.to_client())


if __name__ == "__main__":
    main()
