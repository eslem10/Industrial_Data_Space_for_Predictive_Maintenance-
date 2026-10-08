const express = require("express");
const cors = require("cors");
const fs = require("fs");
const path = require("path");
const mqtt = require("mqtt");
const net = require("net");

const app = express();

app.use(cors());
app.use(express.json());

const PORT = 3001;
const MQTT_BROKER_URL = process.env.MQTT_BROKER_URL || "mqtt://broker.emqx.io:1883";
const MQTT_TOPIC = process.env.MQTT_TOPIC || "industrial/factory/+/sensors";
const EDC_CONNECTORS = [
    {
        id: "F1",
        host: process.env.EDC_F1_HOST || "127.0.0.1",
        port: Number(process.env.EDC_F1_PORT || 19193)
    },
    {
        id: "F2",
        host: process.env.EDC_F2_HOST || "127.0.0.1",
        port: Number(process.env.EDC_F2_PORT || 21193)
    },
    {
        id: "F3",
        host: process.env.EDC_F3_HOST || "127.0.0.1",
        port: Number(process.env.EDC_F3_PORT || 23193)
    }
];

const DATA_DIR = process.env.DATA_DIR || path.join(__dirname, "../../data");

const FIELDNAMES = [
    "timestamp",
    "factory_id",
    "temperature",
    "vibration",
    "pressure",
    "humidity",
    "energy_consumption",
    "state"
];

const liveLatest = new Map();
const liveHistory = new Map();
const streamClients = new Set();

function checkPort(host, port, timeoutMs = 500) {
    return new Promise((resolve) => {
        const socket = net.createConnection({ host, port });
        let settled = false;
        const finish = (available) => {
            if (settled) return;
            settled = true;
            socket.destroy();
            resolve(available);
        };

        socket.once("connect", () => finish(true));
        socket.once("error", () => finish(false));
        socket.setTimeout(timeoutMs, () => finish(false));
    });
}

const mqttStatus = {
    broker: MQTT_BROKER_URL,
    topic: MQTT_TOPIC,
    connected: false,
    lastMessageAt: null,
    lastError: null
};

function normalizeRow(row) {
    const normalized = {};

    Object.entries(row).forEach(([key, value]) => {
        normalized[key.trim()] = typeof value === "string" ? value.trim() : value;
    });

    return normalized;
}

function parseCsvLine(headers, line) {
    const values = line.split(",");
    const data = {};

    headers.forEach((header, index) => {
        data[header.trim()] = values[index] ? values[index].trim() : "";
    });

    return data;
}

function inferState(data) {
    if (data.state) {
        return data.state;
    }

    const temperature = Number(data.temperature);
    const vibration = Number(data.vibration);
    const pressure = Number(data.pressure);
    const energy = Number(data.energy_consumption);

    if (temperature > 85 || vibration > 1.2 || pressure > 5.5 || energy > 10) {
        return "failure";
    }

    return "normal";
}

function getFactoryNumber(factoryId) {
    return String(factoryId || "").replace("F", "");
}

function getFactoryFromTopic(topic) {
    const topicParts = topic.split("/");
    return topicParts[2];
}

function getCsvPath(factoryNumber) {
    return path.join(DATA_DIR, `factory_${factoryNumber}`, "sensor_data.csv");
}

function writeSensorData(data) {
    const factoryNumber = getFactoryNumber(data.factory_id);
    const factoryDir = path.join(DATA_DIR, `factory_${factoryNumber}`);
    const filePath = path.join(factoryDir, "sensor_data.csv");

    fs.mkdirSync(factoryDir, { recursive: true });

    const fileExists = fs.existsSync(filePath);
    const row = FIELDNAMES.map((field) => data[field] ?? "").join(",");

    if (!fileExists) {
        fs.writeFileSync(filePath, `${FIELDNAMES.join(",")}\n`, "utf8");
    }

    fs.appendFileSync(filePath, `${row}\n`, "utf8");
}

function sendStreamEvent(response, event, payload) {
    response.write(`event: ${event}\n`);
    response.write(`data: ${JSON.stringify(payload)}\n\n`);
}

function broadcast(event, payload) {
    streamClients.forEach((response) => {
        sendStreamEvent(response, event, payload);
    });
}

function buildFactory(factoryId, data) {
    return {
        id: factoryId,
        name: `Factory ${getFactoryNumber(factoryId)}`,
        status: data ? "online" : "offline",
        data
    };
}

function getLatestData(factoryNumber) {
    const filePath = getCsvPath(factoryNumber);

    if (!fs.existsSync(filePath)) {
        return null;
    }

    const content = fs.readFileSync(filePath, "utf8");
    const lines = content.trim().split("\n");

    if (lines.length < 2) {
        return null;
    }

    const headers = lines[0].split(",");
    return parseCsvLine(headers, lines[lines.length - 1]);
}

function getHistoryData(factoryNumber, limit = 20) {
    const filePath = getCsvPath(factoryNumber);

    if (!fs.existsSync(filePath)) {
        return [];
    }

    const content = fs.readFileSync(filePath, "utf8").trim();

    if (!content) {
        return [];
    }

    const lines = content.split("\n");

    if (lines.length < 2) {
        return [];
    }

    const headers = lines[0].split(",");

    return lines
        .slice(1)
        .slice(-limit)
        .map((line) => parseCsvLine(headers, line));
}

