from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FEATURES = ["temperature", "vibration", "pressure", "humidity", "energy_consumption"]
LABEL = "state"


def train_local_factory(factory_name: str) -> None:
    csv_path = DATA_DIR / factory_name / "sensor_data.csv"
    if not csv_path.is_file():
        print(f"[-] Data for {factory_name} not found at {csv_path}")
        return

    df = pd.read_csv(csv_path)
    required = FEATURES + [LABEL]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"{csv_path}: missing columns: {', '.join(missing)}")

    df = df[required].dropna()
    unknown_labels = sorted(set(df[LABEL]) - {"normal", "failure"})
    if unknown_labels:
        raise ValueError(f"{csv_path}: unknown states: {unknown_labels}")
    if len(df) < 10:
        print(f"[-] Not enough data points in {factory_name} (only {len(df)} samples)")
        return

    X = df[FEATURES]
    y = df[LABEL].map({"normal": 0, "failure": 1})
    counts = y.value_counts()
    stratify = y if len(counts) > 1 and counts.min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=stratify
    )

    model = RandomForestClassifier(
        n_estimators=100, random_state=42, class_weight="balanced"
    )
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    print(f"\n=== Local model: {factory_name} ===")
    print(f"Samples: {len(df)} | Failure rate: {y.mean() * 100:.2f}%")
    print(
        f"Accuracy: {accuracy_score(y_test, predictions):.2%} | "
        f"F1: {f1_score(y_test, predictions, zero_division=0):.4f}"
    )
    print(
        classification_report(
            y_test,
            predictions,
            labels=[0, 1],
            target_names=["normal", "failure"],
            zero_division=0,
        )
    )


if __name__ == "__main__":
    for number in range(1, 4):
        train_local_factory(f"factory_{number}")
