"""Browser-less unit tests for the pure-Python layer.

Covers the data/gridOptions parsing matrix in aggrid_utils, AgGridReturn's
Mapping interface, and GridOptionsBuilder diagnostics. These run in
milliseconds, so regressions in input handling are caught without Playwright.
"""

import json
import math

import pandas as pd
import pytest

from st_aggrid.AgGrid import _reraise_with_hint
from st_aggrid.aggrid_utils import _parse_data_and_grid_options, _sanitize_nan_inf
from st_aggrid.AgGridReturn import AgGridReturn
from st_aggrid.collectors.custom import CustomCollector
from st_aggrid.collectors.factory import determine_collector
from st_aggrid.grid_options_builder import GridOptionsBuilder
from st_aggrid.shared import (
    DataReturnMode,
    JsCode,
    StAggridTheme,
    walk_gridOptions,
)

DF = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
GRID_OPTIONS = {"columnDefs": [{"field": "a"}, {"field": "b"}]}


def _parse(data, grid_options, **kw):
    kw.setdefault("default_column_parameters", {})
    kw.setdefault("unsafe_allow_jscode", False)
    kw.setdefault("use_json_serialization", "auto")
    return _parse_data_and_grid_options(
        data,
        grid_options,
        kw["default_column_parameters"],
        kw["unsafe_allow_jscode"],
        kw["use_json_serialization"],
    )


# ---------------------------------------------------------------------------
# gridOptions input forms
# ---------------------------------------------------------------------------


def test_grid_options_as_json_string_with_data():
    data, go, _dtypes = _parse(DF.copy(), json.dumps(GRID_OPTIONS))
    assert go["columnDefs"][0]["field"] == "a"
    assert isinstance(data, pd.DataFrame)


def test_grid_options_as_json_file_with_data(tmp_path):
    path = tmp_path / "grid_options.json"
    path.write_text(json.dumps(GRID_OPTIONS))
    _data, go, _dtypes = _parse(DF.copy(), path)
    assert go["columnDefs"][1]["field"] == "b"


def test_grid_options_as_json_string_without_data():
    data, go, _dtypes = _parse(None, json.dumps(GRID_OPTIONS))
    assert go["columnDefs"][0]["field"] == "a"
    assert data is None


def test_no_data_and_no_grid_options():
    data, go, _dtypes = _parse(None, None)
    assert go == {}
    assert data is None


def test_grid_options_invalid_type_raises():
    with pytest.raises(ValueError, match="gridOptions"):
        _parse(None, 42)


# ---------------------------------------------------------------------------
# rowData handling
# ---------------------------------------------------------------------------


def test_data_and_rowdata_conflict_raises_friendly_error():
    go = {"rowData": json.dumps([{"a": 1}])}
    with pytest.raises(ValueError, match="both data and gridOptions rowData"):
        _parse(DF.copy(), go)


def test_rowdata_json_string_moves_to_data():
    go = {"rowData": json.dumps([{"a": 1}, {"a": 2}])}
    data, parsed, _dtypes = _parse(None, go)
    assert "rowData" not in parsed
    assert list(data["a"]) == [1, 2]


def test_rowdata_as_list_of_records():
    go = {"rowData": [{"a": 1}, {"a": 2}]}
    data, _parsed, _dtypes = _parse(None, go)
    assert list(data["a"]) == [1, 2]


def test_use_json_serialization_without_data():
    data, _go, _dtypes = _parse(None, dict(GRID_OPTIONS), use_json_serialization=True)
    assert data is None


# ---------------------------------------------------------------------------
# data input forms
# ---------------------------------------------------------------------------


def test_data_as_json_string_builds_grid_options():
    records = json.dumps([{"a": 1, "b": "x"}])
    _data, go, _dtypes = _parse(records, None)
    fields = [c["field"] for c in go["columnDefs"]]
    assert fields == ["a", "b"]


def test_auto_unique_id_added_without_get_row_id():
    data, _go, _dtypes = _parse(DF.copy(), dict(GRID_OPTIONS))
    assert "::auto_unique_id::" in data.columns


def test_sanitize_nan_inf():
    tree = {"w": float("nan"), "nested": [{"x": float("inf")}, 1.5]}
    _sanitize_nan_inf(tree)
    assert tree["w"] is None
    assert tree["nested"][0]["x"] is None
    assert tree["nested"][1] == 1.5
    assert not any(
        isinstance(v, float) and not math.isfinite(v) for v in tree.values()
    )


