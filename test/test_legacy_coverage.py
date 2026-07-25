"""Python-level coverage ported off the deleted CCv1 (iframe) test files.

The five ``test_grid_*.py`` files drove the CCv1 iframe DOM through
``frame_locator("iframe")``. The CCv2 component renders straight into the page,
so every one of them was unrunnable and sat behind ``collect_ignore`` in
conftest. They are now resolved. The accounting, file by file:

test_grid_initialization.py / grid_initialization.py
    Deleted. Four of its six cases (DataFrame input, JSON-string input,
    gridOptions without data, empty grid) already exist as CCv2 tests in
    test_ccv2_e2e.py. The two that did not, loading data from a .json file and
    loading data and gridOptions from separate .json files, are ported below:
    the file reading happens entirely in Python, so a browser adds nothing.

test_grid_return.py / grid_return.py
    Deleted. Basic return and sorting are covered by
    test_ccv2_e2e.py::test_grid_data_roundtrip and ::test_sort_by_header_click.
    Checkbox selection, header select-all and DataReturnMode.CUSTOM are
    genuinely browser-side and are ported to test_ccv2_legacy_port.py. The
    grouped-data cases (rowGroup, dataGroups, selected_dataGroups) are dropped:
    row grouping is an AG Grid Enterprise feature and those tests ran with
    enable_enterprise_modules=True against a grid with no license key, so they
    cannot be made reliable in CI. Its 30,000 row dummy dataset was incidental
    and no assertion used it.

test_grid_data_render.py / grid_data_render.py
    Deleted. It rendered lists, sets, dicts, nested and empty containers and
    checked only that headers and row counts appeared. What it was really
    guarding is the Python serialization and hashing of unhashable cell
    values, which is ported below. One condensed render check lives in
    test_ccv2_legacy_port.py.

test_grid_drag_and_drop_example.py / grid_drag_and_drop_example.py
    Deleted, not ported. It asserted AG Grid's own managed row-drag reordering
    (aria-rowindex after a drag). The only st-aggrid code it exercised was
    gridOptions pass-through, which every other grid on the CCv2 fixture pages
    already covers, and drag-and-drop e2e is a well known flake source.

test_grid_performance.py / grid_performance_1m.py
    Deleted, not ported. It built a one million row grid and asserted
    wall-clock thresholds (initialization under 30s, load under 60s,
    interaction under 1s) with 60 to 120 second waits. Those assertions
    measure the CI runner, not the component, and it checks no behavior that
    the correctness suite does not already check at a workable size.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from grid_stub import render_grid

GRID_OPTIONS = {"columnDefs": [{"field": "a"}, {"field": "b"}]}
RECORDS = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]


# ---------------------------------------------------------------------------
# Loading data and gridOptions from .json files
# (from test_grid_initialization.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def data_file(tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps(RECORDS))
    return path


@pytest.fixture
def grid_options_file(tmp_path):
    path = tmp_path / "grid_options.json"
    path.write_text(json.dumps(GRID_OPTIONS))
    return path


def test_data_loaded_from_a_json_file(monkeypatch, data_file):
    call = render_grid(monkeypatch, str(data_file), key="lf1")

    assert [row["a"] for row in call.component_data["row_data"]] == [1, 2]
    fields = [c["field"] for c in call.grid_options["columnDefs"]]
    assert fields == ["a", "b"]


def test_data_and_grid_options_loaded_from_json_files(
    monkeypatch, data_file, grid_options_file
):
    call = render_grid(monkeypatch, str(data_file), str(grid_options_file), key="lf2")

    assert [row["b"] for row in call.component_data["row_data"]] == ["x", "y"]
    fields = [c["field"] for c in call.grid_options["columnDefs"]]
    assert fields == ["a", "b"]


def test_data_loaded_from_a_pathlib_path(monkeypatch, data_file):
    call = render_grid(monkeypatch, data_file, key="lf3")

    assert len(call.component_data["row_data"]) == 2


# ---------------------------------------------------------------------------
# Unhashable cell values (from test_grid_data_render.py)
# ---------------------------------------------------------------------------


UNHASHABLE_FRAMES = {
    "lists": pd.DataFrame(
        {
            "id": [1, 2],
            "simple": [[1, 2, 3], [4, 5, 6]],
            "nested": [[[1, 2], [3, 4]], [[5, 6], [7, 8]]],
            "mixed": [[1, "a", True], [2, "b", None]],
        }
    ),
    "sets": pd.DataFrame(
        {"id": [1, 2], "simple": [{1, 2, 3}, {4, 5, 6}], "text": [{"a"}, {"b", "c"}]}
    ),
    "dicts": pd.DataFrame(
        {
            "id": [1, 2],
            "simple": [{"x": 1}, {"x": 2}],
            "nested": [{"u": {"name": "a", "n": 1}}, {"u": {"name": "b", "n": 2}}],
        }
    ),
    "empty_containers": pd.DataFrame(
        {"id": [1, 2], "lst": [[], []], "st": [set(), set()], "dct": [{}, {}]}
    ),
}


@pytest.mark.parametrize("name", sorted(UNHASHABLE_FRAMES))
@pytest.mark.parametrize("serialization", ["auto", True])
def test_unhashable_cell_values_reach_the_grid(monkeypatch, name, serialization):
    """Lists, sets and dicts in cells must serialize in either mode.

    pd.util.hash_pandas_object raises on these, so the change-detection hash
    falls back through a tuple/frozenset conversion and then to string
    hashing. None of that may raise, and the rows still have to go out.
    """
    frame = UNHASHABLE_FRAMES[name]

    call = render_grid(
        monkeypatch,
        frame.copy(),
        key=f"uh_{name}_{serialization}",
        use_json_serialization=serialization,
    )

    assert call.component_data["data_hash"] not in ("", None)
    if serialization is True:
        assert isinstance(call.grid_options["rowData"], str)
        assert len(json.loads(call.grid_options["rowData"])) == len(frame)
    else:
        assert len(call.component_data["row_data"]) == len(frame)


@pytest.mark.parametrize("name", sorted(UNHASHABLE_FRAMES))
def test_unhashable_hash_still_tracks_the_data(monkeypatch, name):
    """The fallback hash still has to be a hash: same frame, same value;
    changed frame, changed value. A fallback that collapsed to a constant
    would silently stop the grid refreshing rows."""
    frame = UNHASHABLE_FRAMES[name]
    changed = frame.copy()
    changed.loc[0, "id"] = 99

    first = render_grid(monkeypatch, frame.copy(), key=f"h_{name}_1")
    again = render_grid(monkeypatch, frame.copy(), key=f"h_{name}_2")
    other = render_grid(monkeypatch, changed, key=f"h_{name}_3")

    assert first.component_data["data_hash"] == again.component_data["data_hash"]
    assert first.component_data["data_hash"] != other.component_data["data_hash"]
