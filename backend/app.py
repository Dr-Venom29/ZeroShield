from flask import Flask, jsonify
from flask_socketio import SocketIO
import pickle
import random
import time
import pandas as pd

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Load trained model
with open("model.pkl", "rb") as f:
    model = pickle.load(f)

# Store live history
history = []

# Attack mode flag
attack_mode = {"enabled": False}


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
    return {
        "cpu": random.randint(80, 95),
        "ram": random.randint(85, 98),
        "requests_per_sec": random.randint(100, 250),
        "failed_logins": random.randint(8, 20),
        "response_time": random.randint(400, 900)
    }


def detect(metrics):
    # Use DataFrame with proper feature names to match training
    features = pd.DataFrame([{
        "cpu": metrics["cpu"],
        "ram": metrics["ram"],
        "requests_per_sec": metrics["requests_per_sec"],
        "failed_logins": metrics["failed_logins"],
        "response_time": metrics["response_time"]
    }])

    prediction = model.predict(features)[0]

    # Simulated threat score based on anomaly result
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
    attack_mode["enabled"] = True
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
    print("Client connected")


def background_stream():
    while True:
        metrics = generate_attack_data() if attack_mode["enabled"] else generate_normal_data()
        result = detect(metrics)
        socketio.emit("update", result)
        socketio.sleep(2)


if __name__ == "__main__":
    socketio.start_background_task(background_stream)
    socketio.run(app, debug=True)