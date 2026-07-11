"""Browser-less unit tests for the pure-Python layer.

Covers the data/gridOptions parsing matrix in aggrid_utils, AgGridReturn's
Mapping interface, and GridOptionsBuilder diagnostics. These run in
milliseconds, so regressions in input handling are caught without Playwright.
"""

import json
import math

import pandas as pd
import pytest

from st_aggrid.AgGridReturn import AgGridReturn
from st_aggrid.aggrid_utils import _parse_data_and_grid_options, _sanitize_nan_inf
from st_aggrid.grid_options_builder import GridOptionsBuilder


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
    data, go, dtypes = _parse(DF.copy(), json.dumps(GRID_OPTIONS))
    assert go["columnDefs"][0]["field"] == "a"
    assert isinstance(data, pd.DataFrame)


def test_grid_options_as_json_file_with_data(tmp_path):
    path = tmp_path / "grid_options.json"
    path.write_text(json.dumps(GRID_OPTIONS))
    data, go, dtypes = _parse(DF.copy(), path)
    assert go["columnDefs"][1]["field"] == "b"


def test_grid_options_as_json_string_without_data():
    data, go, dtypes = _parse(None, json.dumps(GRID_OPTIONS))
    assert go["columnDefs"][0]["field"] == "a"
    assert data is None


def test_no_data_and_no_grid_options():
    data, go, dtypes = _parse(None, None)
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
    data, parsed, dtypes = _parse(None, go)
    assert "rowData" not in parsed
    assert list(data["a"]) == [1, 2]


def test_rowdata_as_list_of_records():
    go = {"rowData": [{"a": 1}, {"a": 2}]}
    data, parsed, dtypes = _parse(None, go)
    assert list(data["a"]) == [1, 2]


def test_use_json_serialization_without_data():
    data, go, dtypes = _parse(None, dict(GRID_OPTIONS), use_json_serialization=True)
    assert data is None


# ---------------------------------------------------------------------------
# data input forms
# ---------------------------------------------------------------------------


def test_data_as_json_string_builds_grid_options():
    records = json.dumps([{"a": 1, "b": "x"}])
    data, go, dtypes = _parse(records, None)
    fields = [c["field"] for c in go["columnDefs"]]
    assert fields == ["a", "b"]


def test_auto_unique_id_added_without_get_row_id():
    data, go, dtypes = _parse(DF.copy(), dict(GRID_OPTIONS))
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
    assert "data" in response.keys()


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
