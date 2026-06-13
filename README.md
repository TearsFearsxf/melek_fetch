# Melek AI Fetch Engine (`melek_fetch`)

Unified web scraper, hardware monitor, and process controller library for the Melek AI assistant.

## Installation

```bash
pip install -e .
```

## Features

### 1. Web Fetcher (`MelekFetchController`)
- **Weather Forecasting**: Keyless API querying (via Open-Meteo).
- **Currency & Gold Rates**: TRY currency rates with fallbacks to TCMB XML parser.
- **Wikipedia Summarizer**: Queries the official Wikipedia REST API for clean 2-3 sentence summaries.
- **TTL Cache**: RAM-based caching to avoid redundant API queries.

### 2. Hardware Monitor (`HardwareMonitor`)
- **System Profile**: Dynamic detection of CPU (AMD Ryzen 5 4600H), RAM (16GB), GPU (RTX 3050), and SSD models.
- **Background Loop**: Runs a lightweight background daemon thread to monitor hardware parameters.
- **Mode Switching**: Automatically switches between Idle and Game Mode thresholds.
- **Unresponsive Process Cleanup**: Detects hung processes and cleans them up after callback confirmation.
