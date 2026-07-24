"""Streamlit fixture app for coverage ported off the deleted CCv1 test files.

Kept separate from ``ccv2_e2e_app.py`` on purpose: that page already carries a
dozen grids, and every extra grid lengthens the rerun that the round-trip
assertions there are waiting on. These grids only need a browser because the
behavior they cover is browser-side (a JsCode collector, AG Grid's own
selection machinery, cells holding nested objects).
"""

import pandas as pd
import streamlit as st

from st_aggrid import AgGrid, JsCode


st.title("CCv2 ported legacy coverage")

# 1) DataReturnMode.CUSTOM. The user's JsCode runs inside the grid and its
# return value becomes the whole response, so this is only observable in a
# browser. Ported from the deleted test/grid_return.py make_grid2(), minus its
# 30,000 row dummy dataset, which the assertions never used.
custom_df = pd.DataFrame(
    {"first": ["a", "b"], "second": [1, 2], "third": [True, False]}
)
custom_return = JsCode("""
function collect_return({streamlitRerunEventTriggerName, eventData}){
    let api = eventData.api;
    let colNames = api.getAllDisplayedColumns().map((c) => c.colDef.field);
    return {columns: colNames, trigger: streamlitRerunEventTriggerName};
}
""")
custom_result = AgGrid(
    custom_df,
    gridOptions={
        "columnDefs": [
            {"headerName": "first", "field": "first", "sortable": True},
            {"headerName": "second", "field": "second", "sortable": True},
            {"headerName": "third", "field": "third", "sortable": True},
        ]
    },
    data_return_mode="CUSTOM",
    update_on=["sortChanged"],
    custom_jscode_for_grid_return=custom_return,
    key="custom_return_grid",
)
st.html(
    f"""
    <h2>custom return</h2>
    <pre data-testid='custom-return'>{
        "NONE" if custom_result.raw_data is None else str(custom_result)
    }</pre>
    """
)

# 2) Checkbox multi-selection, including the header select-all checkbox.
# Ported from the deleted test/test_grid_return.py selection tests.
selection_df = pd.DataFrame(
    {"id": [1, 2, 3, 4], "name": ["w", "x", "y", "z"], "value": [10, 20, 30, 40]}
)
selection_result = AgGrid(
    selection_df,
    gridOptions={
        "columnDefs": [
            {
                "headerName": "ID",
                "field": "id",
                "checkboxSelection": True,
                "headerCheckboxSelection": True,
            },
            {"headerName": "Name", "field": "name"},
            {"headerName": "Value", "field": "value"},
        ],
        "rowSelection": {"mode": "multiRow", "checkboxes": True, "headerCheckbox": True},
    },
    update_on=["selectionChanged"],
    key="checkbox_selection_grid",
)
selected = selection_result.selected_data
st.html(
    f"""
    <h2>checkbox selection</h2>
    <pre data-testid='checkbox-selected-count'>{
        0 if selected is None else len(selected)
    }</pre>
    <pre data-testid='checkbox-selected-names'>{
        "NONE" if selected is None or selected.empty else ",".join(selected["name"])
    }</pre>
    """
)

# 3) Cells holding lists, sets and dicts. Ported from the deleted
# test/grid_data_render.py: the Python side of this is covered far more
# cheaply in test_legacy_coverage.py, so all that is left to check here is
# that a grid whose cells hold nested objects actually mounts and shows its
# rows rather than dying in the frontend's JSON parse.
unhashable_df = pd.DataFrame(
    {
        "id": [1, 2, 3],
        "a_list": [[1, 2], [3, 4], []],
        "a_set": [{1, 2}, {"x", "y"}, set()],
        "a_dict": [{"k": 1}, {"nested": {"deep": [1, 2]}}, {}],
    }
)
AgGrid(unhashable_df, key="unhashable_grid", use_json_serialization=True)
