const express = require("express");
const cors = require("cors");
const fs = require("fs");
const path = require("path");

const app = express();

app.use(cors());
app.use(express.json());

const PORT = 3001;

const DATA_DIR = path.join(
    __dirname,
    "../../data"
);

app.get("/api/fl/metrics", (req, res) => {
    const filePath = path.join(__dirname, "fl_metrics.json");

    if (!fs.existsSync(filePath)) {
        return res.json({ rounds: [] });
    }

    try {
        const content = fs.readFileSync(filePath, "utf8").trim();
        if (!content) {
            return res.json({ rounds: [] });
        }
        const data = JSON.parse(content);
        res.json(data);
    } catch (err) {
        console.error("Error reading fl_metrics.json:", err);
        res.json({ rounds: [] });
    }
});


// ============================================================
// Read latest data from a factory CSV
// ============================================================

function getLatestData(factoryNumber) {

    const filePath = path.join(
        DATA_DIR,
        `factory_${factoryNumber}`,
        "sensor_data.csv"
    );

    if (!fs.existsSync(filePath)) {
        return null;
    }

    const content = fs.readFileSync(
        filePath,
        "utf8"
    );

    const lines = content
        .trim()
        .split("\n");

    if (lines.length < 2) {
        return null;
    }

    const headers = lines[0].split(",");

    const values = lines[lines.length - 1].split(",");

    const data = {};

    headers.forEach((header, index) => {
        data[header] = values[index];
    });

    return data;
}
function getHistoryData(factoryNumber, limit = 20) {
    const filePath = path.join(
        DATA_DIR,
        `factory_${factoryNumber}`,
        "sensor_data.csv"
    );

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

    const dataLines = lines
        .slice(1)
        .slice(-limit);

    return dataLines.map((line) => {
        const values = line.split(",");
        const data = {};

        headers.forEach((header, index) => {
            data[header] = values[index];
        });

        return data;
    });
}


// ============================================================
// Get all factories
// ============================================================

app.get("/api/factories", (req, res) => {

    const factories = [];

    for (let i = 1; i <= 3; i++) {

        const data = getLatestData(i);

        factories.push({
            id: `F${i}`,
            name: `Factory ${i}`,
            status: data ? "online" : "offline",
            data: data
        });
    }

    res.json(factories);
});


// ============================================================
// Get latest data for one factory
// ============================================================

app.get("/api/factories/:id/latest", (req, res) => {

    const factoryId = req.params.id;

    const factoryNumber = factoryId.replace("F", "");

    const data = getLatestData(factoryNumber);

    if (!data) {

        return res.status(404).json({
            error: "Factory data not found"
        });
    }

    res.json(data);
});


// ============================================================
// Health check
// ============================================================

app.get("/api/health", (req, res) => {

    res.json({
        status: "OK",
        service: "Industrial Data Space Dashboard API"
    });
});


// ============================================================
// Start server
// ============================================================
app.get("/api/factories/:id/history", (req, res) => {
    const factoryId = req.params.id;
    const factoryNumber = factoryId.replace("F", "");

    const limit = parseInt(req.query.limit) || 20;

    const data = getHistoryData(factoryNumber, limit);

    res.json(data);
});
app.listen(PORT, () => {

    console.log(
        `Dashboard backend running on http://localhost:${PORT}`
    );

});