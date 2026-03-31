# CHANGELOG


## v0.1.2 (2026-03-31)

### Bug Fixes

- Commit frontend build artifacts for Streamlit Cloud
  ([`0db98c8`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/0db98c8facb6a476808ff8e3e7ececf4faea3f0c))

Streamlit Cloud clones the repo and Python imports st_aggrid from the local directory (not the pip
  wheel), so build/ must be present in the repo. CI still builds fresh artifacts for the PyPI wheel.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

### Chores

- Bump demo requirement to v0.1.1
  ([`5ede648`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/5ede6481b88e172909bd74fcb6bf9960339f39fa))

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.1.1 (2026-03-30)

### Bug Fixes

- Add frontend package-lock.json for CI builds
  ([`3820ef1`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/3820ef151202f553d53fa824121a7e8d46f755d8))

- Un-ignore st_aggrid/frontend/package-lock.json so npm ci works in CI - Fix bump-demo job failing
  when requirements.txt is already up to date

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- Build wheel directly so frontend artifacts are included
  ([`368227d`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/368227da2e8a31c0ba4dfc9ce0d06c520fd84875))

python -m build creates sdist first then builds wheel from it, which strips gitignored files like
  frontend/build/. Building --wheel first ensures hatchling's artifacts directive works.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- Bump to v0.1.1 — rebuild with frontend assets included
  ([`63f98f3`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/63f98f32703c992ea30108ac74dd6c2990901d36))

v0.1.0 on PyPI was published without frontend build artifacts. This release includes the complete
  wheel with AG Grid frontend.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

### Chores

- Trigger release pipeline
  ([`f901578`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/f901578a46bc9b9b34fa50149e5f1763a0a8d18c))

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.1.0 (2026-03-30)

### Features

- Initial release of streamlit-aggrid-v2
  ([`c871cdd`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/c871cddcf5dfbeedc0e73f25e84b5080905b2fc5))

Complete rewrite of streamlit-aggrid using Streamlit Custom Components v2.

Architecture: - CCv2 direct DOM rendering (no iframes, no postMessage overhead) - Vite + ESM build
  replacing webpack/CRA - AG Grid v34.3.1 with React 18 - Theme auto-detection via CSS --st-*
  variables on parentElement - Dark mode via background luminance (no --st-base-theme in Streamlit)
  - Collector pattern for pluggable response processing (Legacy/Minimal/Custom)

Fixes (25 total): - Path handling bugs in aggrid_utils.py (wrong variable, nonexistent method) -
  Mutable default arguments in AgGrid() and AgGridReturn() - selected_rows_id crash when grid_state
  is None - Event listener memory leaks (no cleanup on unmount) - Direct React state mutation
  replaced with gridApiRef - Style/script injection deduplication - Quartz theme missing dark mode
  recipe - Material theme using wrong base (themeAlpine instead of themeMaterial) -
  conversion_errors parameter ignored in LegacyCollector - All ruff lint issues resolved

Themes: - All 4 AG Grid v34 themes: quartz, alpine, balham, material - 6 color schemes + 6 icon sets
  available for custom themes - Automatic dark/light mode detection from Streamlit

Showcase (12 pages): - Basic grid, Cell editing, Row selection - Filtering & sorting, Floating
  filters, Data return modes - Themes, Column config, Cell renderers, Row styling, Inline buttons -
  Enterprise: row grouping, pivot, status bar, side bar, Excel export, cell selection, sparklines
