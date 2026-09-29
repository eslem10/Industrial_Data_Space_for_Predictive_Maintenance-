from pathlib import Path

import flwr as fl
import tensorflow as tf


def create_model():
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(5,)),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dense(16, activation="relu"),
        tf.keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    return model


def weighted_average(metrics):
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
            model_path = Path(__file__).resolve().parent / "global_model.keras"
            self.model.save(model_path)
            print(f"[Serveur] Modèle global sauvegardé: {model_path}")
        return parameters, metrics


def main():
    model = create_model()
    strategy = SaveModelStrategy(
        model,
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=3,
        min_evaluate_clients=3,
        min_available_clients=3,
        evaluate_metrics_aggregation_fn=weighted_average,
    )
    print("Serveur fédéré en attente de 3 clients sur le port 8080...")
    fl.server.start_server(
        server_address="0.0.0.0:8080",
        config=fl.server.ServerConfig(num_rounds=5),
        strategy=strategy,
    )
    print("Entraînement fédéré terminé.")


if __name__ == "__main__":
    main()
