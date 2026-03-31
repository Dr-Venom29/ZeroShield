## ZeroShield

AI-powered zero-day **detection, propagation analysis, and adaptive response** demo.

ZeroShield streams live cloud workload telemetry from a Python backend into a React dashboard, scores it with an IsolationForest model, simulates structured attacks, models blast radius across a small service graph, and visualizes propagation-aware automated response decisions in real time.

---

## Project structure

```bash
ZeroShield/
├── backend/              # Python API, anomaly model, threat graph, and response engine
│   ├── app.py            # Flask + Socket.IO backend, propagation model, STRIDE + DREAD, isolation logic
│   ├── collector.py      # Collects real baseline telemetry into baseline.csv
│   ├── train_model.py    # Trains IsolationForest on baseline.csv and saves model.pkl
│   └── model.pkl         # Trained model artifact (generated)
├── simulator/            # Attack traffic generator (Phase B–E simulator)
│   └── attack_sim.py     # Generates typed, severity-aware attacks from baseline.csv
├── data/
│   └── baseline.csv      # Baseline workload telemetry (collected via collector.py)
├── frontend/
│   └── zeroshield-ui/    # React + Vite dashboard
├── requirements.txt      # Python dependencies
└── README.md
```

---

## Key features

- **Live Threat Score**
	- Streams model-derived anomaly scores (0–100) over WebSocket.
	- Color-coded risk tier: NORMAL / LOW / MEDIUM / HIGH.
	- Uses a dynamic threshold (mean − C·std) rather than a fixed score cut.

- **Attack Simulator (typed + severity-aware)**
	- `simulator/attack_sim.py` generates realistic attack telemetry from `baseline.csv`.
	- Attack types: `CPU_SPIKE`, `AUTH_FLOOD`, `MEM_EXHAUSTION`, `SLOWDOWN`.
	- Severity levels: `mild`, `moderate`, `severe` with weighted distribution.
	- Metrics are perturbed according to attack type/severity and then clipped/normalized.

- **Graph-aware Threat Propagation & Blast Radius**
	- Fixed service graph for four workloads (`svc-1`..`svc-4`) with weighted edges.
	- Backend propagates risk from the primary node to neighbors based on link strength.
	- Computes a qualitative blast radius: MINIMAL / LOW / MEDIUM / HIGH.
	- UI shows a mini topology map and impacted services with risk bars.

- **Adaptive Response Engine (Propagation-Aware)**
	- Response decisions consider both anomaly tier and blast radius.
	- Automatically chooses between:
		- Passive monitoring
		- Traffic throttling
		- Lateral movement prevention
		- Workload isolation
		- Full containment zone
	- Response scope expands from a single workload to a **Propagation containment zone** on wider blast radius.
	- Response Engine card surfaces Threat State, Confidence, Action, Strategy, Blast Radius, and Enforcement Scope.

- **STRIDE Threat Classification**
	- Every attack is mapped to STRIDE-style categories via a simple lookup:
		- `CPU_SPIKE` / `MEM_EXHAUSTION` → `DoS` (Denial of Service)
		- `AUTH_FLOOD` → `S` (Spoofing)
		- `SLOWDOWN` → `T` (Tampering)
	- Frontend shows:
		- STRIDE code + human label in the Attack Intelligence panel.
		- STRIDE code in Recent Alerts (with a small legend for judges).

- **DREAD Heat Map**
	- Backend computes a DREAD assessment per attack type:
		- Damage, Reproducibility, Exploitability, Affected Users, Discoverability.
		- Overall score (1–10) and level (LOW / MEDIUM / HIGH / CRITICAL).
	- Frontend renders a “DREAD Heat Map” card with:
		- Per-factor 1–10 bar visualization.
		- Overall risk badge.
		- Color-coded legend for quick visual triage.

- **Workload Isolation Status**
	- Card that reflects the current isolation posture for the active workload.
	- Backend flips isolation to **QUARANTINED** when tier is **HIGH**,
		otherwise **MONITORING** / **RECOVERED**.

- **Cloud Workload Telemetry**
	- Metrics shaped to feel like cloud infra:
		- CPU Utilization
		- Memory Utilization
		- Request Throughput
		- Auth Failure Rate
		- Service Latency

