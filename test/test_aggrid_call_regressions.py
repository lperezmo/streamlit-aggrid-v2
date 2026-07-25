"""Regression tests for defects observable in the ``AgGrid()`` call itself.

Each test drives a real ``AgGrid()`` call through ``grid_stub.render_grid``,
which swaps out only the Streamlit component call. That makes the exact
payload the frontend would receive, and the ``AgGridReturn`` built from a
frontend-shaped reply, both assertable in milliseconds.

Every test here was verified to fail against the unfixed source before being
committed.
"""

from __future__ import annotations

import json
import warnings

import pandas as pd
import pytest

from st_aggrid import GridUpdateMode, JsCode

# _AGGRID_MODULE, not ``import st_aggrid.AgGrid``: the package __init__ rebinds
# that name to the function, so the plain import hands back a callable with no
# module globals on it. grid_stub goes through the module registry for the same
# reason and documents it.
from grid_stub import _AGGRID_MODULE, nodes_payload, render_grid

DF = pd.DataFrame({"ints": [1, 2, 3], "floats": [1.5, 2.5, 3.5]})


@pytest.fixture(autouse=True)
def _reset_warning_dedupe():
    """Forget which warnings this process has already shown.

    AgGrid keeps a module-level set so a warning fires once rather than on
    every Streamlit rerun. That state leaks between tests: whichever test
    happened to run first got the warning and the rest saw silence, which made
    the assertions here depend on collection order.
    """
    _AGGRID_MODULE._shown_once_warnings.clear()
    yield
    _AGGRID_MODULE._shown_once_warnings.clear()

# What the browser sends back for DF: AG Grid hands values to Python as the
# strings the cell renderers hold, so the dtype round-trip has real work to do.
ROWS_BACK = nodes_payload(
    [
        {"ints": "1", "floats": "1.5"},
        {"ints": "2", "floats": "2.5"},
        {"ints": "3", "floats": "3.5"},
    ]
)


# ---------------------------------------------------------------------------
# use_json_serialization=True must not degrade the payload or the response
# ---------------------------------------------------------------------------


def test_json_serialization_still_hashes_the_frame(monkeypatch):
    """data_hash has to describe the frame that is on the wire.

    Under ``use_json_serialization=True`` the frame moves into
    ``gridOptions["rowData"]`` and the ``data`` local becomes None. Hashing
    that local pinned data_hash at "", and the frontend only refreshes rows
    when data_hash changes under the default ``server_sync_strategy=
    "client_wins"``, so the grid froze on the rows it mounted with.
    """
    call = render_grid(monkeypatch, DF.copy(), key="j1", use_json_serialization=True)

    assert call.component_data["data_hash"] != "", (
        "data_hash is empty under use_json_serialization=True, so the frontend "
        "will never refresh rows after mount"
    )
    # The frame really did travel as a JSON string, i.e. this is the mode
    # under test and not a silent fallback to the records path.
    assert isinstance(call.grid_options["rowData"], str)
    assert call.component_data["row_data"] is None


def test_json_serialization_hash_changes_with_the_data(monkeypatch):
    """A changed frame must produce a changed hash, which is the whole point:
    equal hashes are what kept the grid pinned to its mounted rows."""
    first = render_grid(monkeypatch, DF.copy(), key="j2", use_json_serialization=True)
    other = DF.copy()
    other.loc[0, "ints"] = 99
    second = render_grid(monkeypatch, other, key="j2", use_json_serialization=True)

    assert first.component_data["data_hash"] != second.component_data["data_hash"]


def test_json_serialization_hash_matches_auto_mode(monkeypatch):
    """The serialization mode is a transport detail; the same frame has to
    hash the same either way."""
    auto = render_grid(monkeypatch, DF.copy(), key="j3", use_json_serialization="auto")
    explicit = render_grid(monkeypatch, DF.copy(), key="j3", use_json_serialization=True)

    assert auto.component_data["data_hash"] == explicit.component_data["data_hash"]


