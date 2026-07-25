import json
import math
import os
from collections.abc import Mapping
from io import StringIO
from pathlib import Path

import pandas as pd

from st_aggrid.grid_options_builder import GridOptionsBuilder
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
        pass
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
            # converts date columns to iso format. Missing values must stay
            # empty: pd.NaT.isoformat() returns the string "NaT", which would
            # be rendered literally in cells, quick search and CSV export.
            for c, d in data.dtypes.items():
                if d.kind == "M":
                    data[c] = data[c].apply(
                        lambda s: None if pd.isna(s) else s.isoformat()
                    )

        # if there is data and no grid options, create grid options from the data
        if not grid_options:
            gb = GridOptionsBuilder.from_dataframe(data, **default_column_parameters)
            grid_options = gb.build()

        # computes rows data types before adding id column
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