# ---------------------------------------------------------------------------
# AgGridReturn Mapping interface
# ---------------------------------------------------------------------------


def test_aggrid_return_len_and_iter_do_not_materialize_data(monkeypatch):
    """len()/iter()/keys() must not evaluate the data properties (which
    rebuild DataFrames) just to enumerate attribute names."""
    response = AgGridReturn(originalData=DF)

    def boom(*args, **kwargs):
        raise AssertionError("data property getter was evaluated during iteration")

    monkeypatch.setattr(AgGridReturn, "_get_data", boom)
    keys = list(response)
    assert "data" in keys
    assert "selected_rows" in keys
    assert len(response) == len(keys)
    # SIM118 wants `in response`, but Mapping.__contains__ does a __getitem__,
    # which is exactly the materialization this test forbids. keys() is the
    # thing under test here.
    assert "data" in response.keys()  # noqa: SIM118


def test_aggrid_return_selected_rows_id_without_state():
    response = AgGridReturn(originalData=DF)
    assert response.selected_rows_id is None


def test_aggrid_return_data_before_component_value():
    response = AgGridReturn(originalData=DF)
    assert response.data is DF
    assert response.selected_data is None


# ---------------------------------------------------------------------------
# GridOptionsBuilder diagnostics
# ---------------------------------------------------------------------------


def test_from_dataframe_warns_on_unknown_parameter():
    with pytest.warns(UserWarning, match="not a valid gridOption"):
        GridOptionsBuilder.from_dataframe(DF, not_a_real_option=1)


def test_build_is_idempotent():
    """build() must not mutate the builder.

    It replaced the internal columnDefs mapping with a list, so calling
    build() a second time (the normal thing to do when one builder configures
    several grids) raised AttributeError on .values().
    """
    builder = GridOptionsBuilder.from_dataframe(DF)

    first = builder.build()
    second = builder.build()

    assert first == second
    assert isinstance(second["columnDefs"], list)
    assert [c["field"] for c in second["columnDefs"]] == ["a", "b"]


def test_build_result_is_detached_from_the_builder():
    """Mutating a built dict must not leak back into the next build()."""
    builder = GridOptionsBuilder.from_dataframe(DF)

    first = builder.build()
    first["columnDefs"] = []
    first["rowHeight"] = 99

    second = builder.build()
    assert len(second["columnDefs"]) == 2
    assert "rowHeight" not in second


def test_build_result_is_detached_at_every_level():
    """The nested dicts must be detached too, not just the top level.

    build() returned a shallow copy, so defaultColDef and every entry of
    columnDefs were the *same* objects in the builder and in every build. The
    top-level-only assertions above pass against that.
    """
    builder = GridOptionsBuilder.from_dataframe(DF)
    builder.configure_default_column(editable=True)

    first = builder.build()
    second = builder.build()

    assert first["defaultColDef"] is not second["defaultColDef"]
    assert first["columnDefs"][0] is not second["columnDefs"][0]

    first["defaultColDef"]["editable"] = "mutated"
    first["columnDefs"][0]["headerName"] = "mutated"

    third = builder.build()
    assert third["defaultColDef"]["editable"] is True
    assert third["columnDefs"][0].get("headerName") != "mutated"


def test_build_survives_jscode_flattening_by_a_previous_grid():
    """A second build() must still carry JsCode objects, not flattened strings.

    AgGrid(..., allow_unsafe_jscode=True) rewrites JsCode leaves into
    ``::JSCODE::`` strings in place via walk_gridOptions. With colDefs shared
    across builds, the rewrite hit the builder's own dicts and every later
    build came out pre-flattened, so the second grid got a string where the
    frontend expects the marker-wrapped code it re-parses.
    """
    builder = GridOptionsBuilder.from_dataframe(DF)
    renderer = JsCode("function(params) { return params.value }")
    builder.configure_column("a", cellRenderer=renderer)

    first = builder.build()
    assert isinstance(first["columnDefs"][0]["cellRenderer"], JsCode)
    # What AgGrid() does to gridOptions when allow_unsafe_jscode is on.
    walk_gridOptions(first, lambda v: v.js_code if isinstance(v, JsCode) else v)
    assert isinstance(first["columnDefs"][0]["cellRenderer"], str)

    second = builder.build()
    assert isinstance(second["columnDefs"][0]["cellRenderer"], JsCode)
    # JsCode objects are shared, not copied: callers compare against the object
    # they handed in.
    assert second["columnDefs"][0]["cellRenderer"] is renderer