def test_json_serialization_returns_original_dtypes(monkeypatch):
    """The returned frame must be typed the same in both serialization modes.

    ``try_to_convert_back_to_original_types`` was cleared by an
    ``isinstance(data, pd.DataFrame)`` guard that saw None under
    use_json_serialization=True. That withheld frame_dtypes from
    LegacyCollector, and AgGridReturn only converts columns when frame_dtypes
    is set, so every column came back as object.
    """
    auto = render_grid(
        monkeypatch,
        DF.copy(),
        key="j4",
        use_json_serialization="auto",
        grid_return=ROWS_BACK,
    )
    explicit = render_grid(
        monkeypatch,
        DF.copy(),
        key="j4",
        use_json_serialization=True,
        grid_return=ROWS_BACK,
    )

    assert list(explicit.response.data.dtypes) == list(auto.response.data.dtypes)
    # Spelled out, so the test still means something if auto mode ever breaks
    # in the same way and the two agree on garbage.
    assert str(explicit.response.data["ints"].dtype) == "Int64"
    assert str(explicit.response.data["floats"].dtype) == "float64"


def test_json_serialization_response_data_is_a_dataframe(monkeypatch):
    """``response.data`` must stay a DataFrame.

    Moving the frame onto gridOptions.rowData left AgGrid with no original
    data to hand the response, so AgGridReturn fell through to its JSON branch
    and ``.data`` came back as a JSON string.
    """
    call = render_grid(
        monkeypatch,
        DF.copy(),
        key="j5",
        use_json_serialization=True,
        grid_return=ROWS_BACK,
    )

    assert isinstance(call.response.data, pd.DataFrame), (
        f"expected a DataFrame, got {type(call.response.data).__name__}"
    )
    assert list(call.response.data.columns) == ["ints", "floats"]
    assert list(call.response.data["ints"]) == [1, 2, 3]


def test_json_serialization_keeps_internal_column_out_of_the_response(monkeypatch):
    """The internal ``::auto_unique_id::`` column is added by the parser and
    must not leak into the frame the response reports as the original data."""
    call = render_grid(monkeypatch, DF.copy(), key="j6", use_json_serialization=True)

    assert "::auto_unique_id::" not in call.response.data.columns


def test_json_serialization_with_row_data_in_grid_options(monkeypatch):
    """rowData inside gridOptions must still reach the grid under
    use_json_serialization=True.

    The parser refused to move rowData into ``data`` in that mode, so the list
    of record dicts stayed on gridOptions.rowData. The frontend's parseData
    only unwraps rowData when it is a JSON *string*; a list fell through to []
    and the grid rendered empty.
    """
    call = render_grid(
        monkeypatch,
        gridOptions={"columnDefs": [{"field": "a"}], "rowData": [{"a": 1}, {"a": 2}]},
        key="jr1",
        use_json_serialization=True,
    )

    row_data = call.grid_options["rowData"]
    assert isinstance(row_data, str), (
        "rowData reached the frontend as a Python list, which parseData ignores"
    )
    parsed = json.loads(row_data)
    assert [row["a"] for row in parsed] == [1, 2]
    # getRowId is derived from this column on the frontend, and it is only
    # added on the path that treats rowData as data.
    assert all("::auto_unique_id::" in row for row in parsed)


def test_json_serialization_with_row_data_refreshes_on_change(monkeypatch):
    """The grid only reloads rows when data_hash changes, so rowData supplied
    through gridOptions has to be hashed like any other frame."""
    first = render_grid(
        monkeypatch,
        gridOptions={"columnDefs": [{"field": "a"}], "rowData": [{"a": 1}]},
        key="jr2",
        use_json_serialization=True,
    )
    second = render_grid(
        monkeypatch,
        gridOptions={"columnDefs": [{"field": "a"}], "rowData": [{"a": 2}]},
        key="jr2",
        use_json_serialization=True,
    )

    assert first.component_data["data_hash"] != ""
    assert first.component_data["data_hash"] != second.component_data["data_hash"]


def test_row_data_in_grid_options_is_still_moved_without_json_serialization(monkeypatch):
    """The default path must keep behaving exactly as before."""
    call = render_grid(
        monkeypatch,
        gridOptions={"columnDefs": [{"field": "a"}], "rowData": [{"a": 1}, {"a": 2}]},
        key="jr3",
    )

    assert "rowData" not in call.grid_options
    assert [row["a"] for row in call.component_data["row_data"]] == [1, 2]


# ---------------------------------------------------------------------------
# The caller's gridOptions dict is an input, not scratch space
# ---------------------------------------------------------------------------
#
# A Streamlit script reruns top to bottom on every interaction, and it is
# ordinary to build gridOptions once and keep it: in session_state, behind
# st.cache_resource, or as a module-level constant in a helper module. Every
# write AgGrid made into that dict therefore landed on the next rerun.


