"""st-aggrid example app — basic grid with editing and selection."""

import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode

st.set_page_config(page_title="st-aggrid demo", layout="wide")
st.title("st-aggrid demo")

# ---------- sample data ----------
@st.cache_data
def load_data():
    return pd.DataFrame(
        {
            "Name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
            "Age": [28, 34, 45, 23, 31],
            "City": ["New York", "London", "Paris", "Tokyo", "Sydney"],
            "Score": [92.5, 87.3, 95.1, 78.9, 88.6],
            "Active": [True, False, True, True, False],
        }
    )

df = load_data()

# ---------- grid options ----------
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_default_column(editable=True)
gb.configure_selection("multiple", use_checkbox=True)
grid_options = gb.build()

# ---------- render grid ----------
grid_response = AgGrid(
    df,
    gridOptions=grid_options,
    data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
    height=300,
    key="demo_grid",
)

# ---------- show returned data ----------
st.subheader("Returned data")
st.dataframe(grid_response.data)

if grid_response.selected_rows is not None and len(grid_response.selected_rows) > 0:
    st.subheader("Selected rows")
    st.dataframe(pd.DataFrame(grid_response.selected_rows))
