
import os
import json
from pathlib import Path

import flwr as fl
import tensorflow as tf


# ============================================================
# Global model architecture
# ============================================================

def create_model():

    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(5,)),

        tf.keras.layers.Dense(
            32,
            activation="relu"
        ),

        tf.keras.layers.Dense(
            16,
            activation="relu"
        ),

        tf.keras.layers.Dense(
            1,
            activation="sigmoid"
        )
    ])

    model.compile(
        optimizer="adam",
        loss="binary_crossentropy",
        metrics=["accuracy"]
    )

    return model


# ============================================================
# Global model
# ============================================================

global_model = create_model()
SERVER_ADDRESS = os.environ.get("SERVER_ADDRESS", "0.0.0.0:8080")
NUM_ROUNDS = int(os.environ.get("NUM_ROUNDS", "5"))
NUM_CLIENTS = int(os.environ.get("NUM_CLIENTS", "3"))
METRICS_PATH = Path(__file__).resolve().parent / "results" / "metrics.json"


# ============================================================
# Aggregate Metrics
# ============================================================

def weighted_average(metrics):
    total_examples = sum(num_examples for num_examples, _ in metrics)
    if total_examples == 0:
        return {}
    keys = set.intersection(*(set(values) for _, values in metrics)) if metrics else set()
    return {
        key: sum(count * values[key] for count, values in metrics) / total_examples
        for key in keys
    }


# ============================================================
# Custom FedAvg Strategy
# ============================================================

class SaveModelStrategy(fl.server.strategy.FedAvg):

    def aggregate_fit(
        self,
        server_round,
        results,
        failures
    ):

        aggregated_parameters, aggregated_metrics = super().aggregate_fit(
            server_round,
            results,
            failures
        )

        if aggregated_parameters is not None:

            # Convert Flower Parameters to NumPy arrays
            weights = fl.common.parameters_to_ndarrays(
                aggregated_parameters
            )

            # Update our TensorFlow global model
            global_model.set_weights(weights)

            print(
                f"\n[Server] Global model updated "
                f"after round {server_round}."
            )

            # Save the latest global model
            model_path = os.path.join(
                os.path.dirname(__file__),
                "global_model.keras"
            )

            global_model.save(model_path)

            print(
                f"[Server] Global model saved -> "
                f"{model_path}"
            )

        return aggregated_parameters, aggregated_metrics

    def aggregate_evaluate(self, server_round, results, failures):
        loss, metrics = super().aggregate_evaluate(server_round, results, failures)
        metrics = metrics or {}
        record = {"round": server_round, "loss": float(loss) if loss is not None else None}
        record.update({key: float(metrics[key]) for key in ("accuracy", "precision", "recall", "f1") if key in metrics})
        METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        records = json.loads(METRICS_PATH.read_text(encoding="utf-8")) if METRICS_PATH.exists() else []
        records.append(record)
        METRICS_PATH.write_text(json.dumps(records, indent=2), encoding="utf-8")
        return loss, metrics


# ============================================================
# FedAvg Strategy
# ============================================================

strategy = SaveModelStrategy(

    fraction_fit=1.0,

    fraction_evaluate=1.0,

    min_fit_clients=NUM_CLIENTS,

    min_evaluate_clients=NUM_CLIENTS,

    min_available_clients=NUM_CLIENTS,

    fit_metrics_aggregation_fn=weighted_average,
    evaluate_metrics_aggregation_fn=weighted_average
)


# ============================================================
# Start Server
# ============================================================

if NUM_ROUNDS < 1 or NUM_CLIENTS < 3:
    raise ValueError("NUM_ROUNDS must be positive and NUM_CLIENTS must be at least 3")

METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
METRICS_PATH.write_text("[]", encoding="utf-8")
print("\nStarting Federated Learning server...")
print(f"Waiting for {NUM_CLIENTS} factories...\n")

fl.server.start_server(

    server_address=SERVER_ADDRESS,

    config=fl.server.ServerConfig(
        num_rounds=NUM_ROUNDS
    ),

    strategy=strategy
)

print("\nFederated Learning finished.")
print("Final global model saved.")
