"""CCv2 e2e tests.

These tests target the Custom Components v2 DOM directly (no iframe).
Each grid is wrapped inside a `.st-key-<key>` div produced by Streamlit's
key= prop, and the CCv2 component mounts at `.stBidiComponent` inside it.
AG Grid then renders `.ag-root` etc. directly in the page DOM.
"""

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from e2e_utils import StreamlitRunner


ROOT_DIRECTORY = Path(__file__).parent.parent.absolute()
FIXTURE_APP = ROOT_DIRECTORY / "test" / "ccv2_e2e_app.py"


@pytest.fixture(autouse=True, scope="module")
def streamlit_app():
    with StreamlitRunner(FIXTURE_APP) as runner:
        yield runner


@pytest.fixture(autouse=True, scope="function")
def go_to_app(page: Page, streamlit_app: StreamlitRunner):
    page.goto(streamlit_app.server_url)
    # Wait for the first grid to be attached so subsequent assertions don't
    # race against initial Streamlit hydration.
    expect(page.locator(".st-key-grid_from_dataframe .stBidiComponent")).to_be_attached()


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
