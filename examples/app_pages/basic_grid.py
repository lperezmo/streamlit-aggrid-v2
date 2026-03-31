"""Basic grid — render a DataFrame with zero configuration."""

import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder
from utils.data import get_sample_data

df = get_sample_data()

st.markdown(
    "Drop a DataFrame into `AgGrid()` and get an interactive grid with sorting, "
    "resizing, and filtering — no configuration needed."
)

# -- Minimal example ---------------------------------------------------------
with st.container(border=True):
    st.caption("Minimal — just pass a DataFrame")
    AgGrid(df, key="basic_minimal", height=350)

st.space("medium")

# -- With GridOptionsBuilder ------------------------------------------------
st.subheader("With GridOptionsBuilder")
st.markdown("Use `GridOptionsBuilder` to customize column behavior without writing raw JSON.")

with st.container(border=True):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_column("Name", pinned="left", width=160)
    gb.configure_column("Salary", type=["numericColumn"], valueFormatter="'$' + x.toLocaleString()")
    gb.configure_column("Rating", type=["numericColumn"], width=100)
    gb.configure_column("Remote", width=100)
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=6)
    grid_options = gb.build()

    AgGrid(df, gridOptions=grid_options, key="basic_configured", height=350)

# -- Code snippet ------------------------------------------------------------
with st.expander("Code", icon=":material/code:"):
    st.code(
        '''from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd

df = pd.DataFrame({"Name": [...], "Salary": [...]})

# Option A: zero-config
AgGrid(df)

# Option B: with builder
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_column("Name", pinned="left", width=160)
gb.configure_column(
    "Salary",
    type=["numericColumn"],
    valueFormatter="'$' + x.toLocaleString()",
)
gb.configure_pagination(paginationPageSize=6)
AgGrid(df, gridOptions=gb.build())''',
        language="python",
    )
