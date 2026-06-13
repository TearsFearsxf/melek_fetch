# Melek AI System Monitor (`melek_sys`)

Industrial-grade hardware monitoring and unresponsive process controller library for Melek AI.

## Installation

```bash
pip install -e .
```

## Features

- **Automatic Hardware Detection**: Automatically profiles CPU, logical/physical cores, total RAM, GPU name, total VRAM, and disk drives on startup.
- **Background Thread Monitoring**: Runs a background monitoring daemon that updates system metrics asynchronously without blocking the main program.
- **Dynamic Mode Thresholds**: Automatically switches between Idle and Game Mode (adjusts alert temperature limits).
- **Hung Application Callback**: Detects unresponsive applications ("Not Responding") on Windows and triggers callback to clean them up.
