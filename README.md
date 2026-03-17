# ⚡ Entropy Engine

**Watch your data shrink in real time through a sci-fi terminal interface.**

Entropy Engine is a terminal-based data optimization visualizer built in Python. Feed it JSON or CSV, and it runs your data through a multi-stage compression pipeline -- deduplication, dictionary encoding, field trimming, and compression -- rendering animated ASCII visualizations at every step.

---

## Demo

> Demo GIF coming soon

```
▸ INITIALIZING ENTROPY ENGINE...
▸ LOADING CORE MODULES...
▸ SYSTEM READY.

┌─── DEDUPLICATION ────────────────────┐
│ [████████████░░░░░░░░░░░░░░░░░░] 40% │
└──────────────────────────────────────┘

▸ DEDUP COMPLETE
▸ 3.2 KB → 2.4 KB  [-25.0%]
```

---

## Features

- Real-time pipeline visualization with animated terminal output
- 4-stage optimization: deduplication, dictionary encoding, field trimming, compression
- Animated progress bars for each stage
- Per-stage and cumulative size metrics reported inline
- JSON and CSV input support
- Zero external dependencies beyond `rich`

---

## Quick Start

```bash
git clone https://github.com/your-username/EntropyEngine.git
cd EntropyEngine
pip install -r requirements.txt
python main.py samples/sample.json
```

---

## How It Works

Entropy Engine processes input data through four sequential stages. Each stage transforms the data and reports size reduction metrics before handing off to the next.

| Stage | Description |
|---|---|
| **Deduplication** | Identifies and removes duplicate records, keeping only unique entries. |
| **Dictionary Encoding** | Replaces repeated field values with compact integer references via a lookup table. |
| **Field Trimming** | Strips whitespace, null fields, and zero-information columns from each record. |
| **Compression** | Applies byte-level compression to the optimized payload and reports final size. |

Each stage writes its before/after byte counts to the metrics tracker, which the UI reads to render progress bars and reduction percentages.

---

## Architecture

```
EntropyEngine/
├── main.py                 # CLI entry point and pipeline orchestration
├── requirements.txt        # Dependencies (just rich)
├── samples/
│   ├── sample.json         # Example JSON dataset (50 records)
│   └── sample.csv          # Same data in CSV format
├── entropy/                # Core pipeline logic (stdlib only)
│   ├── __init__.py
│   ├── loader.py           # JSON/CSV file loading
│   ├── metrics.py          # Size tracking and human-readable formatting
│   ├── pipeline.py         # Stage orchestration with callbacks
│   └── transforms.py       # Dedup, dict encoding, field trim, gzip
└── ui/                     # Terminal rendering (rich)
    ├── __init__.py
    ├── theme.py            # Colors, stage names, boot messages
    ├── animations.py       # Progress bars, pipeline diagrams, headers
    └── terminal.py         # Main UI controller with Live animation
```

---

## Options

```
usage: main.py [-h] [--no-animation] input

positional arguments:
  input              Path to a JSON or CSV file

optional arguments:
  --no-animation     Disable animated progress bars and transitions.
                     Prints results only. Useful for piping output
                     or running in non-interactive environments.
```

---

## License

This project is licensed under the [MIT License](LICENSE).
