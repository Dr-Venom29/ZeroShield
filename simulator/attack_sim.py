import numpy as np
import pandas as pd
import os

BASELINE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "baseline.csv"
)


def generate_attack_samples(n=10):
    base = pd.read_csv(BASELINE_PATH)

    expected_cols = [
        "cpu",
        "ram",
        "requests_per_sec",
        "failed_logins",
        "response_time"
    ]

    for col in expected_cols:
        if col not in base.columns:
            raise ValueError(f"Missing column in baseline.csv: {col}")

    sampled = base.sample(n=n, replace=True).copy()

    # Create realistic attack spikes
    sampled["cpu"] = np.clip(sampled["cpu"] * np.random.uniform(3, 5, n), 0, 100)
    sampled["ram"] = np.clip(sampled["ram"] * np.random.uniform(2, 3, n), 0, 100)
    sampled["requests_per_sec"] *= np.random.randint(5, 15, n)
    sampled["failed_logins"] += np.random.randint(5, 20, n)
    sampled["response_time"] *= np.random.uniform(3, 6, n)

    sampled["label"] = 1

    return sampled


if __name__ == "__main__":
    attacks = generate_attack_samples(5)
    print(attacks)