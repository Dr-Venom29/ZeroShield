from flask import Flask, jsonify
from flask_socketio import SocketIO
import pickle
import time
import pandas as pd
import os
import sys
import psutil
import random
import logging
import json

# Allow importing from simulator folder
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from simulator.attack_sim import generate_attack_samples

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config["SECRET_KEY"] = "zeroshield-secret"

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="eventlet",
)

# Load trained model + metadata
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")
with open(MODEL_PATH, "rb") as f:
    saved = pickle.load(f)

model = saved["model"]
threshold = saved["threshold"]
baseline_min = saved["baseline_min"]
baseline_max = saved["baseline_max"]
mean_score = saved.get("mean", 0.0)
std_score = saved.get("std", 0.05)

# Runtime state
history = []
isolation_log = []
attack_mode = {"enabled": False}
attack_buffer = []
C_VALUE = {"val": 1.5}
isolated_state = {"active": False}


# Fixed service-to-service dependency graph used for threat propagation
SERVICE_GRAPH = {
    "svc-1": {"svc-2": 0.9, "svc-3": 0.4},
    "svc-2": {"svc-1": 0.8, "svc-4": 0.7},
    "svc-3": {"svc-1": 0.5, "svc-4": 0.3},
    "svc-4": {"svc-2": 0.6},
}


def log_event(result):
  """Emit a single structured security telemetry log.

  This keeps downstream monitoring simple: logs are JSON lines that
  include the core detection fields and attack metadata.
  """
  response = result.get("response_engine") or {}
  threat_graph = result.get("threat_graph") or {}
  logging.info(
      json.dumps(
          {
              "timestamp": result.get("timestamp"),
              "tier": result.get("tier"),
              "score": result.get("anomaly_score"),
              "attack_type": result.get("attack_type"),
              "attack_severity": result.get("attack_severity"),
              "response_action": response.get("action"),
              "workload_id": result.get("workload_id"),
              "isolation_status": result.get("isolation_status"),
              "blast_radius": threat_graph.get("blast_radius"),
          }
      )
  )


def get_confidence_tier(score):
    if score >= 85:
        return "HIGH"
    elif score >= 60:
        return "MEDIUM"
    elif score >= 35:
        return "LOW"
    return "NORMAL"


def propagate_threat(primary_service, primary_score):
    """Estimate propagated risk to neighboring services in the graph.

    Uses a simple weighted model: risk decays by link strength and a
    global attenuation factor so neighbors are always lower risk than
    the primary node.
    """

    neighbors = SERVICE_GRAPH.get(primary_service, {})
    impacted = []

    for neighbor, weight in neighbors.items():
        propagated_risk = round(primary_score * weight * 0.55, 2)

        if propagated_risk >= 30:
            tier = get_confidence_tier(propagated_risk)
            impacted.append(
                {
                    "service": neighbor,
                    "risk_score": propagated_risk,
                    "tier": tier,
                    "link_strength": weight,
                }
            )

    impacted.sort(key=lambda x: x["risk_score"], reverse=True)
    return impacted


def estimate_blast_radius(impacted_services):
    """Summarize how wide the potential impact is across the graph."""

    high = sum(1 for s in impacted_services if s["risk_score"] >= 60)
    med = sum(1 for s in impacted_services if 35 <= s["risk_score"] < 60)
    low = sum(1 for s in impacted_services if s["risk_score"] < 35)

    if high >= 2:
        return "HIGH"
    elif high >= 1 or med >= 2:
        return "MEDIUM"
    elif med >= 1 or low >= 2:
        return "LOW"
    return "MINIMAL"


def generate_normal_data():
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent

    return {
        "workload_id": f"svc-{random.randint(1, 3)}",
        "cpu": round(cpu, 2),
        "ram": round(ram, 2),
        "requests_per_sec": max(1, int(8 + (cpu / 100) * 15 + random.uniform(-2, 2))),
        "failed_logins": random.choices([0, 1], weights=[95, 5])[0],
        "response_time": max(80, int(110 + (ram / 100) * 80 + random.uniform(-10, 10))),
    }


def generate_attack_sample():
    """Generate a single synthetic attack metrics dict from baseline.

    Uses simulator.attack_sim.generate_attack_samples to keep backend
    logic thin and reuse the simulator's attack semantics.
    """
    df = generate_attack_samples(1)
    sample = df.iloc[0].to_dict()

    # Attach a workload id for UI/response scope (baseline.csv has none)
    sample["workload_id"] = f"svc-{random.randint(1, 3)}"

    return sample


def trigger_isolation(workload_id):
    event = {
        "workload_id": workload_id,
        "time": time.strftime("%H:%M:%S"),
        "status": "QUARANTINED",
        "action": "Suspicious workload isolated"
    }

    isolation_log.append(event)
    if len(isolation_log) > 20:
        isolation_log.pop(0)

    isolated_state["active"] = True
    return event


