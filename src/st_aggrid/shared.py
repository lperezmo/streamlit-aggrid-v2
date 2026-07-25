import json
import pathlib
from collections.abc import Mapping
from enum import Enum, EnumMeta, Flag, IntEnum, auto
from typing import Literal

DEFAULT_COLUMN_PROPS = [
    "cellDataType",
    "checkboxSelection",
    "suppressNavigable",
    "editable",
    "cellEditorPopupPosition",
    "singleClickEdit",
    "useValueParserForImport",
    "autoHeaderHeight",
    "suppressHeaderMenuButton",
    "suppressHeaderFilterButton",
    "suppressHeaderContextMenu",
    "headerCheckboxSelectionFilteredOnly",
    "headerCheckboxSelectionCurrentPageOnly",
    "lockPinned",
    "enablePivot",
    "autoHeight",
    "wrapText",
    "enableCellChangeFlash",
    "rowDrag",
    "rowGroup",
    "enableRowGroup",
    "enableValue",
    "defaultAggFunc",
    "sortable",
    "unSortIcon",
    "resizable",
    "suppressSizeToFit",
    "suppressAutoSize",
    "marryChildren",
    "suppressStickyLabel",
    "openByDefault",
    "suppressColumnsToolPanel",
    "suppressFiltersToolPanel",
    "suppressSpanHeaderHeight",
    "filter",
]


# gridOptions.json and columnProps.json were scraped from the AG Grid docs,
# https://ag-grid.com/react-data-grid/grid-options/ and .../column-properties/,
# and are checked in as snapshots. There is no automated refresh: the scraper
# that produced them selected on hashed CSS classes from the docs build and
# stopped matching long ago. Regenerating means writing the extraction against
# whatever the page looks like at the time.
def getAllGridOptions():
    jsonRoot = pathlib.Path(__file__).parent / "json"
    with open(jsonRoot / "gridOptions.json") as f:
        return json.load(f)


def getAllColumnProps():
    jsonRoot = pathlib.Path(__file__).parent / "json"
    with open(jsonRoot / "columnProps.json") as f:
        return json.load(f)


class MetaEnum(EnumMeta):
    def __contains__(cls, item):
        try:
            cls(item)
        except ValueError:
            return False
        return True


class BaseEnum(Enum, metaclass=MetaEnum):
    pass


class GridUpdateMode(Flag):
    NO_UPDATE = auto()
    MANUAL = auto()
    VALUE_CHANGED = auto()
    SELECTION_CHANGED = auto()
    FILTERING_CHANGED = auto()
    SORTING_CHANGED = auto()
    COLUMN_RESIZED = auto()
    COLUMN_MOVED = auto()
    COLUMN_PINNED = auto()
    COLUMN_VISIBLE = auto()
    MODEL_CHANGED = (
        VALUE_CHANGED | SELECTION_CHANGED | FILTERING_CHANGED | SORTING_CHANGED
    )
    COLUMN_CHANGED = COLUMN_RESIZED | COLUMN_MOVED | COLUMN_VISIBLE | COLUMN_PINNED
    GRID_CHANGED = MODEL_CHANGED | COLUMN_CHANGED


class DataReturnMode(str, Enum):
    AS_INPUT = "AS_INPUT"
    FILTERED = "FILTERED"
    FILTERED_AND_SORTED = "FILTERED_AND_SORTED"
    MINIMAL = "MINIMAL"
    CUSTOM = "CUSTOM"


class ColumnsAutoSizeMode(IntEnum):
    NO_AUTOSIZE = 0
    FIT_ALL_COLUMNS_TO_VIEW = 1
    FIT_CONTENTS = 2


class ExcelExportMode(BaseEnum):
    NONE = "NONE"
    MANUAL = "MANUAL"  # Add a download button to the grid
    FILE_BLOB_IN_GRID_RESPONSE = "FILE_BLOB_IN_GRID_RESPONSE"  # include in grid's return an Excel Blob Property with file binary encoded as B64 String
    TRIGGER_DOWNLOAD = "TRIGGER_DOWNLOAD"  # After Grid Refreshes triggers the download.
    SHEET_BLOB_IN_GRID_RESPONSE = "SHEET_BLOB_IN_GRID_RESPONSE"  # include in grid's return a SheetlBlob Property with sheet binary encoded as B64 String. Meant to be used with MULTIPLE
    MULTIPLE_SHEETS = "MULTIPLE_SHEETS"  # Triggers the download and add other B64 encoded sheets. Send sheets as a list using excel_export_extra_sheets parameter


# stole from https://github.com/andfanilo/streamlit-echarts/blob/master/streamlit_echarts/frontend/src/utils.js Thanks andfanilo
class JsCode:
    def __init__(self, js_code: str):
        """Wrapper around a js function to be injected on gridOptions.
        code is not checked at all.
        set allow_unsafe_jscode=True on AgGrid call to use it.
        Code is rebuilt on client using new Function Syntax (https://javascript.info/new-function)

        Args:
            js_code (str): javascript function code as str
        """
        import re

        match_js_comment_expression = r"\/\*[\s\S]*?\*\/|([^\\:]|^)\/\/.*$"
        js_code = re.sub(
            re.compile(match_js_comment_expression, re.MULTILINE), r"\1", js_code
        )

        js_placeholder = "::JSCODE::"
        one_line_jscode = re.sub(r"\s+|\r\s*|\n+", " ", js_code, flags=re.MULTILINE)

        self.js_code = f"{js_placeholder}{one_line_jscode}{js_placeholder}"


def walk_gridOptions(go, func):
    """Recursively walk grid options applying func at each leaf node

    Args:
        go (dict): gridOptions dictionary
        func (callable): a function to apply at leaf nodes
    """
    from collections.abc import Mapping

    # Mappings and lists need different key sets: enumerating a list yields
    # (index, element) pairs, so indexing it by the element blows up on nested
    # lists and skips scalar elements (leaving JsCode objects unconverted).
    if isinstance(go, Mapping):
        keys = list(go)
    elif isinstance(go, list):
        keys = range(len(go))
    else:
        return

    for k in keys:
        value = go[k]
        if isinstance(value, (Mapping, list)):
            walk_gridOptions(value, func)
        else:
            go[k] = func(value)


# add deprecation note
class AgGridTheme(BaseEnum):
    STREAMLIT = "streamlit"
    QUARTZ = "quartz"
    ALPINE = "alpine"
    BALHAM = "balham"
    MATERIAL = "material"


# suclassing a dict because it is JSON serializable.
class StAggridTheme(dict):
    def __init__(self, base: Literal["quartz", "alpine", "balham", "material"] | None = None):
        super()

        self["params"] = {}
        self["parts"] = []
        # themeName must always be set: the frontend theme parser falls back to
        # balham for an undefined name, silently discarding withParams/withParts.
        self["themeName"] = "custom"
        if base:
            self.base(base)

    def base(self, base: Literal["quartz", "alpine", "balham", "material"]):
        self["base"] = base

    def withParams(self, **params: Mapping[str, str | int]):
        self["params"].update(params)
        return self

    def withParts(self, *parts: list[str]):
        self["parts"] = list(set(self["parts"]).union(set(parts)))
        return self
