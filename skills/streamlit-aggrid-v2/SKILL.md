---
name: streamlit-aggrid-v2
description: Build interactive data tables in Streamlit using streamlit-aggrid-v2 (AG Grid v34 via Custom Components v2). Use when a user asks for an AG Grid in Streamlit, or when code imports from `st_aggrid` or mentions `AgGrid`, `GridOptionsBuilder`, `JsCode`, `StAggridTheme`. Covers install, quick start, grid options, JsCode renderers/formatters, row selection, filtering, data return modes, theming, tree data, and common gotchas.
---

# streamlit-aggrid-v2

AG Grid for Streamlit via Custom Components v2 (CCv2). Drop-in replacement for the older `streamlit-aggrid`: same Python API (`from st_aggrid import AgGrid, ...`), different pip name.

## Install

```bash
pip install streamlit-aggrid-v2
# or: uv add streamlit-aggrid-v2
```

Python import stays `st_aggrid`. Only the pip name changed.

Requirements: Python 3.10+, Streamlit >= 1.51, pandas >= 1.4.

## Quick start

```python
import pandas as pd
from st_aggrid import AgGrid

df = pd.read_csv("data.csv")
AgGrid(df)
```

That's it. Renders an interactive table with sorting, column resize, and filter UI.

## GridOptionsBuilder — the fluent configurator

Use this for common configuration. Build once, pass to `AgGrid`.

```python
from st_aggrid import AgGrid, GridOptionsBuilder

gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_pagination(paginationAutoPageSize=True)
gb.configure_selection("multiple", use_checkbox=True)
gb.configure_default_column(filter=True, sortable=True, floatingFilter=True)
gb.configure_column("Salary", type=["numericColumn"], valueFormatter="'$' + x.toLocaleString()")
grid_options = gb.build()

response = AgGrid(df, gridOptions=grid_options, height=400)
selected = response.selected_rows
filtered = response.data
```

Useful methods:
- `configure_default_column(**kwargs)` — applies to every column
- `configure_column(name, **kwargs)` — override a single column
- `configure_selection(selection_mode="multiple", use_checkbox=True, pre_selected_rows=[0, 2])`
- `configure_pagination(enabled=True, paginationAutoPageSize=True)`
- `configure_side_bar(filters_panel=True, columns_panel=True)` (enterprise)
- `build()` — returns a plain dict you can further edit (e.g. `grid_options["pivotMode"] = True`)

Anything not covered by the builder: edit the dict directly before passing.

## JsCode — inject JavaScript safely

`JsCode` wraps JS strings so they survive JSON transport. Need `allow_unsafe_jscode=True` on `AgGrid`.

```python
from st_aggrid import AgGrid, JsCode

currency = JsCode("function(p) { return '$' + p.value.toLocaleString(); }")

gb.configure_column("price", valueFormatter=currency)

AgGrid(df, gridOptions=gb.build(), allow_unsafe_jscode=True)
```

Use `JsCode` for: `valueFormatter`, `valueGetter`, `cellRenderer`, `cellStyle`, `getRowStyle`, `getDataPath`, `rowClassRules` values, etc.

Class-based cell renderer:

```python
btn = JsCode("""
class BtnRenderer {
    init(p) { this.p = p; this.eGui = document.createElement('button');
              this.eGui.innerText = 'Click'; this.eGui.onclick = () => alert(p.value); }
    getGui() { return this.eGui; }
    refresh() { return false; }
}
""")
gb.configure_column("action", cellRenderer=btn)
```

## Data return modes

The response object from `AgGrid()` contains:
- `.data` — a DataFrame after filtering/sorting/editing (depends on mode)
- `.selected_rows` — selected row DataFrame
- `.grid_state` — full grid state dict (column order, sorts, filters, etc.)

```python
from st_aggrid import DataReturnMode

response = AgGrid(
    df,
    gridOptions=grid_options,
    data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
)
```

Modes:
- `AS_INPUT` (default) — data unchanged
- `FILTERED` — only filtered rows
- `FILTERED_AND_SORTED` — filtered + user-sorted order
- `MINIMAL` — just selection + grid_state, no full data (fast for big grids)
- `CUSTOM` — run user JsCode to compute the return

## Update triggers — when the Streamlit rerun fires

```python
from st_aggrid import GridUpdateMode

AgGrid(
    df,
    update_mode=GridUpdateMode.MODEL_CHANGED,  # filter/sort/select/edit
    # other options:
    # GridUpdateMode.VALUE_CHANGED
    # GridUpdateMode.SELECTION_CHANGED
    # GridUpdateMode.FILTERING_CHANGED
    # GridUpdateMode.SORTING_CHANGED
    # GridUpdateMode.MANUAL       # rerun only on explicit action
    # GridUpdateMode.NO_UPDATE    # one-shot display
)
```

