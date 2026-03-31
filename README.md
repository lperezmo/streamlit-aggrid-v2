# streamlit-aggrid-v2

AG Grid component for Streamlit — interactive tables, editing, filtering & more.

Built on [AG Grid](https://www.ag-grid.com/) v34.3.1.

## Acknowledgments

This project is a continuation of [streamlit-aggrid](https://github.com/PablocFonseca/streamlit-aggrid), originally created by **[Pablo Fonseca](https://github.com/PablocFonseca)**. Huge thanks to Pablo for building and maintaining the first version that the Streamlit community relied on for years.

## Install

```bash
pip install streamlit-aggrid-v2
```

## Quick Start

```python
from st_aggrid import AgGrid
import pandas as pd

df = pd.read_csv(
    "https://raw.githubusercontent.com/fivethirtyeight/data/master/airline-safety/airline-safety.csv"
)
AgGrid(df)
```

> **Note:** The Python import stays `st_aggrid` — only the `pip install` name changed.

```bash
streamlit run example.py
```

## What's New in v2

- **No iframes** — AG Grid renders directly in the Streamlit DOM via Custom Components v2 (CCv2), eliminating postMessage serialization overhead for large datasets.
- **Better theming** — CSS `--st-*` variables auto-adapt to the active Streamlit theme. All four AG Grid themes (quartz, alpine, balham, material) supported with automatic dark mode detection.
- **Modern build** — Vite + ESM replaces the legacy webpack/CRA toolchain.
- **Bug fixes** — 25 bugs fixed from the original codebase (mutable defaults, Path handling, event listener leaks, theme issues, and more).
- **Maintained** — Active development with semantic versioning and automated releases.

The public Python API (`AgGrid()`, `GridOptionsBuilder`, etc.) is fully backward compatible. Existing code should work by changing only the `pip install` line.

## License

MIT