def test_build_shares_callables_instead_of_copying_them():
    """User callables inside gridOptions must survive the copy by identity."""

    def get_row_id(params):
        return params["data"]["a"]

    builder = GridOptionsBuilder.from_dataframe(DF)
    builder.configure_grid_options(getRowId=get_row_id)

    assert builder.build()["getRowId"] is get_row_id


# ---------------------------------------------------------------------------
# walk_gridOptions
# ---------------------------------------------------------------------------


def test_walk_grid_options_converts_values_stored_directly_in_a_list():
    """Leaf values inside a plain list must be passed to func.

    The walk enumerated lists and then indexed them by the *element* instead
    of the index, so scalar list entries were skipped entirely. A JsCode
    stored in a list therefore reached the frontend unconverted.
    """
    go = {
        "columnDefs": [
            {
                "field": "a",
                "cellRenderers": [
                    JsCode("function(p){return 1}"),
                    JsCode("function(p){return 2}"),
                ],
            }
        ]
    }

    walk_gridOptions(go, lambda v: v.js_code if isinstance(v, JsCode) else v)

    renderers = go["columnDefs"][0]["cellRenderers"]
    assert all(isinstance(r, str) for r in renderers), (
        f"JsCode inside a list was not converted: {renderers}"
    )
    assert all(r.startswith("::JSCODE::") for r in renderers)


def test_walk_grid_options_handles_nested_lists():
    """A list of lists must not crash the walk.

    Indexing a list by its element raised
    "TypeError: list indices must be integers or slices, not str".
    """
    go = {"rowClassRules": [["alpha", "beta"], ["gamma"]]}

    walk_gridOptions(go, lambda v: v.upper() if isinstance(v, str) else v)

    assert go["rowClassRules"] == [["ALPHA", "BETA"], ["GAMMA"]]


# ---------------------------------------------------------------------------
# Datetime handling
# ---------------------------------------------------------------------------


def test_missing_datetimes_do_not_serialize_as_the_string_nat():
    """pd.NaT.isoformat() returns the string "NaT", which was written into
    the payload and rendered literally in cells, quick search and CSV
    export. Missing datetimes have to travel as null."""
    frame = pd.DataFrame(
        {"when": pd.to_datetime(["2024-01-01", None, "2024-01-03"])}
    )

    data, _go, _dtypes = _parse(frame, None)

    values = list(data["when"])
    assert values[1] is None, f"missing datetime serialized as {values[1]!r}"
    assert "NaT" not in [v for v in values if isinstance(v, str)]
    assert values[0].startswith("2024-01-01")


# ---------------------------------------------------------------------------
# AgGridReturn contracts
# ---------------------------------------------------------------------------


def test_aggrid_return_keys_agree_with_len_and_iter():
    """Mapping requires keys(), __iter__ and __len__ to describe the same set.

    keys() used to append the raw grid_response keys on top of the attribute
    names, so len(r) reported 18 while len(r.keys()) reported 21 and
    dict(zip(r.keys(), r.values())) silently dropped the extras.
    """
    response = AgGridReturn(originalData=DF)
    response._set_component_value(
        {"nodes": [], "gridState": {}, "columnsState": [], "eventData": None}
    )

    keys = response.keys()
    assert len(keys) == len(response)
    assert list(keys) == list(iter(response))
    assert len(set(keys)) == len(keys)
    # dict(zip(...)) is the idiom that lost entries.
    assert len(dict(zip(response.keys(), response.values()))) == len(response)
    # The raw response keys stay reachable, just not through the Mapping.
    assert response["gridState"] == {}


def test_aggrid_return_data_with_zero_nodes():
    """A grid that reported no nodes must produce an empty frame.

    Type conversion built one Series per column and finished with pd.concat(),
    which raises "No objects to concatenate" on an empty list.
    """
    response = AgGridReturn(originalData=DF, frame_dtypes=DF.dtypes)
    response._set_component_value(
        {"nodes": [], "rowIdsAfterFilter": [], "rowIdsAfterSortAndFilter": []}
    )

    data = response.data
    assert isinstance(data, pd.DataFrame)
    assert data.empty