def test_json_serialization_does_not_write_row_data_into_the_caller_dict(monkeypatch):
    """The serialized frame must not be parked on the caller's own dict."""
    grid_options = {"columnDefs": [{"field": "ints"}]}

    render_grid(
        monkeypatch,
        DF.copy(),
        gridOptions=grid_options,
        key="gm1",
        use_json_serialization=True,
    )

    assert "rowData" not in grid_options, (
        "AgGrid wrote the serialized frame onto the caller's gridOptions dict"
    )


def test_reused_grid_options_dict_survives_a_rerun_under_json_serialization(monkeypatch):
    """Two renders from one gridOptions dict must both work.

    The first render used to write rowData onto the caller's dict, so the
    second saw data supplied by both ``data=`` and ``gridOptions.rowData`` and
    raised. The grid rendered once and then took the page down on the next
    interaction.
    """
    grid_options = {"columnDefs": [{"field": "ints"}]}

    for run in ("gm2a", "gm2b", "gm2c"):
        call = render_grid(
            monkeypatch,
            DF.copy(),
            gridOptions=grid_options,
            key=run,
            use_json_serialization=True,
        )
        assert isinstance(call.grid_options["rowData"], str)


def test_row_data_is_not_popped_out_of_the_caller_dict(monkeypatch):
    """The mirror image: rows supplied through gridOptions must survive.

    rowData was popped off the caller's dict to become the data frame, so a
    reused dict had no rows left on the second render and the grid came back
    empty. Silent, unlike the ValueError above.
    """
    grid_options = {"columnDefs": [{"field": "a"}], "rowData": [{"a": 1}, {"a": 2}]}

    for run in ("gm3a", "gm3b"):
        call = render_grid(monkeypatch, gridOptions=grid_options, key=run)
        assert [row["a"] for row in call.component_data["row_data"]] == [1, 2]

    assert grid_options["rowData"] == [{"a": 1}, {"a": 2}]


def test_jscode_is_not_flattened_inside_the_caller_dict(monkeypatch):
    """walk_gridOptions rewrites JsCode leaves into ::JSCODE:: strings in
    place. Reaching into the caller's colDefs meant the second render handed
    the frontend an already-flattened string where it expects marker-wrapped
    code it re-parses."""
    getter = JsCode("function(params) { return params.data.ints }")
    grid_options = {"columnDefs": [{"field": "ints", "valueGetter": getter}]}

    render_grid(
        monkeypatch,
        DF.copy(),
        gridOptions=grid_options,
        key="gm4",
        allow_unsafe_jscode=True,
    )

    assert grid_options["columnDefs"][0]["valueGetter"] is getter


def test_grid_options_copy_shares_its_leaves(monkeypatch):
    """Only the container spine is copied. Callers compare JsCode objects and
    callables by identity, so duplicating them would be its own bug."""
    getter = JsCode("function(params) { return 1 }")
    grid_options = {"columnDefs": [{"field": "ints", "valueGetter": getter}]}

    call = render_grid(
        monkeypatch, DF.copy(), gridOptions=grid_options, key="gm5"
    )

    # Not rewritten here (allow_unsafe_jscode defaults to False), so the leaf
    # that reached the payload is the very object the caller passed in.
    assert call.grid_options["columnDefs"][0]["valueGetter"] is getter
    assert call.grid_options["columnDefs"] is not grid_options["columnDefs"]


# ---------------------------------------------------------------------------
# DataReturnMode.MINIMAL first render
# ---------------------------------------------------------------------------


def test_minimal_mode_returns_the_input_frame_before_the_first_response(monkeypatch):
    """MINIMAL must hand back the input frame on a first render.

    Every other mode does. MinimalCollector.create_initial_response ignored
    original_data and returned a bare MinimalResponse, so ``.data`` was None
    until an update_on event fired. Under update_mode=MANUAL, which attaches
    no events at all, that meant None until the toolbar button was clicked.
    """
    call = render_grid(monkeypatch, DF.copy(), key="mn1", data_return_mode="MINIMAL")

    data = call.response.data
    assert data is not None, "MINIMAL returns .data None on a first render"
    assert isinstance(data, pd.DataFrame)
    assert list(data["ints"]) == [1, 2, 3]
    # The internal id column is added by the parser and must not be reported.
    assert "::auto_unique_id::" not in data.columns
    assert call.response.selected_rows == []


