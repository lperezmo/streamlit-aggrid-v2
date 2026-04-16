# CHANGELOG


## v0.1.5 (2026-04-16)

### Bug Fixes

- Match Streamlit font across all themes and fix material dark header
  ([`c8419cc`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/c8419ccee07c4bda8edb1ea558cc9a15b7da10e0))

Extract a streamlitFontFamily helper reading --st-font from the CCv2 host, and apply it via
  .withParams({fontFamily}) in the quartz/alpine/balham/ material recipes (previously only the
  streamlit recipe matched the font).

Also override headerTextColor with streamlitTheme.textColor in material dark mode; AG Grid's
  material theme hardcodes the header text to near-black and colorSchemeDark doesn't flip it, making
  headers unreadable on Streamlit's dark background.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

- Sanitize NaN/Infinity in gridOptions before CCv2 transport
  ([`0e76365`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/0e763651233816bf5e6ea7107088b4ce0cbef3a9))

Streamlit CCv2 serializes component data with strict JSON, which rejects NaN and Infinity tokens.
  User pipelines that compute numeric gridOptions fields (e.g. column widths via
  df[col].astype(str).str.len().max() on an empty column) can resolve to NaN and blow up JSON.parse
  on the frontend with "SyntaxError: Unexpected token 'N'".

Walk grid_options at the end of _parse_data_and_grid_options and replace any non-finite float with
  None. Row data is unaffected (pd.to_json already converts NaN to null).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

### Chores

- Add comparison table to README (v1 vs v2)
  ([`1919c21`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/1919c21a234a40b9907ea6d017ca5f45f2f2f3b1))

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- Bump demo app requirement to v0.1.4
  ([`aace8c4`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/aace8c46553727e69bfcfb3d8047437523bbcd00))

- Fix deprecation warnings and SettingWithCopyWarning
  ([`cb7edf5`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/cb7edf5b5cc1ec2f881acd07d6c7415b7b143fa6))

Replace use_container_width with width="stretch" in example pages (enterprise.py, inline_buttons.py)
  and copy DataFrame before mutation in aggrid_utils.py to avoid pandas SettingWithCopyWarning.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- Fix inaccurate claim about original project activity
  ([`24c6de0`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/24c6de0f2b28d1106632332470765c27757efb9a))

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- Ignore .streamlit/secrets.toml
  ([`0ff454f`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/0ff454fda343747062c6e9293d56711ef731d5ce))

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

- Increase header top padding to prevent cutoff
  ([`ccf3ed8`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/ccf3ed81d26ceedeee8fe7363854c9e7f69f9883))

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- Remove all em dashes from README
  ([`b5b12c7`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/b5b12c77a36a8165f3e9a0cdc200d2ae47ed47de))

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- Remove downloads badge from README
  ([`53ba913`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/53ba913712c4d0d3dff3ff8ec0cf81344388b64b))

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- Shrink showcase header, use repo name, drop version from footer
  ([`26ac55a`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/26ac55a8b2cc749f9a6547ea8f6dd70a99a09481))

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- Update README with badges, features, and API overview
  ([`b36dffb`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/b36dffb712cabfebad2291e18d1d9a75fd0a0ae9))

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- Use subheader for individual page titles
  ([`3c5eb52`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/3c5eb5260e1ada2ce836edb89f60ea7ff1ab80fb))

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

### Documentation

- Add tree-data example, AI copilot skill, and README updates
  ([`bdba3b6`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/bdba3b69b5c842a71cef1fe07703d3cd05b204a4))

- examples/app_pages/tree_data.py: new Enterprise-group page showing treeData + getDataPath + three
  mutually-exclusive action button cell renderers (Delete / Audit / Approve) with conditional row
  styling. - examples/showcase.py: register the tree-data page in the Enterprise nav group. -
  skills/streamlit-aggrid-v2/SKILL.md: self-contained Claude Code / Claude Agent SDK skill for AI
  copilots. Users can copy the folder into their project's .claude/skills/ so their copilot knows
  how to use GridOptionsBuilder, JsCode, data return modes, theming, tree data, and common gotchas
  without re-reading the whole repo. - README.md: bump showcase example count to 13 and add an "AI
  copilot skill" section pointing to the skill.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>


## v0.1.4 (2026-03-31)

### Bug Fixes

- Match component name to distribution for CCv2 resolver
  ([`1a53cc5`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/1a53cc56fa5ad46a9395ae3aec655a3bda3330da))

Streamlit CCv2 validates that the inner pyproject.toml [project].name matches the distribution name.
  Changed from "st-aggrid" to "streamlit-aggrid-v2" and updated the component registration key.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

### Chores

- Bump demo app requirement to v0.1.3
  ([`fbb1b72`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/fbb1b72ecc21442be3789438e36208bfb06dc6cd))


## v0.1.3 (2026-03-31)

### Bug Fixes

- Move to src layout so Streamlit Cloud uses pip package
  ([`78735a6`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/78735a6ac2852646dde299844a9f93e0c14abbba))

Moved st_aggrid/ to src/st_aggrid/ so that when Streamlit Cloud clones the repo, Python imports
  st_aggrid from the pip-installed wheel (which has frontend build artifacts) instead of the local
  source directory (which doesn't).

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

### Chores

- Bump demo app requirement to v0.1.2
  ([`2afa3af`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/2afa3afca86f4e5888ac48f4832efe61c7488c73))


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