def test_conversion_errors_ignore_returns_the_column_unchanged():
    """conversion_errors='ignore' is implemented locally now, because pandas
    deprecated errors='ignore' and removes it in pandas 3.0. Unconvertible
    values must leave the column as it came back."""
    frame = pd.DataFrame({"num": [1.0, 2.0]})
    response = AgGridReturn(
        originalData=frame,
        frame_dtypes=frame.dtypes,
        conversion_errors="ignore",
    )
    response._set_component_value(
        {
            "nodes": [
                {"id": "0", "rowIndex": 0, "data": {"num": "not-a-number"}},
                {"id": "1", "rowIndex": 1, "data": {"num": "2.0"}},
            ],
            "rowIdsAfterFilter": ["0", "1"],
            "rowIdsAfterSortAndFilter": ["0", "1"],
        }
    )

    assert list(response.data["num"]) == ["not-a-number", "2.0"]


# ---------------------------------------------------------------------------
# Error re-wrapping
# ---------------------------------------------------------------------------


def test_reraise_with_hint_keeps_the_exception_type():
    """Rebuilding with type(ex)(*ex.args) turned json.JSONDecodeError into a
    TypeError, because its constructor takes msg/doc/pos rather than its own
    args."""
    with pytest.raises(json.JSONDecodeError) as excinfo:
        try:
            json.loads("{oops")
        except json.JSONDecodeError as ex:
            _reraise_with_hint(ex, "check allow_unsafe_jscode")

    assert "check allow_unsafe_jscode" in str(excinfo.value)


def test_reraise_with_hint_does_not_garble_the_message():
    """Exceptions that build their own message from a short argument had that
    message fed back in as the argument, nesting the whole text inside itself.
    StreamlitDuplicateElementId is the one users actually hit."""
    from streamlit.errors import StreamlitDuplicateElementId

    original = StreamlitDuplicateElementId("dataframe")
    marker = "There are multiple"

    with pytest.raises(StreamlitDuplicateElementId) as excinfo:
        _reraise_with_hint(original, "hint text")

    message = str(excinfo.value)
    assert message.count(marker) == 1, f"message was garbled: {message}"
    assert message.endswith("hint text")


def test_reraise_with_hint_survives_empty_args():
    """``args[0] += ...`` raised IndexError on an exception with no args,
    destroying the original error."""

    class NoArgs(Exception):
        def __init__(self):
            super().__init__()

    with pytest.raises(NoArgs) as excinfo:
        _reraise_with_hint(NoArgs(), "hint text")

    # str(), not __notes__: notes are never rendered by Streamlit, and
    # add_note does not exist on the 3.10 floor, where the old fallback
    # rebuilt this as a RuntimeError and lost the NoArgs type entirely.
    assert "hint text" in str(excinfo.value)


def test_reraise_with_hint_keeps_the_original_traceback():
    """The frame that actually failed has to stay in the traceback; Streamlit
    renders it and it is the only pointer to the real cause."""

    def failing():
        raise ValueError("boom")

    with pytest.raises(ValueError) as excinfo:
        try:
            failing()
        except ValueError as ex:
            _reraise_with_hint(ex, "hint text")

    frames = [tb.tb_frame.f_code.co_name for tb in _walk_tb(excinfo.tb)]
    assert "failing" in frames


def _walk_tb(tb):
    while tb is not None:
        yield tb
        tb = tb.tb_next


# ---------------------------------------------------------------------------
# Collector factory
# ---------------------------------------------------------------------------


def test_determine_collector_supports_custom_mode():
    """DataReturnMode.CUSTOM fell through to "Unsupported DataReturnMode"."""
    collector = determine_collector(
        collect_grid_return=JsCode("function(p){return {}}"),
        data_return_mode=DataReturnMode.CUSTOM,
    )
    assert isinstance(collector, CustomCollector)


def test_determine_collector_custom_mode_requires_jscode():
    with pytest.raises(ValueError, match="collect_grid_return is required"):
        determine_collector(data_return_mode=DataReturnMode.CUSTOM)


# ---------------------------------------------------------------------------
# Themes
# ---------------------------------------------------------------------------


def test_custom_theme_without_a_base_still_names_itself():
    """themeName drove the frontend's theme lookup, and a StAggridTheme built
    without a base left it unset, so the parser fell back to balham and threw
    away the withParams/withParts the caller configured."""
    theme = StAggridTheme().withParams(accentColor="#ff0000")

    assert theme["themeName"] == "custom"
    assert theme["params"] == {"accentColor": "#ff0000"}
