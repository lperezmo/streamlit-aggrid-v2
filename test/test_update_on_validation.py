"""``update_on`` entries that cannot fire have to be reported, not ignored.

The frontend hands every ``update_on`` entry to ``api.addEventListener``, which
takes any string and keeps a listener for an event AG Grid will never dispatch.
Before this validation, ``update_on=["selectionChange"]`` produced no error, no
warning and a grid that simply never updated, which is indistinguishable from a
broken component. ``GridUpdateMode``, the API ``update_on`` replaces, turned the
same typo into a NameError at the call site, so the regression was a real loss.

The warnings are advisory on purpose and every test here asserts that: the
entry still reaches the frontend, because the generated catalog is read from the
bundled AG Grid version and could lag a newer one.
"""

from __future__ import annotations

import importlib
import inspect
import warnings
from pathlib import Path

import pandas as pd
import pytest

from st_aggrid import AgGrid

from grid_stub import render_grid

DF = pd.DataFrame({"ints": [1, 2, 3]})

_AGGRID_MODULE = importlib.import_module("st_aggrid.AgGrid")


def update_on_warnings(monkeypatch, **kwargs):
    """Run one ``AgGrid()`` call and return it with the update_on warnings.

    Only UserWarnings naming an ``update_on`` entry are returned. The
    GridUpdateMode deprecation notice is a DeprecationWarning and fires at most
    once per process, so it cannot be asserted on reliably from here and must
    not be mistaken for a validation warning either.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        call = render_grid(monkeypatch, DF.copy(), **kwargs)

    messages = [
        str(w.message)
        for w in caught
        if issubclass(w.category, UserWarning) and "update_on entry" in str(w.message)
    ]
    return call, messages


# ---------------------------------------------------------------------------
# Names that are not AG Grid events
# ---------------------------------------------------------------------------


def test_typo_is_reported_with_the_intended_name(monkeypatch):
    """The canonical mistake: a dropped trailing "d". The suggestion is the
    entire point, since the name looks right to the person who typed it."""
    _call, messages = update_on_warnings(
        monkeypatch, key="v1", update_on=["selectionChange"]
    )

    assert len(messages) == 1, messages
    message = messages[0]
    assert "selectionChange" in message
    assert "selectionChanged" in message
    assert "not an AG Grid event" in message
    # The user has to learn that the consequence is a grid that never updates,
    # which is the symptom that brought them to the docs in the first place.
    assert "never" in message
    # Which catalog was consulted, so a name added by a newer AG Grid than the
    # bundled one can be recognized as a version skew rather than a typo.
    assert "35.3.0" in message


def test_unknown_name_without_a_close_match_gets_no_suggestion(monkeypatch):
    """A wrong guess is worse than none: it sends the reader off to fix
    something they never wrote."""
    _call, messages = update_on_warnings(
        monkeypatch, key="v2", update_on=["totallyMadeUpEvent"]
    )

    assert len(messages) == 1, messages
    message = messages[0]
    assert "totallyMadeUpEvent" in message
    assert "not an AG Grid event" in message
    assert "Did you mean" not in message


@pytest.mark.parametrize(
    ("typo", "intended"),
    [
        ("selectionchanged", "selectionChanged"),
        ("SelectionChanged", "selectionChanged"),
        ("onSelectionChanged", "selectionChanged"),
        ("cellValueChange", "cellValueChanged"),
        ("filterchange", "filterChanged"),
        ("columnResize", "columnResized"),
        ("celClicked", "cellClicked"),
        ("valueChanged", "rowValueChanged"),
        ("rowClick", "rowClicked"),
        ("firstDataRender", "firstDataRendered"),
    ],
)
def test_realistic_misspellings_all_get_a_suggestion(monkeypatch, typo, intended):
    """Pins the suggestion cutoff from the tight side.

    Without this, raising _SUGGESTION_CUTOFF keeps every other test in this file
    green while quietly turning suggestions off: at 0.85 "valueChanged" stops
    resolving to "rowValueChanged", and at 0.95 seven of these ten go silent.
    The cases are the ways a name actually gets typed wrong, including the React
    prop spelling and a plain case error, both of which look correct to whoever
    wrote them.
    """
    _call, messages = update_on_warnings(
        monkeypatch, key=f"sugg-{typo}", update_on=[typo]
    )

    assert len(messages) == 1, messages
    assert f"Did you mean {intended!r}?" in messages[0]


@pytest.mark.parametrize("typo", ["dataChange", "widthChange", "click"])
def test_a_name_close_to_nothing_real_gets_no_suggestion(monkeypatch, typo):
    """The other side of the same constant.

    difflib's default 0.6 answers "dataChange" with "sortChanged" and "click"
    with "cellClicked", names that share a suffix and nothing else. "widthChange"
    is the tightest case: it still resolves to the unrelated "findChanged" at
    0.7 and only stops at 0.75. Between this test and the one above, the cutoff
    cannot move in either direction without something failing.
    """
    _call, messages = update_on_warnings(
        monkeypatch, key=f"nosugg-{typo}", update_on=[typo]
    )

    assert len(messages) == 1, messages
    assert "Did you mean" not in messages[0]


@pytest.mark.parametrize(
    ("typo", "intended"),
    [("onRedoEnded", "redoEnded"), ("onRedoStarted", "redoStarted")],
)
def test_the_on_prefixed_redo_events_are_not_confused_with_undo(
    monkeypatch, typo, intended
):
    """Fuzzy matching alone gets this pair actively wrong.

    "onRedoEnded" scores an identical 0.8 against "redoEnded" and "undoEnded",
    and difflib breaks the tie lexicographically, so it used to answer
    "undoEnded": a confident suggestion pointing at the opposite operation.
    Stripping the React "on" prefix and looking for an exact match resolves it
    outright instead of guessing.
    """
    _call, messages = update_on_warnings(
        monkeypatch, key=f"redo-{typo}", update_on=[typo]
    )

    assert len(messages) == 1, messages
    assert f"Did you mean {intended!r}?" in messages[0]
    assert "undo" not in messages[0]


def test_an_ambiguous_best_match_is_not_guessed_at(monkeypatch):
    """When two real events are equally close, naming one is a coin flip.

    "onXdoEnded" sits the same distance from "undoEnded" and "redoEnded" with no
    prefix trick available, so the right answer is to report the bad name and
    keep quiet about which event was meant.
    """
    _call, messages = update_on_warnings(
        monkeypatch, key="ambiguous", update_on=["oXdoEnded"]
    )

    assert len(messages) == 1, messages
    assert "not an AG Grid event" in messages[0]
    assert "Did you mean" not in messages[0]


def test_an_internal_event_is_reported_as_internal_not_as_unknown(monkeypatch):
    """AG Grid splits _PUBLIC_EVENTS from _INTERNAL_EVENTS, and its event service
    does not validate names, so an internal event probably does fire today.
    Saying it "is not an AG Grid event" would be false; what the caller needs to
    know is that it is unsupported and can vanish on an upgrade."""
    call, messages = update_on_warnings(
        monkeypatch, key="internal", update_on=["displayedRowsChanged"]
    )

    assert len(messages) == 1, messages
    message = messages[0]
    assert "displayedRowsChanged" in message
    assert "not an AG Grid event" not in message
    assert "internal" in message
    # Forwarded like everything else the catalog cannot vouch for.
    assert call.component_data["update_on"] == ["displayedRowsChanged"]


def test_unknown_name_still_reaches_the_frontend(monkeypatch):
    """The catalog is generated from the bundled AG Grid and can lag a newer
    one, so an unlisted name is a warning and never a silent drop."""
    call, messages = update_on_warnings(
        monkeypatch, key="v3", update_on=["selectionChange", "sortChanged"]
    )

    assert messages
    assert call.component_data["update_on"] == ["selectionChange", "sortChanged"]


# ---------------------------------------------------------------------------
# Real events that the grid api never dispatches
# ---------------------------------------------------------------------------


def test_column_only_event_is_reported_as_a_column_event(monkeypatch):
    """The name "widthChanged" is a real AG Grid event, so the message must not
    claim otherwise; what it has to explain is that a Column dispatches it."""
    call, messages = update_on_warnings(
        monkeypatch, key="v4", update_on=["widthChanged"]
    )

    assert len(messages) == 1, messages
    message = messages[0]
    assert "widthChanged" in message
    assert "not an AG Grid event" not in message
    assert "Column" in message
    assert "row node" not in message
    # Still forwarded, like any other name the catalog does not vouch for.
    assert call.component_data["update_on"] == ["widthChanged"]


def test_row_node_only_event_is_reported_as_a_row_node_event(monkeypatch):
    """The RowNode counterpart, worded so the two cases are distinguishable:
    "dataChanged" fires per row, not on the grid."""
    _call, messages = update_on_warnings(
        monkeypatch, key="v5", update_on=["dataChanged"]
    )

    assert len(messages) == 1, messages
    message = messages[0]
    assert "dataChanged" in message
    assert "not an AG Grid event" not in message
    assert "row node" in message
    assert "Column" not in message


def test_event_that_is_both_a_column_and_a_grid_event_is_accepted(monkeypatch):
    """sortChanged is dispatched on a Column *and* on the grid api. Only the
    grid api matters for update_on, so it must pass without a word."""
    _call, messages = update_on_warnings(
        monkeypatch, key="v6", update_on=["sortChanged"]
    )

    assert messages == []


# ---------------------------------------------------------------------------
# Valid input must stay silent
# ---------------------------------------------------------------------------


def test_valid_event_names_do_not_warn(monkeypatch):
    _call, messages = update_on_warnings(
        monkeypatch,
        key="v7",
        update_on=["cellClicked", "rowSelected", "paginationChanged"],
    )

    assert messages == []


def test_the_default_update_on_does_not_warn(monkeypatch):
    """A warning on the built-in default would fire for every grid in every app
    and would say nothing about anything the caller wrote."""
    call, messages = update_on_warnings(monkeypatch, key="v8")

    assert messages == []
    assert call.component_data["update_on"] == [
        "cellValueChanged",
        "selectionChanged",
        "filterChanged",
        "sortChanged",
    ]


@pytest.mark.parametrize(
    "update_mode",
    ["MODEL_CHANGED", "VALUE_CHANGED", "GRID_CHANGED", "SELECTION_CHANGED", "MANUAL"],
)
def test_the_deprecated_update_mode_path_does_not_warn(monkeypatch, update_mode):
    """Every event GridUpdateMode can contribute is a real grid event, and its
    events are merged into update_on before validation runs. A false warning
    here would be unfixable from user code: nothing they passed produced it."""
    _call, messages = update_on_warnings(monkeypatch, key="v9", update_mode=update_mode)

    assert messages == []


# ---------------------------------------------------------------------------
# Entry shapes and duplicates
# ---------------------------------------------------------------------------


def test_a_debounced_tuple_entry_is_validated_on_its_name(monkeypatch):
    """``(event, debounce_ms)`` describes the same listener as the bare name, so
    a typo inside a tuple is just as dead and must be reported the same way."""
    _call, messages = update_on_warnings(
        monkeypatch, key="v10", update_on=[("columnResize", 300)]
    )

    assert len(messages) == 1, messages
    assert "columnResize" in messages[0]
    assert "columnResized" in messages[0]


def test_a_valid_debounced_tuple_entry_does_not_warn(monkeypatch):
    _call, messages = update_on_warnings(
        monkeypatch, key="v11", update_on=[("columnResized", 300)]
    )

    assert messages == []


def test_a_repeated_bad_name_warns_once(monkeypatch):
    """Validation runs after the dedupe, so the report is per event and not per
    entry. The same name arriving twice is one mistake to fix."""
    _call, messages = update_on_warnings(
        monkeypatch,
        key="v12",
        update_on=["selectionChange", ("selectionChange", 200)],
    )

    assert len(messages) == 1, messages


def test_a_name_shared_with_update_mode_warns_once(monkeypatch):
    """The same rule across the deprecated merge: update_mode re-adds names
    update_on already carries, and one of them being a typo is still one
    mistake."""
    _call, messages = update_on_warnings(
        monkeypatch,
        key="v13",
        update_mode="COLUMN_RESIZED",
        update_on=["columnResize", "columnResize"],
    )

    assert len(messages) == 1, messages


def test_every_bad_name_is_reported(monkeypatch):
    """Distinct mistakes are distinct warnings: stopping at the first would
    hide the rest behind a second run."""
    _call, messages = update_on_warnings(
        monkeypatch,
        key="v14",
        update_on=["selectionChange", "widthChanged", "totallyMadeUpEvent"],
    )

    assert len(messages) == 3, messages


# ---------------------------------------------------------------------------
# Attribution
# ---------------------------------------------------------------------------


def test_the_warning_points_at_the_line_that_called_aggrid(monkeypatch):
    """A warning attributed to aggrid_utils.py reads as a library bug and hides
    the one thing the reader needs, which is their own ``AgGrid(...)`` line.

    ``AgGrid`` is called directly here rather than through ``render_grid``,
    because the stub helper would otherwise be the caller the warning names.
    """
    monkeypatch.setattr(
        _AGGRID_MODULE, "_get_component_func", lambda: lambda **kwargs: None
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        expected_lineno = inspect.currentframe().f_lineno + 1
        AgGrid(DF.copy(), key="v15", update_on=["selectionChange"])

    entries = [w for w in caught if "update_on entry" in str(w.message)]
    assert len(entries) == 1, [str(w.message) for w in caught]
    assert Path(entries[0].filename) == Path(__file__)
    assert entries[0].lineno == expected_lineno


# ---------------------------------------------------------------------------
# Malformed input
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("entry", [1, None, {"event": "cellClicked"}, [{"a": 1}]])
def test_validation_does_not_crash_on_a_malformed_entry(entry):
    """Validation is a diagnostic and must never be the reason a call fails.
    An entry that is neither a name nor a ``(name, debounce)`` tuple is left to
    the code that consumes it, including the shapes for which
    ``update_event_name`` hands back something unhashable and would blow up a
    set lookup.
    """
    from st_aggrid.aggrid_utils import validate_update_on

    with warnings.catch_warnings():
        warnings.simplefilter("always")
        validate_update_on([entry])


def test_the_warning_is_visible_under_default_filters(monkeypatch):
    """Every other test here runs under simplefilter("always"), which is exactly
    the setting that would hide a warning suppressed by the default filters.

    Only the first occurrence is asserted. Python's default action for
    UserWarning is "once per (message, category, module, lineno)", so the repeat
    cadence depends on registry state this test has no business pinning: it
    currently resets far more often than that, because pandas uses
    warnings.catch_warnings internally on the path AgGrid takes to inspect
    dtypes, and entering that context invalidates every __warningregistry__ in
    the process. Asserting "fires every time" would pin a pandas implementation
    detail and go red on an unrelated upgrade. What has to hold is that the
    developer sees it without opting in.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.resetwarnings()
        warnings.simplefilter("default")
        render_grid(
            monkeypatch, DF.copy(), key="defaults", update_on=["selectionChange"]
        )

    messages = [str(w.message) for w in caught if "update_on entry" in str(w.message)]
    assert len(messages) == 1, [str(w.message) for w in caught]
    assert "selectionChanged" in messages[0]


