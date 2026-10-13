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
            endpoint: EDC_CONNECTOR_URLS.F1
        },
        {
            factoryId: "F2",
            id: "EDC-F2-PROD",
            factory: "Factory 2 (Hot Env)",
            endpoint: EDC_CONNECTOR_URLS.F2
        },
        {
            factoryId: "F3",
            id: "EDC-F3-PROD",
            factory: "Factory 3 (Legacy Machinery)",
            endpoint: EDC_CONNECTOR_URLS.F3
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
                if (active) {
                    setEdcStatus({
                        available: 0,
                        total: connectors.length,
                        connectors: [],
                        identity: "Unavailable",
                        policyMode: "Unavailable",
                        transferType: "Unavailable"
                    });
                }
            }
        };

        refreshStatus();
        const timer = setInterval(refreshStatus, 5000);
        return () => {
            active = false;
            clearInterval(timer);
        };
    }, [apiBaseUrl]);

    const statusFor = (factoryId) =>
        edcStatus?.connectors?.find((connector) => connector.id === factoryId);

    const isAvailable = (factoryId) => statusFor(factoryId)?.available === true;

    const formatBytes = (bytes) => {
        if (!Number.isFinite(bytes)) return "No transfer";
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    return (
        <section className="dashboard-section">
            <div className="section-head-wrap">
                <div>
                    <div className="badge-pill edc-pill">
                        <span className="dot-pulse-green"></span>
                        Local EDC Pull Flow
                    </div>
                    <h2 className="section-title">Eclipse Dataspace Connectors (EDC)</h2>
                    <p className="section-subtitle">
                        Provider catalog, contract negotiation, EDR resolution, and model-weight transfer
                    </p>
                </div>

                <div className="edc-overall-status">
                    <span className="shield-icon">EDC</span>
                    <div>
                        <span className="edc-status-label">Connector Availability</span>
                        <strong className="edc-status-val">
                            {edcStatus ? `${edcStatus.available}/${edcStatus.total}` : "Checking"} Local Connectors Available
                        </strong>
                    </div>
                </div>
            </div>

            <div className="edc-cards-grid">
                {connectors.map((connector) => {
                    const live = statusFor(connector.factoryId);
                    const latestTransfer = live?.latestTransfer;
                    const endpoint = connector.endpoint || live?.managementUrl;

                    return (
                        <div
                            className={`edc-glass-card ${selectedConnector === connector.id ? "card-expanded" : ""}`}
                            key={connector.id}
                            onClick={() => setSelectedConnector(selectedConnector === connector.id ? null : connector.id)}
                        >
                            <div className="edc-card-top">
                                <div className="edc-avatar">
                                    <span>EDC</span>
                                </div>

                                <div className="edc-main-info">
                                    <h4>{connector.id}</h4>
                                    <p>{connector.factory}</p>
                                </div>

                                <span className={`edc-pill-connected ${isAvailable(connector.factoryId) ? "" : "edc-pill-disconnected"}`}>
                                    <span className="beacon-dot"></span>
                                    {edcStatus ? (isAvailable(connector.factoryId) ? "Online" : "Offline") : "Checking"}
                                </span>
                            </div>

                            <div className="edc-stats-row">
                                <div className="edc-stat-box">
                                    <span className="stat-name">Identity</span>
                                    <strong className="stat-value">{edcStatus?.identity || "Checking"}</strong>
                                </div>
                                <div className="edc-stat-box">
                                    <span className="stat-name">Latest Round</span>
                                    <strong className="stat-value highlight-cyan">
                                        {latestTransfer ? `#${latestTransfer.round}` : "None"}
                                    </strong>
                                </div>
                                <div className="edc-stat-box">
                                    <span className="stat-name">Received</span>
                                    <strong className="stat-value">{formatBytes(latestTransfer?.bytes)}</strong>
                                </div>
                            </div>

                            {selectedConnector === connector.id && (
                                <div className="edc-expanded-drawer">
                                    <div className="detail-line">
                                        <span>Protocol:</span>
                                        <code>{edcStatus?.protocol || "Checking"}</code>
                                    </div>
                                    <div className="detail-line">
                                        <span>Policy:</span>
                                        <span className="policy-badge">{edcStatus?.policyMode || "Checking"}</span>
                                    </div>
                                    <div className="detail-line">
                                        <span>Transfer:</span>
                                        <code>{edcStatus?.transferType || "Checking"}</code>
                                    </div>
                                    <div className="detail-line">
                                        <span>Endpoint:</span>
                                        <code className="endpoint-code">{endpoint}</code>
                                    </div>
                                    <div className="detail-line">
                                        <span>Latest file:</span>
                                        <code>{latestTransfer?.file || "No transferred file found"}</code>
                                    </div>
                                </div>
                            )}

                            <div className="edc-card-foot">
                                <span className="click-hint">
                                    {selectedConnector === connector.id ? "Hide EDC details" : "View EDC details"}
                                </span>
                            </div>
                        </div>
                    );
                })}
            </div>
        </section>
    );
}

export default EDCStatus;
