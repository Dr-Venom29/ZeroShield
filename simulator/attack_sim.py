import numpy as np
import pandas as pd
import os

BASELINE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "baseline.csv")


def generate_attack_samples(n=10, noise_scale=0.5):
    base = pd.read_csv(BASELINE_PATH)
    feature_cols = [c for c in base.columns if c != "label"]

    benign = base[base["label"] == 0]
    if benign.empty:
        raise ValueError("baseline.csv must contain some benign samples (label == 0)")

    benign_features = benign[feature_cols].values

    idx = np.random.choice(len(benign_features), size=n, replace=True)
    sampled = benign_features[idx]

    noise = np.random.normal(scale=noise_scale, size=sampled.shape)
    attacks = sampled + noise

    df_attacks = pd.DataFrame(attacks, columns=feature_cols)
    df_attacks["label"] = 1
    return df_attacks


if __name__ == "__main__":
    attacks = generate_attack_samples(5)
    print(attacks.head())
