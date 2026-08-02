"""e2e guard for the grid following a Streamlit appearance change.

The AG Grid theme is built by baking Streamlit's --st-* properties into an
AG Grid theme object at parse time. Nothing re-reads those properties on its
own, and an appearance flip changes them without changing anything the grid
compares against, so the grid used to hold the palette it was first built with
until a full remount: a light grid marooned on a dark page.
"""

import re
from pathlib import Path

import pytest
import streamlit as st
from packaging.version import Version
from playwright.sync_api import Page, expect

from e2e_utils import StreamlitRunner

pytestmark = pytest.mark.browser

ROOT_DIRECTORY = Path(__file__).parent.parent.absolute()
FIXTURE_APP = ROOT_DIRECTORY / "test" / "ccv2_e2e_app.py"

expect.set_options(timeout=20_000)

# Streamlit itself has to repaint when the OS appearance flips, or there is no
# appearance change for the grid to follow and the test measures nothing.
# Streamlit does not repaint on a live prefers-color-scheme change before 1.54;
# the wait below would then time out on Streamlit's own background, before the
# grid is involved at all.
#
# Parsed with packaging (a Streamlit dependency, so always available) rather
# than by splitting on dots: a prerelease like "1.54.0rc1" would crash an int()
# parse at import time and take the whole module down with it.
_LIVE_APPEARANCE_SWITCHING = Version("1.54")

requires_live_appearance_switching = pytest.mark.skipif(
    Version(st.__version__) < _LIVE_APPEARANCE_SWITCHING,
    reason=(
        f"Streamlit {st.__version__} does not repaint on a live "
        "prefers-color-scheme change, so there is no flip to follow"
    ),
)

# The grid this exercises is the plain DataFrame one, which takes the default
# theme="streamlit" and so is the recipe that reads the most --st-* properties.
_GRID_KEY = "grid_from_dataframe"

# Read Streamlit's own property off the grid rather than off an outer wrapper.
# Streamlit declares --st-* on the div it hands the component as parentElement
# (data-testid="stBidiComponentRegular"), which is inside .stBidiComponent and
# well inside .st-key-*; on either of those outer elements, and on
# document.documentElement, the property resolves to an empty string. The grid
# is a descendant of the declaring div, so it inherits the real value.
_STREAMLIT_BACKGROUND = f"""() => {{
    const wrapper = document.querySelector(
        '.st-key-{_GRID_KEY} .ag-root-wrapper'
    );
    if (!wrapper) return '';
    return getComputedStyle(wrapper)
        .getPropertyValue('--st-background-color')
        .trim()
        .toLowerCase();
}}"""

_GRID_BACKGROUND = f"""() => {{
    const wrapper = document.querySelector(
        '.st-key-{_GRID_KEY} .ag-root-wrapper'
    );
    if (!wrapper) return '';
    return getComputedStyle(wrapper).backgroundColor;
}}"""


@pytest.fixture(autouse=True, scope="module")
def streamlit_app():
    with StreamlitRunner(FIXTURE_APP) as runner:
        yield runner


@pytest.fixture(autouse=True, scope="function")
def go_to_app(page: Page, streamlit_app: StreamlitRunner):
    page.goto(streamlit_app.server_url)
    expect(page.locator(f".st-key-{_GRID_KEY} .ag-root-wrapper")).to_be_visible(
        timeout=30_000
    )


def _relative_luminance(color: str) -> float:
    """WCAG relative luminance of an rgb()/rgba() string.

    getComputedStyle always resolves a background-color to this form, so a
    parse failure means the selector matched something without a background
    rather than a color format worth supporting.
    """
    channels = re.match(r"rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)", color)
    assert channels, f"not an rgb color: {color!r}"

    def to_linear(value: str) -> float:
        channel = float(value) / 255
        if channel <= 0.03928:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (to_linear(channels.group(i)) for i in (1, 2, 3))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


@requires_live_appearance_switching
def test_grid_theme_follows_a_streamlit_appearance_change(page: Page):
    """Nothing is clicked here on purpose. The flip alone has to be enough: a
    user who changes the appearance and touches nothing else is the case that
    broke, and driving a grid interaction first would hide a re-introduced
    staleness behind the re-theme that interaction would have triggered."""
    light_page = page.evaluate(_STREAMLIT_BACKGROUND)
    assert light_page, "Streamlit did not expose --st-background-color"

    light_grid = page.evaluate(_GRID_BACKGROUND)
    assert _relative_luminance(light_grid) > 0.5, (
        f"grid did not start light: {light_grid!r}"
    )

    page.emulate_media(color_scheme="dark")

    # Streamlit has to switch first, or the assertion below proves nothing
    # about the grid.
    page.wait_for_function(
        f"previous => ({_STREAMLIT_BACKGROUND})() !== previous",
        arg=light_page,
        timeout=30_000,
    )

    page.wait_for_function(
        f"previous => ({_GRID_BACKGROUND})() !== previous",
        arg=light_grid,
        timeout=30_000,
    )
    dark_grid = page.evaluate(_GRID_BACKGROUND)
    assert _relative_luminance(dark_grid) < 0.1, (
        f"grid did not follow the flip to dark: {dark_grid!r}"
    )

    # And back, so the re-theme is shown to keep following rather than to have
    # fired once on the way to a value it would have reached regardless.
    page.emulate_media(color_scheme="light")
    page.wait_for_function(
        f"previous => ({_GRID_BACKGROUND})() !== previous",
        arg=dark_grid,
        timeout=30_000,
    )
    assert _relative_luminance(page.evaluate(_GRID_BACKGROUND)) > 0.5
