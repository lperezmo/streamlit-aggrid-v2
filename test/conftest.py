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

Suite layout:

- `test_python_layer.py`, `test_aggrid_call_regressions.py` and
  `test_legacy_coverage.py` are browser-less and run in milliseconds. Anything
  observable from Python belongs there.
- `test_registration_smoke.py` checks CCv2 discovery on the installed
  Streamlit without a server or a browser.
- `test_ccv2_e2e.py` and `test_ccv2_legacy_port.py` are the Playwright suites,
  for behavior that only exists in a browser.

The legacy CCv1 (iframe) `test_grid_*.py` files that used to be excluded here
via `collect_ignore` are gone; their surviving coverage was ported, and
`test_legacy_coverage.py` documents the decision for each one.
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
