import pandas as pd
import pickle
from sklearn.ensemble import IsolationForest
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "baseline.csv")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")

# Load baseline data
df = pd.read_csv(DATA_PATH)

# Train Isolation Forest
model = IsolationForest(contamination=0.1, random_state=42)
model.fit(df)

# Save model
with open(MODEL_PATH, "wb") as f:
    pickle.dump(model, f)

print("✅ Model trained and saved as model.pkl")