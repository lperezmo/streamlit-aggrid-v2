"""Invariants of the generated event catalog, asserted directly.

``scripts/gen_event_catalog.py --check`` cannot cover this: it compares the
committed file against the output of the same parser that produced it, so it
proves the file is current and says nothing about whether the parse was right.
A generator that silently dropped a name, or leaked a word out of a JSDoc
comment, would pass ``--check`` on every run.

The set arithmetic in particular needs an independent assertion. ``update_on``
validation checks ``GRID_EVENTS`` first and returns early, so a bug that left
``sortChanged`` in ``COLUMN_ONLY_EVENTS`` would be invisible to every behavior
test: the name is in both sets, the early return wins, no warning is emitted,
and the tests pass while the catalog is wrong.
"""

from __future__ import annotations

import itertools

import pytest

from st_aggrid._event_catalog import (
    AG_GRID_VERSION,
    COLUMN_ONLY_EVENTS,
    GRID_EVENTS,
    INTERNAL_EVENTS,
    ROW_NODE_ONLY_EVENTS,
)

SETS = {
    "GRID_EVENTS": GRID_EVENTS,
    "COLUMN_ONLY_EVENTS": COLUMN_ONLY_EVENTS,
    "ROW_NODE_ONLY_EVENTS": ROW_NODE_ONLY_EVENTS,
    "INTERNAL_EVENTS": INTERNAL_EVENTS,
}


@pytest.mark.parametrize(("left", "right"), itertools.combinations(SETS, 2))
def test_the_catalog_sets_are_disjoint(left, right):
    """Overlap would make the warning text wrong rather than merely imprecise.

    A name in both GRID_EVENTS and COLUMN_ONLY_EVENTS is a valid update_on
    value, so reporting it as a Column event would tell the caller to remove
    something that works.
    """
    overlap = SETS[left] & SETS[right]
    assert overlap == frozenset(), f"{left} and {right} share {sorted(overlap)}"


@pytest.mark.parametrize(
    ("label", "floor"),
    [
        ("GRID_EVENTS", 90),
        ("COLUMN_ONLY_EVENTS", 8),
        ("ROW_NODE_ONLY_EVENTS", 15),
        ("INTERNAL_EVENTS", 40),
    ],
)
def test_the_catalog_is_not_suspiciously_small(label, floor):
    """A partial parse is the failure mode that does not announce itself.

    The generator has its own floors, but they live in the same file as the
    parser they are meant to police. These run against the committed artifact.
    """
    assert len(SETS[label]) >= floor


@pytest.mark.parametrize(
    "name",
    [
        # The four defaults. If any of these ever left GRID_EVENTS, every grid
        # in every app would start warning about its own default configuration.
        "cellValueChanged",
        "selectionChanged",
        "filterChanged",
        "sortChanged",
        # Everything GridUpdateMode can contribute, since those arrive merged
        # into update_on and a caller cannot remove them by hand.
        "columnMoved",
        "columnPinned",
        "columnResized",
        "columnVisible",
        # Dispatched on a RowNode and on the grid api both, so it has to stay on
        # the grid side of the split.
        "rowSelected",
    ],
)
def test_names_that_must_be_valid_update_on_values(name):
    assert name in GRID_EVENTS


@pytest.mark.parametrize(
    ("name", "expected_set"),
    [
        ("widthChanged", "COLUMN_ONLY_EVENTS"),
        ("visibleChanged", "COLUMN_ONLY_EVENTS"),
        ("filterActiveChanged", "COLUMN_ONLY_EVENTS"),
        ("dataChanged", "ROW_NODE_ONLY_EVENTS"),
        ("expandedChanged", "ROW_NODE_ONLY_EVENTS"),
        ("mouseEnter", "ROW_NODE_ONLY_EVENTS"),
        ("displayedRowsChanged", "INTERNAL_EVENTS"),
        ("gridOptionsChanged", "INTERNAL_EVENTS"),
    ],
)
def test_names_that_must_be_classified_as_unusable(name, expected_set):
    """Each of these is a real AG Grid event that update_on cannot rely on, and
    each lands in the set whose warning explains the specific reason."""
    assert name in SETS[expected_set]
    assert name not in GRID_EVENTS


def test_the_version_is_recorded_and_looks_like_a_version():
    """The version reaches users inside the warning text, so an empty or
    placeholder value would be visible in the one place it matters."""
    assert AG_GRID_VERSION
    major = AG_GRID_VERSION.split(".")[0]
    assert major.isdigit()
    assert int(major) >= 35


def test_every_name_looks_like_an_ag_grid_event():
    """Catches a parse that harvested prose instead of identifiers, which is how
    a JSDoc comment inside the declaration would leak in."""
    for label, names in SETS.items():
        for name in names:
            assert name[:1].islower(), f"{label} has {name!r}"
            assert name.isalnum(), f"{label} has {name!r}"
