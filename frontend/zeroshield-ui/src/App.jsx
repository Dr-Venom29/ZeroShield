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

  const formatStrategy = (strategy) => {
    if (strategy === "PROPAGATION_AWARE") {
      return "Propagation-Aware Defense";
    }
    if (!strategy || strategy === "STANDARD") {
      return "Standard Defense";
    }
    return strategy;
  };

  const getClusterStatus = (tier) => {
    switch (tier) {
      case "HIGH":
        return "CRITICAL";
      case "MEDIUM":
        return "DEGRADED";
      case "LOW":
        return "ELEVATED";
      case "NORMAL":
      default:
        return "HEALTHY";
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

  const dreadFactors = [
    { key: "damage", label: "Damage" },
    { key: "reproducibility", label: "Reproducibility" },
    { key: "exploitability", label: "Exploitability" },
    { key: "affected_users", label: "Affected Users" },
    { key: "discoverability", label: "Discoverability" },
  ];

  const getDreadCellClass = (score) => {
    if (score >= 8) return "dread-high";
    if (score >= 6) return "dread-medium-high";
    if (score >= 4) return "dread-medium";
    if (score >= 2) return "dread-low";
    return "dread-very-low";
  };

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>ZeroShield</h1>
          <p>Graph-Aware Zero-Day Defense for Cloud Infrastructure</p>
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
            Launch Attack Simulation
          </button>
          <button className="stop-btn" onClick={stopAttack}>
            Restore Normal State
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
              {getClusterStatus(data?.tier)}
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
            <div className="chart-timeline-stack">
              <div className="chart-card">
                <h2>Live Threat Trend</h2>
                <p className="subtle-label">Anomaly score over time</p>
                <ResponsiveContainer width="100%" height={220}>
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

              <section className="dread-card">
                <div className="dread-header">
                  <div>
                    <h2>DREAD Heat Map</h2>
                    <p className="subtle-label">
                      Threat prioritization across DREAD risk factors
                    </p>
                  </div>

                  <div className="dread-score-badge">
                    <span className="score-label">Overall Risk</span>
                    <span className="score-value">
                      {data?.dread_assessment?.level || "LOW"} ({
                        data?.dread_assessment?.score || 1
                      }
                      /10)
                    </span>
                  </div>
                </div>

                <div className="dread-grid">
                  {dreadFactors.map((factor) => {
                    const score = data?.dread_assessment?.[factor.key] || 1;

                    return (
                      <div className="dread-row" key={factor.key}>
                        <span className="dread-label">{factor.label}</span>

                        <div className="dread-cells">
                          {Array.from({ length: 10 }).map((_, idx) => {
                            const active = idx < score;
                            return (
                              <div
                                key={idx}
                                className={`dread-cell ${
                                  active
                                    ? getDreadCellClass(score)
                                    : "dread-inactive"
                                }`}
                              />
                            );
                          })}
                        </div>

                        <span className="dread-score">{score}</span>
                      </div>
                    );
                  })}
                </div>

                <div className="dread-legend">
                  <span>
                    <span className="legend-dot dread-high"></span> High (8–10)
                  </span>
                  <span>
                    <span className="legend-dot dread-medium-high"></span> Medium-High (6–7)
                  </span>
                  <span>
                    <span className="legend-dot dread-medium"></span> Medium (4–5)
                  </span>
                  <span>
                    <span className="legend-dot dread-low"></span> Low (2–3)
                  </span>
                  <span>
                    <span className="legend-dot dread-very-low"></span> Very Low (1)
                  </span>
                </div>
              </section>

              <div className="timeline-card">
                <h2>Threat Timeline</h2>
                <p className="subtle-label">Narrative feed from recent detections</p>
                <div className="timeline-list">
                  {[...history]
                    .slice(-20)
                    .reverse()
                    .map((item, idx) => {
                      const attackLabel = (item.attack_type || "Normal Activity").replaceAll(
                        "_",
                        " "
                      );
                      const severityLabel = item.attack_severity
                        ? item.attack_severity.toUpperCase()
                        : "NORMAL";
                      const tierLabel = item.tier;
                      const scoreLabel = Math.round(item.anomaly_score);
                      const workload = item.workload_id;
                      const isolation = item.isolation_status;
                      const action = item.response_engine?.action;

                      let message;
                      if (item.attack_type) {
                        message = `${workload} flagged ${attackLabel} (${severityLabel}) at score ${scoreLabel}.`;
                      } else if (tierLabel === "HIGH" || tierLabel === "MEDIUM") {
                        message = `${workload} entered ${tierLabel} risk band (score ${scoreLabel}).`;
                      } else {
                        message = `${workload} operating within normal band (score ${scoreLabel}).`;
                      }

                      if (item.threat_graph?.impacted_services?.length) {
                        const impactedNames = item.threat_graph.impacted_services
                          .map((svc) => svc.service)
                          .join(", ");
                        const blast = item.threat_graph.blast_radius;
                        message += ` Propagation risk towards ${impactedNames} (${blast} blast radius).`;
                      }

                      if (action || isolation) {
                        message += ` Response: ${action || isolation}.`;
                      }

                      return (
                        <div className="timeline-item" key={idx}>
                          <span className="timeline-time">{item.timestamp}</span>
                          <p className="timeline-text">{message}</p>
                        </div>
                      );
                    })}
                </div>
              </div>
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
                      <li>
                        <span className="label">Threat Model (STRIDE)</span>
                        <span className="value">
                          {data.threat_classification?.stride || "N/A"}
                          {data.threat_classification?.label && (
                            <span className="context-text" style={{ marginLeft: "0.4rem" }}>
                              {`(${data.threat_classification.label})`}
                            </span>
                          )}
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
                  <>
                    <p className="subtle-label">Calm-state telemetry intelligence</p>
                    {(() => {
                      const latest = history[history.length - 1] || data || {};
                      const posture =
                        latest.tier === "HIGH" || latest.tier === "MEDIUM"
                          ? "Elevated"
                          : "Stable";
                      const source = latest.workload_id || "N/A";

                      let drift = "Low";
                      const window = history.slice(-5);
                      if (window.length >= 2) {
                        const start = window[0].anomaly_score || 0;
                        const end = window[window.length - 1].anomaly_score || 0;
                        const delta = end - start;
                        if (delta > 10) drift = "Rising";
                        else if (delta < -10) drift = "Falling";
                      }

                      const observedPattern = "None";

                      return (
                        <ul className="attack-intel-list">
                          <li>
                            <span className="label">Current Posture</span>
                            <span className="value">
                              <span style={{ color: getTierColor(latest.tier || "LOW") }}>
                                {posture}
                              </span>
                            </span>
                          </li>
                          <li>
                            <span className="label">Most Recent Anomaly Source</span>
                            <span className="value">{source}</span>
                          </li>
                          <li>
                            <span className="label">Observed Pattern</span>
                            <span className="value">{observedPattern}</span>
                          </li>
                          <li>
                            <span className="label">Threat Drift</span>
                            <span className="value">{drift}</span>
                          </li>
                        </ul>
                      );
                    })()}
                  </>
                )}
              </div>

              <div className="attack-intel-card">
                <h2>Threat Propagation</h2>
                {data?.threat_graph ? (
                  <>
                    <p className="subtle-label">Blast radius across dependent services</p>
                    <ul className="attack-intel-list">
                      <li>
                        <span className="label">Primary Node</span>
                        <span className="value">{data.threat_graph.primary_node}</span>
                      </li>
                      <li>
                        <span className="label">Blast Radius</span>
                        <span className="value">
                          <span
                            className="severity-pill"
                            style={{ color: getTierColor(data.tier) }}
                          >
                            {data.threat_graph.blast_radius}
                          </span>
                        </span>
                      </li>
                    </ul>

                    {(() => {
                      const tg = data.threat_graph;
                      const primaryNode = tg.primary_node;
                      const impacted = tg.impacted_services || [];

                      const nodeStyle = (name) => {
                        if (name === primaryNode) {
                          const c = getTierColor(data.tier || "LOW");
                          return { borderColor: c, color: c };
                        }
                        const svcInfo = impacted.find((svc) => svc.service === name);
                        if (svcInfo) {
                          const c = getTierColor(svcInfo.tier || "LOW");
                          return { borderColor: c, color: c };
                        }
                        return {};
                      };

                      return (
                        <div className="topology-section">
                          <p className="context-label">Cloud topology / threat map</p>
                          <div className="topology-map">
                            <div className="topology-node node-svc1" style={nodeStyle("svc-1")}>
                              svc-1
                            </div>
                            <div className="topology-connector horiz conn-1-2" />
                            <div className="topology-node node-svc2" style={nodeStyle("svc-2")}>
                              svc-2
                            </div>
                            <div className="topology-connector horiz conn-2-4" />
                            <div className="topology-node node-svc4" style={nodeStyle("svc-4")}>
                              svc-4
                            </div>

                            <div className="topology-connector vert conn-1-3" />
                            <div className="topology-node node-svc3" style={nodeStyle("svc-3")}>
                              svc-3
                            </div>
                          </div>
                        </div>
                      );
                    })()}

                    {data.threat_graph.impacted_services &&
                      data.threat_graph.impacted_services.length > 0 && (
                        <div className="threat-context">
                          <p className="context-label">Impacted Services</p>
                          <ul className="propagation-list">
                            {data.threat_graph.impacted_services.map((svc) => {
                              const risk = Math.round(svc.risk_score || 0);
                              const clamped = Math.min(Math.max(risk, 0), 100);
                              const width = `${clamped}%`;
                              return (
                                <li key={svc.service} className="propagation-row">
                                  <span className="label">{svc.service}</span>
                                  <div className="propagation-bar-wrapper">
                                    <div
                                      className="propagation-bar-fill"
                                      style={{
                                        width,
                                        backgroundColor: getTierColor(svc.tier),
                                      }}
                                    />
                                  </div>
                                  <span className="propagation-score">{risk}</span>
                                </li>
                              );
                            })}
                          </ul>
                        </div>
                      )}
                  </>
                ) : (
                  <p className="subtle-label">No lateral impact estimated</p>
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
                    (threatDetected ? "Workload isolation enforced" : "Passive monitoring");
                  const strategy = formatStrategy(data?.response_engine?.strategy);
                  const blastRadius =
                    data?.response_engine?.blast_radius || data?.threat_graph?.blast_radius;
                  const responseColor = getResponseStateColor(data);

                  return (
                    <ul className="response-list">
                      <li>
                        <span className="label">Threat State</span>
                        <span className="value">
                          <span style={{ color: responseColor }}>
                            {threatDetected ? "ACTIVE THREAT" : "NO ACTIVE THREAT"}
                          </span>
                        </span>
                      </li>
                      <li>
                        <span className="label">Detection Confidence</span>
                        <span className="value">
                          <span style={{ color: responseColor }}>{confidence}</span>
                        </span>
                      </li>
                      <li>
                        <span className="label">Automated Action</span>
                        <span className="value">
                          <span style={{ color: responseColor }}>{actionText}</span>
                        </span>
                      </li>
                      <li>
                        <span className="label">Strategy</span>
                        <span className="value">
                          <span style={{ color: responseColor }}>{strategy}</span>
                        </span>
                      </li>
                      <li>
                        <span className="label">Blast Radius</span>
                        <span className="value">
                          <span style={{ color: responseColor }}>{blastRadius}</span>
                        </span>
                      </li>
                      <li>
                        <span className="label">Enforcement Scope</span>
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
                <p className="subtle-label">
                  STRIDE: S = Spoofing 
                  • T = Tampering • DoS = Denial of Service
                </p>
                <div className="alerts-list">
                  {[...history].reverse().map((item, idx) => (
                    <div className="alert-item" key={idx}>
                      <div>
                        <strong>{item.timestamp}</strong>
                        <p>
                          {item.workload_id} •{" "}
                          {(item.attack_type || "Normal Activity").replaceAll("_", " ")} •{" "}
                          {item.threat_classification?.stride || "N/A"} • Score:{" "}
                          {Math.round(item.anomaly_score)}
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