- **Attack Intelligence Panel**
	- Shows `attack_type` (prettified, e.g. `AUTH FLOOD`) and `attack_severity`.
	- Displays detection confidence and a natural-language explanation of why the
		model flagged the current pattern.
	- Includes STRIDE classification (code + human label) for the active attack.

- **Threat Timeline & Recent Alerts**
	- Live time-series chart of anomaly score (Live Threat Trend).
	- Threat Timeline: narrative text feed describing recent detections, propagation,
		and response decisions.
	- Recent Alerts: scrollable list with timestamp, workload, attack type,
		STRIDE code, score, and tier.

---

## Prerequisites

- Python 3.9+ (recommended)
- Node.js 18+ and npm
- Docker + Docker Compose (optional, for containerized run)

---

## Backend setup (local)

From the project root:

```bash
cd backend

# Install Python dependencies
pip install -r ../requirements.txt

# 1) Collect baseline telemetry (CPU, RAM, traffic, etc.)
python collector.py

# 2) Train / refresh the anomaly model from baseline.csv
python train_model.py

# 3) Run the API (Flask + Socket.IO)
python app.py
```

By default the backend exposes:

- `GET  /status` – latest telemetry + threat score payload
- `GET  /history` – recent detection history
- `GET  /isolation-log` – isolation/quarantine timeline
- `POST /simulate-attack` – starts attack simulation (uses `attack_sim.py`)
- `POST /stop-attack` – stops attack simulation
- Socket.IO channel `update` – pushes live status objects

The backend also emits structured JSON logs for each detection event
(`timestamp`, `tier`, `anomaly_score`, `attack_type`, `attack_severity`,
`response_action`, `workload_id`, `isolation_status`, `blast_radius`).

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

Open the URL printed by Vite (usually `http://localhost:5173`). The dashboard
connects to the backend via a `BACKEND_URL` constant inside `App.jsx`
(defaults to `http://localhost:5000`).

---

## Simulating attacks

The UI provides buttons:

- **Simulate Attack** → `POST /simulate-attack` on the backend and then
	immediately fetches `/status` for an instant UI refresh.
- **Stop Attack** → `POST /stop-attack` and then fetches `/status`.

Under attack, you should see:

- Threat Score spike toward 100.
- Tier move to **HIGH**.
- Isolation Status switch to **QUARANTINED**.
- Response Engine show an ACTIVE THREAT with a propagation-aware action
	(e.g. containment zone vs. single-workload isolation).
- Attack Intelligence card populated with attack type, severity, STRIDE label,
	and an explanation of why it was flagged.
- DREAD Heat Map lighting up with higher scores for the relevant factors.
- Threat Propagation panel showing impacted services and blast radius.
- Recent Alerts lines that look like:
	`svc-2 • AUTH FLOOD • S • Score: 97`.

You can also run the simulator script directly (optional):

```bash
cd simulator
python attack_sim.py
```

This prints a small sample of generated attack rows for inspection.

---

## Dockerized run (backend + frontend)

From the project root:

```bash
docker compose down
docker compose up --build
```

This will:

- Build the backend image (Python + Flask + Socket.IO) using `requirements.txt`.
- Build the frontend image (React + Vite) and expose it on port 5173.
- Wire the frontend to talk to the backend service inside the Compose network.

Then open `http://localhost:5173` in your browser.

---

## Tech stack

- **Backend:** Python, Flask, Flask-SocketIO, scikit-learn (pinned), pandas, psutil
- **Simulator:** Python, pandas, NumPy (attack generation over baseline.csv)
- **Frontend:** React, Vite, Recharts, socket.io-client
- **Infra:** Docker, Docker Compose (optional)

---

## Notes

This is an MVP intended for demos and hackathons, not production. For a real
deployment you’d want:

- Strong authN/Z on all endpoints and WebSockets.
- Persistent storage for alerts/events and model metrics.
- Hardening around model loading, input validation, and error handling.
- Production-grade observability (centralized logs, metrics, tracing).
- A proper cloud deployment (Kubernetes, container app, or similar) with
	secrets management and CI/CD.
