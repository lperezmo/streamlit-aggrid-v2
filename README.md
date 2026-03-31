# streamlit-aggrid-v2

[![PyPI version](https://img.shields.io/pypi/v/streamlit-aggrid-v2.svg)](https://pypi.org/project/streamlit-aggrid-v2/)
[![PyPI downloads](https://img.shields.io/pypi/dm/streamlit-aggrid-v2.svg)](https://pypi.org/project/streamlit-aggrid-v2/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.51%2B-FF4B4B.svg?logo=streamlit)](https://streamlit.io)

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://st-aggrid.streamlit.app/)

AG Grid component for Streamlit — interactive tables, editing, filtering, sorting, grouping & more.

Built on [AG Grid](https://www.ag-grid.com/) v34.3.1 with [Streamlit Custom Components v2](https://docs.streamlit.io/develop/concepts/custom-components).

## Acknowledgments

This project is a continuation of [streamlit-aggrid](https://github.com/PablocFonseca/streamlit-aggrid), originally created by **[Pablo Fonseca](https://github.com/PablocFonseca)**. Huge thanks to Pablo for building and maintaining the first version that the Streamlit community relied on for years.

## Install

```bash
pip install streamlit-aggrid-v2
```

> **Note:** The Python import stays `st_aggrid` — only the `pip install` name changed.

## Quick Start

```python
from st_aggrid import AgGrid
import pandas as pd

df = pd.read_csv(
    "https://raw.githubusercontent.com/fivethirtyeight/data/master/airline-safety/airline-safety.csv"
)
AgGrid(df)
```

```bash
streamlit run your_app.py
```

## Why v2?

The original [streamlit-aggrid](https://github.com/PablocFonseca/streamlit-aggrid) is built on Streamlit's legacy iframe-based component model (CCv1). Migrating to CCv2 is a significant architectural change — this rewrite does that while keeping the same Python API.

| | **streamlit-aggrid** (original) | **streamlit-aggrid-v2** |
|---|---|---|
| **Component model** | CCv1 — iframe + postMessage | CCv2 — direct DOM rendering |
| **AG Grid version** | v31 | v34.3.1 |
| **Themes** | 3 themes, no dark mode for quartz | 4 themes, automatic dark/light detection |
| **Build toolchain** | webpack / CRA | Vite + ESM |
| **React** | React 17 | React 18 |
| **Known bugs** | 25 open issues in codebase | All 25 fixed |
| **Event listener cleanup** | Leaks on unmount | Proper cleanup via `componentWillUnmount` |
| **State management** | Direct `this.state.api` mutation | `gridApiRef` pattern (React-safe) |
| **Style/script injection** | Duplicates on re-render | Deduplicated |
| **Mutable defaults** | `grid_response={}`, `update_on=[]` | Fixed with `None` + inline init |
| **Path handling** | Wrong variable, missing method | Corrected |
| **Custom themes** | Not supported | `StAggridTheme` with color schemes, icon sets, params |
| **Maintenance** | Inactive since 2023 | Active, semantic versioning, CI/CD |
| **Python API** | `from st_aggrid import AgGrid` | Same — fully backward compatible |

**Migration:** Change `pip install streamlit-aggrid` to `pip install streamlit-aggrid-v2`. No code changes needed.

## Features

- **No iframes** — AG Grid renders directly in the Streamlit DOM via CCv2, eliminating postMessage overhead.
- **Theming** — All four AG Grid themes (quartz, alpine, balham, material) with automatic dark/light mode detection. Custom themes via `StAggridTheme` with color schemes, icon sets, and param overrides.
- **Editing** — Cell editing with `singleClickEdit`, value parsers, and change detection.
- **Row selection** — Single, multiple, and checkbox selection with pre-selected rows.
- **Filtering & sorting** — Column filters, floating filters, quick search, and multi-column sort.
- **Column configuration** — Pinning, resizing, reordering, auto-sizing, and column groups via `GridOptionsBuilder`.
- **Cell renderers** — Custom cell rendering with `JsCode` (stars, badges, progress bars, buttons).
- **Row styling** — Conditional row/cell styling via `getRowStyle`, `rowClassRules`, and `cellStyle`.
- **Enterprise features** — Row grouping, pivot mode, status bar, side bar, Excel export, cell selection, sparklines (requires AG Grid license).
- **Data return modes** — `AS_INPUT`, `FILTERED`, `FILTERED_AND_SORTED`, `MINIMAL`, and `CUSTOM` via the collector pattern.
- **Modern build** — Vite + ESM replaces the legacy webpack/CRA toolchain.
- **Bug fixes** — 25 bugs fixed from the original codebase.
- **Backward compatible** — Existing `AgGrid()`, `GridOptionsBuilder`, `JsCode` code works with just a `pip install` change.

## API Overview

```python
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from st_aggrid import GridUpdateMode, DataReturnMode, ColumnsAutoSizeMode

# Build grid options from a DataFrame
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_pagination(paginationAutoPageSize=True)
gb.configure_selection("multiple", use_checkbox=True)
gb.configure_default_column(filter=True, sortable=True, floatingFilter=True)
grid_options = gb.build()

# Render the grid
response = AgGrid(
    df,
    gridOptions=grid_options,
    height=400,
    theme="quartz",                          # or "alpine", "balham", "material"
    update_mode=GridUpdateMode.MODEL_CHANGED,
    data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
    allow_unsafe_jscode=True,                # required for JsCode renderers
)

# Access results
selected_rows = response.selected_rows
filtered_data = response.data
```

## Live Demo

Check out the full showcase with 12 interactive examples:

**[st-aggrid.streamlit.app](https://st-aggrid.streamlit.app/)**

## License

MIT
