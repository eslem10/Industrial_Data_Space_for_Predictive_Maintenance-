import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score, f1_score

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
FEATURES = ["temperature", "vibration", "pressure", "humidity", "energy_consumption"]
LABEL = "state"

def train_local_factory(factory_name):
    csv_path = os.path.join(DATA_DIR, factory_name, "sensor_data.csv")
    if not os.path.exists(csv_path):
        print(f"[-] Data for {factory_name} not found at {csv_path}")
        return

    df = pd.read_csv(csv_path)
    if len(df) < 10:
        print(f"[-] Not enough data points in {factory_name} (only {len(df)} samples)")
        return

    print(f"\n==========================================")
    print(f"Training Local Model for {factory_name}")
    print(f"Samples: {len(df)} | Failure rate: {(df[LABEL] == 'failure').mean() * 100:.2f}%")
    print(f"==========================================")

    X = df[FEATURES].values
    y = df[LABEL].map({"normal": 0, "failure": 1}).values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y if len(np.unique(y)) > 1 else None
    )

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    clf = RandomForestClassifier(n_estimators=50, random_state=42)
    clf.fit(X_train, y_train)

    predictions = clf.predict(X_test)
    acc = accuracy_score(y_test, predictions)
    f1 = f1_score(y_test, predictions, zero_division=0)

    print(f"Accuracy: {acc * 100:.2f}% | F1-Score: {f1 * 100:.2f}%")
    print(classification_report(y_test, predictions, target_names=["normal", "failure"] if len(np.unique(y)) > 1 else ["normal"], zero_division=0))

if __name__ == "__main__":
    for i in range(1, 4):
        train_local_factory(f"factory_{i}")