function getAllFactories() {
    const factories = [];

    for (let i = 1; i <= 3; i++) {
        const factoryId = `F${i}`;
        const data = liveLatest.get(factoryId) || getLatestData(i);
        factories.push(buildFactory(factoryId, data));
    }

    return factories;
}

function handleMqttMessage(topic, message) {
    try {
        const payload = JSON.parse(message.toString());
        const factoryId = payload.factory_id || getFactoryFromTopic(topic);

        if (!factoryId) {
            return;
        }

        const data = normalizeRow({
            timestamp: new Date().toISOString().replace("T", " ").slice(0, 19),
            ...payload,
            factory_id: factoryId
        });

        data.state = inferState(data);

        liveLatest.set(factoryId, data);

        const history = liveHistory.get(factoryId) || [];
        history.push(data);
        liveHistory.set(factoryId, history.slice(-100));

        writeSensorData(data);

        mqttStatus.lastMessageAt = data.timestamp;
        mqttStatus.lastError = null;

        broadcast("factory-update", {
            factory: buildFactory(factoryId, data),
            mqtt: mqttStatus
        });
    } catch (err) {
        mqttStatus.lastError = err.message;
        console.error("Error processing MQTT message:", err);
        broadcast("mqtt-status", mqttStatus);
    }
}

function startMqtt() {
    const client = mqtt.connect(MQTT_BROKER_URL, {
        clientId: `industrial-dashboard-${Math.random().toString(16).slice(2)}`,
        reconnectPeriod: 5000
    });

    client.on("connect", () => {
        mqttStatus.connected = true;
        mqttStatus.lastError = null;
        console.log(`Connected to MQTT broker: ${MQTT_BROKER_URL}`);

        client.subscribe(MQTT_TOPIC, (err) => {
            if (err) {
                mqttStatus.lastError = err.message;
                console.error("MQTT subscribe failed:", err);
                return;
            }

            console.log(`Subscribed to MQTT topic: ${MQTT_TOPIC}`);
            broadcast("mqtt-status", mqttStatus);
        });
    });

    client.on("message", handleMqttMessage);

    client.on("close", () => {
        mqttStatus.connected = false;
        broadcast("mqtt-status", mqttStatus);
    });

    client.on("error", (err) => {
        mqttStatus.lastError = err.message;
        console.error("MQTT error:", err.message);
        broadcast("mqtt-status", mqttStatus);
    });
}

app.get("/api/fl/metrics", (req, res) => {
    const metricsPaths = [
        process.env.METRICS_PATH,
        path.join(__dirname, "..", "..", "federated", "results", "metrics.json"),
        path.join(__dirname, "fl_metrics.json"),
    ].filter(Boolean);
    const filePath = metricsPaths.find((candidate) => fs.existsSync(candidate));

    if (!filePath) {
        return res.json({ rounds: [] });
    }

    try {
        const content = fs.readFileSync(filePath, "utf8").trim();
        if (!content) {
            return res.json({ rounds: [] });
        }
        const data = JSON.parse(content);
        res.json(Array.isArray(data) ? { rounds: data } : data);
    } catch (err) {
        console.error(`Error reading federated metrics from ${filePath}:`, err);
        res.json({ rounds: [] });
    }
});

app.get("/api/factories", (req, res) => {
    res.json(getAllFactories());
});

app.get("/api/factories/:id/latest", (req, res) => {
    const factoryId = req.params.id;
    const factoryNumber = getFactoryNumber(factoryId);
    const data = liveLatest.get(factoryId) || getLatestData(factoryNumber);

    if (!data) {
        return res.status(404).json({
            error: "Factory data not found"
        });
    }

    res.json(data);
});

app.get("/api/factories/:id/history", (req, res) => {
    const factoryId = req.params.id;
    const factoryNumber = getFactoryNumber(factoryId);
    const limit = parseInt(req.query.limit) || 20;
    const fileData = getHistoryData(factoryNumber, limit);
    const liveData = liveHistory.get(factoryId) || [];

    res.json([...fileData, ...liveData].slice(-limit));
});

app.get("/api/health", (req, res) => {
    res.json({
        status: "OK",
        service: "Industrial Data Space Dashboard API",
        mqtt: mqttStatus
    });
});

app.get("/api/mqtt/status", (req, res) => {
    res.json(mqttStatus);
});

app.get("/api/edc/status", async (req, res) => {
    const connectors = await Promise.all(
        EDC_CONNECTORS.map(async ({ id, host, port }) => ({
            id,
            host,
            port,
            available: await checkPort(host, port)
        }))
    );

    res.json({
        available: connectors.filter((connector) => connector.available).length,
        total: connectors.length,
        connectors
    });
});

app.get("/api/stream", (req, res) => {
    res.setHeader("Content-Type", "text/event-stream");
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("Connection", "keep-alive");
    res.flushHeaders?.();

    streamClients.add(res);

    sendStreamEvent(res, "mqtt-status", mqttStatus);
    sendStreamEvent(res, "factories", getAllFactories());

    req.on("close", () => {
        streamClients.delete(res);
        res.end();
    });
});

startMqtt();

app.listen(PORT, () => {
    console.log(`Dashboard backend running on http://localhost:${PORT}`);
});
