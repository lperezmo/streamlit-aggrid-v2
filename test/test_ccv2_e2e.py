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