def test_a_bare_string_is_treated_as_one_event_not_as_its_letters(monkeypatch):
    """``update_on="selectionChanged"`` reads naturally and used to be silently
    catastrophic: a string is iterable, so every consumer walked it character by
    character. dedupe_update_on returned ['s', 'e', 'l', 'c', ...] and the
    frontend attached a listener per letter, none of which could fire. It is now
    wrapped, which is unambiguously what the caller meant."""
    call, messages = update_on_warnings(
        monkeypatch, key="bare", update_on="selectionChanged"
    )

    assert messages == []
    assert call.component_data["update_on"] == ["selectionChanged"]


def test_a_bare_string_with_a_typo_reports_the_event_not_a_letter(monkeypatch):
    """The wrapping happens before validation, so the diagnostic is about the
    event the caller wrote rather than about the letter 's'."""
    _call, messages = update_on_warnings(
        monkeypatch, key="bare-typo", update_on="selectionChange"
    )

    assert len(messages) == 1, messages
    assert "selectionChanged" in messages[0]


def test_validate_update_on_called_directly_with_a_string_says_so():
    """AgGrid normalizes before calling, so this path only matters to a direct
    caller, which has no chance to be normalized for."""
    from st_aggrid.aggrid_utils import validate_update_on

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        validate_update_on("selectionChanged")

    messages = [str(w.message) for w in caught]
    assert len(messages) == 1, messages
    assert "should be a list" in messages[0]
    # And it must not then go on to complain about each letter.
    assert "'s'" not in messages[0]


def test_validation_does_not_crash_on_an_empty_tuple_entry():
    """``update_event_name`` indexes [0], so this shape would raise from inside
    the validation itself rather than from the code that reads the entry."""
    from st_aggrid.aggrid_utils import validate_update_on

    validate_update_on([()])
