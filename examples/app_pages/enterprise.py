"""Enterprise Features — row grouping, pivot, status bar, side bar, and more."""

import pandas as pd
import numpy as np
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder
from utils.data import get_sample_data

df = get_sample_data()

st.markdown(
    "AG Grid Enterprise unlocks powerful features like row grouping, pivot tables, "
    "side panels, status bars, Excel export, and cell selection. "
    "These work with `enable_enterprise_modules=True` (watermark shown without a license key)."
)

# -- Feature picker -----------------------------------------------------------
feature = st.radio(
    "Enterprise feature",
    options=[
        "Row grouping",
        "Pivot mode",
        "Status bar",
        "Side bar & tool panels",
        "Excel export",
        "Cell selection",
        "Sparklines",
    ],
    horizontal=True,
)

st.space("small")

# -- Expand dataset for more interesting demos --------------------------------
@st.cache_data
def get_expanded_data():
    """Larger dataset for enterprise feature demos."""
    rng = np.random.default_rng(42)
    n = 60
    departments = ["Engineering", "Sales", "Marketing", "Finance", "HR", "Operations"]
    regions = ["North", "South", "East", "West"]
    names = [f"Employee {i+1}" for i in range(n)]

    monthly_cols = {}
    for m in ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]:
        monthly_cols[m] = rng.integers(3000, 15000, size=n).tolist()

    return pd.DataFrame({
        "Name": names,
        "Department": rng.choice(departments, n).tolist(),
        "Region": rng.choice(regions, n).tolist(),
        "Salary": rng.integers(55000, 185000, size=n).tolist(),
        "Years": rng.integers(1, 20, size=n).tolist(),
        "Rating": (rng.random(n) * 2 + 3).round(1).tolist(),
        "Remote": rng.choice([True, False], n).tolist(),
        **monthly_cols,
    })

big_df = get_expanded_data()

# =============================================================================
# FEATURE IMPLEMENTATIONS
# =============================================================================

if feature == "Row grouping":
    st.info(
        "Group rows by **Department** and **Region**. "
        "Expand groups to see individual rows. Salary is aggregated with `sum`."
    )
    gb = GridOptionsBuilder.from_dataframe(big_df[["Name", "Department", "Region", "Salary", "Years", "Rating"]])
    gb.configure_column("Department", rowGroup=True, hide=True)
    gb.configure_column("Region", rowGroup=True, hide=True)
    gb.configure_column("Salary", aggFunc="sum", valueFormatter="'$' + x.toLocaleString()")
    gb.configure_column("Rating", aggFunc="avg")
    gb.configure_column("Years", aggFunc="avg")

    grid_options = gb.build()
    grid_options["groupDefaultExpanded"] = 1
    grid_options["rowGroupPanelShow"] = "always"
    grid_options["autoGroupColumnDef"] = {
        "headerName": "Group",
        "minWidth": 250,
    }

    with st.container(border=True):
        AgGrid(
            big_df[["Name", "Department", "Region", "Salary", "Years", "Rating"]],
            gridOptions=grid_options,
            enable_enterprise_modules=True,
            height=480,
            key="grouping_grid",
        )

elif feature == "Pivot mode":
    st.info(
        "Pivot **Department** as columns, group by **Region**, "
        "and aggregate **Salary** by sum. Drag columns in the panel to reconfigure."
    )
    pivot_df = big_df[["Name", "Department", "Region", "Salary", "Years"]].copy()
    gb = GridOptionsBuilder.from_dataframe(pivot_df)
    gb.configure_column("Region", rowGroup=True, hide=True)
    gb.configure_column("Department", pivot=True, hide=True)
    gb.configure_column("Salary", aggFunc="sum", valueFormatter="'$' + x.toLocaleString()")
    gb.configure_column("Years", aggFunc="avg")
    gb.configure_column("Name", hide=True)

    grid_options = gb.build()
    grid_options["pivotMode"] = True
    grid_options["groupDefaultExpanded"] = -1
    grid_options["autoGroupColumnDef"] = {"minWidth": 150}

    with st.container(border=True):
        AgGrid(
            pivot_df,
            gridOptions=grid_options,
            enable_enterprise_modules=True,
            height=480,
            key="pivot_grid",
        )

