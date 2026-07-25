"""CCv2 e2e tests.

These tests target the Custom Components v2 DOM directly (no iframe).
Each grid is wrapped inside a `.st-key-<key>` div produced by Streamlit's
key= prop, and the CCv2 component mounts at `.stBidiComponent` inside it.
AG Grid then renders `.ag-root` etc. directly in the page DOM.
"""

import re
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from e2e_utils import StreamlitRunner

# Selects this file into the e2e CI job and out of the browser-less one.
pytestmark = pytest.mark.browser

ROOT_DIRECTORY = Path(__file__).parent.parent.absolute()
FIXTURE_APP = ROOT_DIRECTORY / "test" / "ccv2_e2e_app.py"

# Every assertion that waits on a Streamlit rerun is racing a full round trip:
# grid event -> websocket -> script rerun -> re-render of every grid on the
# fixture page. The page carries a dozen AG Grid instances behind a 6 MB
# bundle, and the default 5s expect timeout is close enough to that round trip
# to flake. This is a wait ceiling, not a delay: passing assertions still
# return as soon as the value lands.
expect.set_options(timeout=20_000)


@pytest.fixture(autouse=True, scope="module")
def streamlit_app():
    with StreamlitRunner(FIXTURE_APP) as runner:
        yield runner


@pytest.fixture(autouse=True, scope="function")
def go_to_app(page: Page, streamlit_app: StreamlitRunner):
    page.goto(streamlit_app.server_url)
    # Wait for the first grid to be attached so subsequent assertions don't
    # race against initial Streamlit hydration. The generous timeout absorbs
    # cold starts (first page load after the server boots plus a fresh
    # Chromium), which routinely blow the default 5s and flake the suite.
    expect(page.locator(".st-key-grid_from_dataframe .stBidiComponent")).to_be_attached(
        timeout=15_000
    )


def _grid(page: Page, key: str):
    """Return a locator scoped to the CCv2 component for the given grid key."""
    return page.locator(f".st-key-{key} .stBidiComponent")


def test_ccv2_component_attached(page: Page):
    """All grids on the page mount a CCv2 component (no iframe)."""
    for key in (
        "grid_from_dataframe",
        "grid_from_json",
        "grid_options_only",
        "empty_grid",
        "roundtrip_grid",
        "missing_values_grid",
    ):
        expect(_grid(page, key)).to_be_attached()
    # Make sure no iframe was created (would indicate a regression to CCv1)
    expect(page.locator(".st-key-grid_from_dataframe iframe")).to_have_count(0)


def test_initialize_from_dataframe(page: Page):
    grid = _grid(page, "grid_from_dataframe")
    expect(grid.locator(".ag-root")).to_be_visible()
    expect(grid.locator(".ag-header-cell-text").nth(0)).to_have_text("names")
    expect(grid.locator(".ag-header-cell-text").nth(1)).to_have_text("ages")
    expect(grid.locator(".ag-row")).to_have_count(3)


def test_initialize_from_json(page: Page):
    grid = _grid(page, "grid_from_json")
    expect(grid.locator(".ag-root")).to_be_visible()
    expect(grid.locator(".ag-header-cell-text").nth(0)).to_have_text("First Name")
    expect(grid.locator(".ag-header-cell-text").nth(1)).to_have_text("Years")
    expect(grid.locator(".ag-row")).to_have_count(3)
    first_row_cells = grid.locator(".ag-row").nth(0).locator(".ag-cell")
    expect(first_row_cells.nth(0)).to_have_text("alice")
    expect(first_row_cells.nth(1)).to_have_text("25")


def test_initialize_grid_options_only(page: Page):
    """No row data + columnDefs should still render headers."""
    grid = _grid(page, "grid_options_only")
    expect(grid.locator(".ag-root")).to_be_visible()
    expect(grid.locator(".ag-header-cell-text").nth(0)).to_have_text("names")
    expect(grid.locator(".ag-header-cell-text").nth(1)).to_have_text("ages")
    expect(grid.locator(".ag-row")).to_have_count(0)


def test_initialize_empty(page: Page):
    """Empty grid (no data, no options) still mounts the grid container."""
    grid = _grid(page, "empty_grid")
    expect(grid.locator(".ag-root")).to_be_visible()


