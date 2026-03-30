import { useEffect, useState, useCallback } from "react";
import { io } from "socket.io-client";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import "./index.css";
import cpuIcon from "./assets/cpu.svg";
import memoryIcon from "./assets/memory.svg";
import requestIcon from "./assets/request.svg";
import authIcon from "./assets/auth.svg";
import serviceIcon from "./assets/service.svg";

const BACKEND_URL = "http://localhost:5000";

export default function App() {
  const [data, setData] = useState(null);
  const [history, setHistory] = useState([]);
  const [connected, setConnected] = useState(false);

  const fetchLatestStatus = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/status`);
      const latest = await res.json();
      setData(latest);
      setHistory((prev) => [...prev, latest].slice(-20));
    } catch (err) {
      console.error("Failed to fetch latest status:", err);
    }
  }, []);

  useEffect(() => {
    let socket;

    socket = io(BACKEND_URL, {
      transports: ["websocket", "polling"],
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
    });

    socket.on("connect", () => {
      console.log("Connected:", socket.id);
      setConnected(true);
      fetchLatestStatus();
    });

    socket.on("disconnect", () => {
      console.log("Disconnected");
      setConnected(false);
    });

    socket.on("update", (incoming) => {
      console.log("📡 Incoming:", incoming);
      setData(incoming);
      setHistory((prev) => [...prev, incoming].slice(-20));
    });

    return () => {
      if (socket) socket.disconnect();
    };
  }, [fetchLatestStatus]);

  const triggerAttack = async () => {
    try {
      await fetch(`${BACKEND_URL}/simulate-attack`, {
        method: "POST",
      });
      await fetchLatestStatus();
    } catch (err) {
      console.error("Failed to trigger attack:", err);
    }
  };

  const stopAttack = async () => {
    try {
      await fetch(`${BACKEND_URL}/stop-attack`, {
        method: "POST",
      });
      await fetchLatestStatus();
    } catch (err) {
      console.error("Failed to stop attack:", err);
    }
  };

  const getTierColor = (tier) => {
    switch (tier) {
      case "HIGH":
        return "#ff3b3b";
      case "MEDIUM":
        return "#ff9800";
      case "LOW":
        return "#ffd54f";
      default:
        return "#00e676";
    }
  };

  const getIsolationColor = (status) => {
    switch (status) {
      case "QUARANTINED":
        return "#ff3b3b";
      case "RECOVERED":
        return "#00e5ff";
      case "MONITORING":
      default:
        return "#00e676";
    }
  };

  const getResponseStateColor = (d) => {
    if (!d) return "#00e676";
    const tier = d.response_engine?.confidence || d.tier || "NORMAL";
    const isolated = d.isolation_status === "QUARANTINED";

    if (isolated || tier === "HIGH") return "#ff3b3b";
    if (tier === "MEDIUM") return "#ff9800";
    return "#00e676";
  };

  const getSeverityColor = (severity) => {
    switch ((severity || "").toLowerCase()) {
      case "severe":
        return "#ff3b3b";
      case "moderate":
        return "#ff9800";
      case "mild":
        return "#00e676";
      default:
        return "#9ca3af";
    }
  };

  const getThreatContext = (d) => {
    if (!d) return null;
    const cpu = d.cpu || 0;
    const ram = d.ram || 0;
    const rps = d.requests_per_sec || 0;
    const fails = d.failed_logins || 0;
    const rt = d.response_time || 0;
    const atk = d.attack_type;

    if (atk === "AUTH_FLOOD" || fails >= 5 || rps >= 40) {
      return "High failed logins and request volume suggest an auth flood / brute-force pattern.";
    }
    if (atk === "CPU_SPIKE" || (cpu >= 80 && rt >= 180)) {
      return "Elevated CPU usage and increased latency are consistent with a CPU spike pattern.";
    }
    if (atk === "MEM_EXHAUSTION" || ram >= 85) {
      return "High memory utilization with slower responses indicates a possible memory exhaustion pattern.";
    }
    if (atk === "SLOWDOWN" || rt >= 500) {
      return "Significantly increased response times with moderate resource usage indicate a service slowdown.";
    }
    if (d.tier === "HIGH" || d.tier === "MEDIUM") {
      return "Anomalous combination of workload metrics pushed the risk score above the normal operating band.";
    }
    return null;
  };

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>ZeroShield</h1>
          <p>AI-Powered Zero-Day Threat Detection &amp; Response</p>
          <span
            className="header-status"
            style={{
              color: connected ? "#00e676" : "#ff3b3b",
            }}
          >
            {connected ? "LIVE CONNECTED" : "DISCONNECTED"}
          </span>
        </div>

        <div className="controls">
          <button className="attack-btn" onClick={triggerAttack}>
            Simulate Attack
          </button>
          <button className="stop-btn" onClick={stopAttack}>
            Stop Attack
          </button>
        </div>
      </header>

      <div className="command-bar-wrapper">
        <div className="command-bar">
          <div className="command-item">
            <span className="label">Environment</span>
            <span className="value">CLOUD-SIMULATED</span>
          </div>
          <div className="command-item">
            <span className="label">Cluster Status</span>
            <span className="value">
              {data?.tier === "HIGH" ? "DEGRADED" : "HEALTHY"}
            </span>
          </div>
          <div className="command-item">
            <span className="label">Active Workload</span>
            <span className="value">{data?.workload_id || "svc-1"}</span>
          </div>
          <div className="command-item">
            <span className="label">Detection Engine</span>
            <span className="value">ONLINE</span>
          </div>
        </div>
      </div>

      {!data ? (
        <div className="loading">Connecting to live threat feed...</div>
      ) : (
        <>
          <section className="top-grid">
            <div className="score-card">
              <h2>Threat Score</h2>
              <p className="subtle-label">Live Risk Index</p>
              <div
                className="score"
                style={{ color: getTierColor(data.tier) }}
              >
                {Math.round(data.anomaly_score)}
              </div>
              <span
                className="tier-badge"
                style={{ backgroundColor: getTierColor(data.tier) }}
              >
                {data.tier}
              </span>
            </div>

            <div className="right-top-grid">
              <div className="isolation-card">
                <h2>Workload Isolation Status</h2>
                <p className="subtle-label">
                  Target Workload: {data.workload_id}
                </p>

                <div
                  className="isolation-status"
                  style={{
                    color: getIsolationColor(data.isolation_status),
                    borderColor: getIsolationColor(data.isolation_status),
                  }}
                >
                  {data.isolation_status}
                </div>

                <p className="isolation-legend">
                  MONITORING <span className="dot">•</span> QUARANTINED{" "}
                  <span className="dot">•</span> RECOVERED
                </p>
              </div>

              <div className="metrics-section">
                <h2>Cloud Workload Telemetry</h2>
                <div className="metrics-grid">
                  <MetricCard
                    label="CPU Utilization"
                    value={`${Math.round(data.cpu)}%`}
                  />
                  <MetricCard
                    label="Memory Utilization"
                    value={`${Math.round(data.ram)}%`}
                  />
                  <MetricCard
                    label="Request Throughput"
                    value={Math.round(data.requests_per_sec)}
                  />
                  <MetricCard
                    label="Auth Failure Rate"
                    value={Math.round(data.failed_logins)}
                  />
                  <MetricCard
                    label="Service Latency"
                    value={`${Math.round(data.response_time)} ms`}
                  />
                </div>
              </div>
            </div>
          </section>

          <section className="chart-alerts-grid">
            <div className="chart-card">
              <h2>Live Threat Trend</h2>
              <p className="subtle-label">Anomaly score over time</p>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={history}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
                  <XAxis dataKey="timestamp" stroke="#999" />
                  <YAxis stroke="#999" domain={[0, 100]} />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="anomaly_score"
                    stroke={getTierColor(
                      history[history.length - 1]?.tier || data?.tier || "LOW"
                    )}
                    strokeWidth={3}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="right-bottom-grid">
              <div className="attack-intel-card">
                <h2>Attack Intelligence</h2>
                {data?.attack_type ? (
                  <>
                    <p className="subtle-label">Live attack classification</p>
                    <ul className="attack-intel-list">
                      <li>
                        <span className="label">Attack Type</span>
                        <span className="value">
                          {data.attack_type.replaceAll("_", " ")}
                        </span>
                      </li>
                      <li>
                        <span className="label">Severity</span>
                        <span className="value">
                          <span
                            className="severity-pill"
                            style={{ color: getSeverityColor(data.attack_severity) }}
                          >
                            {data.attack_severity}
                          </span>
                        </span>
                      </li>
                      <li>
                        <span className="label">Detection Confidence</span>
                        <span className="value">
                          <span
                            style={{ color: getTierColor(data.tier) }}
                          >
                            {data.response_engine?.confidence || data.tier}
                          </span>
                        </span>
                      </li>
                    </ul>
                    {(() => {
                      const ctx = getThreatContext(data);
                      if (!ctx) return null;
                      return (
                        <div className="threat-context">
                          <p className="context-label">Why the model flagged this</p>
                          <p className="context-text">{ctx}</p>
                        </div>
                      );
                    })()}
                  </>
                ) : (
                  <p className="subtle-label">No active attack pattern detected</p>
                )}
              </div>

              <div className="response-card">
                <h2>Response Engine</h2>
                {data && (
                  <p className="subtle-label">
                    Automated response posture for active workload
                  </p>
                )}
                {(() => {
                  const threatDetected =
                    data?.response_engine?.threat_detected === "YES";
                  const confidence =
                    data?.response_engine?.confidence || data?.tier || "NORMAL";
                  const scope = data?.response_engine?.scope || data?.workload_id;
                  const actionText =
                    data?.response_engine?.action ||
                    (threatDetected ? "Quarantine triggered" : "Monitoring only");
                  const responseColor = getResponseStateColor(data);

                  return (
                    <ul className="response-list">
                      <li>
                        <span className="label">Threat Detected</span>
                        <span className="value">
                          <span style={{ color: responseColor }}>
                            {threatDetected ? "ACTIVE THREAT" : "NO ACTIVE THREAT"}
                          </span>
                        </span>
                      </li>
                      <li>
                        <span className="label">Confidence</span>
                        <span className="value">
                          <span style={{ color: responseColor }}>{confidence}</span>
                        </span>
                      </li>
                      <li>
                        <span className="label">Action</span>
                        <span className="value">
                          <span style={{ color: responseColor }}>{actionText}</span>
                        </span>
                      </li>
                      <li>
                        <span className="label">Scope</span>
                        <span className="value">
                          <span style={{ color: responseColor }}>{scope}</span>
                        </span>
                      </li>
                    </ul>
                  );
                })()}
              </div>

              <div className="alerts-card">
                <h2>Recent Alerts</h2>
                <div className="alerts-list">
                  {[...history].reverse().map((item, idx) => (
                    <div className="alert-item" key={idx}>
                      <div>
                        <strong>{item.timestamp}</strong>
                        <p>
                          {item.workload_id} • {" "}
                          {(item.attack_type || "Normal Activity").replaceAll("_", " ")}
                          {" "}• {" "}
                          {item.attack_severity ? item.attack_severity.toUpperCase() : "N/A"}
                          {" "}• Score: {Math.round(item.anomaly_score)}
                        </p>
                      </div>
                      <span
                        className="alert-tier"
                        style={{ color: getTierColor(item.tier) }}
                      >
                        {item.tier}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function MetricCard({ label, value }) {
  const getMeta = (metricLabel) => {
    switch (metricLabel) {
      case "CPU Utilization":
        return { icon: cpuIcon, tone: "cpu" };
      case "Memory Utilization":
        return { icon: memoryIcon, tone: "mem" };
      case "Request Throughput":
        return { icon: requestIcon, tone: "net" };
      case "Auth Failure Rate":
        return { icon: authIcon, tone: "auth" };
      case "Service Latency":
        return { icon: serviceIcon, tone: "lat" };
      default:
        return { icon: cpuIcon, tone: "default" };
    }
  };

  const meta = getMeta(label);

  return (
    <div className={`metric-card metric-${meta.tone}`}>
      <div className="metric-header-row">
        <div className="metric-icon">
          <img src={meta.icon} alt={label} />
        </div>
        <h3>{label}</h3>
      </div>
      <p>{value}</p>
    </div>
  );
}
