"""Call ``AgGrid()`` end to end without a Streamlit runtime.

``AgGrid()`` is almost entirely pure Python: it normalizes arguments, parses
data and gridOptions, builds the ``component_data`` payload, hands that to the
registered CCv2 component and wraps whatever comes back in a collector
response. Only the middle step needs Streamlit, and it goes through the module
level ``_get_component_func()`` indirection.

Swapping that one function out lets a test drive the whole Python layer in
milliseconds: it can assert on the exact payload the frontend would have
received (``data_hash``, ``update_on``, ``gridOptions``, ...) and feed a
frontend-shaped response back in to assert on the ``AgGridReturn`` that comes
out.

``streamlit.testing.v1.AppTest`` is deliberately not used: it never runs CCv2
component discovery, so a file-backed component always looks unregistered
under it.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any

from st_aggrid import AgGrid

# ``st_aggrid.AgGrid`` is both a module and (after the package __init__ runs)
# an attribute holding the function, so plain attribute access would hand back
# the function. Go through the module registry to get the module itself.
_AGGRID_MODULE = importlib.import_module("st_aggrid.AgGrid")


@dataclass
class _FakeComponentResult:
    """Stands in for Streamlit's CCv2 component return value."""

    grid_return: Any


@dataclass
class GridCall:
    """What one ``AgGrid()`` call sent to the frontend and got back."""

    component_data: dict
    grid_options: dict
    response: Any
    call_count: int


def render_grid(monkeypatch, *args, grid_return=None, raises=None, **kwargs) -> GridCall:
    """Run ``AgGrid(*args, **kwargs)`` against a stubbed component.

    Parameters
    ----------
    grid_return
        Payload the stubbed frontend sends back, in the shape the TypeScript
        collectors produce. ``None`` models a first render, where the component
        has not reported anything yet.
    raises
        Exception the stubbed component raises instead of returning, used to
        exercise the error re-wrapping paths.
    """
    captured: dict[str, Any] = {}
    calls = {"n": 0}

    def fake_component_func(**call_kwargs):
        calls["n"] += 1
        captured.update(call_kwargs)
        if raises is not None:
            raise raises
        return _FakeComponentResult(grid_return) if grid_return is not None else None

    monkeypatch.setattr(
        _AGGRID_MODULE, "_get_component_func", lambda: fake_component_func
    )

    response = AgGrid(*args, **kwargs)

    component_data = captured["data"]
    return GridCall(
        component_data=component_data,
        grid_options=component_data["gridOptions"],
        response=response,
        call_count=calls["n"],
    )


def nodes_payload(records, *, selected_ids=()):
    """Build a LegacyCollector-shaped response for ``records``.

    ``records`` are dicts of column name to the *string* the browser sends
    back, which is what AG Grid produces for edited cells and what forces the
    dtype round-trip on the Python side to do real work.
    """
    nodes = []
    for index, record in enumerate(records):
        row_id = str(index)
        nodes.append(
            {
                "id": row_id,
                "rowIndex": index,
                "group": False,
                "isSelected": row_id in selected_ids,
                "data": {**record, "::auto_unique_id::": row_id},
            }
        )
    row_ids = [n["id"] for n in nodes]
    return {
        "nodes": nodes,
        "rowIdsAfterFilter": row_ids,
        "rowIdsAfterSortAndFilter": row_ids,
    }
