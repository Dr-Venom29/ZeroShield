import pandas as pd
import pickle
from sklearn.ensemble import IsolationForest

# Load baseline data
df = pd.read_csv("../data/baseline.csv")

# Train model
model = IsolationForest(contamination=0.1, random_state=42)
model.fit(df)

# Save model
with open("model.pkl", "wb") as f:
    pickle.dump(model, f)

print("✅ Model trained and saved as model.pkl")