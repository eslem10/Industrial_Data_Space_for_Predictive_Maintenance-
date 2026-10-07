import { useState } from "react";

function Alerts({ factories = [] }) {
    const [filter, setFilter] = useState("all"); // "all", "critical", "warning"
    const [acknowledged, setAcknowledged] = useState({});

    const alerts = [];

    factories.forEach((factory) => {
        if (factory.status === "offline") {
            alerts.push({
                id: `${factory.id}-offline`,
                factoryId: factory.id,
                factoryName: factory.name,
                type: "warning",
                title: "Telemetry Link Offline",
                message: `${factory.name} (${factory.id}) is unreachable on MQTT broker or EDC gateway. Check network link.`,
                metric: "Connection Status: Dropped",
                timestamp: "Real-Time Telemetry"
            });
            return;
        }

        if (factory.data) {
            if (factory.data.state === "failure") {
                alerts.push({
                    id: `${factory.id}-failure`,
                    factoryId: factory.id,
                    factoryName: factory.name,
                    type: "critical",
                    title: "CRITICAL FAILURE DETECTED",
                    message: `Predictive model flagged imminent machine failure in ${factory.name}. High temperature combined with destructive vibration patterns.`,
                    metric: `Temp: ${factory.data.temperature}°C | Vib: ${factory.data.vibration} | State: FAILURE`,
                    timestamp: "Active Right Now"
                });
            }

            if (Number(factory.data.temperature) > 75 && factory.data.state !== "failure") {
                alerts.push({
                    id: `${factory.id}-temp`,
                    factoryId: factory.id,
                    factoryName: factory.name,
                    type: "warning",
                    title: "Thermal Exceedance Warning",
                    message: `Cooling circuit under stress. Ambient/machine temperature crossed safety ceiling of 75°C.`,
                    metric: `Actual: ${factory.data.temperature}°C (Limit: 75°C)`,
                    timestamp: "Threshold Exceeded"
                });
            }

            if (Number(factory.data.vibration) > 0.7 && factory.data.state !== "failure") {
                alerts.push({
                    id: `${factory.id}-vib`,
                    factoryId: factory.id,
                    factoryName: factory.name,
                    type: "warning",
                    title: "Vibration Harmonics Anomaly",
                    message: `Mechanical wear suspected in rotary motor bearings. Harmonics exceed standard tolerance.`,
                    metric: `Vibration: ${factory.data.vibration} mm/s (Limit: 0.70 mm/s)`,
                    timestamp: "Kinetic Anomaly"
                });
            }

            if (Number(factory.data.pressure) > 5.5 && factory.data.state !== "failure") {
                alerts.push({
                    id: `${factory.id}-press`,
                    factoryId: factory.id,
                    factoryName: factory.name,
                    type: "warning",
                    title: "Hydraulic Pressure Surge",
                    message: `System pressure exceeds recommended operating baseline.`,
                    metric: `Pressure: ${factory.data.pressure} bar`,
                    timestamp: "Pressure Spike"
                });
            }
        }
    });

    const filteredAlerts = alerts.filter((alert) => {
        if (filter === "critical") return alert.type === "critical";
        if (filter === "warning") return alert.type === "warning";
        return true;
    });

    const handleAcknowledge = (id) => {
        setAcknowledged((prev) => ({
            ...prev,
            [id]: !prev[id]
        }));
    };

    const criticalCount = alerts.filter((a) => a.type === "critical").length;
    const warningCount = alerts.filter((a) => a.type === "warning").length;

    return (
        <section className="dashboard-section">
            <div className="section-head-wrap">
                <div>
                    <div className="badge-pill alert-pill">
                        <span className={`dot-pulse-${criticalCount > 0 ? "rose" : "green"}`}></span>
                        Anomaly Detection & Early Warning System
                    </div>
                    <h2 className="section-title">Diagnostics & Incident Center</h2>
                    <p className="section-subtitle">
                        Automated threshold monitoring and predictive fault classification
                    </p>
                </div>

                <div className="alert-filter-group">
                    <button
                        className={`filter-btn ${filter === "all" ? "active" : ""}`}
                        onClick={() => setFilter("all")}
                    >
                        All ({alerts.length})
                    </button>
                    <button
                        className={`filter-btn critical ${filter === "critical" ? "active" : ""}`}
                        onClick={() => setFilter("critical")}
                    >
                        Critical ({criticalCount})
                    </button>
                    <button
                        className={`filter-btn warning ${filter === "warning" ? "active" : ""}`}
                        onClick={() => setFilter("warning")}
                    >
                        Warnings ({warningCount})
                    </button>
                </div>
            </div>

            {criticalCount > 0 && (
                <div className="emergency-banner">
                    <div className="emergency-pulse-icon">🚨</div>
                    <div className="emergency-text">
                        <strong>EMERGENCY INTERVENTION REQUIRED</strong>
                        <p>{criticalCount} critical equipment anomaly detected across the industrial fleet. Predictive model suggests imminent breakdown.</p>
                    </div>
                </div>
            )}

            {filteredAlerts.length === 0 ? (
                <div className="all-clear-card">
                    <div className="clear-sparkle">✨</div>
                    <div className="clear-info">
                        <h3>Nominal Factory Operations</h3>
                        <p>All monitored factory units are executing within standard safety, thermal, and kinetic envelopes. 0 active faults.</p>
                    </div>
                    <span className="safe-badge">STATUS: OPTIMAL</span>
                </div>
            ) : (
                <div className="cyber-alerts-list">
                    {filteredAlerts.map((alert) => {
                        const isAcked = acknowledged[alert.id];
                        return (
                            <div
                                key={alert.id}
                                className={`cyber-alert-card ${alert.type} ${isAcked ? "acknowledged" : ""}`}
                            >
                                <div className="alert-left-indicator">
                                    <span className="alert-symbol">
                                        {alert.type === "critical" ? "⚠️" : "⚡"}
                                    </span>
                                </div>

                                <div className="alert-body">
                                    <div className="alert-heading-row">
                                        <div>
                                            <span className="alert-factory-badge">{alert.factoryName} ({alert.factoryId})</span>
                                            <h4>{alert.title}</h4>
                                        </div>
                                        <div className="alert-timing">
                                            <span className={`alert-severity-badge ${alert.type}`}>
                                                {alert.type.toUpperCase()}
                                            </span>
                                            <small>{alert.timestamp}</small>
                                        </div>
                                    </div>

                                    <p className="alert-text">{alert.message}</p>

                                    <div className="alert-telemetry-strip">
                                        <code>{alert.metric}</code>
                                        <button
                                            className={`ack-button ${isAcked ? "acked" : ""}`}
                                            onClick={() => handleAcknowledge(alert.id)}
                                        >
                                            {isAcked ? "✓ Acknowledged by Operator" : "Mark Acknowledged"}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </section>
    );
}

export default Alerts;