def test_grid_data_roundtrip(page: Page):
    """Grid data is echoed back to Python and rendered in the page."""
    grid = _grid(page, "roundtrip_grid")
    expect(grid.locator(".ag-root")).to_be_visible()
    expect(grid.locator(".ag-row")).to_have_count(3)

    roundtrip = page.get_by_test_id("roundtrip-data")
    expect(roundtrip).to_be_visible()
    expect(roundtrip).to_contain_text("alice")
    expect(roundtrip).to_contain_text("bob")
    expect(roundtrip).to_contain_text("charlie")


def test_renders_with_missing_values(page: Page):
    """A DataFrame with None/NaN cells must still render the grid.

    Regression guard for streamlit/streamlit#15435: missing numeric values
    are stored by pandas as float NaN, which previously serialized to a bare
    `NaN` token that the frontend JSON.parse rejected, leaving the grid
    unmounted. The grid must mount and show every row.
    """
    grid = _grid(page, "missing_values_grid")
    expect(grid.locator(".ag-root")).to_be_visible()
    expect(grid.locator(".ag-header-cell-text").nth(0)).to_have_text("text")
    expect(grid.locator(".ag-header-cell-text").nth(1)).to_have_text("int")
    expect(grid.locator(".ag-row")).to_have_count(4)
    # The populated cells still carry their values.
    expect(grid.locator(".ag-cell").filter(has_text="abc")).to_have_count(1)
    expect(grid.locator(".ag-cell").filter(has_text="35")).to_have_count(1)


def test_sort_by_header_click(page: Page):
    """Clicking the Score column header cycles through AG Grid's sort states.

    We assert on `aria-sort` rather than the row order because the default
    `update_on` set doesn't include `sortChanged`, so the sort applies in
    the browser but Streamlit may rerun and re-seed the row data
    asynchronously. The header attribute is the canonical signal that AG
    Grid registered the click.
    """
    grid = _grid(page, "roundtrip_grid")
    expect(grid.locator(".ag-root")).to_be_visible()
    expect(grid.locator(".ag-row")).to_have_count(3)

    score_header = grid.locator(".ag-header-cell[col-id='score']")
    expect(score_header).to_have_attribute("aria-sort", "none")

    score_header.locator(".ag-header-cell-label").click()
    expect(score_header).to_have_attribute("aria-sort", "ascending")

    score_header.locator(".ag-header-cell-label").click()
    expect(score_header).to_have_attribute("aria-sort", "descending")


def test_update_on_selection_roundtrip(page: Page):
    """update_on=['selectionChanged'] must rerun Streamlit and deliver the
    clicked row to Python via selected_rows.

    Regression guard: clicking a row in a single-select grid configured only
    with update_on (no update_mode) has to round-trip the selection back to
    the script, not just highlight client-side.
    """
    grid = _grid(page, "update_on_selection_grid")
    expect(grid.locator(".ag-root")).to_be_visible()
    expect(grid.locator(".ag-row")).to_have_count(3)

    echo = page.get_by_test_id("update-on-selection")
    expect(echo).to_contain_text("NONE")

    grid.locator(".ag-row[row-index='0'] .ag-cell").first.click()

    # Streamlit reruns asynchronously; expect() retries until the value lands.
    expect(echo).not_to_contain_text("NONE")
    expect(echo).to_contain_text("A")


def test_update_on_cell_value_changed_roundtrip(page: Page):
    """update_on=['cellValueChanged'] must rerun Streamlit and deliver the
    edited cell value to Python."""
    grid = _grid(page, "update_on_edit_grid")
    expect(grid.locator(".ag-root")).to_be_visible()
    expect(grid.locator(".ag-row")).to_have_count(3)

    echo = page.get_by_test_id("update-on-edit")
    expect(echo).to_contain_text("x")
    expect(echo).not_to_contain_text("zzz")

    cell = grid.locator(".ag-row[row-index='0'] .ag-cell[col-id='label']").first
    cell.dblclick()
    page.keyboard.type("zzz")
    page.keyboard.press("Enter")

    expect(echo).to_contain_text("zzz")


def test_manual_update_button_is_the_only_return_path(page: Page):
    """update_mode='MANUAL' shows a toolbar update button that is the *only*
    way the grid returns data.

    Two regression guards in one flow. First, MANUAL used to attach the
    default update_on events anyway (cellValueChanged among them), so the edit
    below returned data on its own and the button was one trigger among
    several; this grid passes no update_on, so an edit that reaches Python
    before the click means MANUAL is not exclusive. Second, the button's
    handler used to be a debug console.log only, so clicking it never returned
    anything.
    """
    grid = _grid(page, "manual_update_grid")
    expect(grid.locator(".ag-root")).to_be_visible()

    echo = page.get_by_test_id("manual-update-data")
    expect(echo).to_contain_text("m1")
    expect(echo).not_to_contain_text("edited")

    cell = grid.locator(".ag-row[row-index='0'] .ag-cell[col-id='item']").first
    cell.dblclick()
    page.keyboard.type("edited")
    page.keyboard.press("Enter")

    # The edit alone must not rerun Streamlit: with no update_on passed,
    # MANUAL has to leave the grid with no event triggers at all.
    page.wait_for_timeout(1000)
    expect(echo).not_to_contain_text("edited")

    grid.locator(".grid-toolbar .update-button").click()
    expect(echo).to_contain_text("edited")


