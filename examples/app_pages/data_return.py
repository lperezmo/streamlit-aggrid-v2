"""Data return modes — control what data comes back to Python."""

import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode
from utils.data import get_sample_data

df = get_sample_data()

st.markdown(
    "`DataReturnMode` controls which rows are sent back to Python after "
    "the user interacts with the grid."
)

# -- Mode picker -------------------------------------------------------------
mode_label = st.segmented_control(
    "Data return mode",
    options=["As input", "Filtered", "Filtered & sorted", "Minimal"],
    default="Filtered & sorted",
)

mode_map = {
    "As input": DataReturnMode.AS_INPUT,
    "Filtered": DataReturnMode.FILTERED,
    "Filtered & sorted": DataReturnMode.FILTERED_AND_SORTED,
    "Minimal": DataReturnMode.MINIMAL,
}
selected_mode = mode_map[mode_label]

st.info(
    {
        "As input": "Returns the original DataFrame regardless of grid state.",
        "Filtered": "Returns only rows that pass the active filters (original sort order).",
        "Filtered & sorted": "Returns rows matching filters, in the grid's current sort order.",
        "Minimal": "Returns only the grid's internal state — lightest payload.",
    }[mode_label],
    icon=":material/info:",
)

# -- Grid setup with filters so modes are visible ----------------------------
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_default_column(filter=True, sortable=True, floatingFilter=True)
gb.configure_column("Name", pinned="left", width=160)
gb.configure_column("Salary", type=["numericColumn"], valueFormatter="'$' + x.toLocaleString()")
gb.configure_column("Department", filter="agTextColumnFilter")
gb.configure_column("Rating", type=["numericColumn"], width=100)
gb.configure_column("Remote", width=100)
grid_options = gb.build()

with st.container(border=True):
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        data_return_mode=selected_mode,
        height=350,
        key="data_return_grid",
    )

# -- Results -----------------------------------------------------------------
st.subheader("Returned data")
st.caption(
    f"{len(grid_response.data) if grid_response.data is not None else 0} rows · mode: `{mode_label}`"
)
st.dataframe(grid_response.data, width="stretch", hide_index=True)

# -- Code snippet ------------------------------------------------------------
with st.expander("Code", icon=":material/code:"):
    st.code(
        '''from st_aggrid import AgGrid, DataReturnMode

response = AgGrid(
    df,
    gridOptions=grid_options,
    data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
)
# response.data contains only visible rows in display order''',
        language="python",
    )