def test_minimal_mode_still_reports_the_grid_rows_once_they_arrive(monkeypatch):
    """The input frame is only a placeholder: a real response wins."""
    call = render_grid(
        monkeypatch,
        DF.copy(),
        key="mn2",
        data_return_mode="MINIMAL",
        grid_return={"data": [{"ints": 2, "floats": 2.5}], "selectedRows": []},
    )

    assert call.response.data.to_dict("records") == [{"ints": 2, "floats": 2.5}]


def test_minimal_mode_data_stays_a_dataframe_across_the_first_response(monkeypatch):
    """``.data`` must not change type once the user touches the grid.

    It returned the input DataFrame on a first render and the raw list of
    record dicts from the payload afterwards, so ``response.data["col"]``,
    ``.empty``, ``.iloc`` and ``len(response.data.index)`` all worked on load
    and raised on the first selection. ``raw_data`` is where the records live.
    """
    before = render_grid(monkeypatch, DF.copy(), key="mn4", data_return_mode="MINIMAL")
    after = render_grid(
        monkeypatch,
        DF.copy(),
        key="mn5",
        data_return_mode="MINIMAL",
        grid_return={"data": [{"ints": 2, "floats": 2.5}], "selectedRows": []},
    )

    assert isinstance(before.response.data, pd.DataFrame)
    assert isinstance(after.response.data, pd.DataFrame), (
        "MINIMAL switched .data from a DataFrame to a list once the grid replied"
    )
    # Ordinary DataFrame use that used to break on the second render.
    assert list(after.response.data["ints"]) == [2]
    assert not after.response.data.empty
    # The unwrapped payload is still reachable for callers that want it lean.
    assert after.response.raw_data["data"] == [{"ints": 2, "floats": 2.5}]


def test_minimal_mode_reports_an_empty_grid_as_empty(monkeypatch):
    """A response that filtered every row away must report no rows, not fall
    back to the input frame."""
    call = render_grid(
        monkeypatch,
        DF.copy(),
        key="mn3",
        data_return_mode="MINIMAL",
        grid_return={"data": [], "selectedRows": []},
    )

    data = call.response.data
    assert isinstance(data, pd.DataFrame)
    assert data.empty
    # pd.DataFrame([]) has no columns at all, which describes nothing. An empty
    # result still describes the same table as a full one.
    assert list(data.columns) == ["ints", "floats"]


# ---------------------------------------------------------------------------
# update_mode=MANUAL is exclusive
# ---------------------------------------------------------------------------


def test_manual_update_mode_attaches_no_default_events(monkeypatch):
    """MANUAL means the toolbar button is the only return path.

    The default update_on set was still attached, so the grid kept returning
    data on every edit, selection, filter and sort and the button was just one
    more trigger among several. v1 semantics made MANUAL exclusive.
    """
    call = render_grid(monkeypatch, DF.copy(), key="m1", update_mode="MANUAL")

    assert call.component_data["update_on"] == [], (
        "MANUAL still attaches update_on events, so the update button is not "
        f"the only return path: {call.component_data['update_on']}"
    )
    assert call.component_data["manual_update"] is True
    # The button lives in the toolbar, so the toolbar has to be shown.
    assert call.component_data["show_toolbar"] is True


def test_manual_update_mode_honors_explicit_update_on(monkeypatch):
    """An update_on passed by the caller is used verbatim alongside the
    button, so anyone who wants the old triggers can still ask for them."""
    call = render_grid(
        monkeypatch,
        DF.copy(),
        key="m2",
        update_mode="MANUAL",
        update_on=["cellValueChanged", "selectionChanged"],
    )

    assert call.component_data["update_on"] == ["cellValueChanged", "selectionChanged"]
    assert call.component_data["manual_update"] is True


def test_manual_update_mode_composed_with_another_flag(monkeypatch):
    """GridUpdateMode is a Flag, so MANUAL composes.

    The mode was matched with ``==``, which read MANUAL | VALUE_CHANGED as
    "not MANUAL": no update button was rendered, the toolbar was not forced
    on, and parse_update_mode dropped the MANUAL bit, leaving a grid with no
    manual return path at all. Both halves of the flag have to be honored.
    """
    call = render_grid(
        monkeypatch,
        DF.copy(),
        key="m8",
        update_mode=GridUpdateMode.MANUAL | GridUpdateMode.VALUE_CHANGED,
    )

    assert call.component_data["manual_update"] is True, (
        "a composed MANUAL flag rendered no update button"
    )
    assert call.component_data["show_toolbar"] is True
    # The other bit still contributes its event, and the defaults MANUAL
    # clears do not come back.
    assert call.component_data["update_on"] == ["cellValueChanged"]


