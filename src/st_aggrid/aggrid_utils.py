import difflib
import json
import math
import os
import warnings
from collections.abc import Mapping
from io import StringIO
from pathlib import Path

import pandas as pd

from st_aggrid._event_catalog import (
    AG_GRID_VERSION,
    COLUMN_ONLY_EVENTS,
    GRID_EVENTS,
    INTERNAL_EVENTS,
    ROW_NODE_ONLY_EVENTS,
)
from st_aggrid.grid_options_builder import GridOptionsBuilder, _copy_containers
from st_aggrid.shared import GridUpdateMode, JsCode, walk_gridOptions


def _sanitize_nan_inf(obj):
    """Replace NaN/+Inf/-Inf floats with None in a dict/list tree.

    Streamlit CCv2 serializes component data with strict JSON, which rejects
    NaN and Infinity tokens. User pipelines that compute numeric gridOptions
    fields (e.g. column widths) from empty DataFrames can yield NaN; this
    keeps the payload parseable on the frontend.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, float) and not math.isfinite(v):
                obj[k] = None
            elif isinstance(v, (dict, list)):
                _sanitize_nan_inf(v)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, float) and not math.isfinite(v):
                obj[i] = None
            elif isinstance(v, (dict, list)):
                _sanitize_nan_inf(v)
    return obj


def _parse_data_and_grid_options(
    data,
    grid_options,
    default_column_parameters,
    unsafe_allow_jscode,
    use_json_serialization,
):
    column_types = None

    # Parse grid_options first, independently of data, so a JSON string or a
    # path to a JSON file works whether or not data was supplied. (It used to
    # live in an elif only reachable when data was None, so combining a
    # DataFrame with string gridOptions crashed downstream on a str.)
    if grid_options is None:
        # May still be inferred from data below; empty grid otherwise.
        grid_options = {}
    elif isinstance(grid_options, Mapping):
        # Detached from the caller's object, because everything below writes
        # into it: rowData is popped out of it, walk_gridOptions rewrites JsCode
        # leaves in place, _sanitize_nan_inf replaces non-finite floats, and
        # AgGrid() puts the serialized frame back on rowData afterwards. A
        # Streamlit app that keeps one gridOptions dict across reruns (in
        # session_state, behind st.cache_resource, or as a module constant) was
        # therefore handing a different dict to every rerun than the one it
        # built. Under use_json_serialization=True that turned into a hard
        # failure: the first render wrote rowData onto the caller's dict, and
        # the second saw both data= and gridOptions.rowData and raised. Popping
        # rowData had the mirror-image effect, emptying a grid whose rows came
        # from a reused dict on the second render.
        #
        # Only the container spine is copied. _copy_containers shares every
        # leaf, so JsCode objects and callables the caller holds a reference to
        # keep their identity; the containers are all that anything mutates.
        grid_options = _copy_containers(
            grid_options if isinstance(grid_options, dict) else dict(grid_options)
        )
    elif isinstance(grid_options, (str, Path)):
        if isinstance(grid_options, Path):
            grid_options = str(Path(grid_options).resolve().absolute())
        # if grid_options is a path to a json file. Validate and load it as dictionary.
        if str(grid_options).endswith(".json") and os.path.exists(grid_options):
            try:
                with open(os.path.abspath(grid_options)) as f:
                    grid_options = json.dumps(json.load(f))
            except Exception as ex:
                raise ValueError(f"Error reading {grid_options}. {ex}") from ex

        # if grid_options is a json string load is as as dict
        try:
            grid_options = json.loads(grid_options)
        except Exception as ex:
            raise ValueError(
                "Error parsing gridOptions parameter as raw json."
            ) from ex
    else:
        raise ValueError(
            "gridOptions must be a dict, a JSON string, or a path to a JSON file, "
            f"got {type(grid_options).__name__}."
        )

    if data is not None:
        if isinstance(data, (str, Path)):
            if isinstance(data, Path):
                data = str(Path(data).resolve().absolute())

            # if data is a path to a json file. Validate and load it as string.
            if str(data).endswith(".json") and os.path.exists(data):
                try:
                    with open(os.path.abspath(data)) as f:
                        data = json.dumps(json.load(f))
                except Exception as ex:
                    raise ValueError(f"Error reading {data}. {ex}") from ex

            # if data is a json string load is as as data frame
            try:
                data = pd.read_json(StringIO(data))
            except Exception as ex:
                raise ValueError("Error parsing data parameter as raw json.") from ex
        # handles the case where dataframe is a polars dataframe without add dependency on polars
        if (
            hasattr(data, "__class__")
            and data.__class__.__module__
            and "polars" in data.__class__.__module__
            and data.__class__.__name__ == "DataFrame"
        ):
            data = data.to_pandas(use_pyarrow_extension_array=False)

        if isinstance(data, pd.DataFrame):
            # Recorded BEFORE the ISO conversion below, which overwrites every
            # datetime column with object-dtype strings. Capturing afterwards
            # stored kind "O" for those columns, so AgGridReturn's datetime
            # branch was unreachable on this path and a datetime column came
            # back from the grid as ISO strings rather than Timestamps.
            column_types = data.dtypes.copy()

            # converts date columns to iso format. Missing values must stay
            # empty: pd.NaT.isoformat() returns the string "NaT", which would
            # be rendered literally in cells, quick search and CSV export.
            for c, d in column_types.items():
                if d.kind == "M":
                    # Built as an explicit object Series rather than with
                    # .apply(). pandas 3.0 infers its new `str` dtype from a
                    # result that is all strings, and None lands in a str
                    # column as nan, which is not valid JSON and reaches the
                    # browser as NaN. Naming the dtype keeps the null a null
                    # on both pandas 2 and 3.
                    data[c] = pd.Series(
                        [None if pd.isna(s) else s.isoformat() for s in data[c]],
                        index=data.index,
                        dtype=object,
                    )

        # if there is data and no grid options, create grid options from the data
        if not grid_options:
            gb = GridOptionsBuilder.from_dataframe(data, **default_column_parameters)
            grid_options = gb.build()

        # Only for the path where data is not a DataFrame by this point. The
        # DataFrame case recorded its dtypes above, before the ISO conversion,
        # and must not be overwritten with the post-conversion ones. Either way
        # this happens before the id column is added, so it stays out.
        if column_types is None:
            column_types = data.dtypes

    # if data is supplied via gridOptions.rowData move it to data parameter.
    # This runs for every serialization mode. It used to be skipped under
    # use_json_serialization=True, which left a list of record dicts sitting on
    # gridOptions.rowData: the frontend's parseData only unwraps rowData when it
    # is a JSON *string*, so it fell through to [] and rendered an empty grid.
    # It also left ``data`` at None, so the frame was never hashed and the grid
    # could never refresh.
    if grid_options.get("rowData", None) is not None:
        if data is not None:
            raise ValueError(
                "Data was supplied by both data and gridOptions rowData. Use only one to load data into the grid."
            )
        data = grid_options.pop("rowData")
        if isinstance(data, str):
            data = pd.read_json(StringIO(data))
        else:
            # rowData given the AG Grid way: a list of record dicts.
            data = pd.DataFrame(data)
        column_types = data.dtypes

    # if rowId is not defined, create an unique row_id as the rows_hash
    if "getRowId" not in grid_options and data is not None:
        data = data.copy()
        data["::auto_unique_id::"] = list(
            map(str, range(data.shape[0]))
        )  ##pd.util.hash_pandas_object(data).astype(str)

    # NOTE: when use_json_serialization is True the frame is moved into
    # grid_options["rowData"] by the caller (AgGrid), which keeps a reference to
    # it so the response object can still expose a DataFrame.

    # process the JsCode Objects
    if unsafe_allow_jscode:
        walk_gridOptions(
            grid_options, lambda v: v.js_code if isinstance(v, JsCode) else v
        )

    _sanitize_nan_inf(grid_options)

    return data, grid_options, column_types


def update_event_name(event):
    """The AG Grid event name an ``update_on`` entry refers to.

    Entries are either a plain event name or an ``(event, debounce_ms)``
    tuple, and the two forms describe the same listener.
    """
    if isinstance(event, (tuple, list)):
        return event[0]
    return event


def dedupe_update_on(update_on):
    """Collapse ``update_on`` to one entry per AG Grid event.

    The frontend builds a fresh closure for every entry and hands each one to
    ``api.addEventListener``, which keys its listener set by function identity.
    Two entries for the same event therefore attach two live listeners, and
    every occurrence of that event runs the whole collector walk and the
    Streamlit state write twice.

    Order follows first appearance, so a caller's own ``update_on`` ordering
    survives. The spec kept is the *last* one seen, because that is the one
    contributed by update_mode: a bare "columnResized" from the caller loses
    to the ("columnResized", 300) that GridUpdateMode.COLUMN_RESIZED adds,
    and dropping the debounce would be the more surprising outcome.
    """
    order = []
    specs = {}
    for event in update_on:
        name = update_event_name(event)
        if name not in specs:
            order.append(name)
        specs[name] = event
    return [specs[name] for name in order]


# difflib similarity a name must reach before it is offered as "did you mean".
# The library default of 0.6 is too loose for a catalog of 107 names built from
# the same handful of words: it answers "dataChange" with "sortChanged" and
# "click" with "cellClicked", suggestions that share a suffix and nothing else
# and send the reader off to fix the wrong thing. 0.75 still catches every
# realistic way of misspelling a name that exists (a dropped trailing "d" as in
# "selectionChange", wrong case as in "selectionchanged", the on-prefixed form
# "onSelectionChanged" that the React props use) while refusing to guess for
# names that were never AG Grid events at all.
_SUGGESTION_CUTOFF = 0.75

# warnings.warn counts frames outward from the warn() call: 1 is this module, 2
# is AgGrid, 3 is the app line that called AgGrid. Only 3 is useful, because the
# message quotes an event name the app author typed and the fix is on their
# line; the internal frames say nothing they can act on.
#
# warnings.warn rather than a logger call because this reports caller error, so
# it should be filterable and escalatable to an exception with -W error. That
# brings the standard once-per-location cadence with it, which is the right
# trade: the first run after a typo shows it, and a diagnostic repeated on every
# Streamlit rerun forever would train people to ignore it.
_CALLER_STACKLEVEL = 3


def _suggest_event_name(name):
    """The event the caller probably meant, or None when guessing would mislead.

    Two things happen before difflib is consulted at all. React's props spell
    these events as onSelectionChanged, so an "on" prefix is stripped and tried
    as an exact match: "onRedoEnded" then resolves to "redoEnded" outright.
    Fuzzy matching gets that pair wrong, because "onRedoEnded" scores an
    identical 0.8 against both "redoEnded" and "undoEnded" and difflib breaks
    the tie lexicographically, answering "undoEnded" with total confidence.

    That tie is also why an ambiguous best match yields no suggestion. Naming
    one of two equally close events is a coin flip dressed up as advice, and
    sending someone to fix an event they never wrote is worse than saying
    nothing, which is the same reason the similarity cutoff is not looser.
    """
    if name.startswith("on") and len(name) > 2:
        unprefixed = name[2].lower() + name[3:]
        if unprefixed in GRID_EVENTS:
            return unprefixed

    # Sorted, not the frozenset itself: string hashing is salted per process, so
    # set iteration order changes between runs, and difflib's tie-breaking would
    # make an ambiguous suggestion vary from one run to the next.
    matches = difflib.get_close_matches(
        name, sorted(GRID_EVENTS), n=2, cutoff=_SUGGESTION_CUTOFF
    )
    if not matches:
        return None
    if len(matches) > 1:
        ratios = [difflib.SequenceMatcher(None, name, m).ratio() for m in matches]
        if ratios[0] == ratios[1]:
            return None
    return matches[0]


def validate_update_on(update_on):
    """Warn about ``update_on`` entries that can never fire.

    ``update_on`` names AG Grid events verbatim, and the frontend hands each one
    to ``api.addEventListener``, which accepts any string and silently keeps a
    listener for an event that will never be dispatched. A misspelling therefore
    produces a grid that simply does not update, which from the app author's
    side looks exactly like a broken component. This is the likely first mistake
    with the parameter: the ``GridUpdateMode`` flags it replaces were enum
    members, so the same typo used to be a NameError at the call site.

    Three kinds of entry cannot be relied on: names that are not AG Grid events
    at all, names that are real events dispatched on a ``Column`` or a
    ``RowNode`` rather than on the grid api (the only object ``update_on`` can
    attach to), and names AG Grid marks internal. Each gets its own message,
    because telling someone that ``widthChanged`` "is not an AG Grid event"
    would be plainly false and would send them looking for a typo that is not
    there.

    Nothing here raises, deliberately. The catalog is generated from the
    bundled AG Grid version and can lag a newer one, so treating an unlisted
    name as fatal would break a grid whose event is genuinely supported, which
    is a worse failure than the silent typo this replaces.
    """
    # A bare string is iterable, so it would otherwise be validated one
    # character at a time: update_on="selectionChanged" produced thirteen
    # warnings about events named 's', 'e', 'l' and so on, none of which said
    # the one useful thing. AgGrid wraps a string before calling this, so a
    # reader here is calling the function directly.
    if isinstance(update_on, str):
        warnings.warn(
            f"update_on should be a list of event names, not the bare string "
            f"{update_on!r}. A string is iterated character by character, so "
            "each letter would be treated as its own event name. Use "
            f"update_on=[{update_on!r}].",
            UserWarning,
            stacklevel=_CALLER_STACKLEVEL,
        )
        update_on = [update_on]

    for event in update_on:
        # update_event_name indexes [0], so an empty tuple would raise here.
        # Validation must never be the thing that turns a malformed update_on
        # into a traceback; the entry is left to the code that consumes it.
        if isinstance(event, (tuple, list)) and not event:
            continue
        name = update_event_name(event)
        # Anything that is not a string cannot be an event name, and some of
        # what update_event_name hands back (a dict from a nested list, say) is
        # not even hashable, so this guard also keeps the set lookups safe.
        if not isinstance(name, str) or name in GRID_EVENTS:
            continue

        if name in COLUMN_ONLY_EVENTS or name in ROW_NODE_ONLY_EVENTS:
            owner = "a Column instance" if name in COLUMN_ONLY_EVENTS else "a row node"
            warnings.warn(
                f"update_on entry {name!r} is a real ag-grid-community "
                f"{AG_GRID_VERSION} event, but it is dispatched on {owner} "
                "rather than on the grid, so it cannot be used with update_on "
                "and the grid will never update because of it.",
                UserWarning,
                stacklevel=_CALLER_STACKLEVEL,
            )
            continue

        if name in INTERNAL_EVENTS:
            warnings.warn(
                f"update_on entry {name!r} is an internal ag-grid-community "
                f"{AG_GRID_VERSION} event. It may well fire today, but AG Grid "
                "documents internal events as removable without notice and does "
                "not support listening for them, so a grid built on it can stop "
                "updating on any AG Grid upgrade. Prefer a public event.",
                UserWarning,
                stacklevel=_CALLER_STACKLEVEL,
            )
            continue

        message = (
            f"update_on entry {name!r} is not an AG Grid event (checked against "
            f"ag-grid-community {AG_GRID_VERSION}), so update_on will never "
            "fire for it and the grid will not update."
        )
        suggestion = _suggest_event_name(name)
        if suggestion:
            message += f" Did you mean {suggestion!r}?"
        warnings.warn(message, UserWarning, stacklevel=_CALLER_STACKLEVEL)


def parse_update_mode(update_mode: GridUpdateMode, update_on=None):
    def add_unique_update_event(update_on, event):
        if event not in update_on:
            update_on.append(event)

    if update_on is None:
        update_on = []

    if update_mode & GridUpdateMode.VALUE_CHANGED:
        add_unique_update_event(update_on, "cellValueChanged")
    if update_mode & GridUpdateMode.SELECTION_CHANGED:
        add_unique_update_event(update_on, "selectionChanged")
    if update_mode & GridUpdateMode.FILTERING_CHANGED:
        add_unique_update_event(update_on, "filterChanged")
    if update_mode & GridUpdateMode.SORTING_CHANGED:
        add_unique_update_event(update_on, "sortChanged")
    if update_mode & GridUpdateMode.COLUMN_RESIZED:
        add_unique_update_event(update_on, ("columnResized", 300))
    if update_mode & GridUpdateMode.COLUMN_MOVED:
        add_unique_update_event(update_on, ("columnMoved", 500))
    if update_mode & GridUpdateMode.COLUMN_PINNED:
        add_unique_update_event(update_on, "columnPinned")
    if update_mode & GridUpdateMode.COLUMN_VISIBLE:
        add_unique_update_event(update_on, "columnVisible")
    return dedupe_update_on(update_on)
