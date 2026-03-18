# ⚡ Entropy Engine

**Watch your data shrink in real time through a futuristic system interface.**

Entropy Engine is a data optimization visualizer with two interfaces: a terminal-based CLI with animated ASCII progress bars, and a web application with a Marathon-style sci-fi dashboard. Feed it JSON or CSV, and watch your data flow through a 4-stage compression pipeline in real time.

---

## Demo

> Demo GIF coming soon

### Terminal Interface

```
▸ INITIALIZING ENTROPY ENGINE...
▸ LOADING CORE MODULES...
▸ SYSTEM READY.

┌─── DEDUPLICATION ────────────────────┐
  [████████████░░░░░░░░░░░░░░░░░░] 40%

▸ DEDUP COMPLETE
▸ 3.2 KB → 2.4 KB  [-25.0%]
```

### Web Interface

4-panel dashboard: file upload, animated pipeline visualization with glowing nodes, real-time metrics, and an embedded terminal log -- all in a dark sci-fi theme with neon green and cyan accents.

---

## Features

- 4-stage optimization pipeline: deduplication, dictionary encoding, field trimming, gzip compression
- Two interfaces: animated terminal CLI and web dashboard
- Real-time streaming progress via Server-Sent Events
- Pipeline nodes that pulse and glow as data flows through
- Animated data size bar that visibly shrinks
- Embedded terminal panel with typing effect
- Per-stage and total size reduction metrics
- JSON and CSV input support
- Drag-and-drop file upload (web)

---

## Quick Start

### Terminal (CLI)

```bash
git clone https://github.com/Positivitty/EntropyEngine.git
cd EntropyEngine
pip install -r requirements.txt
python main.py samples/sample.json
```

### Web Application

Start the backend and frontend in separate terminals:

```bash
# Terminal 1 - Backend
cd EntropyEngine
pip install -r web-backend/requirements.txt
./web-backend/run.sh

# Terminal 2 - Frontend
cd EntropyEngine/web-frontend
npm install
npm run dev
```

Open http://localhost:5173 and drop a JSON or CSV file.

---

## How It Works

| Stage | Description |
|---|---|
| **Deduplication** | Removes duplicate records, keeping only unique entries. |
| **Dictionary Encoding** | Replaces repeated field values with compact integer codes. |
| **Field Trimming** | Strips whitespace, null fields, and empty values. |
| **Compression** | Applies gzip compression to the optimized payload. |

Each stage reports before/after byte counts. The web backend streams progress as Server-Sent Events so the frontend can animate each stage in real time.

---

## Tech Stack

| Component | Technology |
|---|---|
| Core Engine | Python (stdlib only) |
| Terminal UI | Rich |
| Backend API | FastAPI + Uvicorn |
| Frontend | React + Vite |
| Streaming | Server-Sent Events |

---

## Architecture

```
EntropyEngine/
├── main.py                 # CLI entry point
├── requirements.txt        # CLI dependencies (rich)
├── samples/
│   ├── sample.json         # Example dataset (50 records)
│   └── sample.csv
├── entropy/                # Core pipeline (stdlib only)
│   ├── loader.py           # JSON/CSV file loading
│   ├── metrics.py          # Size tracking and formatting
│   ├── pipeline.py         # Stage orchestration
│   └── transforms.py       # Dedup, encoding, trim, gzip
├── ui/                     # Terminal rendering (rich)
│   ├── theme.py            # Colors and boot messages
│   ├── animations.py       # Progress bars and diagrams
│   └── terminal.py         # UI controller
├── web-backend/            # FastAPI server
│   ├── app.py              # API endpoints (/upload, /process, /results)
│   ├── requirements.txt
│   └── run.sh
└── web-frontend/           # React + Vite
    └── src/
        ├── App.jsx         # 4-panel grid layout
        ├── App.css         # Marathon-style dark theme
        ├── hooks/useEntropy.js    # State + SSE streaming
        └── components/
            ├── UploadPanel.jsx    # Drag-and-drop file upload
            ├── PipelineView.jsx   # Animated pipeline nodes + size bar
            ├── MetricsPanel.jsx   # Per-stage results + summary
            └── TerminalPanel.jsx  # ASCII log with typing effect
```

---

## CLI Options

```
usage: main.py [-h] [--no-animation] file

positional arguments:
  file               Path to a JSON or CSV file

optional arguments:
  --no-animation     Skip animation delays
```

---

## License

MIT