Fine-grained: pass `update_on=["cellValueChanged", ("columnResized", 300)]` to subscribe to specific AG Grid events. Tuples `(event, debounce_ms)` debounce chatty events.

## Theming

Streamlit's theme (font, primary color, text/background) is applied automatically to all AG Grid themes.

```python
AgGrid(df, theme="streamlit")   # follows Streamlit theme closely (balham base)
AgGrid(df, theme="quartz")      # AG Grid default
AgGrid(df, theme="alpine")
AgGrid(df, theme="balham")
AgGrid(df, theme="material")
```

Custom theme:

```python
from st_aggrid import StAggridTheme

theme = (
    StAggridTheme(base="quartz")
    .withParams(accentColor="#3b82f6", fontSize=13)
    .withParts("iconSetMaterial", "colorSchemeDark")
)
AgGrid(df, theme=theme)
```

## Pre-selected rows

```python
gb.configure_selection("multiple", use_checkbox=True, pre_selected_rows=[0, 3, 5])
```

## Tree data (enterprise)

Hierarchical rows via a path list per row. Requires `enable_enterprise_modules=True`.

```python
df = pd.DataFrame([
    {"path": ["Folder", "File.txt"], "size": 100},
    {"path": ["Folder", "Sub", "Inner.md"], "size": 50},
])

grid_options = {
    "columnDefs": [{"field": "size"}],
    "treeData": True,
    "groupDefaultExpanded": -1,
    "getDataPath": JsCode("function(data) { return data.path; }"),
    "autoGroupColumnDef": {"headerName": "Files", "minWidth": 280},
}

AgGrid(
    df,
    gridOptions=grid_options,
    allow_unsafe_jscode=True,
    enable_enterprise_modules=True,
)
```

## Enterprise flag

- `enable_enterprise_modules=True` — all enterprise features + watermark (no license).
- `enable_enterprise_modules="enterprise+AgCharts"` — include AG Charts (needed for sparklines).
- `enable_enterprise_modules=False` (default) — community only.

To remove the watermark, pass `license_key="..."` alongside `enable_enterprise_modules=True`.

## Row styling

```python
row_style = JsCode("""
function(params) {
    if (params.data && params.data.score > 90) {
        return {'background-color': 'rgba(34, 197, 94, 0.14)'};
    }
    return null;
}
""")

grid_options = gb.build()
grid_options["getRowStyle"] = row_style
```

Or column-level: `gb.configure_column("score", cellStyle=JsCode("..."))`.

## Rerun scope: `key=`

Always set `key=` if you have multiple grids on the same page. Without it, widget identity collisions cause silent state mixups.

```python
AgGrid(df, key="users_grid")
AgGrid(other_df, key="orders_grid")
```

## Common gotchas

1. **`JsCode` without `allow_unsafe_jscode=True`** — the JS string is passed literally as a string, not executed. Always pair them.
2. **NaN in numeric `gridOptions` fields** (e.g. `width=df[col].str.len().max()` on an empty column) — sanitized automatically by the Python side before CCv2 transport. Use pandas numeric guards upstream if you want a fallback value rather than auto-null.
3. **Enterprise watermark** — shown unless `license_key` is set. Harmless in dev.
4. **`getRowId`** — if not set, rows use positional row numbers. For stable selection across reruns with changing data, set a `getRowId`:
   ```python
   grid_options["getRowId"] = JsCode("function(p) { return p.data.id; }")
   ```
5. **Tree data needs `allow_unsafe_jscode=True`** — `getDataPath` is a JS function.
6. **Multiple grids on one page** — always pass distinct `key=` values.
7. **Editing in place** — `gb.configure_default_column(editable=True)` or per-column `editable=True`. Edited values come back via `response.data` when `update_mode` includes `VALUE_CHANGED`.
8. **Polars DataFrames work** — converted to pandas internally with no extra dep.

## Minimum viable reference

```python
import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode, DataReturnMode

df = pd.DataFrame({"name": ["Ada", "Alan"], "score": [91, 87]})

gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_selection("multiple", use_checkbox=True)
gb.configure_default_column(filter=True, sortable=True, floatingFilter=True)
gb.configure_column(
    "score",
    cellStyle=JsCode("p => p.value > 90 ? {color: 'green'} : null"),
)

response = AgGrid(
    df,
    gridOptions=gb.build(),
    height=360,
    theme="streamlit",
    update_mode=GridUpdateMode.MODEL_CHANGED,
    data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
    allow_unsafe_jscode=True,
    key="main_grid",
)

st.write("Selected:", response.selected_rows)
st.write("Visible after filters:", response.data)
```
