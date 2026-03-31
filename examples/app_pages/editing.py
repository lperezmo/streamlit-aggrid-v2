"""Cell editing — edit cells inline and get changes back in Python."""

import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode
from utils.data import get_sample_data

df = get_sample_data()

st.markdown(
    "Make columns editable and read the modified data back. "
    "Try changing a salary or toggling the remote column below."
)

# -- Editable grid -----------------------------------------------------------
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_default_column(editable=True)
gb.configure_column("Name", editable=False, pinned="left", width=160)
gb.configure_column("Salary", type=["numericColumn"], valueFormatter="'$' + x.toLocaleString()")
gb.configure_column("Rating", type=["numericColumn"], width=100)
gb.configure_column("Remote", width=100)
grid_options = gb.build()

with st.container(border=True):
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        height=350,
        key="editing_grid",
    )

# -- Show returned data side by side -----------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("Original data")
    st.dataframe(df, width="stretch", hide_index=True)

with col2:
    st.subheader("Grid data (after edits)")
    st.dataframe(grid_response.data, width="stretch", hide_index=True)

# -- Code snippet ------------------------------------------------------------
with st.expander("Code", icon=":material/code:"):
    st.code(
        '''gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_default_column(editable=True)
gb.configure_column("Name", editable=False)

response = AgGrid(
    df,
    gridOptions=gb.build(),
    data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
)
edited_df = response.data  # contains edits''',
        language="python",
    )
