import logging
import typing
import warnings
from typing import Literal

import pandas as pd
import streamlit as st
from decouple import config

try:
    import pyarrow.lib
except ImportError:
    pyarrow = None
from st_aggrid import _compat
from st_aggrid.aggrid_utils import (
    _parse_data_and_grid_options,
    _sanitize_nan_inf,
    dedupe_update_on,
    parse_update_mode,
)
from st_aggrid.AgGridReturn import AgGridReturn
from st_aggrid.shared import (
    AgGridTheme,
    ColumnsAutoSizeMode,
    DataReturnMode,
    GridUpdateMode,
    JsCode,
    StAggridTheme,
)

# A library must not log through the root logger: root calls install a handler
# on first use and the record carries no module name, so the message shows up
# unattributed in the host app's console and cannot be silenced per package.
_LOGGER = logging.getLogger(__name__)

# Track shown deprecation warnings to avoid repetition in Streamlit
_shown_deprecation_warnings = set()

_RELEASE = config("AGGRID_RELEASE", default=True, cast=bool)

_component_func = None


def _get_component_func():
    """Lazily register and return the CCv2 component callable.

    Registration is deferred so the module can be imported outside
    of the Streamlit runtime (e.g. for testing or type checking).
    """
    global _component_func
    if _component_func is None:
        if not _RELEASE:
            warnings.warn("WARNING: ST_AGGRID is in development mode.")
        _component_func = _compat.component(
            "streamlit-aggrid-v2.st_aggrid",
            html='<div id="root"></div>',
            js="index-*.js",
            css="index-*.css",
        )
    return _component_func


def _on_grid_return_change():
    """Callback for when the grid return state changes in the frontend."""


def _reraise_with_hint(ex: Exception, hint: str):
    """Re-raise ``ex`` with an extra hint, preserving type and traceback.

    Rebuilding the exception with ``type(ex)(*ex.args)`` breaks for any
    exception whose constructor does not take its own args back (for example
    StreamlitDuplicateElementId or json.JSONDecodeError) and blows up on
    exceptions with empty args, destroying the original error. Mutating
    ``args`` in place skips the constructor entirely, so the type and the
    traceback both survive.

    The hint has to land in ``str(ex)`` to do any good: Streamlit renders the
    exception message and the formatted traceback, and neither one includes
    ``__notes__``. ``add_note`` would file the hint exactly where nobody can
    read it, and it is 3.11+ while this package supports 3.10, where falling
    back to a rebuilt RuntimeError destroyed the original exception type.
    Every branch below keeps the type and reaches ``str(ex)`` on 3.10.
    """
    if hint in str(ex):
        # Already annotated. The same exception object can cross more than one
        # boundary, and suffixes must not stack up.
        raise ex
    if not ex.args:
        # str(ex) is "" here, so the hint is the entire message.
        ex.args = (hint,)
    elif isinstance(ex.args[0], str):
        ex.args = (f"{ex.args[0]}. {hint}", *ex.args[1:])
    else:
        # A non-string first argument has to survive intact for callers that
        # read args[0] (json.JSONDecodeError carries the document and the
        # position there), so the hint goes on as an extra argument instead.
        # str() of a multi-arg exception is the repr of the whole tuple, so
        # the hint still reaches the browser.
        ex.args = (*ex.args, hint)
    raise ex