elif feature == "Status bar":
    st.info(
        "The status bar at the bottom shows total rows, filtered count, "
        "and selected count. Try selecting rows to see it update."
    )
    gb = GridOptionsBuilder.from_dataframe(big_df[["Name", "Department", "Region", "Salary", "Years", "Rating"]])
    gb.configure_column("Name", width=160)
    gb.configure_column("Salary", type=["numericColumn"], valueFormatter="'$' + x.toLocaleString()")
    gb.configure_default_column(filter=True, floatingFilter=True)
    gb.configure_selection("multiple", use_checkbox=True)

    grid_options = gb.build()
    grid_options["statusBar"] = {
        "statusPanels": [
            {"statusPanel": "agTotalAndFilteredRowCountComponent", "align": "left"},
            {"statusPanel": "agSelectedRowCountComponent", "align": "center"},
            {"statusPanel": "agAggregationComponent", "align": "right"},
        ]
    }

    with st.container(border=True):
        AgGrid(
            big_df[["Name", "Department", "Region", "Salary", "Years", "Rating"]],
            gridOptions=grid_options,
            enable_enterprise_modules=True,
            height=480,
            key="statusbar_grid",
        )

elif feature == "Side bar & tool panels":
    st.info(
        "The side bar provides **Columns** and **Filters** tool panels. "
        "Use them to show/hide columns, reorder, or build advanced filters."
    )
    gb = GridOptionsBuilder.from_dataframe(big_df[["Name", "Department", "Region", "Salary", "Years", "Rating", "Remote"]])
    gb.configure_column("Name", width=160)
    gb.configure_column("Salary", type=["numericColumn"], valueFormatter="'$' + x.toLocaleString()")
    gb.configure_default_column(filter=True, enableRowGroup=True, enableValue=True, enablePivot=True)

    grid_options = gb.build()
    grid_options["sideBar"] = True

    with st.container(border=True):
        AgGrid(
            big_df[["Name", "Department", "Region", "Salary", "Years", "Rating", "Remote"]],
            gridOptions=grid_options,
            enable_enterprise_modules=True,
            height=480,
            key="sidebar_grid",
        )

elif feature == "Excel export":
    st.info(
        "Click the **Export** button to download the grid data as an Excel file. "
        "Enterprise enables `.xlsx` export (community only supports CSV)."
    )
    gb = GridOptionsBuilder.from_dataframe(big_df[["Name", "Department", "Region", "Salary", "Years", "Rating"]])
    gb.configure_column("Name", width=160)
    gb.configure_column("Salary", type=["numericColumn"], valueFormatter="'$' + x.toLocaleString()")

    grid_options = gb.build()

    col1, col2 = st.columns([3, 1])
    with col2:
        export_btn = st.button("Export to Excel", type="primary", use_container_width=True)

    with st.container(border=True):
        result = AgGrid(
            big_df[["Name", "Department", "Region", "Salary", "Years", "Rating"]],
            gridOptions=grid_options,
            enable_enterprise_modules=True,
            height=420,
            key="excel_grid",
        )

    st.caption(
        "Programmatic export uses `api.exportDataAsExcel()`. "
        "The grid's built-in context menu also offers Excel export."
    )

elif feature == "Cell selection":
    st.info(
        "Click and drag to select a range of cells. "
        "The status bar shows aggregations (sum, avg, count) for the selection."
    )
    gb = GridOptionsBuilder.from_dataframe(big_df[["Name", "Department", "Salary", "Years", "Rating"]])
    gb.configure_column("Name", width=160)
    gb.configure_column("Salary", type=["numericColumn"], valueFormatter="'$' + x.toLocaleString()")
    gb.configure_column("Years", type=["numericColumn"])
    gb.configure_column("Rating", type=["numericColumn"])

    grid_options = gb.build()
    grid_options["cellSelection"] = True
    grid_options["statusBar"] = {
        "statusPanels": [
            {"statusPanel": "agAggregationComponent", "align": "right"},
        ]
    }

    with st.container(border=True):
        AgGrid(
            big_df[["Name", "Department", "Salary", "Years", "Rating"]],
            gridOptions=grid_options,
            enable_enterprise_modules=True,
            height=480,
            key="cellselection_grid",
        )

