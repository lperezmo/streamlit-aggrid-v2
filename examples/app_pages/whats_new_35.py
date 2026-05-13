"""What's new in AG Grid v35 — highlights and runnable examples."""

import pandas as pd
import streamlit as st

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode


st.markdown(
    "AG Grid v35 (released March 2026, current patch **35.3.0**) ships a batch of "
    "new features on top of v34. Below are the highlights and two runnable demos."
)

st.markdown(
    """
| Version  | Highlights |
| -------- | ---------- |
| **35.0** | Formulas, Row Group Dragging, Absolute Sorting, Column Selection, Filter/Export Overlays |
| **35.1** | Formula Editor (autocomplete + click-to-fill), Named Date Ranges, BigInt cell type, Theme Builder Imports, Excel Export Data Protection |
| **35.2** | Aggregation Editing, Compact Group Column, Deferred Tool Panel Updates, Async Rich Select Editor, Accessibility |
| **35.3** | Quick Access Toolbar, Cell Notes, Server-Side Grand Total Row |
"""
)

st.caption(
    "Most of these are AG Grid Enterprise features. They render with an evaluation "
    "watermark unless you supply `license_key=...`."
)

st.space("medium")

# -- Demo picker -------------------------------------------------------------
demo = st.radio(
    "Demo",
    options=["Formulas (the functions thingy)", "Column selection (35.0)"],
    horizontal=True,
)

st.space("small")

# =============================================================================
# DEMO 1 - Formulas
# =============================================================================
if demo == "Formulas (the functions thingy)":
    st.info(
        "Double-click the **Total** cells and type a formula like `=A2*B2` (or "
        "`=SUM(C2:C5)` in the **Running** column). Formula cells autocomplete "
        "function names and show ranges as you type. New in v35.0; v35.1 added "
        "the click-to-pick-cells editor."
    )

    invoice = pd.DataFrame(
        {
            "rid": [1, 2, 3, 4, 5],
            "Item": ["Widget", "Gadget", "Sprocket", "Cog", "Lever"],
            "Price": [12.50, 4.25, 9.75, 18.00, 3.10],
            "Quantity": [3, 8, 5, 2, 10],
            "Total": [None, None, None, None, None],
            "Running": [None, None, None, None, None],
        }
    )

    grid_options = {
        # Stable IDs are required by the formula engine.
        "getRowId": JsCode("function(params) { return String(params.data.rid); }"),
        "columnDefs": [
            {"field": "Item", "width": 130, "editable": False},
            {
                "field": "Price",
                "type": ["numericColumn"],
                "valueFormatter": "'$' + Number(x).toFixed(2)",
                "editable": True,
            },
            {
                "field": "Quantity",
                "type": ["numericColumn"],
                "editable": True,
            },
            {
                "field": "Total",
                "type": ["numericColumn"],
                "valueFormatter": "x != null ? '$' + Number(x).toFixed(2) : ''",
                "allowFormula": True,
                "editable": True,
            },
            {
                "field": "Running",
                "type": ["numericColumn"],
                "valueFormatter": "x != null ? '$' + Number(x).toFixed(2) : ''",
                "allowFormula": True,
                "editable": True,
            },
        ],
        # AG Grid recommends pairing formulas with the fill handle so users can
        # drag-fill a formula across rows the way they would in a spreadsheet.
        "cellSelection": {"handle": {"mode": "fill"}},
        "defaultColDef": {"resizable": True, "sortable": True},
    }

    with st.container(border=True):
        AgGrid(
            invoice,
            gridOptions=grid_options,
            enable_enterprise_modules=True,
            allow_unsafe_jscode=True,
            height=320,
            key="whats_new_formulas",
        )

    st.caption(
        "Try: double-click cell `D2` (Total / Widget row) and type `=B2*C2`. Then "
        "select the cell and drag the fill handle in the bottom-right corner down "
        "to row 6 to fill the rest. For `Running`, try `=SUM(D2:D2)` in `E2` and "
        "fill down."
    )

# =============================================================================
# DEMO 2 - Column selection
# =============================================================================
elif demo == "Column selection (35.0)":
    st.info(
        "Click on a column header (the column body, not the menu) to select the "
        "whole column. Shift+click extends the selection, Ctrl/Cmd+click toggles. "
        "The status bar at the bottom aggregates whatever is selected."
    )

    revenue = pd.DataFrame(
        {
            "Region": ["North", "South", "East", "West", "Central"],
            "Jan": [12000, 9800, 14500, 8200, 10100],
            "Feb": [13200, 10100, 14900, 8800, 11000],
            "Mar": [12800, 11400, 15600, 9100, 11800],
            "Apr": [14100, 12300, 16200, 9700, 12400],
        }
    )

    gb = GridOptionsBuilder.from_dataframe(revenue)
    gb.configure_column("Region", pinned="left", width=120)
    for col in ("Jan", "Feb", "Mar", "Apr"):
        gb.configure_column(
            col,
            type=["numericColumn"],
            valueFormatter="'$' + Number(x).toLocaleString()",
        )
    grid_options = gb.build()

    grid_options["cellSelection"] = {
        "handle": {"mode": "range"},
        "columnSelection": "multiple",
    }
    grid_options["statusBar"] = {
        "statusPanels": [
            {"statusPanel": "agSelectedRowCountComponent", "align": "left"},
            {"statusPanel": "agAggregationComponent", "align": "right"},
        ]
    }

    with st.container(border=True):
        AgGrid(
            revenue,
            gridOptions=grid_options,
            enable_enterprise_modules=True,
            allow_unsafe_jscode=True,
            height=320,
            key="whats_new_column_select",
        )

    st.caption(
        "Click `Feb` then shift-click `Apr` to select Feb-Apr. The status bar on "
        "the right shows sum/avg/count for the highlighted cells."
    )


# -- Code snippet ------------------------------------------------------------
with st.expander("Code", icon=":material/code:"):
    if demo == "Formulas (the functions thingy)":
        st.code(
            """grid_options = {
    "getRowId": "params.data.rid",  # required for formulas
    "columnDefs": [
        {"field": "Price",    "type": ["numericColumn"], "editable": True},
        {"field": "Quantity", "type": ["numericColumn"], "editable": True},
        # allowFormula = users can type =B2*C2 in this cell.
        {"field": "Total",    "allowFormula": True, "editable": True},
        {"field": "Running",  "allowFormula": True, "editable": True},
    ],
    "cellSelection": {"handle": {"mode": "fill"}},  # spreadsheet-style fill
}

AgGrid(
    df,
    gridOptions=grid_options,
    enable_enterprise_modules=True,
    allow_unsafe_jscode=True,
)""",
            language="python",
        )
    else:
        st.code(
            """grid_options["cellSelection"] = {
    "handle": {"mode": "range"},
    "columnSelection": "multiple",  # new in 35.0
}
grid_options["statusBar"] = {
    "statusPanels": [
        {"statusPanel": "agAggregationComponent", "align": "right"},
    ]
}

AgGrid(df, gridOptions=grid_options, enable_enterprise_modules=True)""",
            language="python",
        )
