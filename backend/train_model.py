import pandas as pd
import pickle
from sklearn.ensemble import IsolationForest
import os
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "baseline.csv")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")

EXPECTED_COLS = [
    "cpu",
    "ram",
    "requests_per_sec",
    "failed_logins",
    "response_time",
]

# Load baseline data
df = pd.read_csv(DATA_PATH)

# Validate columns
for col in EXPECTED_COLS:
    if col not in df.columns:
        raise ValueError(f"Missing required column in baseline.csv: {col}")

df = df[EXPECTED_COLS]

# Train model
model = IsolationForest(contamination=0.1, random_state=42)
model.fit(df)

# Baseline decision scores
scores = model.decision_function(df)

# Save stats
mean_score = float(np.mean(scores))
std_score = float(np.std(scores))
threshold = mean_score - 1.5 * std_score
baseline_min = float(np.min(scores))
baseline_max = float(np.max(scores))

with open(MODEL_PATH, "wb") as f:
    pickle.dump(
        {
            "model": model,
            "threshold": threshold,
            "baseline_min": baseline_min,
            "baseline_max": baseline_max,
            "mean": mean_score,
            "std": std_score,
        },
        f,
    )

print("Model trained and saved as model.pkl")
print(f"Samples: {len(df)}")
print(f"Mean Score: {mean_score:.4f}")
print(f"Std Dev: {std_score:.4f}")
print(f"Threshold: {threshold:.4f}")
print(f"Baseline Min: {baseline_min:.4f}")
print(f"Baseline Max: {baseline_max:.4f}")