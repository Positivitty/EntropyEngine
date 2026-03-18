# ⚡ Entropy Engine

**Detect, understand, and fix inefficient data in real time.**

Entropy Engine is a data efficiency analyzer that detects inefficiencies in datasets, explains why they matter with engineer-level insight, lets you simulate fixes safely, and exports optimized data and reports. The interface is a Marathon-style sci-fi dashboard with real-time animations.

---

## Demo

> Demo GIF coming soon

### Issue Detection

Upload a dataset and Entropy Engine immediately identifies:
- Duplicate records from ETL pipelines or retry logic
- High string repetition in low-cardinality fields
- Excess whitespace from CSV parsers or user input
- Structural redundancy exploitable by compression

Each issue includes impact metrics, field-level breakdowns, engineer-level explanations, and projections to 1M records.

### Terminal Interface

```
▸ INITIALIZING ENTROPY ENGINE...
▸ SYSTEM READY.
▸ ANALYSIS COMPLETE: 4 issue(s) detected
▸ EFFICIENCY SCORE: 44/100
▸ SIMULATING: DEDUP...
▸ DEDUP: 7.4 KB → 6.8 KB [-7.9%]
```

---

## Features

- Issue detection engine with 4 analyzers (duplicates, repetition, whitespace, compression)
- Primary issue callout with severity, impact percentage, and byte-level waste
- Engineer-level explanations: why issues happen, impact on storage/perf/compression
- Simulate fixes per-issue without mutating original data
- State toggle between Original and Simulated views
- Efficiency Score (0-100) with color-coded gauge
- Projected impact at 1M records for each issue
- Export optimized data (JSON/CSV) or full analysis reports
- 4-stage optimization pipeline with animated visualization
- Real-time streaming via Server-Sent Events
- Embedded terminal panel with typing effect
- Terminal CLI with animated ASCII progress bars
- JSON and CSV input support

---

## Quick Start

### Web Application

```bash
git clone https://github.com/Positivitty/EntropyEngine.git
cd EntropyEngine

# Terminal 1 - Backend
pip install -r web-backend/requirements.txt
./web-backend/run.sh

# Terminal 2 - Frontend
cd web-frontend
npm install
npm run dev
```

Open http://localhost:5173, drop a JSON/CSV file, and click **Analyze Issues**.

### Terminal CLI

```bash
pip install -r requirements.txt
python main.py samples/sample.json
```

---

## How It Works

### Issue Detection

| Issue | What It Detects | Fix Stage |
|---|---|---|
| **Duplicate Records** | Exact row duplicates from ETL, merges, retries | Deduplication |
| **String Repetition** | Low-cardinality fields storing full strings N times | Dictionary Encoding |
| **Excess Whitespace** | Leading/trailing spaces, empty fields | Field Trimming |
| **Compression Opportunity** | Structural redundancy in JSON/CSV format | gzip Compression |

### Simulation System

Simulate fixes one issue at a time without touching original data:
1. Click **Simulate Fix** on any issue
2. Watch the relevant pipeline node pulse and the size bar shrink
3. Review the simulated reduction in the metrics panel
4. Toggle between Original and Simulated views
5. Export the optimized dataset or a full report

---

## Tech Stack

| Component | Technology |
|---|---|
| Issue Detection | Python (stdlib) |
| Core Engine | Python (stdlib) |
| Terminal UI | Rich |
| Backend API | FastAPI + Uvicorn |
| Frontend | React + Vite |
| Streaming | Server-Sent Events |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/upload` | Upload JSON/CSV file |
| POST | `/analyze/{id}` | Detect issues and return report |
| POST | `/simulate/{id}/{issue}` | Simulate fixing one issue (SSE) |
| POST | `/process/{id}` | Run full pipeline (SSE) |
| POST | `/apply/{id}` | Apply all fixes |
| GET | `/results/{id}` | Get cached results |
| GET | `/export/{id}` | Download data or report |

---

## Architecture

```
EntropyEngine/
├── main.py                 # Terminal CLI entry point
├── entropy/                # Core engine (stdlib only)
│   ├── issues.py           # Issue detection (duplicates, repetition, whitespace, compression)
│   ├── loader.py           # JSON/CSV file loading
│   ├── metrics.py          # Size tracking and formatting
│   ├── pipeline.py         # Stage orchestration
│   └── transforms.py       # Dedup, encoding, trim, gzip
├── ui/                     # Terminal rendering (rich)
│   ├── theme.py
│   ├── animations.py
│   └── terminal.py
├── web-backend/            # FastAPI server
│   ├── app.py              # All API endpoints
│   ├── requirements.txt
│   └── run.sh
├── web-frontend/           # React + Vite
│   └── src/
│       ├── App.jsx         # 4-panel grid layout
│       ├── hooks/useEntropy.js
│       └── components/
│           ├── IssuesPanel.jsx     # Primary issue callout + issue cards
│           ├── SimulationBanner.jsx # State toggle banner
│           ├── UploadPanel.jsx
│           ├── PipelineView.jsx
│           ├── MetricsPanel.jsx
│           └── TerminalPanel.jsx
└── samples/
    ├── sample.json
    └── sample.csv
```

---

## License

MIT
