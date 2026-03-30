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

    # Convert mutable numeric telemetry columns to float before perturbation
    numeric_cols = [
        "cpu",
        "ram",
        "requests_per_sec",
        "failed_logins",
        "response_time",
    ]
    sampled[numeric_cols] = sampled[numeric_cols].astype(float)

    attack_types = ["CPU_SPIKE", "AUTH_FLOOD", "MEM_EXHAUSTION", "SLOWDOWN"]

    # Severity distribution (mild / moderate / severe)
    # Recommended demo weights: 0.3, 0.4, 0.3
    # For more intense demos you could use: [0.2, 0.3, 0.5]
    severities = random.choices(
        ["mild", "moderate", "severe"],
        weights=[0.3, 0.4, 0.3],
        k=n
    )

    chosen_types = [random.choice(attack_types) for _ in range(n)]

    for i in range(n):
        atk_type = chosen_types[i]
        severity = severities[i]
        idx = sampled.index[i]

        # Severity profiles: define strong / moderate / slight multipliers
        if severity == "mild":
            strong = np.random.uniform(1.4, 1.8)
            moderate = np.random.uniform(1.15, 1.35)
            slight = np.random.uniform(1.02, 1.1)
            fail_base = (0, 2)
        elif severity == "moderate":
            strong = np.random.uniform(1.8, 2.4)
            moderate = np.random.uniform(1.3, 1.6)
            slight = np.random.uniform(1.05, 1.15)
            fail_base = (2, 6)
        else:  # severe
            strong = np.random.uniform(2.4, 3.2)
            moderate = np.random.uniform(1.5, 2.0)
            slight = np.random.uniform(1.1, 1.2)
            fail_base = (5, 12)

        # CPU_SPIKE
        # cpu ↑↑, response_time ↑, ram slight ↑, failed_logins not much
        if atk_type == "CPU_SPIKE":
            sampled.at[idx, "cpu"] *= strong
            sampled.at[idx, "response_time"] *= moderate
            sampled.at[idx, "ram"] *= slight
            # keep auth noise small
            sampled.at[idx, "failed_logins"] += random.randint(*fail_base[:2]) // 2
            sampled.at[idx, "requests_per_sec"] *= moderate

        # AUTH_FLOOD
        # failed_logins ↑↑, requests_per_sec ↑, response_time ↑, cpu moderate ↑
        elif atk_type == "AUTH_FLOOD":
            sampled.at[idx, "cpu"] *= moderate
            sampled.at[idx, "response_time"] *= moderate
            sampled.at[idx, "requests_per_sec"] *= strong
            sampled.at[idx, "failed_logins"] += random.randint(*fail_base)

        # MEM_EXHAUSTION
        # ram ↑↑, cpu moderate ↑, response_time ↑, requests moderate ↑
        elif atk_type == "MEM_EXHAUSTION":
            sampled.at[idx, "ram"] *= strong
            sampled.at[idx, "cpu"] *= moderate
            sampled.at[idx, "response_time"] *= moderate
            sampled.at[idx, "requests_per_sec"] *= moderate
            sampled.at[idx, "failed_logins"] += random.randint(*fail_base[:2])

        # SLOWDOWN
        # response_time ↑↑, cpu moderate, ram moderate, requests may not be huge
        elif atk_type == "SLOWDOWN":
            sampled.at[idx, "response_time"] *= strong
            sampled.at[idx, "cpu"] *= moderate
            sampled.at[idx, "ram"] *= moderate
            sampled.at[idx, "requests_per_sec"] *= slight
            sampled.at[idx, "failed_logins"] += random.randint(*fail_base[:2]) // 2

        # Ensure integer-like counters stay reasonable
        sampled.at[idx, "requests_per_sec"] = max(
            1,
            int(round(sampled.at[idx, "requests_per_sec"]))
        )
        sampled.at[idx, "failed_logins"] = max(
            0,
            int(round(sampled.at[idx, "failed_logins"]))
        )

    # Clip values to realistic ranges
    sampled["cpu"] = np.clip(sampled["cpu"], 0, 100)
    sampled["ram"] = np.clip(sampled["ram"], 0, 100)
    sampled["response_time"] = np.clip(sampled["response_time"], 0, 2000)

    # Normalize output types
    sampled["cpu"] = sampled["cpu"].round(2)
    sampled["ram"] = sampled["ram"].round(2)
    sampled["response_time"] = sampled["response_time"].round(2)
    sampled["requests_per_sec"] = sampled["requests_per_sec"].astype(int)
    sampled["failed_logins"] = sampled["failed_logins"].astype(int)

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