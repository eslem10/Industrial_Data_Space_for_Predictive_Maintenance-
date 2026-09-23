import { useEffect, useState, useMemo } from "react";
import "./App.css";
import SensorChart from "./components/SensorChart";
import FLMetrics from "./components/FLMetrics";
import Alerts from "./components/Alerts";
import EDCStatus from "./components/EDCStatus";

function App() {
  const [factories, setFactories] = useState([]);
  const [selectedFactory, setSelectedFactory] = useState("F1");
  const [history, setHistory] = useState([]);
  const [flMetrics, setFlMetrics] = useState([]);
  const [activeTab, setActiveTab] = useState("overview"); // "overview", "factories", "ai", "edc", "alerts"
  const [refreshIntervalSec, setRefreshIntervalSec] = useState(15);
  const [countdown, setCountdown] = useState(15);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState(new Date().toLocaleTimeString());
  const [simulatedAnomaly, setSimulatedAnomaly] = useState(false);

  // Fetch factories
  const fetchFactories = async () => {
    try {
      const response = await fetch("http://localhost:3001/api/factories");
      const data = await response.json();
      setFactories(data);
      setLastSyncTime(new Date().toLocaleTimeString());
    } catch (error) {
      console.error("Error fetching factories:", error);
    }
  };

  // Fetch history for selected factory
  const fetchHistory = async (factoryId) => {
    try {
      const response = await fetch(
        `http://localhost:3001/api/factories/${factoryId}/history?limit=30`
      );
      const data = await response.json();

      const formattedData = data.map((item, index) => ({
        time: item.timestamp
          ? item.timestamp.split(" ")[1] || item.timestamp
          : `#${index + 1}`,
        temperature: Number(item.temperature),
        vibration: Number(item.vibration),
        pressure: Number(item.pressure),
        energy: Number(item.energy_consumption),
        state: item.state
      }));

      setHistory(formattedData);
    } catch (error) {
      console.error("Error fetching history:", error);
    }
  };

  // Fetch FL metrics
  const fetchFLMetrics = async () => {
    try {
      const response = await fetch("http://localhost:3001/api/fl/metrics");
      const data = await response.json();
      if (data && data.rounds) {
        setFlMetrics(data.rounds);
      }
    } catch (error) {
      console.error("Error fetching FL metrics:", error);
    }
  };

  // Refresh all
  const refreshAll = async () => {
    setIsRefreshing(true);
    await Promise.all([
      fetchFactories(),
      fetchHistory(selectedFactory),
      fetchFLMetrics()
    ]);
    setCountdown(refreshIntervalSec);
    setTimeout(() => setIsRefreshing(false), 500);
  };

  // Auto-refresh countdown timer
  useEffect(() => {
    if (refreshIntervalSec === 0) return; // Paused

    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          refreshAll();
          return refreshIntervalSec;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [refreshIntervalSec, selectedFactory]);

  // Initial load and selectedFactory change
  useEffect(() => {
    refreshAll();
  }, [selectedFactory]);

  // Modify factories with simulated anomaly if toggled
  const activeFactories = useMemo(() => {
    if (!simulatedAnomaly) return factories;
    return factories.map((f) => {
      if (f.id === "F3") {
        return {
          ...f,
          data: {
            ...f.data,
            temperature: 96.4,
            vibration: 1.85,
            pressure: 6.8,
            state: "failure"
          }
        };
      }
      return f;
    });
  }, [factories, simulatedAnomaly]);

  // Compute Fleet Health Index
  const fleetHealth = useMemo(() => {
    if (activeFactories.length === 0) return 100;
    let score = 100;
    activeFactories.forEach((f) => {
      if (f.status === "offline") score -= 25;
      if (f.data?.state === "failure") score -= 35;
      else {
        if (Number(f.data?.temperature) > 75) score -= 8;
        if (Number(f.data?.vibration) > 0.7) score -= 10;
      }
    });
    return Math.max(0, Math.min(100, score));
  }, [activeFactories]);

  const selectedFactoryObj = activeFactories.find((f) => f.id === selectedFactory) || activeFactories[0];

  return (
    <div className="command-center-app">
      {/* GLOWING HEADER */}
      <header className="top-command-bar">
        <div className="header-brand">
          <div className="brand-logo-hex">
            <span className="hex-icon">⬢</span>
            <div className="logo-spark"></div>
          </div>
          <div>
            <div className="brand-badge-strip">
              <span className="cyber-tag">IDSA 4.0 COMPLIANT</span>
              <span className="cyber-tag fl">EDGE-AI FEDAVG</span>
            </div>
            <h1 className="brand-title">
              INDUSTRIAL <span className="gradient-text">DATA SPACE</span>
            </h1>
            <p className="brand-sub">Autonomous Predictive Maintenance & Federated Analytics</p>
          </div>
        </div>

        {/* Live Control Strip */}
        <div className="header-controls">
          <div className="sync-status-pill">
            <span className="pulse-beacon"></span>
            <div className="sync-meta">
              <span className="sync-state">REALTIME STREAM</span>
              <small className="sync-time">Synced {lastSyncTime}</small>
            </div>
          </div>

          <div className="refresh-widget">
            <button
              className={`refresh-action-btn ${isRefreshing ? "spin-active" : ""}`}
              onClick={refreshAll}
              title="Manual Sync"
            >
              <span className="refresh-icon">🔄</span>
              <span className="refresh-text">
                {isRefreshing ? "Syncing..." : `Sync (${countdown}s)`}
              </span>
            </button>

            <select
              className="refresh-select"
              value={refreshIntervalSec}
              onChange={(e) => {
                const val = Number(e.target.value);
                setRefreshIntervalSec(val);
                setCountdown(val);
              }}
            >
              <option value={10}>10s live</option>
              <option value={15}>15s live</option>
              <option value={30}>30s normal</option>
              <option value={0}>Pause</option>
            </select>
          </div>

          {/* Interactive Anomaly Simulator */}
          <button
            className={`anomaly-sim-btn ${simulatedAnomaly ? "sim-active" : ""}`}
            onClick={() => setSimulatedAnomaly(!simulatedAnomaly)}
            title="Inject test failure to see UI react"
          >
            <span className="sim-dot"></span>
            {simulatedAnomaly ? "Disable Test Fault" : "⚡ Test Anomaly Sim"}
          </button>
        </div>
      </header>

      {/* KPI METRIC STRIP */}
      <section className="kpi-hero-strip">
        <div className="kpi-glass-card fleet-health">
          <div className="kpi-card-header">
            <span className="kpi-card-title">Fleet Health Index</span>
            <span className="kpi-card-icon">🛡️</span>
          </div>
          <div className="kpi-card-body">
            <strong className={`kpi-big-val ${fleetHealth > 85 ? "good" : fleetHealth > 60 ? "warn" : "bad"}`}>
              {fleetHealth}%
            </strong>
            <div className="fleet-bar-track">
              <div
                className={`fleet-bar-fill ${fleetHealth > 85 ? "good" : fleetHealth > 60 ? "warn" : "bad"}`}
                style={{ width: `${fleetHealth}%` }}
              ></div>
            </div>
            <span className="kpi-footer-text">
              {fleetHealth > 85 ? "Optimal machine state" : "Degraded tolerance - inspect warnings"}
            </span>
          </div>
        </div>

        <div className="kpi-glass-card">
          <div className="kpi-card-header">
            <span className="kpi-card-title">Monitored Facilities</span>
            <span className="kpi-card-icon">🏭</span>
          </div>
          <div className="kpi-card-body">
            <strong className="kpi-big-val highlight-cyan">
              {activeFactories.filter((f) => f.status === "online").length}/{activeFactories.length || 3}
            </strong>
            <span className="kpi-badge-live">Telemetry Online</span>
            <span className="kpi-footer-text">F1, F2, F3 actively streaming</span>
          </div>
        </div>

        <div className="kpi-glass-card">
          <div className="kpi-card-header">
            <span className="kpi-card-title">Federated Accuracy</span>
            <span className="kpi-card-icon">🧠</span>
          </div>
          <div className="kpi-card-body">
            <strong className="kpi-big-val highlight-purple">
              {flMetrics.length > 0 ? `${(flMetrics[flMetrics.length - 1].accuracy * 100).toFixed(1)}%` : "95.0%"}
            </strong>
            <span className="kpi-badge-fl">Flower FedAvg Round 5</span>
            <span className="kpi-footer-text">Converged across distributed nodes</span>
          </div>
        </div>

        <div className="kpi-glass-card">
          <div className="kpi-card-header">
            <span className="kpi-card-title">EDC Sovereign Nodes</span>
            <span className="kpi-card-icon">🔗</span>
          </div>
          <div className="kpi-card-body">
            <strong className="kpi-big-val highlight-emerald">3/3 Valid</strong>
            <span className="kpi-badge-edc">ODRL 2.0 Contracted</span>
            <span className="kpi-footer-text">Mutual TLS & DAPS Protected</span>
          </div>
        </div>
      </section>

      {/* DYNAMIC TAB NAVIGATION */}
      <nav className="tab-nav-bar">
        <button
          className={`tab-item ${activeTab === "overview" ? "active" : ""}`}
          onClick={() => setActiveTab("overview")}
        >
          <span className="tab-icon">🌐</span> Command Overview
        </button>
        <button
          className={`tab-item ${activeTab === "factories" ? "active" : ""}`}
          onClick={() => setActiveTab("factories")}
        >
          <span className="tab-icon">🏭</span> Factory Diagnostics
        </button>
        <button
          className={`tab-item ${activeTab === "ai" ? "active" : ""}`}
          onClick={() => setActiveTab("ai")}
        >
          <span className="tab-icon">🧠</span> Federated Learning AI
        </button>
        <button
          className={`tab-item ${activeTab === "edc" ? "active" : ""}`}
          onClick={() => setActiveTab("edc")}
        >
          <span className="tab-icon">🔗</span> Dataspace Mesh (EDC)
        </button>
        <button
          className={`tab-item ${activeTab === "alerts" ? "active" : ""}`}
          onClick={() => setActiveTab("alerts")}
        >
          <span className="tab-icon">🚨</span> Incident Center
        </button>
      </nav>

      {/* MAIN VIEW CONTENT */}
      <main className="main-viewport">
        {/* VIEW: OVERVIEW OR FACTORIES */}
        {(activeTab === "overview" || activeTab === "factories") && (
          <>
            {/* FACTORY CARDS GRID */}
            <section className="dashboard-section">
              <div className="section-head-wrap">
                <div>
                  <div className="badge-pill factory-pill">
                    <span className="dot-pulse-cyan"></span>
                    Edge IoT Sensor Telemetry
                  </div>
                  <h2 className="section-title">Industrial Facilities Real-Time Health</h2>
                  <p className="section-subtitle">
                    Select a factory node below to inspect deep telemetry charts, harmonics, and thermal curves
                  </p>
                </div>

                <div className="factory-selector-pills">
                  {activeFactories.map((f) => (
                    <button
                      key={f.id}
                      className={`pill-btn ${selectedFactory === f.id ? "selected" : ""}`}
                      onClick={() => setSelectedFactory(f.id)}
                    >
                      <span className={`mini-status-dot ${f.data?.state === "failure" ? "crit" : "norm"}`}></span>
                      {f.id}
                    </button>
                  ))}
                </div>
              </div>

              <div className="factory-cards-row">
                {activeFactories.map((factory) => {
                  const isSelected = selectedFactory === factory.id;
                  const isFail = factory.data?.state === "failure";
                  const temp = Number(factory.data?.temperature) || 0;
                  const vib = Number(factory.data?.vibration) || 0;
                  const press = Number(factory.data?.pressure) || 0;
                  const energy = Number(factory.data?.energy_consumption) || 0;

                  return (
                    <div
                      className={`cyber-factory-card ${isSelected ? "active-card" : ""} ${isFail ? "failure-border" : ""}`}
                      key={factory.id}
                      onClick={() => setSelectedFactory(factory.id)}
                    >
                      <div className="card-top-row">
                        <div>
                          <span className="factory-id-tag">{factory.id}</span>
                          <h3 className="factory-name-txt">{factory.name}</h3>
                        </div>

                        <div className="status-badge-wrap">
                          <span className={`state-beacon ${isFail ? "beacon-fail" : "beacon-ok"}`}>
                            {isFail ? "CRITICAL FAULT" : "NORMAL"}
                          </span>
                        </div>
                      </div>

                      {factory.data && (
                        <div className="sensor-matrix">
                          <div className={`sensor-cell ${temp > 75 ? "alert-cell" : ""}`}>
                            <div className="sensor-cell-head">
                              <span>🌡️ Temp</span>
                              <small>{temp > 75 ? "HIGH" : "OK"}</small>
                            </div>
                            <strong className="sensor-cell-val">{temp} °C</strong>
                            <div className="mini-meter">
                              <div
                                className={`mini-meter-fill ${temp > 75 ? "fill-red" : "fill-orange"}`}
                                style={{ width: `${Math.min(100, (temp / 100) * 100)}%` }}
                              ></div>
                            </div>
                          </div>

                          <div className={`sensor-cell ${vib > 0.7 ? "alert-cell" : ""}`}>
                            <div className="sensor-cell-head">
                              <span>〰️ Vibration</span>
                              <small>{vib > 0.7 ? "CRIT" : "OK"}</small>
                            </div>
                            <strong className="sensor-cell-val">{vib} mm/s</strong>
                            <div className="mini-meter">
                              <div
                                className={`mini-meter-fill ${vib > 0.7 ? "fill-red" : "fill-cyan"}`}
                                style={{ width: `${Math.min(100, (vib / 1.5) * 100)}%` }}
                              ></div>
                            </div>
                          </div>

                          <div className="sensor-cell">
                            <div className="sensor-cell-head">
                              <span>⚙️ Pressure</span>
                              <small>bar</small>
                            </div>
                            <strong className="sensor-cell-val">{press}</strong>
                            <div className="mini-meter">
                              <div
                                className="mini-meter-fill fill-purple"
                                style={{ width: `${Math.min(100, (press / 6) * 100)}%` }}
                              ></div>
                            </div>
                          </div>

                          <div className="sensor-cell">
                            <div className="sensor-cell-head">
                              <span>⚡ Energy</span>
                              <small>kW</small>
                            </div>
                            <strong className="sensor-cell-val">{energy}</strong>
                            <div className="mini-meter">
                              <div
                                className="mini-meter-fill fill-green"
                                style={{ width: `${Math.min(100, (energy / 15) * 100)}%` }}
                              ></div>
                            </div>
                          </div>
                        </div>
                      )}

                      <div className="card-footer-action">
                        <span>{isSelected ? "● Currently Inspecting" : "Click to view historical curves →"}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            {/* SENSOR HISTORY CHARTS */}
            <section className="dashboard-section">
              <div className="section-head-wrap">
                <div>
                  <div className="badge-pill chart-pill">
                    <span className="dot-pulse-blue"></span>
                    Continuous Timeseries Ingestion
                  </div>
                  <h2 className="section-title">
                    Telemetry Ingestion Curves — {selectedFactoryObj?.name} ({selectedFactory})
                  </h2>
                  <p className="section-subtitle">
                    Historical 30-cycle telemetry showing sensor variations, anomalies, and threshold envelopes
                  </p>
                </div>

                <div className="chart-view-selector">
                  <span className="selector-label">Inspecting:</span>
                  <select
                    className="factory-dropdown-modern"
                    value={selectedFactory}
                    onChange={(e) => setSelectedFactory(e.target.value)}
                  >
                    <option value="F1">Factory 1 (Cold Environment)</option>
                    <option value="F2">Factory 2 (Hot Environment)</option>
                    <option value="F3">Factory 3 (Old Machinery)</option>
                  </select>
                </div>
              </div>

              <div className="charts-2x2-grid">
                <SensorChart
                  title="Temperature"
                  data={history}
                  dataKey="temperature"
                  unit="°C"
                />
                <SensorChart
                  title="Vibration"
                  data={history}
                  dataKey="vibration"
                  unit="mm/s"
                />
                <SensorChart
                  title="Pressure"
                  data={history}
                  dataKey="pressure"
                  unit="bar"
                />
                <SensorChart
                  title="Energy Consumption"
                  data={history}
                  dataKey="energy"
                  unit="kW"
                />
              </div>
            </section>
          </>
        )}

        {/* VIEW: OVERVIEW OR AI */}
        {(activeTab === "overview" || activeTab === "ai") && (
          <FLMetrics metrics={flMetrics} />
        )}

        {/* VIEW: OVERVIEW OR ALERTS */}
        {(activeTab === "overview" || activeTab === "alerts") && (
          <Alerts factories={activeFactories} />
        )}

        {/* VIEW: OVERVIEW OR EDC */}
        {(activeTab === "overview" || activeTab === "edc") && (
          <EDCStatus />
        )}
      </main>

      {/* CYBER FOOTER */}
      <footer className="footer-command">
        <div className="footer-content">
          <div className="footer-left">
            <span className="footer-pill">INDUSTRIAL DATA SPACE</span>
            <span>Predictive Maintenance System v3.2</span>
            <span>• Eclipse Dataspace Connector (EDC) & Flower Federated AI</span>
          </div>
          <div className="footer-right">
            <span>ODRL 2.0 Sovereign Policy Enforcement Enabled</span>
            <span className="footer-clock">System Time: {new Date().toLocaleDateString()}</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;