def test_bare_manual_update_mode_adds_no_events_through_the_flag_path(monkeypatch):
    """parse_update_mode now runs for MANUAL too. MANUAL alone maps to no
    events, so the mode stays exclusive."""
    call = render_grid(
        monkeypatch, DF.copy(), key="m9", update_mode=GridUpdateMode.MANUAL
    )

    assert call.component_data["update_on"] == []
    assert call.component_data["manual_update"] is True


def test_non_manual_update_mode_keeps_the_default_events(monkeypatch):
    """Only MANUAL clears the defaults. Every other mode still adds its own
    events on top of them."""
    call = render_grid(monkeypatch, DF.copy(), key="m3", update_mode="COLUMN_PINNED")

    update_on = call.component_data["update_on"]
    assert "cellValueChanged" in update_on
    assert "selectionChanged" in update_on
    assert "columnPinned" in update_on
    assert call.component_data["manual_update"] is False


def test_default_update_mode_keeps_the_default_events(monkeypatch):
    """A grid with no update_mode at all is untouched by the MANUAL rule."""
    call = render_grid(monkeypatch, DF.copy(), key="m4")

    assert call.component_data["update_on"] == [
        "cellValueChanged",
        "selectionChanged",
        "filterChanged",
        "sortChanged",
    ]


# ---------------------------------------------------------------------------
# update_on must hold one entry per event
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "update_mode",
    ["MODEL_CHANGED", "VALUE_CHANGED", "GRID_CHANGED", "SELECTION_CHANGED"],
)
def test_update_mode_does_not_duplicate_the_default_events(monkeypatch, update_mode):
    """Each AG Grid event may appear at most once in update_on.

    parse_update_mode deduped only within the list it built, and the result was
    appended onto the already-populated defaults. The frontend attaches a fresh
    closure per entry and AG Grid stores listeners in a Set keyed by function
    identity, so both fired: the full collector walk and the Streamlit state
    write ran twice for every event.
    """
    call = render_grid(monkeypatch, DF.copy(), key="d1", update_mode=update_mode)

    update_on = call.component_data["update_on"]
    names = [e[0] if isinstance(e, (list, tuple)) else e for e in update_on]
    assert len(names) == len(set(names)), f"duplicate update_on entries: {update_on}"
    # The defaults are still all there; dedupe must not drop events.
    assert {"cellValueChanged", "selectionChanged", "filterChanged", "sortChanged"} <= set(names)


def test_update_on_dedupe_keeps_the_debounced_spec(monkeypatch):
    """When the same event arrives as a bare name and as a debounced tuple,
    the tuple wins: silently dropping the debounce would be the more surprising
    outcome, and it is what update_mode contributes."""
    call = render_grid(
        monkeypatch,
        DF.copy(),
        key="d2",
        update_mode="COLUMN_RESIZED",
        update_on=["columnResized"],
    )

    assert call.component_data["update_on"] == [("columnResized", 300)]


def test_update_on_dedupe_preserves_caller_order(monkeypatch):
    """Order is first appearance, so a caller's own ordering survives."""
    call = render_grid(
        monkeypatch,
        DF.copy(),
        key="d3",
        update_mode="MODEL_CHANGED",
        update_on=["sortChanged", "cellValueChanged"],
    )

    assert call.component_data["update_on"] == [
        "sortChanged",
        "cellValueChanged",
        "selectionChanged",
        "filterChanged",
    ]


# ---------------------------------------------------------------------------
# show_toolbar under update_mode=MANUAL
# ---------------------------------------------------------------------------


def test_manual_update_mode_warns_when_it_overrides_show_toolbar(monkeypatch, caplog):
    """An explicit show_toolbar=False is discarded under MANUAL. The override
    has to stay (no toolbar means no update button means no return path at
    all), but it must not be silent."""
    with caplog.at_level("WARNING", logger="st_aggrid.AgGrid"):
        call = render_grid(
            monkeypatch,
            DF.copy(),
            key="m5",
            update_mode="MANUAL",
            show_toolbar=False,
        )

    assert call.component_data["show_toolbar"] is True
    messages = [r.getMessage() for r in caplog.records]
    assert any("show_toolbar" in m and "MANUAL" in m for m in messages), messages
    # The remedy the message names has to be one that exists. It used to offer
    # "pass update_on explicitly, if the toolbar has to stay hidden", but
    # show_toolbar is forced to True regardless of update_on, so following the
    # advice changed nothing.
    conflict = next(m for m in messages if "show_toolbar" in m)
    assert "update_on" not in conflict or "drop update_mode=MANUAL" in conflict