def test_manual_update_grid_does_not_return_on_selection(page: Page):
    """The other half of MANUAL exclusivity: selectionChanged is in the
    default update_on set, so a row click used to rerun Streamlit too."""
    grid = _grid(page, "manual_update_grid")
    expect(grid.locator(".ag-root")).to_be_visible()

    echo = page.get_by_test_id("manual-update-data")
    expect(echo).to_contain_text("m1")

    cell = grid.locator(".ag-row[row-index='1'] .ag-cell[col-id='item']").first
    cell.dblclick()
    page.keyboard.type("selection-probe")
    page.keyboard.press("Enter")
    grid.locator(".ag-row[row-index='0'] .ag-cell[col-id='item']").first.click()

    page.wait_for_timeout(1000)
    expect(echo).not_to_contain_text("selection-probe")


def test_columns_state_is_applied_on_mount(page: Page):
    """A columns_state present from the first render has to be applied.

    Regression guard: it was applied only from componentDidUpdate, and only
    when it differed from prevProps, so restoring a saved layout did nothing
    on mount and nothing on a rerun that kept the same state. The fixture
    state reverses the order and hides 'bravo'.
    """
    grid = _grid(page, "columns_state_grid")
    expect(grid.locator(".ag-root")).to_be_visible()

    headers = grid.locator(".ag-header-cell-text")
    expect(headers).to_have_count(2)
    expect(headers.nth(0)).to_have_text("charlie")
    expect(headers.nth(1)).to_have_text("alpha")
    expect(grid.locator(".ag-header-cell[col-id='bravo']")).to_have_count(0)


def test_grid_options_change_does_not_push_rowdata_as_a_string(page: Page):
    """A rerun that changes a gridOption must not hand AG Grid a rowData
    string.

    Regression guard: componentDidUpdate pushed the whole cloned gridOptions
    into updateGridOptions, and under use_json_serialization=True that object
    still carries rowData as a raw JSON string.

    The assertion is on the console rather than on the rows because AG Grid
    35.3 defends itself: it rejects the malformed value with
    "warning #1 `rowData` must be an array" and keeps the rows it already had.
    That warning is the whole visible symptom, so it is what the test watches.
    A row-count assertion here would pass against the unfixed code and is
    therefore worthless; the count check below is only a sanity floor.
    """
    grid = _grid(page, "json_rerun_grid")
    expect(grid.locator(".ag-root")).to_be_visible()
    expect(grid.locator(".ag-row")).to_have_count(3)

    messages: list[str] = []
    page.on("console", lambda m: messages.append(m.text))

    page.get_by_test_id("stButton").filter(has_text="bump json rerun").click()

    # The rerun changes rowHeight only. Waiting on the applied height is what
    # proves componentDidUpdate ran at all, so an absent warning below means
    # "did not happen", not "never got there".
    expect(grid.locator(".ag-row").first).to_have_css("height", "31px")

    offending = [m for m in messages if re.search(r"rowData.*must be an array", m)]
    assert not offending, (
        "gridOptions update pushed rowData into AG Grid as a raw JSON string: "
        f"{offending}"
    )
    expect(grid.locator(".ag-row")).to_have_count(3)