def detect(metrics):
    features = pd.DataFrame([
        {
            "cpu": metrics["cpu"],
            "ram": metrics["ram"],
            "requests_per_sec": metrics["requests_per_sec"],
            "failed_logins": metrics["failed_logins"],
            "response_time": metrics["response_time"],
        }
    ])

    raw_score = model.decision_function(features)[0]

    # Dynamic threshold using mean - C * std
    dynamic_threshold = mean_score - (C_VALUE["val"] * std_score)

    # Distance from threshold
    delta = dynamic_threshold - raw_score

    if delta <= 0:
        # Normal zone (0–35)
        anomaly_score = max(0, 35 - (abs(delta) / (std_score + 1e-8)) * 20)
    else:
        # Attack zone — calibrated using std only
        severity = delta / (std_score + 1e-8)

        if severity < 0.5:
            anomaly_score = 40 + severity * 20      # 40–50
        elif severity < 1.0:
            anomaly_score = 50 + (severity - 0.5) * 30   # 50–65
        elif severity < 2.0:
            anomaly_score = 65 + (severity - 1.0) * 20   # 65–85
        elif severity < 3.0:
            anomaly_score = 85 + (severity - 2.0) * 10   # 85–95
        else:
            anomaly_score = 95 + min((severity - 3.0) * 2, 5)  # cap 100

    anomaly_score = round(max(0, min(100, anomaly_score)), 2)
    tier = get_confidence_tier(anomaly_score)

    workload_id = metrics.get("workload_id", "svc-1")
    isolation_status = "MONITORING"
    response_action = "Monitoring only"
    isolation_event = None

    if tier == "HIGH":
        isolation_status = "QUARANTINED"
        response_action = "Quarantine triggered"

        if not isolated_state["active"]:
            isolation_event = trigger_isolation(workload_id)

    elif isolated_state["active"] and tier in ["NORMAL", "LOW"]:
        isolation_status = "RECOVERED"
        response_action = "Recovered to monitoring state"
        isolated_state["active"] = False

    # Threat propagation over the fixed service graph
    propagated = propagate_threat(workload_id, anomaly_score)
    blast_radius = estimate_blast_radius(propagated)

    result = {
        **metrics,
        "anomaly_score": anomaly_score,
        "tier": tier,
        "timestamp": time.strftime("%H:%M:%S"),
        "isolation_status": isolation_status,
        "threat_graph": {
            "primary_node": workload_id,
            "impacted_services": propagated,
            "blast_radius": blast_radius,
        },
        "response_engine": {
            "threat_detected": "YES" if tier in ["MEDIUM", "HIGH"] else "NO",
            "confidence": tier,
            "action": response_action,
            "scope": workload_id,
        },
        "isolation_event": isolation_event,
    }

    history.append(result)
    if len(history) > 50:
        history.pop(0)

    # Emit structured security telemetry for downstream monitoring
    log_event(result)

    return result


@app.route("/status")
def status():
    if attack_mode["enabled"]:
        metrics = generate_attack_sample()
    else:
        metrics = generate_normal_data()
    return jsonify(detect(metrics))


@app.route("/history")
def get_history():
    return jsonify(history)


@app.route("/isolation-log")
def get_isolation_log():
    return jsonify(isolation_log)


@app.route("/simulate-attack", methods=["POST"])
def simulate_attack():
    global attack_buffer
    attack_mode["enabled"] = True
    attack_buffer = []
    isolated_state["active"] = False
    return jsonify({"message": "Attack simulation started!"})


@app.route("/stop-attack", methods=["POST"])
def stop_attack():
    attack_mode["enabled"] = False
    isolated_state["active"] = False
    return jsonify({"message": "Attack simulation stopped."})


@app.route("/set-threshold/<float:c>", methods=["POST"])
def set_threshold(c):
    C_VALUE["val"] = round(c, 2)
    return jsonify({"c_value": C_VALUE["val"]})


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "attack_mode": attack_mode["enabled"],
        "history_count": len(history),
        "c_value": C_VALUE["val"],
        "isolated": isolated_state["active"]
    })


@socketio.on("connect")
def handle_connect():
    print("Client connected")


@socketio.on("disconnect")
def handle_disconnect():
    print("Client disconnected")


def background_stream():
    while True:
        if attack_mode["enabled"]:
            metrics = generate_attack_sample()
        else:
            metrics = generate_normal_data()
        result = detect(metrics)
        socketio.emit("update", result)
        print("📡 Emitted:", result)
        socketio.sleep(2)


if __name__ == "__main__":
    socketio.start_background_task(background_stream)
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)