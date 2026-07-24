"""Browser coverage ported off the deleted CCv1 (iframe) test files.

The five ``test_grid_*.py`` files targeted the CCv1 iframe DOM
(``frame_locator("iframe")``), which the CCv2 component no longer produces, so
none of them could run. Rather than leave them excluded forever, the coverage
that is still meaningful and still browser-only landed here; the rest was
either already covered by ``test_ccv2_e2e.py``, moved to the far cheaper
Python-level tests in ``test_legacy_coverage.py``, or dropped. See that file's
module docstring for the per-file accounting.
"""

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from e2e_utils import StreamlitRunner


ROOT_DIRECTORY = Path(__file__).parent.parent.absolute()
FIXTURE_APP = ROOT_DIRECTORY / "test" / "ccv2_legacy_app.py"

expect.set_options(timeout=20_000)


@pytest.fixture(autouse=True, scope="module")
def streamlit_app():
    with StreamlitRunner(FIXTURE_APP) as runner:
        yield runner


@pytest.fixture(autouse=True, scope="function")
def go_to_app(page: Page, streamlit_app: StreamlitRunner):
    page.goto(streamlit_app.server_url)
    expect(page.locator(".st-key-custom_return_grid .stBidiComponent")).to_be_attached(
        timeout=15_000
    )


def _grid(page: Page, key: str):
    return page.locator(f".st-key-{key} .stBidiComponent")


def test_custom_data_return_mode_runs_the_user_jscode(page: Page):
    """DataReturnMode.CUSTOM must run the caller's JsCode in the grid and hand
    its return value back to Python as the whole response.

    Ported from test_grid_return.py::test_grid_return_test_2_custom_return.
    """
    grid = _grid(page, "custom_return_grid")
    expect(grid.locator(".ag-root")).to_be_visible()

    echo = page.get_by_test_id("custom-return")
    expect(echo).to_contain_text("NONE")

    # update_on is sortChanged only, so this click is the trigger.
    grid.locator(".ag-header-cell[col-id='second'] .ag-header-cell-label").click()

    expect(echo).not_to_contain_text("NONE")
    # The JsCode returned the displayed column fields and the trigger name.
    expect(echo).to_contain_text("first")
    expect(echo).to_contain_text("second")
    expect(echo).to_contain_text("third")
    expect(echo).to_contain_text("sortChanged")
    # It is the custom payload, not the legacy one.
    expect(echo).not_to_contain_text("::auto_unique_id::")


def test_checkbox_row_selection_round_trips(page: Page):
    """Ticking a row checkbox must deliver that row to Python.

    Ported from test_grid_return.py::test_grid_return_third_row_checkbox.
    """
    grid = _grid(page, "checkbox_selection_grid")
    expect(grid.locator(".ag-root")).to_be_visible()
    expect(grid.locator(".ag-row")).to_have_count(4)

    count = page.get_by_test_id("checkbox-selected-count")
    names = page.get_by_test_id("checkbox-selected-names")
    expect(count).to_have_text("0")

    grid.locator(".ag-row[row-index='2'] .ag-selection-checkbox").first.click()

    expect(count).to_have_text("1")
    expect(names).to_contain_text("y")


def test_header_checkbox_selects_every_row(page: Page):
    """The header select-all checkbox must deliver every row to Python.

    Ported from
    test_grid_return.py::test_grid_return_test_4_header_checkbox_select_all.
    """
    grid = _grid(page, "checkbox_selection_grid")
    expect(grid.locator(".ag-root")).to_be_visible()

    count = page.get_by_test_id("checkbox-selected-count")
    expect(count).to_have_text("0")

    grid.locator(".ag-header-cell .ag-header-select-all").first.click()

    expect(count).to_have_text("4")
    expect(page.get_by_test_id("checkbox-selected-names")).to_contain_text("w")


def test_grid_with_nested_object_cells_mounts(page: Page):
    """Lists, sets and dicts in cells must not stop the grid from rendering.

    Ported from the deleted test_grid_data_render.py, condensed: the Python
    serialization and hashing of these types is covered in
    test_legacy_coverage.py, so what is left for a browser is whether the grid
    mounts and shows its rows.
    """
    grid = _grid(page, "unhashable_grid")
    expect(grid.locator(".ag-root")).to_be_visible()
    expect(grid.locator(".ag-row")).to_have_count(3)
    headers = [
        grid.locator(".ag-header-cell-text").nth(i).inner_text() for i in range(4)
    ]
    assert headers == ["id", "a_list", "a_set", "a_dict"]
