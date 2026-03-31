"""Filtering & sorting — column filters and sort indicators."""

import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder
from utils.data import get_sample_data

df = get_sample_data()

st.markdown(
    "AG Grid includes built-in column filters and multi-column sorting. "
    "Click a column header to sort, or use the filter icon to filter."
)

# -- Grid with filters enabled -----------------------------------------------
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_default_column(filter=True, sortable=True, floatingFilter=True)
gb.configure_column("Name", pinned="left", width=160, filter="agTextColumnFilter")
gb.configure_column(
    "Salary",
    type=["numericColumn"],
    valueFormatter="'$' + x.toLocaleString()",
    filter="agNumberColumnFilter",
)
gb.configure_column("Department", filter="agTextColumnFilter")
gb.configure_column("Rating", type=["numericColumn"], filter="agNumberColumnFilter", width=100)
gb.configure_column("Years", type=["numericColumn"], filter="agNumberColumnFilter", width=100)
gb.configure_column("Remote", width=100)
grid_options = gb.build()

with st.container(border=True):
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        height=420,
        key="filter_grid",
    )

# -- Show returned data ------------------------------------------------------
st.subheader("Returned data (filtered & sorted)")
st.caption(f"{len(grid_response.data)} rows returned")
st.dataframe(grid_response.data, width="stretch", hide_index=True)

# -- Code snippet ------------------------------------------------------------
with st.expander("Code", icon=":material/code:"):
    st.code(
        '''gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_default_column(
    filter=True,
    sortable=True,
    floatingFilter=True,
)
gb.configure_column("Name", filter="agTextColumnFilter")
gb.configure_column("Salary", filter="agNumberColumnFilter")

response = AgGrid(df, gridOptions=gb.build())
filtered_df = response.data  # only visible rows''',
        language="python",
    )
