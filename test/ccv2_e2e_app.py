"""Streamlit fixture app for the CCv2 e2e tests.

Renders a small set of grids that exercise the most common code paths:
- DataFrame input
- JSON-string input with explicit columnDefs
- gridOptions-only (no data)
- Empty grid
- Sorted/edited grid that round-trips data back to Python
"""

import json

import pandas as pd
import streamlit as st

from st_aggrid import AgGrid, ColumnsAutoSizeMode, GridOptionsBuilder


st.title("CCv2 e2e tests")

# 1) DataFrame
df = pd.DataFrame({"names": ["alice", "bob", "charlie"], "ages": [25, 30, 35]})
AgGrid(df, key="grid_from_dataframe")

# 2) JSON string with explicit columnDefs
data = json.dumps(
    [
        {"name": "alice", "age": 25},
        {"name": "bob", "age": 30},
        {"name": "charlie", "age": 35},
    ]
)
grid_options = {
    "columnDefs": [
        {"headerName": "First Name", "field": "name", "width": 200},
        {
            "headerName": "Years",
            "field": "age",
            "width": 120,
            "type": ["numericColumn", "numberColumnFilter"],
        },
    ],
}
AgGrid(data, grid_options, key="grid_from_json")

# 3) gridOptions only, no data
go_only = {
    "columnDefs": [
        {"headerName": "names", "field": "name"},
        {"headerName": "ages", "field": "age"},
    ]
}
AgGrid(None, go_only, key="grid_options_only")

# 4) Empty grid
AgGrid(None, {}, key="empty_grid")

# 5) Round-trip: render a grid and echo its returned data so a test can
# verify Python sees the rows back through grid_response.
roundtrip_df = pd.DataFrame(
    {
        "name": ["bob", "alice", "charlie"],
        "score": [20, 10, 30],
    }
)
roundtrip_options = {
    "columnDefs": [
        {"headerName": "Name", "field": "name", "sortable": True},
        {
            "headerName": "Score",
            "field": "score",
            "sortable": True,
            "type": ["numericColumn", "numberColumnFilter"],
        },
    ],
}
result = AgGrid(roundtrip_df, roundtrip_options, key="roundtrip_grid")

st.html(
    f"""
    <h2>Roundtrip Data</h2>
    <pre data-testid='roundtrip-data'>{result.data.to_string()}</pre>
    """
)

# 6) Missing values: a DataFrame with None in both a text and a numeric
# column. pandas stores the missing numeric value as float NaN, which must be
# sanitized to None before serialization. Without that, the payload reaches
# the frontend with a bare `NaN` token and JSON.parse throws, so AG Grid never
# mounts. Regression guard for streamlit/streamlit#15435.
missing_values_df = pd.DataFrame(
    [
        {"text": "abc", "int": 0},
        {"text": None, "int": None},
        {"text": "def", "int": 35},
        {"text": None, "int": None},
    ]
)
AgGrid(missing_values_df, key="missing_values_grid")

# 7) update_on selection round-trip. Clicking a row with
# update_on=["selectionChanged"] must rerun Streamlit and deliver the clicked
# row to Python via selected_rows. Regression guard for the reported
# "update_on does not trigger reruns" issue.
selection_df = pd.DataFrame({"part": ["A", "B", "C"], "price": [1.0, 2.0, 3.0]})
gb_sel = GridOptionsBuilder.from_dataframe(selection_df)
gb_sel.configure_selection(selection_mode="single", use_checkbox=False)
selection_result = AgGrid(
    selection_df,
    gridOptions=gb_sel.build(),
    update_on=["selectionChanged"],
    key="update_on_selection_grid",
)
selected = selection_result.selected_rows
st.html(
    f"""
    <h2>update_on selection</h2>
    <pre data-testid='update-on-selection'>{
        "NONE" if selected is None or len(selected) == 0 else selected.to_string()
    }</pre>
    """
)

# 8) update_on cell-edit round-trip. Editing a cell with
# update_on=["cellValueChanged"] must rerun Streamlit and deliver the edited
# value to Python.
edit_df = pd.DataFrame({"label": ["x", "y", "z"], "qty": [1, 2, 3]})
edit_options = {
    "columnDefs": [
        {"headerName": "Label", "field": "label", "editable": True},
        {
            "headerName": "Qty",
            "field": "qty",
            "editable": True,
            "type": ["numericColumn", "numberColumnFilter"],
        },
    ],
}
edit_result = AgGrid(
    edit_df,
    edit_options,
    update_on=["cellValueChanged"],
    key="update_on_edit_grid",
)
st.html(
    f"""
    <h2>update_on edit</h2>
    <pre data-testid='update-on-edit'>{edit_result.data.to_string()}</pre>
    """
)

