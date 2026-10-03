"""Serveur Flower FedAvg et ecriture des performances globales."""

import json
import os
from pathlib import Path

import flwr as fl
import tensorflow as tf

if __package__:
    from .preprocessing import FEATURES
else:
    from preprocessing import FEATURES


SERVER_ADDRESS = os.environ.get("SERVER_ADDRESS", "0.0.0.0:8080")
NUM_ROUNDS = int(os.environ.get("NUM_ROUNDS", "5"))
NUM_CLIENTS = int(os.environ.get("NUM_CLIENTS", "3"))
OUTPUT_DIR = Path(__file__).resolve().parent
MODEL_PATH = OUTPUT_DIR / "global_model.keras"
METRICS_PATH = OUTPUT_DIR / "results" / "metrics.json"


def create_model():
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(len(FEATURES),)),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dense(16, activation="relu"),
        tf.keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy")
    return model


def weighted_average(metrics):
    """Agrege les metriques client en les ponderant par leurs exemples."""
    total_examples = sum(num_examples for num_examples, _ in metrics)
    if total_examples == 0:
        return {}
    keys = set.intersection(*(set(values) for _, values in metrics)) if metrics else set()
    return {
        key: sum(count * values[key] for count, values in metrics) / total_examples
        for key in keys
    }


class SaveModelStrategy(fl.server.strategy.FedAvg):
    def __init__(self, model, **kwargs):
        super().__init__(**kwargs)
        self.model = model

    def aggregate_fit(self, server_round, results, failures):
        parameters, metrics = super().aggregate_fit(server_round, results, failures)
        if parameters is not None:
            self.model.set_weights(fl.common.parameters_to_ndarrays(parameters))
            self.model.save(MODEL_PATH)
            print(f"[Serveur] Round {server_round}: modele global sauvegarde dans {MODEL_PATH}")
        return parameters, metrics

    def aggregate_evaluate(self, server_round, results, failures):
        loss, metrics = super().aggregate_evaluate(server_round, results, failures)
        metrics = metrics or {}
        record = {
            "round": server_round,
            "loss": float(loss) if loss is not None else None,
            "accuracy": metrics.get("accuracy"),
            "precision": metrics.get("precision"),
            "recall": metrics.get("recall"),
            "f1": metrics.get("f1"),
        }
        for key in ("accuracy", "precision", "recall", "f1"):
            if record[key] is not None:
                record[key] = float(record[key])

        METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        records = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
        records.append(record)
        METRICS_PATH.write_text(json.dumps(records, indent=2), encoding="utf-8")

        print(
            f"[Serveur] Round {server_round}: "
            f"loss={record['loss']}, accuracy={record['accuracy']}, "
            f"precision={record['precision']}, recall={record['recall']}, f1={record['f1']}"
        )
        return loss, metrics


def main():
    if NUM_ROUNDS < 1 or NUM_CLIENTS < 3:
        raise ValueError("NUM_ROUNDS doit etre positif et NUM_CLIENTS doit valoir au moins 3")
    model = create_model()
    strategy = SaveModelStrategy(
        model,
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=NUM_CLIENTS,
        min_evaluate_clients=NUM_CLIENTS,
        min_available_clients=NUM_CLIENTS,
        fit_metrics_aggregation_fn=weighted_average,
        evaluate_metrics_aggregation_fn=weighted_average,
    )
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text("[]", encoding="utf-8")
    print(f"Serveur FedAvg en attente de {NUM_CLIENTS} clients sur {SERVER_ADDRESS}...")
    fl.server.start_server(
        server_address=SERVER_ADDRESS,
        config=fl.server.ServerConfig(num_rounds=NUM_ROUNDS),
        strategy=strategy,
    )
    print("Entrainement federe termine.")


if __name__ == "__main__":
    main()
