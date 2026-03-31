"""Floating Filters — inline filter inputs under each column header."""

import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder
from utils.data import get_sample_data

df = get_sample_data()

st.markdown(
    "Floating filters render a compact filter input directly below each column header. "
    "Type in any column's filter box to see results update in real time."
)

# -- Config ------------------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    suppress_button = st.toggle(
        "Hide floating filter button (cleaner look)", value=True
    )
with col2:
    filter_height = st.slider("Floating filter row height (px)", 20, 60, 35)

gb = GridOptionsBuilder.from_dataframe(df)

# Enable floating filters on all columns
gb.configure_default_column(
    filter=True,
    floatingFilter=True,
    suppressFloatingFilterButton=suppress_button,
)

# Fine-tune specific columns with appropriate filter types
gb.configure_column("Name", filter="agTextColumnFilter", minWidth=160)
gb.configure_column("Department", filter="agTextColumnFilter")
gb.configure_column("Title", filter="agTextColumnFilter")
gb.configure_column(
    "Salary",
    filter="agNumberColumnFilter",
    type=["numericColumn"],
    valueFormatter="'$' + x.toLocaleString()",
)
gb.configure_column("Years", filter="agNumberColumnFilter", type=["numericColumn"])
gb.configure_column("Rating", filter="agNumberColumnFilter", type=["numericColumn"])
gb.configure_column("Remote", filter="agTextColumnFilter")

grid_options = gb.build()
grid_options["floatingFiltersHeight"] = filter_height

# -- Render ------------------------------------------------------------------
st.space("small")
with st.container(border=True):
    result = AgGrid(
        df,
        gridOptions=grid_options,
        height=420,
        key="floating_filter_grid",
    )

st.caption(
    "Try typing in the filter boxes: text columns do contains-matching, "
    "number columns support operators like `> 100000` or `< 5`."
)

# -- Show filtered data ------------------------------------------------------
if result.data is not None:
    filtered = result.data
    st.info(f"Showing **{len(filtered)}** of {len(df)} rows after filtering")

# -- Code --------------------------------------------------------------------
with st.expander("Code", icon=":material/code:"):
    st.code(
        '''from st_aggrid import AgGrid, GridOptionsBuilder

gb = GridOptionsBuilder.from_dataframe(df)

# Enable floating filters globally
gb.configure_default_column(
    filter=True,
    floatingFilter=True,
    suppressFloatingFilterButton=True,  # cleaner look
)

# Use specific filter types per column
gb.configure_column("Salary", filter="agNumberColumnFilter")
gb.configure_column("Name", filter="agTextColumnFilter")

grid_options = gb.build()
grid_options["floatingFiltersHeight"] = 35  # pixel height

AgGrid(df, gridOptions=grid_options)''',
        language="python",
    )
