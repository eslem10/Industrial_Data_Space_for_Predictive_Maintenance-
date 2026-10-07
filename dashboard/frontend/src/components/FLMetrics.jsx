import { useState } from "react";
import {
    AreaChart,
    Area,
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Legend
} from "recharts";

function FLMetrics({ metrics = [] }) {
    const [chartMode, setChartMode] = useState("loss"); // "loss" or "accuracy"

    if (!metrics || metrics.length === 0) {
        return (
            <div className="empty-state-glass">
                <span className="empty-icon">🧠</span>
                <h3>Federated Learning Engine</h3>
                <p>Awaiting aggregation metrics from Flower / FedAvg server...</p>
            </div>
        );
    }

    const latest = metrics[metrics.length - 1];

    // Compute progress delta
    const first = metrics[0];
    const accGain = (latest.accuracy - first.accuracy) * 100;

    return (
        <section className="dashboard-section">
            <div className="section-head-wrap">
                <div>
                    <div className="badge-pill fl-pill">
                        <span className="dot-pulse-purple"></span>
                        Privacy-Preserving Edge AI (Flower & TensorFlow)
                    </div>
                    <h2 className="section-title">Federated Learning Model Convergence</h2>
                    <p className="section-subtitle">
                        Decentralized neural network trained across 3 factories without sharing raw sensor data
                    </p>
                </div>

                <div className="fl-round-hero">
                    <span className="fl-round-tag">AGGREGATION CYCLE</span>
                    <strong className="fl-round-val">Round {latest.round} of {metrics.length}</strong>
                    <span className="fl-gain-tag">+{accGain.toFixed(1)}% vs Round 1</span>
                </div>
            </div>

            {/* 4 Key Metrics Cards with Progress Bars */}
            <div className="fl-metrics-grid">
                <div className="fl-metric-glass-card">
                    <div className="fl-metric-top">
                        <span className="fl-metric-name">Global Accuracy</span>
                        <span className="fl-metric-icon">🎯</span>
                    </div>
                    <strong className="fl-metric-number highlight-emerald">
                        {(latest.accuracy * 100).toFixed(1)}%
                    </strong>
                    <div className="fl-progress-track">
                        <div
                            className="fl-progress-fill emerald"
                            style={{ width: `${latest.accuracy * 100}%` }}
                        ></div>
                    </div>
                    <span className="fl-metric-sub">Across stratified test sets</span>
                </div>

                <div className="fl-metric-glass-card">
                    <div className="fl-metric-top">
                        <span className="fl-metric-name">Precision</span>
                        <span className="fl-metric-icon">⚡</span>
                    </div>
                    <strong className="fl-metric-number highlight-cyan">
                        {(latest.precision * 100).toFixed(1)}%
                    </strong>
                    <div className="fl-progress-track">
                        <div
                            className="fl-progress-fill cyan"
                            style={{ width: `${latest.precision * 100}%` }}
                        ></div>
                    </div>
                    <span className="fl-metric-sub">Low false alarm rate</span>
                </div>

                <div className="fl-metric-glass-card">
                    <div className="fl-metric-top">
                        <span className="fl-metric-name">Recall (Sensitivity)</span>
                        <span className="fl-metric-icon">🔍</span>
                    </div>
                    <strong className="fl-metric-number highlight-purple">
                        {(latest.recall * 100).toFixed(1)}%
                    </strong>
                    <div className="fl-progress-track">
                        <div
                            className="fl-progress-fill purple"
                            style={{ width: `${latest.recall * 100}%` }}
                        ></div>
                    </div>
                    <span className="fl-metric-sub">Detected failure states</span>
                </div>

                <div className="fl-metric-glass-card">
                    <div className="fl-metric-top">
                        <span className="fl-metric-name">F1-Score</span>
                        <span className="fl-metric-icon">⭐</span>
                    </div>
                    <strong className="fl-metric-number highlight-amber">
                        {(latest.f1 * 100).toFixed(1)}%
                    </strong>
                    <div className="fl-progress-track">
                        <div
                            className="fl-progress-fill amber"
                            style={{ width: `${latest.f1 * 100}%` }}
                        ></div>
                    </div>
                    <span className="fl-metric-sub">Harmonic mean balance</span>
                </div>
            </div>

            {/* FL Chart Card */}
            <div className="glass-chart-card fl-chart-container">
                <div className="chart-header">
                    <div>
                        <h3>Model Optimization Trajectory</h3>
                        <span className="chart-unit-badge">Federated Averaging (FedAvg)</span>
                    </div>

                    <div className="segmented-control">
                        <button
                            className={`seg-btn ${chartMode === "loss" ? "active" : ""}`}
                            onClick={() => setChartMode("loss")}
                        >
                            Loss Descent Curve
                        </button>
                        <button
                            className={`seg-btn ${chartMode === "accuracy" ? "active" : ""}`}
                            onClick={() => setChartMode("accuracy")}
                        >
                            Accuracy & F1 Trajectory
                        </button>
                    </div>
                </div>

                <div className="chart-canvas-wrap">
                    <ResponsiveContainer width="100%" height={270}>
                        {chartMode === "loss" ? (
                            <AreaChart data={metrics} margin={{ top: 15, right: 15, left: -15, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="lossGradient" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4} />
                                        <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                                <XAxis dataKey="round" tickFormatter={(r) => `Round ${r}`} stroke="#64748b" tick={{ fill: "#64748b", fontSize: 12 }} />
                                <YAxis stroke="#64748b" tick={{ fill: "#64748b", fontSize: 12 }} />
                                <Tooltip
                                    contentStyle={{ background: "#ffffff", borderColor: "#e2e8f0", borderRadius: 8, color: "#0f172a", boxShadow: "0 6px 20px rgba(0,0,0,0.06)" }}
                                    formatter={(v) => [`Loss: ${Number(v).toFixed(4)}`, "Cross-Entropy Loss"]}
                                />
                                <Area
                                    type="monotone"
                                    dataKey="loss"
                                    stroke="#f43f5e"
                                    strokeWidth={3}
                                    fillOpacity={1}
                                    fill="url(#lossGradient)"
                                    dot={{ fill: "#f43f5e", r: 4, stroke: "#fff", strokeWidth: 2 }}
                                    activeDot={{ r: 6 }}
                                />
                            </AreaChart>
                        ) : (
                            <LineChart data={metrics} margin={{ top: 15, right: 15, left: -15, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                                <XAxis dataKey="round" tickFormatter={(r) => `Round ${r}`} stroke="#64748b" tick={{ fill: "#64748b", fontSize: 12 }} />
                                <YAxis domain={[0.5, 1.0]} stroke="#64748b" tick={{ fill: "#64748b", fontSize: 12 }} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                                <Tooltip
                                    contentStyle={{ background: "#ffffff", borderColor: "#e2e8f0", borderRadius: 8, color: "#0f172a", boxShadow: "0 6px 20px rgba(0,0,0,0.06)" }}
                                    formatter={(v, name) => [`${(Number(v) * 100).toFixed(1)}%`, name]}
                                />
                                <Legend />
                                <Line type="monotone" dataKey="accuracy" name="Accuracy" stroke="#10b981" strokeWidth={3} dot={{ r: 4 }} />
                                <Line type="monotone" dataKey="f1" name="F1-Score" stroke="#a855f7" strokeWidth={3} dot={{ r: 4 }} />
                                <Line type="monotone" dataKey="precision" name="Precision" stroke="#00f2fe" strokeWidth={2} strokeDasharray="4 4" dot={false} />
                            </LineChart>
                        )}
                    </ResponsiveContainer>
                </div>
            </div>
        </section>
    );
}

export default FLMetrics;