# 9) Manual update: with update_mode="MANUAL" the toolbar shows an update
# button that must send the current grid state (including local edits) back
# to Python when clicked. No update_on is passed on purpose: MANUAL is
# exclusive, so the button has to be the only return path all by itself.
manual_df = pd.DataFrame({"item": ["m1", "m2"], "val": [1, 2]})
manual_options = {
    "columnDefs": [
        {"headerName": "Item", "field": "item", "editable": True},
        {
            "headerName": "Val",
            "field": "val",
            "editable": True,
            "type": ["numericColumn", "numberColumnFilter"],
        },
    ],
}
manual_result = AgGrid(
    manual_df,
    manual_options,
    update_mode="MANUAL",
    show_toolbar=True,
    key="manual_update_grid",
)
st.html(
    f"""
    <h2>manual update</h2>
    <pre data-testid='manual-update-data'>{manual_result.data.to_string()}</pre>
    """
)

# 10) columns_auto_size_mode=FIT_CONTENTS on a wide from_dataframe grid. The
# columns must size to their content (a long header column far wider than a
# short one), not collapse to a uniform minWidth. Regression guard for the
# reported FIT_CONTENTS-collapses-every-column issue: from_dataframe injects
# autoSizeStrategy=fitGridWidth, which FIT_CONTENTS must override.
autosize_df = pd.DataFrame(
    {
        "Rev": ["A", "B", "C"],
        "Part Number": ["HW-178644", "HW-119379", "HW-110673"],
        "Qty Req (released jobs only)": [1593, 1200, 1040],
        "On Hand": [-36.4, -1090.0, 671.0],
        "Non-Netable": [0, 1, 2],
        "Review Status": ["ok", "ok", "no"],
        "Qty On Order": [10, 20, 30],
        "Standard Cost": [1.1, 2.2, 3.3],
        "Web Price Check": ["x", "y", "z"],
        "Extra A": [1, 2, 3],
        "Extra B": [4, 5, 6],
        "Extra C": [7, 8, 9],
    }
)
gb_autosize = GridOptionsBuilder.from_dataframe(autosize_df)
AgGrid(
    autosize_df,
    gridOptions=gb_autosize.build(),
    columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS,
    key="autosize_fit_contents_grid",
)

# 11) columns_state on mount. A saved column state has to be applied the first
# time the grid renders. It was only applied from componentDidUpdate when it
# differed from prevProps, so a state present from the very first render (the
# normal "restore the user's saved layout" case) was never applied at all.
# The state below reverses the column order and hides one column, so the
# rendered header row is unambiguous evidence either way.
state_df = pd.DataFrame(
    {"alpha": [1, 2], "bravo": [3, 4], "charlie": [5, 6]}
)
AgGrid(
    state_df,
    gridOptions={
        "columnDefs": [
            {"headerName": "alpha", "field": "alpha"},
            {"headerName": "bravo", "field": "bravo"},
            {"headerName": "charlie", "field": "charlie"},
        ]
    },
    columns_state=[
        {"colId": "charlie", "hide": False},
        {"colId": "alpha", "hide": False},
        {"colId": "bravo", "hide": True},
    ],
    key="columns_state_grid",
)

# 12) gridOptions change under use_json_serialization=True. A rerun that
# changes any gridOption pushed the whole cloned gridOptions into
# updateGridOptions, and under JSON serialization that object still carries
# rowData as a raw JSON *string*, so AG Grid was handed a string where it
# expects rows and the grid emptied out. Clicking the button changes rowHeight
# and nothing else; the rows have to survive it.
if st.button("bump json rerun", key="json_rerun_button"):
    st.session_state["json_rerun_nonce"] = (
        st.session_state.get("json_rerun_nonce", 0) + 1
    )
json_rerun_nonce = st.session_state.get("json_rerun_nonce", 0)
json_rerun_df = pd.DataFrame({"sku": ["js-1", "js-2", "js-3"], "qty": [1, 2, 3]})
AgGrid(
    json_rerun_df,
    {
        "columnDefs": [
            {"headerName": "SKU", "field": "sku"},
            {"headerName": "Qty", "field": "qty"},
        ],
        "rowHeight": 30 + json_rerun_nonce,
    },
    use_json_serialization=True,
    key="json_rerun_grid",
)

# 13) DataReturnMode.MINIMAL. MINIMAL routed to the TypeScript LegacyCollector,
# whose payload is {nodes, gridState, columnsState, ...}. MinimalResponse reads
# {data, selectedRows}, so .data came back None and .selected_rows came back
# empty no matter what the user did. Selecting a row must now deliver both.
minimal_df = pd.DataFrame({"tag": ["min-a", "min-b", "min-c"], "n": [1, 2, 3]})
gb_minimal = GridOptionsBuilder.from_dataframe(minimal_df)
gb_minimal.configure_selection(selection_mode="single", use_checkbox=False)
minimal_result = AgGrid(
    minimal_df,
    gridOptions=gb_minimal.build(),
    data_return_mode="MINIMAL",
    update_on=["selectionChanged"],
    key="minimal_return_grid",
)
minimal_data = minimal_result.data
minimal_selected = minimal_result.selected_rows
st.html(
    f"""
    <h2>minimal return</h2>
    <pre data-testid='minimal-data'>{
        "NONE" if minimal_data is None else json.dumps(minimal_data)
    }</pre>
    <pre data-testid='minimal-selected'>{
        "NONE" if not minimal_selected else json.dumps(minimal_selected)
    }</pre>
    """
)
