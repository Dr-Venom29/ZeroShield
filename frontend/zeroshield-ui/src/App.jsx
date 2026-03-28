import { useEffect, useState } from "react";
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

const socket = io("http://127.0.0.1:5000");

export default function App() {
  const [data, setData] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    socket.on("update", (incoming) => {
      setData(incoming);
      setHistory((prev) => {
        const updated = [...prev, incoming];
        return updated.slice(-20);
      });
    });

    return () => {
      socket.off("update");
    };
  }, []);

  const triggerAttack = async () => {
    await fetch("http://127.0.0.1:5000/simulate-attack");
  };

  const stopAttack = async () => {
    await fetch("http://127.0.0.1:5000/stop-attack");
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

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>ZeroShield</h1>
          <p>AI-Powered Zero-Day Threat Detection & Response</p>
        </div>
        <div className="controls">
          <button className="attack-btn" onClick={triggerAttack}>
            🚨 Simulate Attack
          </button>
          <button className="stop-btn" onClick={stopAttack}>
            ✅ Stop Attack
          </button>
        </div>
      </header>

      {!data ? (
        <div className="loading">Connecting to live threat feed...</div>
      ) : (
        <>
          <section className="top-grid">
            <div className="score-card">
              <h2>Threat Score</h2>
              <div
                className="score"
                style={{ color: getTierColor(data.tier) }}
              >
                {data.anomaly_score}
              </div>
              <span
                className="tier-badge"
                style={{ backgroundColor: getTierColor(data.tier) }}
              >
                {data.tier}
              </span>
            </div>

            <div className="metrics-grid">
              <MetricCard label="CPU" value={`${data.cpu}%`} />
              <MetricCard label="RAM" value={`${data.ram}%`} />
              <MetricCard label="Req/Sec" value={data.requests_per_sec} />
              <MetricCard label="Failed Logins" value={data.failed_logins} />
              <MetricCard label="Response Time" value={`${data.response_time} ms`} />
            </div>
          </section>

          <section className="chart-alerts-grid">
            <div className="chart-card">
              <h2>Live Threat Trend</h2>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={history}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" />
                  <XAxis dataKey="timestamp" stroke="#999" />
                  <YAxis stroke="#999" />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="anomaly_score"
                    stroke="#00e5ff"
                    strokeWidth={3}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="alerts-card">
              <h2>Recent Alerts</h2>
              <div className="alerts-list">
                {[...history].reverse().map((item, idx) => (
                  <div className="alert-item" key={idx}>
                    <div>
                      <strong>{item.timestamp}</strong>
                      <p>Threat Score: {item.anomaly_score}</p>
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
          </section>
        </>
      )}
    </div>
  );
}

function MetricCard({ label, value }) {
  return (
    <div className="metric-card">
      <h3>{label}</h3>
      <p>{value}</p>
    </div>
  );
}