import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from "recharts";

const SENSOR_THEMES = {
    Temperature: {
        stroke: "#f97316",
        fillStart: "rgba(249, 115, 22, 0.4)",
        fillEnd: "rgba(249, 115, 22, 0.0)",
        glow: "rgba(249, 115, 22, 0.25)",
        icon: "🌡️"
    },
    Vibration: {
        stroke: "#06b6d4",
        fillStart: "rgba(6, 182, 212, 0.4)",
        fillEnd: "rgba(6, 182, 212, 0.0)",
        glow: "rgba(6, 182, 212, 0.25)",
        icon: "〰️"
    },
    Pressure: {
        stroke: "#a855f7",
        fillStart: "rgba(168, 85, 247, 0.4)",
        fillEnd: "rgba(168, 85, 247, 0.0)",
        glow: "rgba(168, 85, 247, 0.25)",
        icon: "⚙️"
    },
    "Energy Consumption": {
        stroke: "#10b981",
        fillStart: "rgba(16, 185, 129, 0.4)",
        fillEnd: "rgba(16, 185, 129, 0.0)",
        glow: "rgba(16, 185, 129, 0.25)",
        icon: "⚡"
    }
};

const CustomTooltip = ({ active, payload, label, unit, title }) => {
    if (active && payload && payload.length) {
        const val = payload[0].value;
        return (
            <div className="custom-chart-tooltip">
                <div className="tooltip-time">{label || "Live"}</div>
                <div className="tooltip-val-row">
                    <span className="tooltip-label">{title}:</span>
                    <span className="tooltip-val">{val} {unit}</span>
                </div>
            </div>
        );
    }
    return null;
};

function SensorChart({ title, data = [], dataKey, unit }) {
    const theme = SENSOR_THEMES[title] || {
        stroke: "#38bdf8",
        fillStart: "rgba(56, 189, 248, 0.35)",
        fillEnd: "rgba(56, 189, 248, 0.0)",
        glow: "rgba(56, 189, 248, 0.2)",
        icon: "📊"
    };

    const gradientId = `gradient-${dataKey}-${title.replace(/\s+/g, "")}`;

    // Compute live min, max, current
    const values = data.map((d) => Number(d[dataKey])).filter((v) => !isNaN(v));
    const latestVal = values.length > 0 ? values[values.length - 1] : "--";
    const maxVal = values.length > 0 ? Math.max(...values).toFixed(1) : "--";
    const minVal = values.length > 0 ? Math.min(...values).toFixed(1) : "--";

    return (
        <div className="glass-chart-card">
            <div className="chart-header">
                <div className="chart-title-wrap">
                    <span className="chart-icon">{theme.icon}</span>
                    <div>
                        <h3>{title}</h3>
                        <span className="chart-unit-badge">{unit ? `Unit: ${unit}` : "Normalized"}</span>
                    </div>
                </div>

                <div className="chart-kpis">
                    <div className="chart-kpi">
                        <span className="kpi-tag">Current</span>
                        <strong className="kpi-num" style={{ color: theme.stroke }}>
                            {latestVal} <small>{unit}</small>
                        </strong>
                    </div>
                    <div className="chart-kpi secondary">
                        <span className="kpi-tag">Range</span>
                        <span className="kpi-range">{minVal} - {maxVal}</span>
                    </div>
                </div>
            </div>

            <div className="chart-canvas-wrap">
                <ResponsiveContainer width="100%" height={260}>
                    <AreaChart data={data} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
                        <defs>
                            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor={theme.fillStart} />
                                <stop offset="95%" stopColor={theme.fillEnd} />
                            </linearGradient>
                        </defs>

                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />

                        <XAxis
                            dataKey="time"
                            stroke="#64748b"
                            tick={{ fill: "#64748b", fontSize: 11 }}
                            tickLine={false}
                            axisLine={{ stroke: "#e2e8f0" }}
                        />

                        <YAxis
                            stroke="#64748b"
                            tick={{ fill: "#64748b", fontSize: 11 }}
                            tickLine={false}
                            axisLine={false}
                            domain={["auto", "auto"]}
                        />

                        <Tooltip content={<CustomTooltip unit={unit} title={title} />} />

                        <Area
                            type="monotone"
                            dataKey={dataKey}
                            stroke={theme.stroke}
                            strokeWidth={2.5}
                            fillOpacity={1}
                            fill={`url(#${gradientId})`}
                            dot={false}
                            activeDot={{
                                r: 5,
                                fill: theme.stroke,
                                stroke: "#ffffff",
                                strokeWidth: 2,
                                filter: `drop-shadow(0 0 6px ${theme.stroke})`
                            }}
                        />
                    </AreaChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}

export default SensorChart;