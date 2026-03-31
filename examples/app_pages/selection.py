"""Row selection — single and multi-row selection with checkboxes."""

import streamlit as st
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder
from utils.data import get_sample_data

df = get_sample_data()

st.markdown(
    "Select rows by clicking or with checkboxes. "
    "Selected rows are available in `response.selected_rows`."
)

# -- Selection mode picker ---------------------------------------------------
mode = st.segmented_control(
    "Selection mode",
    options=["Single", "Multiple"],
    default="Multiple",
)

use_checkbox = st.toggle("Show checkboxes", value=True)

# -- Build grid options ------------------------------------------------------
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_column("Name", pinned="left", width=160)
gb.configure_column("Salary", type=["numericColumn"], valueFormatter="'$' + x.toLocaleString()")
gb.configure_column("Rating", type=["numericColumn"], width=100)
gb.configure_column("Remote", width=100)
gb.configure_selection(
    selection_mode="single" if mode == "Single" else "multiple",
    use_checkbox=use_checkbox,
)
grid_options = gb.build()

# -- Render grid -------------------------------------------------------------
with st.container(border=True):
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        height=350,
        key="selection_grid",
    )

# -- Show selected rows ------------------------------------------------------
selected = grid_response.selected_rows
if selected is not None and len(selected) > 0:
    selected_df = pd.DataFrame(selected)
    st.subheader(f"Selected rows ({len(selected_df)})")
    st.dataframe(selected_df, width="stretch", hide_index=True)
else:
    st.info("Click a row (or use checkboxes) to select it.", icon=":material/touch_app:")

# -- Code snippet ------------------------------------------------------------
with st.expander("Code", icon=":material/code:"):
    st.code(
        '''gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_selection("multiple", use_checkbox=True)

response = AgGrid(df, gridOptions=gb.build())
selected = response.selected_rows  # list of dicts''',
        language="python",
    )