elif feature == "Sparklines":
    st.info(
        "Sparklines render mini charts inside cells. Here each row shows a 6-month "
        "revenue trend as an inline line chart."
    )

    # Build sparkline data column
    spark_df = big_df[["Name", "Department", "Region", "Jan", "Feb", "Mar", "Apr", "May", "Jun"]].copy()
    spark_df["Trend"] = spark_df[["Jan", "Feb", "Mar", "Apr", "May", "Jun"]].values.tolist()

    gb = GridOptionsBuilder.from_dataframe(spark_df[["Name", "Department", "Region", "Trend"]])
    gb.configure_column("Name", width=160)
    gb.configure_column("Department", width=130)
    gb.configure_column("Region", width=100)
    gb.configure_column(
        "Trend",
        cellRenderer="agSparklineCellRenderer",
        cellRendererParams={
            "sparklineOptions": {
                "type": "line",
                "line": {"stroke": "#3b82f6", "strokeWidth": 2},
                "highlightStyle": {"size": 4, "fill": "#3b82f6"},
                "padding": {"top": 8, "bottom": 8},
            }
        },
        width=250,
        sortable=False,
        filter=False,
    )

    grid_options = gb.build()

    with st.container(border=True):
        AgGrid(
            spark_df[["Name", "Department", "Region", "Trend"]],
            gridOptions=grid_options,
            enable_enterprise_modules="enterprise+AgCharts",
            height=480,
            key="sparkline_grid",
        )

# -- Code snippet (feature-specific) -----------------------------------------
with st.expander("Code", icon=":material/code:"):
    if feature == "Row grouping":
        st.code(
            '''gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_column("Department", rowGroup=True, hide=True)
gb.configure_column("Region", rowGroup=True, hide=True)
gb.configure_column("Salary", aggFunc="sum")

grid_options = gb.build()
grid_options["groupDefaultExpanded"] = 1
grid_options["rowGroupPanelShow"] = "always"

AgGrid(df, gridOptions=grid_options, enable_enterprise_modules=True)''',
            language="python",
        )
    elif feature == "Pivot mode":
        st.code(
            '''gb.configure_column("Region", rowGroup=True, hide=True)
gb.configure_column("Department", pivot=True, hide=True)
gb.configure_column("Salary", aggFunc="sum")

grid_options = gb.build()
grid_options["pivotMode"] = True

AgGrid(df, gridOptions=grid_options, enable_enterprise_modules=True)''',
            language="python",
        )
    elif feature == "Status bar":
        st.code(
            '''grid_options["statusBar"] = {
    "statusPanels": [
        {"statusPanel": "agTotalAndFilteredRowCountComponent", "align": "left"},
        {"statusPanel": "agSelectedRowCountComponent", "align": "center"},
        {"statusPanel": "agAggregationComponent", "align": "right"},
    ]
}
AgGrid(df, gridOptions=grid_options, enable_enterprise_modules=True)''',
            language="python",
        )
    elif feature == "Side bar & tool panels":
        st.code(
            '''grid_options["sideBar"] = True  # enables Columns + Filters panels
# Or customize:
# grid_options["sideBar"] = {
#     "toolPanels": ["columns", "filters"],
#     "position": "right",
# }
AgGrid(df, gridOptions=grid_options, enable_enterprise_modules=True)''',
            language="python",
        )
    elif feature == "Excel export":
        st.code(
            '''# Enterprise enables .xlsx export (community = CSV only)
# Export via context menu (right-click) or API:
# api.exportDataAsExcel()

AgGrid(df, gridOptions=grid_options, enable_enterprise_modules=True)''',
            language="python",
        )
    elif feature == "Cell selection":
        st.code(
            '''grid_options["cellSelection"] = True
grid_options["statusBar"] = {
    "statusPanels": [
        {"statusPanel": "agAggregationComponent", "align": "right"},
    ]
}
AgGrid(df, gridOptions=grid_options, enable_enterprise_modules=True)''',
            language="python",
        )
    elif feature == "Sparklines":
        st.code(
            '''# Data column must contain lists of numbers
df["Trend"] = df[["Jan","Feb","Mar","Apr","May","Jun"]].values.tolist()

gb.configure_column("Trend",
    cellRenderer="agSparklineCellRenderer",
    cellRendererParams={
        "sparklineOptions": {
            "type": "line",
            "line": {"stroke": "#3b82f6", "strokeWidth": 2},
        }
    },
)
AgGrid(df, gridOptions=grid_options,
       enable_enterprise_modules="enterprise+AgCharts")''',
            language="python",
        )
