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

from st_aggrid import AgGrid


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
