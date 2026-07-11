"""Test bootstrap for the streamlit-aggrid-v2 CCv2 component.

Streamlit's CCv2 manifest scanner discovers `[[tool.streamlit.component.components]]`
entries by reading each installed distribution's `pyproject.toml`. When the package
is installed editable (the default `uv sync` behavior), the distribution file
listing only contains dist-info entries and the resolver cannot locate
`src/st_aggrid/pyproject.toml`. As a result, the file-backed `css="index-*.css"` /
`js="index-*.js"` references in AgGrid.py raise:

    Component 'streamlit-aggrid-v2.st_aggrid' must be declared in pyproject.toml
    with asset_dir to use file-backed css.

A non-editable install (built wheel) ships `st_aggrid/pyproject.toml` as a data
file inside the distribution, so `_pyproject_via_dist_files` finds it. This
fixture builds and force-installs the wheel before the test session runs.

The legacy `test_grid_*.py` files target the CCv1 iframe pattern that the v2
component no longer uses. They're excluded via `collect_ignore` until they're
ported. The current end-to-end suite lives in `test_ccv2_e2e.py`.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]


def _ensure_wheel_install() -> None:
    """Build the wheel and reinstall it non-editable into the active venv."""
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required to bootstrap the wheel install for tests")

    subprocess.run([uv, "build", "--wheel"], cwd=_ROOT, check=True)

    wheels = sorted((_ROOT / "dist").glob("streamlit_aggrid_v2-*.whl"))
    if not wheels:
        raise RuntimeError("Wheel build did not produce a streamlit_aggrid_v2 artifact")

    subprocess.run(
        [uv, "pip", "install", "--reinstall", "--no-deps", str(wheels[-1])],
        cwd=_ROOT,
        check=True,
    )


_ensure_wheel_install()


# Legacy CCv1 iframe-based tests. They'll be ported as part of the migration.
collect_ignore = [
    "test_grid_initialization.py",
    "test_grid_return.py",
    "test_grid_data_render.py",
    "test_grid_drag_and_drop_example.py",
    "test_grid_performance.py",
]