def test_manual_toolbar_warning_fires_once_not_on_every_rerun(monkeypatch, caplog):
    """A Streamlit script reruns on every interaction. An undeduped warning at
    call time repeats for the lifetime of the app, which is how a real
    diagnostic becomes noise the reader learns to scroll past."""
    with caplog.at_level("WARNING", logger="st_aggrid.AgGrid"):
        for run in ("m5a", "m5b", "m5c"):
            render_grid(
                monkeypatch,
                DF.copy(),
                key=run,
                update_mode="MANUAL",
                show_toolbar=False,
            )

    conflicts = [r for r in caplog.records if "show_toolbar" in r.getMessage()]
    assert len(conflicts) == 1, (
        f"the toolbar override warned {len(conflicts)} times across 3 reruns"
    )


def test_manual_update_mode_does_not_warn_about_the_default_toolbar(monkeypatch, caplog):
    """Only an explicit False is a conflict. Warning on the default would fire
    for every MANUAL grid and say nothing about the caller's intent."""
    with caplog.at_level("WARNING", logger="st_aggrid.AgGrid"):
        call = render_grid(monkeypatch, DF.copy(), key="m6", update_mode="MANUAL")

    assert call.component_data["show_toolbar"] is True
    assert not [r for r in caplog.records if "show_toolbar" in r.getMessage()]


def test_show_toolbar_default_is_false_without_manual(monkeypatch):
    """The sentinel default must resolve to False before it is sent: the
    frontend reads a missing show_toolbar as true."""
    call = render_grid(monkeypatch, DF.copy(), key="m7")

    assert call.component_data["show_toolbar"] is False


# ---------------------------------------------------------------------------
# conversion_errors applies to every column kind
# ---------------------------------------------------------------------------

# One integer column, and a value the browser sends back that cannot be a
# number. This is the case conversion_errors exists for.
BAD_INTS = nodes_payload([{"ints": "not-a-number", "floats": "1.5"}])


def test_conversion_errors_ignore_leaves_an_integer_column_alone(monkeypatch):
    """conversion_errors="ignore" is documented as "returns input unchanged on
    failure", and it was honored for float and datetime columns only. The
    integer branch hardcoded errors="coerce", so the uncoercible value came
    back as <NA> and the original was gone."""
    call = render_grid(
        monkeypatch,
        DF.copy(),
        key="c1",
        conversion_errors="ignore",
        grid_return=BAD_INTS,
    )

    assert list(call.response.data["ints"]) == ["not-a-number"]


def test_conversion_errors_raise_propagates_on_an_integer_column(monkeypatch):
    """conversion_errors="raise" is documented as "raises exception on
    conversion failure". The integer branch swallowed the failure."""
    call = render_grid(
        monkeypatch,
        DF.copy(),
        key="c2",
        conversion_errors="raise",
        grid_return=BAD_INTS,
    )

    with pytest.raises(ValueError):
        _ = call.response.data


def test_conversion_errors_coerce_still_nulls_an_integer_column(monkeypatch):
    """The default is unchanged: an uncoercible value becomes <NA>."""
    call = render_grid(
        monkeypatch,
        DF.copy(),
        key="c3",
        conversion_errors="coerce",
        grid_return=BAD_INTS,
    )

    ints = call.response.data["ints"]
    assert str(ints.dtype) == "Int64"
    assert bool(ints.isna().all())


def test_conversion_errors_ignore_does_not_disturb_good_integers(monkeypatch):
    """"ignore" must only fall back when the conversion actually fails."""
    call = render_grid(
        monkeypatch,
        DF.copy(),
        key="c4",
        conversion_errors="ignore",
        grid_return=ROWS_BACK,
    )

    assert str(call.response.data["ints"].dtype) == "Int64"
    assert list(call.response.data["ints"]) == [1, 2, 3]


# ---------------------------------------------------------------------------
# Zero-node responses
# ---------------------------------------------------------------------------


