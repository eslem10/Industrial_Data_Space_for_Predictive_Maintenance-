import os
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


NUM_FACTORIES = 3
SAMPLES_PER_FACTORY = 10000

# data folder is one level above simulator
OUTPUT_DIR = "../data"


def generate_factory_data(factory_id, num_samples):

    data = []

    start_time = datetime.now()

    for i in range(num_samples):

        timestamp = start_time + timedelta(seconds=i)

        # 5% failure cases
        failure = random.random() < 0.05

        if failure:
            temperature = np.random.normal(90, 7)
            vibration = np.random.normal(1.5, 0.3)
            pressure = np.random.normal(6, 0.8)
            humidity = np.random.normal(50, 6)
            energy = np.random.normal(11, 1.5)
            state = "failure"

        else:
            temperature = np.random.normal(65, 5)
            vibration = np.random.normal(0.4, 0.12)
            pressure = np.random.normal(3.5, 0.4)
            humidity = np.random.normal(45, 5)
            energy = np.random.normal(7, 1)
            state = "normal"

        data.append({
            "timestamp": timestamp,
            "factory_id": factory_id,
            "temperature": round(max(0, temperature), 2),
            "vibration": round(max(0, vibration), 3),
            "pressure": round(max(0, pressure), 2),
            "humidity": round(max(0, humidity), 2),
            "energy_consumption": round(max(0, energy), 2),
            "state": state
        })

    return pd.DataFrame(data)


def main():

    print("==========================================")
    print(" Industrial IoT Data Simulator")
    print("==========================================")

    for factory in range(1, NUM_FACTORIES + 1):

        factory_id = f"F{factory}"

        factory_dir = os.path.join(
            OUTPUT_DIR,
            f"factory_{factory}"
        )

        os.makedirs(factory_dir, exist_ok=True)

        print(f"\nGenerating data for {factory_id}...")

        df = generate_factory_data(
            factory_id,
            SAMPLES_PER_FACTORY
        )

        output_file = os.path.join(
            factory_dir,
            "sensor_data.csv"
        )

        df.to_csv(
            output_file,
            index=False
        )

        print(f"OK: {len(df)} samples generated")
        print(f"Saved to: {output_file}")

        print("\nState distribution:")
        print(df["state"].value_counts())

    print("\n==========================================")
    print(" Data generation completed successfully!")
    print("==========================================")


if __name__ == "__main__":
    main()