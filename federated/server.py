
import os

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


# ============================================================
# Aggregate Metrics
# ============================================================

def weighted_average(metrics):

    accuracies = [
        num_examples * metrics_dict["accuracy"]
        for num_examples, metrics_dict in metrics
    ]

    precisions = [
        num_examples * metrics_dict["precision"]
        for num_examples, metrics_dict in metrics
    ]

    recalls = [
        num_examples * metrics_dict["recall"]
        for num_examples, metrics_dict in metrics
    ]

    f1_scores = [
        num_examples * metrics_dict["f1"]
        for num_examples, metrics_dict in metrics
    ]

    total_examples = sum(
        num_examples
        for num_examples, _ in metrics
    )

    return {
        "accuracy": sum(accuracies) / total_examples,
        "precision": sum(precisions) / total_examples,
        "recall": sum(recalls) / total_examples,
        "f1": sum(f1_scores) / total_examples
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
                f"[Server] Global model saved → "
                f"{model_path}"
            )

        return aggregated_parameters, aggregated_metrics


# ============================================================
# FedAvg Strategy
# ============================================================

strategy = SaveModelStrategy(

    fraction_fit=1.0,

    fraction_evaluate=1.0,

    min_fit_clients=3,

    min_evaluate_clients=3,

    min_available_clients=3,

    evaluate_metrics_aggregation_fn=weighted_average
)


# ============================================================
# Start Server
# ============================================================

print("\nStarting Federated Learning server...")
print("Waiting for 3 factories...\n")

fl.server.start_server(

    server_address="0.0.0.0:8080",

    config=fl.server.ServerConfig(
        num_rounds=5
    ),

    strategy=strategy
)

print("\nFederated Learning finished.")
print("Final global model saved.")

