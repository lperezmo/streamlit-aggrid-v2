"""Column config — advanced column definitions with GridOptionsBuilder."""

import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder
from utils.data import get_sample_data

df = get_sample_data()

st.markdown(
    "Use `GridOptionsBuilder` or raw `gridOptions` dicts to configure "
    "column widths, pinning, formatting, and cell renderers."
)

# -- Grid with rich column config --------------------------------------------
gb = GridOptionsBuilder.from_dataframe(df)

gb.configure_column("Name", pinned="left", width=160)
gb.configure_column(
    "Department",
    width=130,
)
gb.configure_column("Title", width=170)
gb.configure_column(
    "Salary",
    type=["numericColumn"],
    valueFormatter="'$' + x.toLocaleString()",
    width=120,
)
gb.configure_column(
    "Years",
    type=["numericColumn"],
    width=90,
    headerName="Exp (yrs)",
)
gb.configure_column(
    "Rating",
    type=["numericColumn"],
    width=100,
)
gb.configure_column("Remote", width=100)

gb.configure_grid_options(
    autoSizeStrategy={"type": "fitGridWidth"},
)

grid_options = gb.build()

with st.container(border=True):
    AgGrid(
        df,
        gridOptions=grid_options,
        height=380,
        key="column_config_grid",
    )

st.space("medium")

# -- Raw gridOptions dict example -------------------------------------------
st.subheader("Using raw gridOptions")
st.markdown(
    "You can skip `GridOptionsBuilder` entirely and pass a plain dict. "
    "This gives full access to the AG Grid API."
)

raw_options = {
    "columnDefs": [
        {"field": "Name", "pinned": "left", "width": 160},
        {"field": "Department", "width": 130},
        {"field": "Title", "width": 170},
        {
            "field": "Salary",
            "type": ["numericColumn"],
            "valueFormatter": {"function": "'$' + params.value.toLocaleString()"},
            "width": 120,
        },
        {"field": "Years", "headerName": "Exp (yrs)", "width": 90},
        {"field": "Rating", "width": 100},
        {"field": "Remote", "width": 100},
    ],
    "defaultColDef": {"sortable": True, "filter": True, "resizable": True},
}

with st.container(border=True):
    AgGrid(df, gridOptions=raw_options, height=300, key="raw_options_grid")

# -- Code snippet ------------------------------------------------------------
with st.expander("Code", icon=":material/code:"):
    st.code(
        '''# Using GridOptionsBuilder
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_column("Name", pinned="left", width=160)
gb.configure_column(
    "Salary",
    type=["numericColumn"],
    valueFormatter="'$' + x.toLocaleString()",
)
AgGrid(df, gridOptions=gb.build())

# Using raw dict
options = {
    "columnDefs": [
        {"field": "Name", "pinned": "left"},
        {"field": "Salary", "type": ["numericColumn"]},
    ],
    "defaultColDef": {"sortable": True, "filter": True},
}
AgGrid(df, gridOptions=options)''',
        language="python",
    )