def test_response_data_on_a_zero_node_grid(monkeypatch):
    """A grid that returns no nodes must yield an empty frame, not raise.

    The dtype conversion built one Series per column and finished with
    pd.concat(), which raises "No objects to concatenate" on an empty list.
    """
    call = render_grid(
        monkeypatch,
        DF.copy(),
        key="z1",
        grid_return={
            "nodes": [],
            "rowIdsAfterFilter": [],
            "rowIdsAfterSortAndFilter": [],
        },
    )

    data = call.response.data
    assert isinstance(data, pd.DataFrame)
    assert data.empty


# ---------------------------------------------------------------------------
# Error re-wrapping at the call site
# ---------------------------------------------------------------------------


def test_component_error_keeps_its_type_and_gains_the_hint(monkeypatch):
    """Errors raised by the component call must survive re-wrapping.

    Rebuilding with ``type(ex)(*args)`` turned a JSONDecodeError into a
    TypeError (its constructor takes msg/doc/pos, not its own args). The hint
    also has to land in ``str(ex)``: Streamlit renders the message and the
    traceback, never ``__notes__``.
    """
    boom = json.JSONDecodeError("Expecting value", "", 0)

    with pytest.raises(json.JSONDecodeError) as excinfo:
        render_grid(monkeypatch, DF.copy(), key="e1", raises=boom)

    assert "allow_unsafe_jscode" in str(excinfo.value), (
        "the hint is not in str(exception), so Streamlit will not show it"
    )


def test_component_error_with_empty_args_is_not_swallowed(monkeypatch):
    """An exception carrying no args used to raise IndexError from the
    re-wrap, destroying the original error."""

    class NoArgs(Exception):
        def __init__(self):
            super().__init__()

    with pytest.raises(NoArgs) as excinfo:
        render_grid(monkeypatch, DF.copy(), key="e2", raises=NoArgs())

    # Asserted on str(), not __notes__. The hint used to be attached with
    # add_note, which Streamlit never renders and which does not exist at all
    # on the 3.10 floor, where the fallback rebuilt the error as a RuntimeError
    # and lost the NoArgs type that pytest.raises above is checking for.
    assert "allow_unsafe_jscode" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Argument handling around gridOptions
# ---------------------------------------------------------------------------


def test_fit_columns_on_grid_load_is_not_reported_as_a_grid_option(monkeypatch):
    """fit_columns_on_grid_load is consumed by AgGrid, not by AG Grid.

    It reached GridOptionsBuilder.from_dataframe, which warned that it is not
    a valid gridOption even though AgGrid honors it right after.
    """
    with pytest.warns(DeprecationWarning) as record:
        call = render_grid(
            monkeypatch, DF.copy(), key="f1", fit_columns_on_grid_load=True
        )

    messages = [str(w.message) for w in record]
    assert not [m for m in messages if "not a valid gridOption" in m], messages
    # ... and it is still honored.
    assert call.grid_options["autoSizeStrategy"] == {"type": "fitGridWidth"}


def test_unknown_string_theme_is_rejected(monkeypatch):
    """Unknown theme names silently fell through to AG Grid's balham theme."""
    with pytest.raises(ValueError, match="not a valid theme"):
        render_grid(monkeypatch, DF.copy(), key="t1", theme="lavender")


@pytest.mark.parametrize("name", ["light", "dark", "blue", "fresh"])
def test_retired_theme_names_warn_instead_of_raising(monkeypatch, name):
    """These four were in the published docstring for this function.

    No release ever implemented them (the frontend fell through to balham for
    any name it did not recognize), but rejecting them outright turns an app
    written against the shipped docs from "renders balham" into a ValueError
    that takes the page down, on a 0.x minor. Keep the rendering, say it is
    going away.
    """
    with pytest.warns(DeprecationWarning, match=name):
        call = render_grid(monkeypatch, DF.copy(), key=f"t-{name}", theme=name)

    assert call.component_data["theme"]["themeName"] == "balham"


def test_retired_theme_warning_fires_once_not_on_every_rerun(monkeypatch):
    """Same reasoning as the toolbar warning: this is call-time, so it would
    otherwise repeat on every Streamlit rerun."""
    with pytest.warns(DeprecationWarning):
        render_grid(monkeypatch, DF.copy(), key="t2a", theme="light")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        render_grid(monkeypatch, DF.copy(), key="t2b", theme="light")

    retired = [w for w in caught if "is deprecated" in str(w.message) and "light" in str(w.message)]
    assert retired == [], "the retired-theme warning repeated on the second render"
