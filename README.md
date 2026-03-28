## ZeroShield

AI-powered zero-day threat detection and response demo.

This MVP streams live cloud workload telemetry from a Python backend into a React dashboard, scores it for anomalies, and visualizes automated response decisions.

---

## Project structure

```bash
ZeroShield/
├── backend/              # Python API, model, and simulator control
│   ├── app.py            # Flask + Socket.IO backend
│   ├── train_model.py    # Trains anomaly model on baseline.csv
│   └── model.pkl         # Trained model artifact
├── simulator/            # Attack traffic generator
│   └── attack_sim.py
├── data/
│   └── baseline.csv      # Baseline workload telemetry
├── frontend/
│   └── zeroshield-ui/    # React + Vite dashboard
├── requirements.txt      # Python dependencies
└── README.md
```

---

## Key features

- **Live Threat Score**
	- Streams anomaly scores (0–100) over WebSocket.
	- Color-coded risk tier: LOW / MEDIUM / HIGH.

- **Workload Isolation Status**
	- Card that reflects the current isolation posture.
	- Logic: if `anomaly_score > 85` → status **QUARANTINED**, else **MONITORING**.

- **Cloud Workload Telemetry**
	- Renamed metrics to feel like cloud infra, not a local laptop:
		- CPU Utilization
		- Memory Utilization
		- Request Throughput
		- Auth Failure Rate
		- Service Latency

- **Response Engine**
	- Summarizes what the system is doing about threats:
		- Status: Threat detected / No active threat
		- Confidence: based on model tier (e.g. HIGH)
		- Action: Quarantine triggered / Monitoring only
		- Scope: Suspicious workload / All workloads

- **Recent Alerts & Trend**
	- Live time-series chart of anomaly score.
	- Scrollable list of recent alerts with timestamp and tier.

---

## Prerequisites

- Python 3.9+ (recommended)
- Node.js 18+ and npm

---

## Backend setup

From the project root:

```bash
cd backend

# Install Python dependencies
pip install -r ../requirements.txt

# Train / refresh the model
python train_model.py

# Run the API (Flask + Socket.IO)
python app.py
```

By default the backend exposes:

- `GET  /status` – latest telemetry + threat score payload
- `POST /simulate-attack` – starts attack simulation
- `POST /stop-attack` – stops attack simulation
- Socket.IO channel `update` – pushes live status objects

Make sure the backend is running before starting the UI.

---

## Frontend (dashboard) setup

In a separate terminal:

```bash
cd frontend/zeroshield-ui

# Install JS dependencies
npm install

# Start the Vite dev server
npm run dev
```

Open the URL printed by Vite (usually `http://localhost:5173`). The dashboard will automatically connect to `http://127.0.0.1:5000` for status and WebSocket updates.

---

## Simulating attacks

The UI already provides buttons:

- **🚨 Simulate Attack** → calls `/simulate-attack` on the backend.
- **✅ Stop Attack** → calls `/stop-attack`.

Under attack, you should see:

- Threat Score spike toward 100.
- Tier move to **HIGH**.
- Isolation Status switch to **QUARANTINED**.
- Response Engine show `Threat detected / Quarantine triggered / Suspicious workload`.

You can also run the simulator script directly (optional):

```bash
cd simulator
python attack_sim.py
```

---

## Tech stack

- **Backend:** Python, Flask, scikit-learn, Socket.IO
- **Frontend:** React, Vite, Recharts, socket.io-client

---

## Notes

This is an MVP intended for demos and hackathons, not production. For a real deployment you’d want:

- AuthN/Z on all endpoints.
- Persistent storage for alerts/events.
- Hardening around model loading and input validation.
- Kubernetes or cloud-hosted deployment (e.g., containerized backend + static frontend).
