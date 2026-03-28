import numpy as np
import pandas as pd
import os
import random

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

    attack_types = ["CPU_SPIKE", "AUTH_FLOOD", "MEM_EXHAUSTION", "SLOWDOWN"]

    # More balanced severity distribution
    severities = random.choices(
        ["mild", "moderate", "severe"],
        weights=[45, 35, 20],   # <-- important
        k=n
    )

    chosen_types = [random.choice(attack_types) for _ in range(n)]

    for i in range(n):
        atk_type = chosen_types[i]
        severity = severities[i]

        if severity == "mild":
            cpu_mult = np.random.uniform(1.05, 1.25)
            ram_mult = np.random.uniform(1.03, 1.18)
            req_mult = np.random.randint(1, 3)
            fail_add = np.random.randint(0, 2)
            resp_mult = np.random.uniform(1.05, 1.35)

        elif severity == "moderate":
            cpu_mult = np.random.uniform(1.2, 1.5)
            ram_mult = np.random.uniform(1.1, 1.35)
            req_mult = np.random.randint(2, 4)
            fail_add = np.random.randint(2, 5)
            resp_mult = np.random.uniform(1.3, 2.0)

        else:  # severe
            cpu_mult = np.random.uniform(1.6, 2.2)
            ram_mult = np.random.uniform(1.3, 1.8)
            req_mult = np.random.randint(3, 6)
            fail_add = np.random.randint(4, 8)
            resp_mult = np.random.uniform(1.8, 3.0)

        # Apply attack-type-specific emphasis
        if atk_type == "CPU_SPIKE":
            sampled.at[sampled.index[i], "cpu"] *= cpu_mult * 1.2
        elif atk_type == "AUTH_FLOOD":
            sampled.at[sampled.index[i], "failed_logins"] += fail_add * 2
            sampled.at[sampled.index[i], "requests_per_sec"] *= req_mult
        elif atk_type == "MEM_EXHAUSTION":
            sampled.at[sampled.index[i], "ram"] *= ram_mult * 1.2
        elif atk_type == "SLOWDOWN":
            sampled.at[sampled.index[i], "response_time"] *= resp_mult * 1.3

        # Apply general anomaly uplift
        sampled.at[sampled.index[i], "cpu"] *= cpu_mult
        sampled.at[sampled.index[i], "ram"] *= ram_mult
        sampled.at[sampled.index[i], "requests_per_sec"] *= req_mult
        sampled.at[sampled.index[i], "failed_logins"] += fail_add
        sampled.at[sampled.index[i], "response_time"] *= resp_mult

    # Clip values to realistic ranges
    sampled["cpu"] = np.clip(sampled["cpu"], 0, 100)
    sampled["ram"] = np.clip(sampled["ram"], 0, 100)
    sampled["response_time"] = np.clip(sampled["response_time"], 0, 2000)

    sampled["label"] = 1
    sampled["attack_type"] = chosen_types
    sampled["attack_severity"] = severities

    return sampled


if __name__ == "__main__":
    attacks = generate_attack_samples(5)
    print(
        attacks[
            [
                "cpu",
                "ram",
                "requests_per_sec",
                "failed_logins",
                "response_time",
                "attack_type",
                "attack_severity"
            ]
        ]
    )