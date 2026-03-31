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


# Simple STRIDE-style mapping for simulated attack patterns
STRIDE_MAP = {
    "CPU_SPIKE": {"stride": "DoS", "label": "Denial of Service"},
    "AUTH_FLOOD": {"stride": "S", "label": "Spoofing"},
    "MEM_EXHAUSTION": {"stride": "DoS", "label": "Denial of Service"},
    "SLOWDOWN": {"stride": "T", "label": "Tampering"},
    "NORMAL": {"stride": "None", "label": "No threat"},
}


DREAD_MAP = {
    "CPU_SPIKE": {
        "damage": 8,
        "reproducibility": 7,
        "exploitability": 6,
        "affected_users": 7,
        "discoverability": 6,
    },
    "AUTH_FLOOD": {
        "damage": 7,
        "reproducibility": 9,
        "exploitability": 8,
        "affected_users": 8,
        "discoverability": 7,
    },
    "MEM_EXHAUSTION": {
        "damage": 8,
        "reproducibility": 8,
        "exploitability": 6,
        "affected_users": 7,
        "discoverability": 6,
    },
    "SLOWDOWN": {
        "damage": 6,
        "reproducibility": 7,
        "exploitability": 5,
        "affected_users": 6,
        "discoverability": 5,
    },
    "NORMAL": {
        "damage": 1,
        "reproducibility": 1,
        "exploitability": 1,
        "affected_users": 1,
        "discoverability": 1,
    },
}


def get_dread_assessment(attack_type):
    scores = DREAD_MAP.get(attack_type, DREAD_MAP["NORMAL"])
    total = sum(scores.values())
    avg = round(total / 5, 1)

    if avg >= 8:
        level = "CRITICAL"
    elif avg >= 6:
        level = "HIGH"
    elif avg >= 4:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        **scores,
        "score": avg,
        "level": level,
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


def get_adaptive_response(tier, blast_radius):
    """Determine response action based on anomaly severity and spread.

    Combines local risk (tier) with system-wide propagation risk (blast_radius)
    to choose a higher-level defense posture. This is intentionally simple but
    mirrors how real adaptive defense systems layer decisions.
    """

    # Critical scenario "+" wider propagation → full containment
    if tier == "HIGH" and blast_radius in ["MEDIUM", "HIGH"]:
        return "Containment zone activated"

    # High anomaly but limited spread
    if tier == "HIGH":
        return "Isolation enforced"

    # Medium anomaly + any non-minimal propagation risk
    if tier == "MEDIUM" and blast_radius in ["LOW", "MEDIUM", "HIGH"]:
        return "Lateral movement prevention"

    # Early-stage suspicious behavior with noticeable spread
    if tier == "LOW" and blast_radius == "MEDIUM":
        return "Traffic throttling enabled"

    # Default calm-state posture
    return "Passive monitoring"


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
    isolation_event = None

    if tier == "HIGH":
        isolation_status = "QUARANTINED"
        if not isolated_state["active"]:
            isolation_event = trigger_isolation(workload_id)

    elif isolated_state["active"] and tier in ["NORMAL", "LOW"]:
        isolation_status = "RECOVERED"
        isolated_state["active"] = False

    # Threat propagation over the fixed service graph
    propagated = propagate_threat(workload_id, anomaly_score)
    blast_radius = estimate_blast_radius(propagated)

    # Adaptive response strategy based on severity and potential spread
    response_action = get_adaptive_response(tier, blast_radius)

    # STRIDE-style threat classification based on simulated attack type
    attack_type = metrics.get("attack_type", "NORMAL")
    stride_info = STRIDE_MAP.get(
        attack_type,
        {
            "stride": "Unknown",
            "label": "Unknown",
        },
    )

    dread = get_dread_assessment(attack_type)

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
        "threat_classification": {
            "stride": stride_info["stride"],
            "label": stride_info["label"],
        },
        "dread_assessment": dread,
        "response_engine": {
            "threat_detected": "YES"
            if (tier in ["MEDIUM", "HIGH"] or blast_radius in ["MEDIUM", "HIGH"])
            else "NO",
            "confidence": tier,
            "action": response_action,
            "scope": "Propagation containment zone" if blast_radius in ["MEDIUM", "HIGH"] else workload_id,
            "strategy": "PROPAGATION_AWARE",
            "blast_radius": blast_radius,
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
        print("Emitted:", result)
        socketio.sleep(2)


if __name__ == "__main__":
    socketio.start_background_task(background_stream)
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)