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

import pandas as pd
import pytest

from grid_stub import nodes_payload, render_grid


DF = pd.DataFrame({"ints": [1, 2, 3], "floats": [1.5, 2.5, 3.5]})

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

    assert "allow_unsafe_jscode" in "".join(getattr(excinfo.value, "__notes__", []))


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
        render_grid(monkeypatch, DF.copy(), key="t1", theme="light")