def test_minimal_data_return_mode_returns_rows(page: Page):
    """DataReturnMode.MINIMAL must deliver rows and the selection to Python.

    Regression guard: MINIMAL routed to the TypeScript LegacyCollector, whose
    payload is {nodes, gridState, columnsState, ...}. MinimalResponse reads
    {data, selectedRows}, so .data was always None and .selected_rows always
    empty.

    The first-render assertion is the second guard: MinimalCollector's initial
    response dropped original_data on the floor, so .data was None until an
    update_on event fired. Every other mode hands back the input frame on load,
    and under update_mode=MANUAL (which attaches no events) None was all a
    caller ever got before clicking the toolbar button.
    """
    grid = _grid(page, "minimal_return_grid")
    expect(grid.locator(".ag-root")).to_be_visible()
    expect(grid.locator(".ag-row")).to_have_count(3)

    data_echo = page.get_by_test_id("minimal-data")
    selected_echo = page.get_by_test_id("minimal-selected")
    # First render, before any interaction: the input frame, not None.
    expect(data_echo).not_to_contain_text("NONE")
    expect(data_echo).to_contain_text("min-a")
    expect(selected_echo).to_contain_text("NONE")

    grid.locator(".ag-row[row-index='1'] .ag-cell").first.click()

    expect(data_echo).not_to_contain_text("NONE")
    expect(data_echo).to_contain_text("min-a")
    expect(data_echo).to_contain_text("min-c")
    expect(selected_echo).not_to_contain_text("NONE")
    expect(selected_echo).to_contain_text("min-b")
    # MINIMAL exists to keep the payload small: the internal id column and the
    # legacy node metadata must not be in it.
    expect(data_echo).not_to_contain_text("::auto_unique_id::")
    expect(data_echo).not_to_contain_text("rowIndex")


def test_minimal_reports_a_selected_row_that_a_filter_hides(page: Page):
    """A selected row must stay in selected_rows once a filter hides it.

    AG Grid does not deselect a row when a filter stops displaying it, and
    MinimalCollector used to pick selections up during its post-filter display
    walk, so a hidden selected row silently vanished from the selection while
    every other data return mode still reported it. That breaks the ordinary
    "tick some rows, then act on them" flow with no error: the handler just
    receives fewer rows than the user ticked.
    """
    grid = _grid(page, "minimal_hidden_selection_grid")
    expect(grid.locator(".ag-root")).to_be_visible()
    expect(grid.locator(".ag-row")).to_have_count(3)

    data_echo = page.get_by_test_id("hidden-data")
    selected_echo = page.get_by_test_id("hidden-selected")

    # Tick keep-a and gone-c. Checkbox clicks, so both land as one selection.
    grid.locator(".ag-row[row-index='0'] .ag-selection-checkbox").first.click()
    expect(selected_echo).to_contain_text("keep-a")
    grid.locator(".ag-row[row-index='2'] .ag-selection-checkbox").first.click()
    expect(selected_echo).to_contain_text("gone-c")

    # Filter so that gone-c is no longer displayed. The row stays selected.
    # "Search..." is the toolbar's own input. The separate QuickSearch.tsx
    # component uses "quickfilter..." but nothing renders it.
    grid.get_by_placeholder("Search...").fill("keep")

    # Proves the filter actually took effect, so the assertion below is about
    # the selection and not about a filter that quietly did nothing.
    expect(grid.locator(".ag-row")).to_have_count(2)
    expect(data_echo).not_to_contain_text("gone-c")

    # The whole point: still selected, still reported, though not displayed.
    expect(selected_echo).to_contain_text("gone-c")
    expect(selected_echo).to_contain_text("keep-a")
    # And the payload stays lean.
    expect(selected_echo).not_to_contain_text("::auto_unique_id::")


def test_columns_auto_size_mode_fit_contents(page: Page):
    """columns_auto_size_mode=FIT_CONTENTS must size columns to their content,
    overriding the fitGridWidth strategy that from_dataframe injects.

    Regression guard: previously every column collapsed to a uniform minWidth
    (~46px) because FIT_CONTENTS was ignored. A long-header column must end up
    clearly wider than a short one, and no column may collapse to minWidth.
    """
    grid = _grid(page, "autosize_fit_contents_grid")
    expect(grid.locator(".ag-root")).to_be_visible()
    # autoSizeStrategy=fitCellContents runs just after first data render.
    page.wait_for_timeout(1000)

    def header_width(col_id: str) -> float:
        cell = grid.locator(f".ag-header-cell[col-id='{col_id}']").first
        box = cell.bounding_box()
        return box["width"] if box else 0.0

    rev = header_width("Rev")
    qty_req = header_width("Qty Req (released jobs only)")

    # Short "Rev" column stays narrow; the long-header column is sized to fit
    # its much wider header text. If FIT_CONTENTS were ignored (fitGridWidth),
    # both would collapse to the same ~46px minWidth.
    assert rev > 0 and qty_req > 0, f"columns not measured: rev={rev} qty_req={qty_req}"
    assert qty_req > 120, f"long-header column collapsed: {qty_req}px"
    assert qty_req > rev + 40, (
        f"columns look uniform (collapsed): qty_req={qty_req} rev={rev}"
    )
