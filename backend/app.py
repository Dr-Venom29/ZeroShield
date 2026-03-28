from flask import Flask, jsonify
from flask_socketio import SocketIO
import pickle
import random
import time
import pandas as pd
import os
import sys

# Allow importing from simulator folder
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from simulator.attack_sim import generate_attack_samples

app = Flask(__name__)
app.config["SECRET_KEY"] = "zeroshield-secret"

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet"
)

# Load trained model
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")
with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)

history = []
attack_mode = {"enabled": False}
attack_buffer = []


def get_confidence_tier(score):
    if score >= 80:
        return "HIGH"
    elif score >= 60:
        return "MEDIUM"
    elif score >= 40:
        return "LOW"
    return "NORMAL"


def generate_normal_data():
    return {
        "cpu": random.randint(18, 25),
        "ram": random.randint(40, 47),
        "requests_per_sec": random.randint(11, 17),
        "failed_logins": random.randint(0, 1),
        "response_time": random.randint(115, 140)
    }


def generate_attack_data():
    global attack_buffer

    if not attack_buffer:
        df_attacks = generate_attack_samples(10)

        if "label" in df_attacks.columns:
            df_attacks = df_attacks.drop(columns=["label"])

        attack_buffer = df_attacks.to_dict(orient="records")

    return attack_buffer.pop(0)


def detect(metrics):
    features = pd.DataFrame([{
        "cpu": metrics["cpu"],
        "ram": metrics["ram"],
        "requests_per_sec": metrics["requests_per_sec"],
        "failed_logins": metrics["failed_logins"],
        "response_time": metrics["response_time"]
    }])

    prediction = model.predict(features)[0]

    if prediction == -1:
        anomaly_score = random.randint(70, 98)
    else:
        anomaly_score = random.randint(5, 35)

    tier = get_confidence_tier(anomaly_score)

    result = {
        **metrics,
        "anomaly_score": anomaly_score,
        "tier": tier,
        "timestamp": time.strftime("%H:%M:%S")
    }

    history.append(result)
    if len(history) > 50:
        history.pop(0)

    return result


@app.route("/status")
def status():
    metrics = generate_attack_data() if attack_mode["enabled"] else generate_normal_data()
    return jsonify(detect(metrics))


@app.route("/history")
def get_history():
    return jsonify(history)


@app.route("/simulate-attack")
def simulate_attack():
    global attack_buffer
    attack_mode["enabled"] = True
    attack_buffer = []
    return jsonify({"message": "🚨 Attack simulation started!"})


@app.route("/stop-attack")
def stop_attack():
    attack_mode["enabled"] = False
    return jsonify({"message": "✅ Attack simulation stopped."})


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "attack_mode": attack_mode["enabled"],
        "history_count": len(history)
    })


@socketio.on("connect")
def handle_connect():
    print("✅ Client connected")


@socketio.on("disconnect")
def handle_disconnect():
    print("❌ Client disconnected")


def background_stream():
    while True:
        metrics = generate_attack_data() if attack_mode["enabled"] else generate_normal_data()
        result = detect(metrics)
        socketio.emit("update", result)
        print("📡 Emitted:", result)   # DEBUG
        socketio.sleep(2)


if __name__ == "__main__":
    socketio.start_background_task(background_stream)
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)