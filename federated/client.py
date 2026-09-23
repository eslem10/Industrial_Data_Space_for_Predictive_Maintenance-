import sys
import os

import flwr as fl
import numpy as np
import pandas as pd
import tensorflow as tf

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score
)


# ============================================================
# Configuration
# ============================================================

FEATURES = [
    "temperature",
    "vibration",
    "pressure",
    "humidity",
    "energy_consumption"
]

LABEL = "state"


# ============================================================
# Load Factory Data
# ============================================================

factory_name = sys.argv[1]

factory_number = factory_name.replace("factory_", "")

csv_path = os.path.join(
    "..",
    "data",
    factory_name,
    "sensor_data.csv"
)

print(f"\nLoading data for {factory_name}...")
print(f"CSV: {csv_path}")


df = pd.read_csv(csv_path)

print(f"Total samples: {len(df)}")


# ============================================================
# Prepare Data
# ============================================================

X = df[FEATURES].values

y = df[LABEL].map({
    "normal": 0,
    "failure": 1
}).values


X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)


# ============================================================
# Scaling
# ============================================================

scaler = StandardScaler()

X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)


print(f"Training samples: {len(X_train)}")
print(f"Testing samples: {len(X_test)}")

print(
    f"Failure rate: {np.mean(y) * 100:.2f}%"
)


# ============================================================
# Model
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


model = create_model()


# ============================================================
# Flower Client
# ============================================================

class FactoryClient(fl.client.NumPyClient):

    def get_parameters(self, config):

        return model.get_weights()


    def fit(self, parameters, config):

        print(
            f"\n[{factory_name}] Local training..."
        )

        model.set_weights(parameters)

        model.fit(
            X_train,
            y_train,
            epochs=5,
            batch_size=32,
            verbose=0
        )

        print(
            f"[{factory_name}] Training completed."
        )

        return (
            model.get_weights(),
            len(X_train),
            {}
        )


    def evaluate(self, parameters, config):

        model.set_weights(parameters)

        # Loss
        loss, accuracy = model.evaluate(
            X_test,
            y_test,
            verbose=0
        )

        # Predictions
        probabilities = model.predict(
            X_test,
            verbose=0
        ).flatten()

        predictions = (
            probabilities >= 0.5
        ).astype(int)


        # Metrics
        accuracy_value = accuracy_score(
            y_test,
            predictions
        )

        precision = precision_score(
            y_test,
            predictions,
            zero_division=0
        )

        recall = recall_score(
            y_test,
            predictions,
            zero_division=0
        )

        f1 = f1_score(
            y_test,
            predictions,
            zero_division=0
        )


        print(
            f"\n[{factory_name}] Evaluation"
        )

        print(
            f"Accuracy  : {accuracy_value:.4f}"
        )

        print(
            f"Precision : {precision:.4f}"
        )

        print(
            f"Recall    : {recall:.4f}"
        )

        print(
            f"F1-score  : {f1:.4f}"
        )


        return (
            float(loss),
            len(X_test),
            {
                "accuracy": float(accuracy_value),
                "precision": float(precision),
                "recall": float(recall),
                "f1": float(f1)
            }
        )


# ============================================================
# Start Client
# ============================================================

print(
    f"\nStarting Flower client for {factory_name}..."
)

fl.client.start_numpy_client(
    server_address="127.0.0.1:8080",
    client=FactoryClient()
)