def AgGrid(
    data: pd.DataFrame | str | None = None,
    gridOptions: dict | None = None,
    height: int = 400,
    update_mode: GridUpdateMode
    | Literal[
        "MANUAL", "MODEL_CHANGED", "VALUE_CHANGED", "SELECTION_CHANGED", "GRID_CHANGED"
    ] = GridUpdateMode.NO_UPDATE,
    data_return_mode: DataReturnMode
    | Literal[
        "AS_INPUT", "FILTERED", "FILTERED_AND_SORTED", "MINIMAL", "CUSTOM"
    ] = DataReturnMode.FILTERED_AND_SORTED,
    allow_unsafe_jscode: bool = False,
    enable_enterprise_modules: bool
    | Literal["enterpriseOnly", "enterprise+AgCharts"] = False,
    license_key: str | None = None,
    conversion_errors: str = "coerce",
    columns_state=None,
    theme: str
    | StAggridTheme
    | Literal["streamlit", "quartz", "alpine", "balham", "material"] = "streamlit",
    custom_css=None,
    key: typing.Any = None,
    update_on=None,
    callback=None,
    show_toolbar: bool | None = None,
    show_search: bool = True,
    show_download_button: bool = True,
    custom_jscode_for_grid_return: JsCode = None,
    should_grid_return: JsCode = None,
    use_json_serialization: bool | Literal["auto"] = "auto",
    server_sync_strategy: Literal["client_wins", "server_wins"] = "client_wins",
    columns_auto_size_mode: ColumnsAutoSizeMode
    | Literal["NO_AUTOSIZE", "FIT_ALL_COLUMNS_TO_VIEW", "FIT_CONTENTS"]
    | int = None,
    **default_column_parameters,
) -> AgGridReturn:
    """Renders a DataFrame using AgGrid.

    Parameters
    ----------
    data : pd.DataFrame | pl.DataFrame | str | Path, optional
        The data to be displayed on the grid. Accepts:
            - Pandas or Polars DataFrames
            - Json string data in records format (list like [{column -> value}, … , {column -> value}])
            - Path to a json file with records

        Defaults to None.

    gridOptions : dict, optional
        Dictionary of AG Grid options. Full documentation at https://www.ag-grid.com/javascript-data-grid/grid-options/
        If None, default grid options will be infered with GridOptionsBuilder.from_dataframe().
        Defaults to None.

    key : Any, optional
        Streamlit widget key for maintaining state across reruns.
        It is highly recommended setting it for each grid.
        Defaults to None.

    height : int, optional
        Grid height in pixels. If None, Auto Height is enabled.
        See: https://www.ag-grid.com/react-data-grid/grid-size/#dom-layout
        Defaults to 400.

    update_mode : GridUpdateMode, optional
        DEPRECATED. Use update_on parameter instead.
        Defines how the grid sends results back to Streamlit. The events it
        implies are added on top of update_on.

        GridUpdateMode.MANUAL is exclusive: the update button in the toolbar
        becomes the only way the grid returns data, and the default update_on
        events (cellValueChanged, selectionChanged, filterChanged,
        sortChanged) are not attached. This matches v1 semantics. Pass
        update_on explicitly to keep extra triggers alongside the button;
        whatever you pass is used verbatim. show_toolbar is forced to True in
        this mode so the button is reachable.

        Defaults to GridUpdateMode.NO_UPDATE.

    data_return_mode : DataReturnMode, optional
        How data is retrieved from the grid:
            - AS_INPUT: Returns data as originally provided, includes edits
            - FILTERED: Returns filtered data in original order
            - FILTERED_AND_SORTED: Returns filtered and sorted data
            - MINIMAL: Returns a MinimalResponse. The frontend sends back only
              the displayed rows (after filter and sort) and the selected rows,
              with no node metadata, grid state or column state, so the wire
              payload stays small on wide or deep grids. Read it through
              .data / .selected_rows.
            - CUSTOM: Returns CustomResponse with user-defined data structure (requires custom_jscode_for_grid_return set)
        Defaults to DataReturnMode.FILTERED_AND_SORTED.

    allow_unsafe_jscode : bool, optional
        Allows JavaScript code injection in gridOptions. Required when using JsCode.
        Defaults to False.

    enable_enterprise_modules : bool | Literal['enterpriseOnly', 'enterprise+AgCharts'], optional
        Enables AG Grid Enterprise features (requires license):
            - True or 'enterpriseOnly': Enterprise modules only
            - 'enterprise+AgCharts': Enterprise + AgCharts modules
            - False: Community features only
        Defaults to False.

    license_key : str, optional
        License key for AG Grid Enterprise features.
        Defaults to None.

    conversion_errors : str, optional
        How to handle type conversion errors:
            - 'raise': Raises exception on conversion failure
            - 'coerce': Sets invalid values to NaT/NaN
            - 'ignore': Returns input unchanged on failure
        Defaults to 'coerce'.

    columns_state : dict, optional
        Initial column state (visibility, order, width, etc.).
        Format follows https://www.ag-grid.com/javascript-data-grid/column-state/#reference-state-applyColumnState
        Defaults to None.

    columns_auto_size_mode : ColumnsAutoSizeMode | str | int, optional
        How columns are auto-sized on first render. Maps to AG Grid's native
        gridOptions.autoSizeStrategy:
            - NO_AUTOSIZE: no automatic sizing (clears any autoSizeStrategy)
            - FIT_ALL_COLUMNS_TO_VIEW: fit all columns into the grid width
              ({"type": "fitGridWidth"})
            - FIT_CONTENTS: size each column to the wider of its header and
              rendered cell content ({"type": "fitCellContents"})
        When set, this overrides any autoSizeStrategy already present in
        gridOptions (including the fitGridWidth default that
        GridOptionsBuilder.from_dataframe injects). Leave as None to keep
        gridOptions untouched. Defaults to None.

    theme : str | AgGridTheme | StAggridTheme, optional
        Grid theme. Strings must be one of the AgGridTheme members:
            - 'streamlit': Matches Streamlit's default styling
            - 'quartz': AG Grid quartz theme
            - 'alpine': AG Grid alpine theme
            - 'balham': AG Grid balham theme
            - 'material': AG Grid material theme
        Pass a StAggridTheme instance to customize a base theme with
        .withParams()/.withParts(). Defaults to 'streamlit'.

    custom_css : dict, optional
        Custom CSS rules injected into the component iframe.
        Defaults to None.

    update_on : list[str | tuple[str, int]], optional
        AG Grid events that trigger data return to Streamlit.
        Events: https://www.ag-grid.com/javascript-data-grid/grid-events/
        Use tuple (event_name, debounce_ms) for debounced events.

        Example: ['cellValueChanged', ('columnResized', 500)]
        Defaults to ['cellValueChanged', 'selectionChanged', 'filterChanged', 'sortChanged'],
        except when update_mode is GridUpdateMode.MANUAL, where the default is
        no events at all so the update button is the only return path.

    callback : callable, optional
        Function called when grid data changes. Receives AgGridReturn object.
        Requires key parameter to be set.
        Defaults to None.

    show_toolbar : bool, optional
        Show toolbar above the grid.
        Defaults to None, which means False, except when update_mode is
        MANUAL, where it is forced to True because the manual update button
        lives in the toolbar and would otherwise be unreachable. Passing False
        explicitly under MANUAL is still overridden, but logs a warning naming
        the conflict instead of discarding the argument silently.

    show_search : bool, optional
        Show search bar in toolbar.
        Defaults to True.

    show_download_button : bool, optional
        Show CSV download button in toolbar.
        Defaults to True.

    custom_jscode_for_grid_return : JsCode, optional
        JavaScript function for custom data collection when using DataReturnMode.CUSTOM.
        Receives: {streamlitRerunEventTriggerName, eventData}
        Required when data_return_mode is DataReturnMode.CUSTOM.

        Example:
            JsCode('''
            function({streamlitRerunEventTriggerName, eventData}) {
                let api = eventData.api;
                return {
                    columnNames: api.getAllDisplayedColumns().map(c => c.colDef.headerName),
                    rowCount: api.getDisplayedRowCount(),
                    selectedCount: api.getSelectedRows().length
                };
            }
            ''')

        Defaults to None.

    should_grid_return : JsCode, optional
        JavaScript function that determines whether the grid should return data to Streamlit.
        This function is called before each potential data return and can be used to
        conditionally prevent updates based on grid state or event data.
        The function receives: {streamlitRerunEventTriggerName, eventData}
        Should return: boolean (true to proceed with data return, false to skip)

        Example:
        should_return = JsCode('''
        function should_return({streamlitRerunEventTriggerName, eventData}){
                //returns only if column Move has finished
                if (streamlitRerunEventTriggerName == 'columnMoved'){
                    return eventData.finished;
                }
            return true;
            }
        ''')

        Defaults to None.

    use_json_serialization : bool | Literal['auto'], optional
        Controls JSON serialization behavior for complex data types:

        - 'auto' (default): Automatically detect PyArrow conversion errors and fallback
          to JSON serialization. User-friendly option that handles complex data seamlessly.
        - True: Always use JSON serialization for non-primitive data types (lists, dicts, sets).
          Converts complex objects to JSON strings before rendering.
        - False: Never use JSON serialization. Will raise PyArrow conversion errors
          for non-hashable or mixed-type data.

        Use 'auto' for best user experience, True for consistent JSON behavior,
        or False for strict type checking.
        Defaults to 'auto'.

    server_sync_strategy : Literal['client_wins', 'server_wins'], optional
        Controls data synchronization behavior between server and client:

        - 'client_wins' (default): After first edit, grid ignores server data updates
          and maintains local edits. Standard behavior for interactive editing.
        - 'server_wins': Server data always overwrites the grid, including edited cells.
          Useful when server data should be the single source of truth.

        When using 'server_wins', consider intercepting grid results with session_state
        to preserve user edits before re-rendering.
        Defaults to 'client_wins'.

    **default_column_parameters
        Additional parameters passed to gridOptions.defaultColDef.

    Returns
    -------
    AgGridReturn | CustomResponse
        The return type depends on the data_return_mode:

        - AS_INPUT, FILTERED, FILTERED_AND_SORTED: Returns AgGridReturn object with full grid data
        - MINIMAL: Returns MinimalResponse object with lightweight access to raw data
        - CUSTOM: Returns CustomResponse object with user-defined data structure

        AgGridReturn provides properties like:
            - .data: DataFrame with grid data
            - .selected_data: DataFrame with selected rows
            - .grid_state: Grid state information
            - .columns_state: Column configuration state

        CustomResponse provides safe access methods:
            - .raw_data: Access to the raw returned data
            - .get(key, default): Safe key access with default value
            - Standard dictionary access with helpful error messages
    """

    ###Deprecation Warnings
    # Check for deprecated reload_data parameter
    if "reload_data" in default_column_parameters:
        default_column_parameters.pop("reload_data")
        warning_key = "reload_data_deprecated"
        if warning_key not in _shown_deprecation_warnings:
            warnings.warn(
                "The 'reload_data' parameter has been removed and has no effect.",
                DeprecationWarning,
                stacklevel=2,
            )
            _shown_deprecation_warnings.add(warning_key)

    try_to_convert_back_to_original_types: bool = True
    # Deprecated parameter handling for backward compatibility
    if "try_to_convert_back_to_original_types" in default_column_parameters:
        try_to_convert_back_to_original_types = default_column_parameters.pop(
            "try_to_convert_back_to_original_types"
        )
        warning_key = "try_to_convert_back_to_original_types_deprecated"
        if warning_key not in _shown_deprecation_warnings:
            warnings.warn(
                "The 'try_to_convert_back_to_original_types' parameter is deprecated and will be removed in a future version. "
                "The component now handles type preservation automatically where appropriate.",
                DeprecationWarning,
                stacklevel=2,
            )
            _shown_deprecation_warnings.add(warning_key)

    ##Parses Themes
    if isinstance(theme, StAggridTheme):
        themeObj = theme

    elif isinstance(theme, AgGridTheme):
        themeObj: StAggridTheme = StAggridTheme(None)
        themeObj["themeName"] = theme.value

    elif isinstance(theme, str):
        # Unknown names used to fall through to AG Grid's balham theme without
        # any warning, so validate against the themes the frontend knows.
        if theme not in AgGridTheme:
            raise ValueError(
                f"{theme} is not a valid theme. Available options: "
                f"{[t.value for t in AgGridTheme]}"
            )
        themeObj = StAggridTheme(None)
        themeObj["themeName"] = theme

    elif theme is None:
        themeObj = StAggridTheme(None)
        themeObj["themeName"] = "streamlit"
    else:
        raise ValueError(
            f"{theme} is not valid. Available options: {AgGridTheme.__members__}"
        )

    # Parse return Mode
    if not isinstance(data_return_mode, (str, DataReturnMode)):
        raise ValueError(
            "DataReturnMode should be either a DataReturnMode enum value or a string."
        )
    elif isinstance(data_return_mode, str):
        try:
            data_return_mode = DataReturnMode[data_return_mode.upper()]
        except Exception:
            raise ValueError(f"{data_return_mode} is not valid.")

    # Parse update Mode
    if not isinstance(update_mode, (str, GridUpdateMode)):
        raise ValueError(
            "GridUpdateMode should be either a valid GridUpdateMode enum value or string"
        )
    elif isinstance(update_mode, str):
        try:
            update_mode = GridUpdateMode[update_mode.upper()]
        except Exception:
            raise ValueError(f"{update_mode} is not valid.")

    # Add deprecation warning for GridUpdateMode
    if update_mode != GridUpdateMode.NO_UPDATE:
        warning_key = "GridUpdateMode_deprecated"
        if warning_key not in _shown_deprecation_warnings:
            warnings.warn(
                "GridUpdateMode is deprecated and will be removed in a future version. "
                "Use the 'update_on' parameter instead to specify which events should trigger updates.",
                DeprecationWarning,
                stacklevel=2,
            )
            _shown_deprecation_warnings.add(warning_key)

    update_on_was_explicit = update_on is not None
    if update_on is None:
        update_on = ["cellValueChanged", "selectionChanged", "filterChanged", "sortChanged"]

    manual_update = False
    if update_mode:
        update_on = list(update_on)
        if update_mode == GridUpdateMode.MANUAL:
            manual_update = True
            # MANUAL is exclusive: the update button is the only return path.
            # The default event list would otherwise keep sending data back on
            # every edit, selection, filter and sort, which defeats the mode.
            # An explicit update_on is honored, so callers who want extra
            # triggers alongside the button can still ask for them.
            if not update_on_was_explicit:
                update_on = []
            # The manual update button lives inside the toolbar, so a hidden
            # toolbar would leave a manual-update grid with no way to update.
            if show_toolbar is False:
                _LOGGER.warning(
                    "show_toolbar=False conflicts with update_mode=MANUAL and is "
                    "being overridden to True: the manual update button lives in "
                    "the toolbar, so hiding it would leave the grid with no way "
                    "to return data. Drop update_mode=MANUAL, or pass update_on "
                    "explicitly, if the toolbar has to stay hidden."
                )
            show_toolbar = True
        else:
            update_on.extend(parse_update_mode(update_mode))

    # One listener per event. The frontend attaches a fresh closure for every
    # entry and AG Grid keys listeners by function identity, so a duplicated
    # entry means the collector walk and the Streamlit state write both run
    # twice per event. update_mode re-adds the same defaults update_on already
    # carries, so MODEL_CHANGED, VALUE_CHANGED and GRID_CHANGED all did this.
    update_on = dedupe_update_on(update_on)

    # None is the "caller said nothing" sentinel used above to tell an explicit
    # show_toolbar=False from the default. The frontend reads a missing value as
    # true (`show_toolbar ?? true`), so it must be resolved before it goes out.
    if show_toolbar is None:
        show_toolbar = False

    # Validate CUSTOM mode parameters
    if data_return_mode == DataReturnMode.CUSTOM:
        if custom_jscode_for_grid_return is None:
            raise ValueError(
                "custom_jscode_for_grid_return parameter is required when using DataReturnMode.CUSTOM"
            )
        if not isinstance(custom_jscode_for_grid_return, JsCode):
            raise ValueError(
                "custom_jscode_for_grid_return must be a JsCode object when using DataReturnMode.CUSTOM"
            )

    # Process JsCode for CUSTOM mode
    original_custom_jscode_for_grid_return = custom_jscode_for_grid_return
    if custom_jscode_for_grid_return is not None:
        custom_jscode_for_grid_return = custom_jscode_for_grid_return.js_code
        allow_unsafe_jscode = True
    
    # Process JsCode for should_grid_return
    if should_grid_return is not None:
        should_grid_return = should_grid_return.js_code
        allow_unsafe_jscode = True

    # These are consumed here, not by AG Grid. Pop them before the parse call
    # or GridOptionsBuilder.from_dataframe warns that they are not valid
    # gridOptions even though both are honored below.
    fit_columns_on_grid_load = default_column_parameters.pop(
        "fit_columns_on_grid_load", False
    )
    pro_assets = default_column_parameters.pop("pro_assets", None)
    debug = default_column_parameters.pop("debug", False)

    # parse data and gridOptions
    data, gridOptions, frame_dtypes = _parse_data_and_grid_options(
        data,
        gridOptions,
        default_column_parameters,
        allow_unsafe_jscode,
        use_json_serialization,
    )

    # JSON serialization hands the frame to the grid as a JSON string on
    # gridOptions.rowData. Keep a reference to it so the response object still
    # exposes a DataFrame instead of silently switching .data to a str.
    json_serialized_frame = None
    if use_json_serialization is True and data is not None:
        gridOptions["rowData"] = data.to_json(orient="records")
        json_serialized_frame = data
        data = None

    # The frame that was actually handed to the grid, whichever serialization
    # path was taken. Everything downstream that reasons about "the data" (dtype
    # round-tripping, the change-detection hash, the response object) has to go
    # through this: under use_json_serialization=True the frame lives in
    # gridOptions["rowData"] and ``data`` is None, and testing ``data`` alone
    # silently degraded both the dtypes and the hash.
    sent_frame = data if data is not None else json_serialized_frame

    if not isinstance(sent_frame, pd.DataFrame):
        try_to_convert_back_to_original_types = False

    custom_css = custom_css or {}

    if height is None:
        gridOptions["domLayout"] = "autoHeight"

    if fit_columns_on_grid_load:
        warnings.warn(
            "fit_columns_on_grid_load is deprecated. Use gridOptions autoSizeStrategy instead.",
            DeprecationWarning,
        )
        gridOptions["autoSizeStrategy"] = {"type": "fitGridWidth"}

    # Map columns_auto_size_mode to AG Grid's native autoSizeStrategy. When set
    # explicitly it overrides any strategy already on gridOptions, including the
    # fitGridWidth default that GridOptionsBuilder.from_dataframe injects (which
    # otherwise collapses wide grids to minWidth and ignores FIT_CONTENTS).
    if columns_auto_size_mode is not None:
        if isinstance(columns_auto_size_mode, str):
            try:
                columns_auto_size_mode = ColumnsAutoSizeMode[
                    columns_auto_size_mode.upper()
                ]
            except KeyError:
                raise ValueError(
                    f"{columns_auto_size_mode} is not a valid ColumnsAutoSizeMode. "
                    f"Available options: {list(ColumnsAutoSizeMode.__members__)}"
                )
        else:
            try:
                columns_auto_size_mode = ColumnsAutoSizeMode(columns_auto_size_mode)
            except ValueError:
                raise ValueError(
                    f"{columns_auto_size_mode} is not a valid ColumnsAutoSizeMode. "
                    f"Available options: {list(ColumnsAutoSizeMode.__members__)}"
                )

        if columns_auto_size_mode == ColumnsAutoSizeMode.NO_AUTOSIZE:
            gridOptions.pop("autoSizeStrategy", None)
        elif columns_auto_size_mode == ColumnsAutoSizeMode.FIT_ALL_COLUMNS_TO_VIEW:
            gridOptions["autoSizeStrategy"] = {"type": "fitGridWidth"}
        elif columns_auto_size_mode == ColumnsAutoSizeMode.FIT_CONTENTS:
            gridOptions["autoSizeStrategy"] = {"type": "fitCellContents"}

    # Create collector based solely on data_return_mode
    if data_return_mode == DataReturnMode.MINIMAL:
        from .collectors.minimal import MinimalCollector

        collector = MinimalCollector()
    elif data_return_mode == DataReturnMode.CUSTOM:
        from .collectors.custom import CustomCollector

        collector = CustomCollector(original_custom_jscode_for_grid_return.js_code)
    else:
        # Use LegacyCollector for AS_INPUT, FILTERED, FILTERED_AND_SORTED
        from .collectors.legacy import LegacyCollector

        collector = LegacyCollector(
            data_return_mode=data_return_mode,
            try_to_convert_back_to_original_types=try_to_convert_back_to_original_types,
            conversion_errors=conversion_errors,
            # Dtype back-conversion is gated on frame_dtypes being set, so
            # honoring the (deprecated) opt-out means withholding them here.
            frame_dtypes=frame_dtypes
            if try_to_convert_back_to_original_types
            else None,
        )

    # Create initial response object that callbacks can safely reference
    original_data = None
    if sent_frame is not None:
        original_data = (
            sent_frame.drop("::auto_unique_id::", axis="columns")
            if "::auto_unique_id::" in sent_frame.columns
            else sent_frame
        )

    response = collector.create_initial_response(
        original_data=original_data,
        grid_options=gridOptions,
        try_to_convert_back_to_original_types=try_to_convert_back_to_original_types,
        conversion_errors=conversion_errors,
    )

    if callback and not key:
        raise ValueError("Component key must be set to use a callback.")

    elif key and not callback:
        # This allows the table to keep its state up to date (eg #176)
        def _inner_callback():
            session_value = st.session_state.get(key)
            _ = session_value.grid_return if session_value else None

    elif callback and key:
        # User defined callback
        def _inner_callback():
            session_value = st.session_state.get(key)
            component_value = session_value.grid_return if session_value else None
            # Update the existing response object with new component value and store the wrapped response
            updated_response = collector.update_response(response, component_value)
            #updating the session key causes the callback to trigger always. Hot fix in 1.2.0.post2
            #st.session_state[key] = updated_response
            return callback(updated_response)
    else:
        _inner_callback = None

    def _compute_data_hash(df):
        if df is None:
            return ""

        try:
            return str(pd.util.hash_pandas_object(df).sum())
        except TypeError:
            _LOGGER.warning(
                "DataFrame contains non-hashable data, attempting type conversion..."
            )

            try:
                df_copy = df.copy()
                for col in df_copy.columns:
                    df_copy[col] = df_copy[col].apply(
                        lambda x: tuple(x)
                        if isinstance(x, list)
                        else frozenset(x)
                        if isinstance(x, set)
                        else frozenset(x.items())
                        if isinstance(x, dict)
                        else x
                    )
                return str(pd.util.hash_pandas_object(df_copy).sum())
            except (TypeError, ValueError, AttributeError) as e:
                _LOGGER.warning(
                    f"Type conversion failed ({e}), falling back to string-based hashing..."
                )
                return str(hash(df.to_string()))

    # Hash the frame that is actually on the wire, not the ``data`` local: the
    # frontend refreshes rows only when data_hash changes, so hashing None under
    # use_json_serialization=True pinned the hash at "" and froze the grid on
    # whatever rows it mounted with.
    data_hash = _compute_data_hash(sent_frame)

    # In CCv2, all data goes through JSON via the `data=` parameter.
    # Convert DataFrame to records for JSON serialization. Missing values
    # (NaN/NaT/Inf) must be sanitized to None here: Streamlit serializes the
    # payload with NaN/Infinity tokens that the frontend JSON.parse rejects,
    # which would otherwise prevent the grid from rendering at all.
    if data is not None and use_json_serialization is not True:
        row_data = _sanitize_nan_inf(data.to_dict("records"))
    else:
        row_data = None

    component_data = {
        "row_data": row_data,
        "data_hash": data_hash,
        "gridOptions": gridOptions,
        "height": height,
        "data_return_mode": data_return_mode,
        "frame_dtypes": str(frame_dtypes),
        "allow_unsafe_jscode": allow_unsafe_jscode,
        "columns_state": columns_state,
        "custom_css": custom_css,
        "enable_enterprise_modules": enable_enterprise_modules,
        "license_key": license_key,
        "manual_update": manual_update,
        "pro_assets": pro_assets,
        "show_download_button": show_download_button,
        "show_search": show_search,
        "show_toolbar": show_toolbar,
        "custom_jscode_for_grid_return": custom_jscode_for_grid_return,
        "should_grid_return": should_grid_return,
        "theme": themeObj,
        "debug": debug,
        "update_on": update_on,
        "use_json_serialization": use_json_serialization,
        "server_sync_strategy": server_sync_strategy,
    }

    try:
        result = _get_component_func()(
            data=component_data,
            key=key,
            on_grid_return_change=_inner_callback or _on_grid_return_change,
        )
        component_value = result.grid_return if result else None
    except Exception as ex:
        error_msg = str(ex)
        is_serialization_error = (
            "is not JSON serializable" in error_msg
            or "serialize" in error_msg.lower()
        )

        if use_json_serialization == "auto" and data is not None and is_serialization_error:
            _LOGGER.warning(
                f"JSON serialization failed, retrying with explicit JSON conversion: {error_msg}"
            )
            # Retry with JSON serialization enabled
            component_data["use_json_serialization"] = True
            component_data["row_data"] = None
            if "rowData" not in gridOptions and data is not None:
                gridOptions["rowData"] = data.to_json(orient="records")
            result = _get_component_func()(
                data=component_data,
                key=key,
                on_grid_return_change=_inner_callback or _on_grid_return_change,
            )
            component_value = result.grid_return if result else None
        else:
            _reraise_with_hint(
                ex,
                "If you're using custom JsCode objects on gridOptions, ensure that allow_unsafe_jscode is True.",
            )

    # Update the response object with final component data
    try:
        response = collector.update_response(response, component_value)
    except Exception as ex:
        # Enhanced error message for collector issues
        hint = f"Error in {collector.__class__.__name__} processing."
        if data_return_mode == DataReturnMode.CUSTOM:
            hint += " Check your custom_jscode_for_grid_return JsCode implementation."
        _reraise_with_hint(ex, hint)

    return response
