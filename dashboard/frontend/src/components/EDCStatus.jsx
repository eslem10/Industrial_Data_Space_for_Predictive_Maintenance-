import { useEffect, useState } from "react";
import { EDC_CONNECTOR_URLS } from "../config";

function EDCStatus({ apiBaseUrl }) {
    const [selectedConnector, setSelectedConnector] = useState(null);
    const [edcStatus, setEdcStatus] = useState(null);

    const connectors = [
        {
            factoryId: "F1",
            id: "EDC-F1-PROD",
            factory: "Factory 1 (Cold Env)",
            status: "connected",
            endpoint: EDC_CONNECTOR_URLS.F1,
            daps: "Local runtime",
            contract: "ODRL 2.0 Maintenance Agreement",
            transferred: "14.2 MB",
            throughput: "42.8 KB/s",
            latency: "14 ms",
            policy: "Sovereign Usage - Read Only"
        },
        {
            factoryId: "F2",
            id: "EDC-F2-PROD",
            factory: "Factory 2 (Hot Env)",
            status: "connected",
            endpoint: EDC_CONNECTOR_URLS.F2,
            daps: "Local runtime",
            contract: "ODRL 2.0 Maintenance Agreement",
            transferred: "18.6 MB",
            throughput: "48.1 KB/s",
            latency: "19 ms",
            policy: "Sovereign Usage - Read Only"
        },
        {
            factoryId: "F3",
            id: "EDC-F3-PROD",
            factory: "Factory 3 (Legacy Machinery)",
            status: "connected",
            endpoint: EDC_CONNECTOR_URLS.F3,
            daps: "Local runtime",
            contract: "ODRL 2.0 Maintenance Agreement",
            transferred: "22.1 MB",
            throughput: "56.4 KB/s",
            latency: "23 ms",
            policy: "Sovereign Usage - Read Only"
        }
    ];

    useEffect(() => {
        let active = true;

        const refreshStatus = async () => {
            try {
                const response = await fetch(`${apiBaseUrl}/api/edc/status`);
                if (!response.ok) throw new Error(`EDC status request failed: ${response.status}`);
                const data = await response.json();
                if (active) setEdcStatus(data);
            } catch (error) {
                console.error("Error fetching EDC status:", error);
                if (active) setEdcStatus({ available: 0, total: connectors.length, connectors: [] });
            }
        };

        refreshStatus();
        const timer = setInterval(refreshStatus, 5000);
        return () => {
            active = false;
            clearInterval(timer);
        };
    }, [apiBaseUrl]);

    const isAvailable = (factoryId) =>
        edcStatus?.connectors?.find((connector) => connector.id === factoryId)?.available === true;

    return (
        <section className="dashboard-section">
            <div className="section-head-wrap">
                <div>
                    <div className="badge-pill edc-pill">
                        <span className="dot-pulse-green"></span>
                        Gaia-X & IDSA Sovereign Data Mesh
                    </div>
                    <h2 className="section-title">Eclipse Dataspace Connectors (EDC)</h2>
                    <p className="section-subtitle">
                        Cross-factory federated data sovereignty, policy enforcement, and trust validation
                    </p>
                </div>

                <div className="edc-overall-status">
                    <span className="shield-icon">🛡️</span>
                    <div>
                        <span className="edc-status-label">DAPS Security Identity</span>
                        <strong className="edc-status-val">
                            {edcStatus ? `${edcStatus.available}/${edcStatus.total}` : "Checking"} Local Connectors Available
                        </strong>
                    </div>
                </div>
            </div>

            <div className="edc-cards-grid">
                {connectors.map((c) => (
                    <div
                        className={`edc-glass-card ${selectedConnector === c.id ? "card-expanded" : ""}`}
                        key={c.id}
                        onClick={() => setSelectedConnector(selectedConnector === c.id ? null : c.id)}
                    >
                        <div className="edc-card-top">
                            <div className="edc-avatar">
                                <span>EDC</span>
                            </div>

                            <div className="edc-main-info">
                                <h4>{c.id}</h4>
                                <p>{c.factory}</p>
                            </div>

                            <span className={`edc-pill-connected ${isAvailable(c.factoryId) ? "" : "edc-pill-disconnected"}`}>
                                <span className="beacon-dot"></span>
                                {edcStatus ? (isAvailable(c.factoryId) ? "Online" : "Offline") : "Checking"}
                            </span>
                        </div>

                        <div className="edc-stats-row">
                            <div className="edc-stat-box">
                                <span className="stat-name">Security</span>
                                <strong className="stat-value">{c.daps}</strong>
                            </div>
                            <div className="edc-stat-box">
                                <span className="stat-name">Latency</span>
                                <strong className="stat-value highlight-cyan">{c.latency}</strong>
                            </div>
                            <div className="edc-stat-box">
                                <span className="stat-name">Rate</span>
                                <strong className="stat-value">{c.throughput}</strong>
                            </div>
                        </div>

                        {selectedConnector === c.id && (
                            <div className="edc-expanded-drawer">
                                <div className="detail-line">
                                    <span>Contract:</span>
                                    <code>{c.contract}</code>
                                </div>
                                <div className="detail-line">
                                    <span>Policy:</span>
                                    <span className="policy-badge">{c.policy}</span>
                                </div>
                                <div className="detail-line">
                                    <span>Endpoint:</span>
                                    <code className="endpoint-code">{c.endpoint}</code>
                                </div>
                            </div>
                        )}

                        <div className="edc-card-foot">
                            <span className="click-hint">
                                {selectedConnector === c.id ? "▲ Hide Contract Details" : "▼ View Data Policy & Agreement"}
                            </span>
                        </div>
                    </div>
                ))}
            </div>
        </section>
    );
}

export default EDCStatus;