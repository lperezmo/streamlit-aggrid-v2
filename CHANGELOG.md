# CHANGELOG


## v0.3.1 (2026-08-02)

### Bug Fixes

- Repaint the grid when Streamlit's appearance changes
  ([`462f893`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/462f893ff3628c6d43004912aeaec64d545792df))

The theme recipes bake Streamlit's --st-* properties into an AG Grid theme object at parse time, and
  nothing re-read them afterwards. componentDidUpdate re-themed only when componentData.theme
  changed, which is the theme argument the app passed, not the theme underneath it. Flipping the
  appearance rewrites every --st-* property while that argument stays byte-identical, so the grid
  held the palette it was first built with: switch an app to dark and the grid alone stayed light
  until a full remount.

Compare a signature built from the properties the recipes actually read, and re-theme when either it
  or the passed theme moves.

Two smaller theme reads were wrong in the same area. Dark detection matched 6-digit hex alone, so a
  background written as #000 or resolved to an rgb() string silently read as light. And an absent
  --st-background-color assumed white, which is how a dark page could get a white grid; fall back to
  what the page renders, then to the color scheme, and let the remaining fallbacks follow the
  appearance that resolves rather than defaulting to light text colors on a dark grid.

The e2e guard flips the emulated color scheme and touches nothing else, which is the case that
  broke. It waits for Streamlit's own background to move first, so a failure to repaint the grid
  cannot pass as Streamlit never having flipped.

### Chores

- Bump demo app requirement to v0.3.0
  ([`c1b273b`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/c1b273bc8d8f3c9a932f771afba08a126af4a735))


## v0.3.0 (2026-07-25)

### Bug Fixes

- Accept the four retired theme names with a deprecation warning
  ([`bb42ea0`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/bb42ea078b42b009429c03bfe3778d80f7e9e57c))

- Attach one grid listener per update_on event
  ([`f44fbcc`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/f44fbcc721b63397e92755702b5745ee43698c3d))

parse_update_mode deduped only within the list it built, and AgGrid then appended that list onto the
  already-populated update_on defaults. Every update_mode that implies a default event therefore
  listed it twice: MODEL_CHANGED, VALUE_CHANGED and GRID_CHANGED all did.

That is not cosmetic. AgGrid.tsx builds a fresh closure per update_on entry and AG Grid's
  addEventListener stores listeners in a Set keyed by function identity, so both closures stay live
  and both fire. The full collector walk and the Streamlit state write ran twice for every such
  event.

Dedupe keys on the event name, since entries are either a plain name or an (event, debounce_ms)
  tuple and the two forms describe the same listener. Order follows first appearance so a caller's
  own ordering survives, and the spec kept is the last one seen: a bare "columnResized" from the
  caller loses to the ("columnResized", 300) that GridUpdateMode.COLUMN_RESIZED adds, because
  dropping the debounce would be the more surprising outcome.

- Correct columns_state, JSON serialization and error handling defects
  ([`dfd2b3c`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/dfd2b3c3d334a83580d55505e5d4efd00de8c14b))

Verified review findings on the installable package:

- columns_state was only applied from componentDidUpdate when it differed from prevProps, so it
  never applied on mount nor on reruns with an unchanged saved state. It is now applied in
  onGridReady as well. - use_json_serialization=True moved the frame into gridOptions.rowData and
  nulled data, which made AgGridReturn.data return a JSON string instead of a DataFrame. AgGrid now
  keeps the frame and hands it to the response. - componentDidUpdate pushed the cloned gridOptions
  (still carrying rowData as a raw JSON string under JSON serialization) straight into
  updateGridOptions, breaking the grid. rowData is now excluded there. - Error re-wrapping rebuilt
  the exception with type(ex)(*args), which garbled StreamlitDuplicateElementId, turned
  json.JSONDecodeError into a TypeError and raised IndexError on empty args. The original exception
  and traceback now survive, with the hint attached as a note. - walk_gridOptions indexed lists by
  element, crashing on nested lists and silently skipping JsCode objects stored directly in a list.
  - GridOptionsBuilder.build() mutated its internal columnDefs mapping into a list, so a second
  build() raised AttributeError. It now returns a copy. - AgGridReturn.data raised "No objects to
  concatenate" when the grid returned zero nodes. - Datetime columns rendered the literal string
  "NaT" for missing values. - theme= documented themes that do not exist and accepted any string,
  falling back to balham silently. String themes are validated against AgGridTheme and StAggridTheme
  always sets themeName, so a custom theme no longer discards its withParams/withParts. -
  update_mode=MANUAL now forces show_toolbar on, since the update button lives in the toolbar and
  the grid is otherwise unusable. - AgGridReturn.keys() disagreed with __iter__/__len__, so
  dict(zip(keys, values)) dropped entries. Raw response keys remain reachable via __getitem__ and
  .grid_response. - fit_columns_on_grid_load, pro_assets and debug are popped before
  GridOptionsBuilder.from_dataframe, which warned they were not valid gridOptions even though all
  three are honored. - conversion_errors='ignore' is implemented locally instead of being passed to
  pandas, which deprecated it and removes it in pandas 3.0. - collectors.factory.determine_collector
  raised "Unsupported DataReturnMode" for DataReturnMode.CUSTOM. - Deleted the unreferenced frontend
  constants module (eventDataWhiteList was replaced by LegacyCollector.filterSerializableEventData).

- Detach every level of the GridOptionsBuilder.build result
  ([`ad1d80d`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/ad1d80ded5207166b108c20ec5c76a1132370c20))

build() returned a shallow copy while its docstring promised independence. defaultColDef and every
  entry of columnDefs were the same dict objects in the builder and in every build, and the existing
  detachment test only checked the top level, so it passed against the bug.

This is not theoretical. AgGrid(..., allow_unsafe_jscode=True) rewrites JsCode values into
  ::JSCODE:: strings in place through walk_gridOptions, so the rewrite reached the builder's own
  colDefs and the next build came out already flattened: the second grid got a plain string where
  the frontend expects marker-wrapped code it re-parses.

The copy walks dicts, lists and tuples and shares every leaf. copy.deepcopy was not used on purpose:
  it would duplicate JsCode objects and break identity for callers holding a reference to what they
  passed in. Only the containers are ever mutated, so only they need to be new. defaultdicts are
  rebuilt with their factory so the built options keep auto-vivifying.

- Document the breaking changes and cut them as a 0.x minor
  ([`c195736`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/c1957368a8f8d59ea99579f3ee9e6185be2dcd39))

- Give DataReturnMode.MINIMAL a genuinely lean frontend collector
  ([`1e4a2d0`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/1e4a2d001877d4ac20f5ddb7fe67f2655718a2e9))

MINIMAL routed to LegacyCollector on the TypeScript side, so the wire payload was the full legacy
  one: an object per row carrying id, rowIndex, group, isSelected, parentPath and the internal
  ::auto_unique_id:: column, plus the whole grid state, the whole column state, the original dtypes
  and the filtered event data, produced by three separate walks of the grid. The mode advertised the
  lightest payload and delivered the heaviest processing.

MinimalCollector walks the grid once with forEachNodeAfterFilterAndSort and sends {data,
  selectedRows, eventTrigger}: the displayed row values in display order, internal columns stripped.
  On a 200 row by 4 column grid with 10 percent selected that is 19598 bytes against 43212, a 55
  percent reduction, and it grows with column count.

The shape matches what MinimalResponse on the Python side already reads, so no Python contract
  changes. As a side effect MinimalResponse.data and .selected_rows return real rows instead of
  None, which is what they were written for.

- Hash and type the frame that JSON serialization puts on the wire
  ([`95eb230`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/95eb23018811700eb0d357d976125493938b11d8))

use_json_serialization=True moves the DataFrame into gridOptions["rowData"] and sets the local
  `data` to None. Two things downstream still read that local and quietly degraded as a result.

data_hash was computed from `data`, so it was always "". The frontend only refreshes rows when
  data_hash changes under the default server_sync_strategy="client_wins", so the grid stayed pinned
  to the rows it mounted with and never picked up new server data.

try_to_convert_back_to_original_types was cleared by the isinstance(data, pd.DataFrame) guard, which
  withheld frame_dtypes from LegacyCollector. AgGridReturn only converts column types when
  frame_dtypes is set, so the returned DataFrame came back entirely object dtype while
  use_json_serialization="auto" returned Int64 and float64 columns for the same input.

Both now go through sent_frame, the frame that was actually handed to the grid in either
  serialization mode.

- Honor conversion_errors on integer columns
  ([`9c1b1bd`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/9c1b1bd5a6ecf4728f8f525f437d1fdf2af6560b))

_convert_with_error_policy was wired into the float and datetime branches only. The integer branch
  called _convert_to_integer, which hardcoded errors="coerce", so conversion_errors was a no-op for
  every integer column: "ignore" turned an uncoercible cell into <NA> instead of leaving the column
  as it came back, and "raise" never raised.

_convert_to_integer now takes the pandas policy from the caller, and the integer branch goes through
  the same error policy helper as the other kinds. The "coerce" default is unchanged.

- Honor every bit of a composed update_mode flag
  ([`81a7dd0`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/81a7dd004305f3ef5a100ec5c7c9f90f714ffe3d))

- Keep DataReturnMode.MINIMAL from changing types and losing tree rows
  ([`b191488`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/b19148844218e896ca4d2c06bdb4269efdf6c4ae))

- Keep missing datetimes null on pandas 3
  ([`7f46206`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/7f4620687a3b2030cef38045b0f60af0c0c6b6c3))

- Keep the exception type and the hint on Python 3.10
  ([`ab33f68`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/ab33f68af77e522acfe3c949642a8df8c3f50d02))

_reraise_with_hint used BaseException.add_note, which is 3.11+. On the declared 3.10 floor the
  getattr probe returned None and the fallback rebuilt the error as a RuntimeError, so an exception
  with empty args or a non-string first arg lost its type: `except StreamlitDuplicateElementId`
  stopped catching the duplicate-key error the hint exists to explain.

The add_note branch was wrong on every version anyway. This function's own docstring says Streamlit
  renders the message and the traceback and never __notes__, so that branch filed the hint exactly
  where nobody can read it.

Now every branch mutates args in place: the hint alone when there are no args, prepended when the
  first arg is a string, appended otherwise so a non-string first arg stays intact for callers that
  read args[0] while str() of the multi-arg tuple still carries the hint to the browser. A repeat
  pass is a no-op, so an exception crossing two boundaries does not accumulate suffixes.

Verified on real 3.10.18 and 3.13 across five exception shapes, including JSONDecodeError and a
  two-argument constructor: type preserved and hint in str() in all ten cases.

Two tests asserted on __notes__ and so encoded the unrenderable behavior; they now assert on str().
  CI ran only 3.13, which is why none of this was caught, so the browser-less suite now also runs on
  3.10.

- Let an explicit update_on debounce win over the one update_mode implies
  ([`1c038df`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/1c038df558b5d8a2d85b15c4adc119bd426def1f))

- Make update_mode MANUAL the only return path again
  ([`694c094`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/694c094ae8f33798b2c06e61183af2a6b91ac956))

update_mode=GridUpdateMode.MANUAL still attached the default update_on events (cellValueChanged,
  selectionChanged, filterChanged, sortChanged), so the grid kept returning data on every edit,
  selection, filter and sort and the update button was just one more trigger among several. In v1
  MANUAL was exclusive.

MANUAL now clears the default event list, leaving the toolbar button as the only way the grid
  returns data. An update_on passed by the caller is still honored verbatim, so anyone who wants
  extra triggers alongside the button keeps them.

Behavior change, deliberate: grids using update_mode="MANUAL" without an explicit update_on will
  stop rerunning Streamlit on cell edits and selection changes. Pass update_on to restore the old
  set. Documented on the update_mode and update_on docstrings.

- Move gridOptions rowData into data under use_json_serialization
  ([`1d127f4`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/1d127f4fef0031a96d7dce3b64d25f24bdce5eb5))

The parser refused to move gridOptions.rowData into the data parameter whenever
  use_json_serialization was True. A list of record dicts therefore stayed on gridOptions.rowData,
  and the frontend's parseData only unwraps rowData when it is a JSON string: a list fell through to
  [] and the grid rendered empty.

The same skip left the data local at None, so no frame was hashed (data_hash stayed ""), no
  ::auto_unique_id:: column was added (so the frontend could not derive getRowId), and the frame
  never reached the response object.

Moving rowData for every serialization mode also means the frame is re-serialized to a JSON string
  by the caller, which is the form parseData expects and the form the frontend already handles for
  the data= argument.

- Put the serialization hint back in the visible error message
  ([`dfa6074`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/dfa6074a30193b09e1b32c35bc6ae1277453ed06))

Attaching the hint with add_note() preserved the exception type and traceback but made the hint
  invisible in the browser: Streamlit renders str(exception) and traceback.format_list(frames), and
  neither includes __notes__, so the allow_unsafe_jscode guidance survived only in the server
  console. Mutating args in place still skips the constructor, so the type and traceback are kept,
  while the hint lands in str(exception) where Streamlit will actually show it. Exceptions with
  empty args or a non-string args[0] fall back to the note.

- Remove em dashes from the PyPI summary and shipped frontend config
  ([`bdc6143`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/bdc6143f13d602d4e640f9029d4818123573738c))

The project description is published as the package summary on PyPI, and vite.config.ts ships inside
  the wheel. Both violated the no-em-dash rule.

- Report a selected row that a filter hides under MINIMAL
  ([`65c3db0`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/65c3db030392894e0c0e6d1c19a4deb58f81d612))

- Return the input frame from DataReturnMode.MINIMAL on first render
  ([`0752138`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/07521380362e2167ce386181fdead1a42a86c757))

MinimalCollector.create_initial_response ignored original_data and handed back a bare
  MinimalResponse, so .data was None until the frontend reported something. Every other
  data_return_mode returns the input frame straight away.

Combined with update_mode=MANUAL, which now attaches no update_on events at all, that meant .data
  stayed None until the user clicked the toolbar button.

A real response still wins, including an empty one: a grid that filtered every row away reports no
  rows rather than falling back to the input.

- Round-trip datetime columns and drop the deprecated copy keyword
  ([`40e2504`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/40e250489922d03277cc25bcc2b00ddd4daa287c))

- Satisfy the ruff version CI actually runs
  ([`32a6199`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/32a61993b871bdff2245b6f6c9a9fa63f564b2c8))

- Stop AgGrid writing into the caller's gridOptions dict
  ([`faee54e`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/faee54e6994ca990f209dc449f4099476a495e49))

- Warn when update_mode MANUAL overrides show_toolbar
  ([`278e8d9`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/278e8d96673b494230d2cfb6921ad45b0dc4d737))

An explicit show_toolbar=False was discarded without a word under update_mode=MANUAL. The override
  itself has to stay: the manual update button lives in the toolbar, and hiding the toolbar would
  leave a MANUAL grid with no return path at all now that MANUAL attaches no update_on events. But a
  silently ignored argument is a bug report waiting to happen, so the conflict is logged through the
  module logger and the message says what to do instead.

show_toolbar now defaults to None rather than False so that an explicit False can be told apart from
  the default. Warning on the default would fire for every MANUAL grid and say nothing about the
  caller's intent. None is resolved to False before the payload goes out, because the frontend reads
  a missing show_toolbar as true.

### Chores

- Add browser-less regression tests for the Python layer
  ([`4d44a54`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/4d44a54f4f54e7500b595f4830a02d36f838c602))

Adds test/grid_stub.py, which swaps out the one Streamlit-dependent step in AgGrid() (the
  _get_component_func() indirection) so a test can drive the whole Python layer in milliseconds: it
  can assert on the exact component_data payload the frontend would receive and feed a
  frontend-shaped reply back in to assert on the AgGridReturn that comes out. AppTest is not usable
  here because it never runs CCv2 component discovery.

Covers, with a verified fail-before-pass-after for each:

- data_hash was "" under use_json_serialization=True, so client_wins never refreshed rows after
  mount - the same mode returned an all-object DataFrame because frame_dtypes was withheld, and
  returned .data as a JSON string instead of a DataFrame - update_mode=MANUAL kept the default
  update_on events, so the update button was not the only return path, and did not force the toolbar
  on - .data raised "No objects to concatenate" on a zero-node grid - the error re-wrap changed the
  exception type, garbled the message and raised IndexError on empty args, and had to put the hint
  in str(exception) because Streamlit never renders __notes__ - walk_gridOptions indexed lists by
  element, crashing on nested lists and skipping JsCode stored directly in a list -
  GridOptionsBuilder.build() was not idempotent - AgGridReturn.keys() disagreed with
  __iter__/__len__ - datetime columns serialized missing values as the literal string NaT -
  conversion_errors='ignore' was forwarded to pandas, which removes it in 3.0 - determine_collector
  rejected DataReturnMode.CUSTOM - unknown string themes fell through to balham silently, and a
  custom theme built without a base lost its withParams/withParts

The three tests that lock the boundaries of the MANUAL change (an explicit update_on is honored,
  other modes keep their defaults) cannot fail against the old code by construction, so they were
  verified against mutations of the fix instead: making MANUAL always clear update_on, and making
  every update_mode clear it.

- Adopt ruff 0.16 default rule set
  ([`41cbd40`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/41cbd40eb3e7907d5679e119ef2caf25922dfd2e))

Drop the stopgap select = ["E4", "E7", "E9", "F"], which pinned the suite to ruff pre-0.16 defaults
  so CI would stop failing on unchanged code. The rule set is now ruff 0.16 defaults (413 rules),
  and the dev floor moves to ruff>=0.16 so a local run and CI agree on what "default" means.

Three rules are ignored with the reason recorded in the config: BLE001 (broad excepts are the
  deliberate shape of the error boundaries), TRY004 (the entry point has raised ValueError for bad
  argument types since v1) and PYI034 (typing.Self is 3.11+, the supported floor is 3.10). N999 is
  ignored for the two PascalCase modules that are public import paths.

- Apply ruff autofixes for the 0.16 default rules
  ([`4bbfda0`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/4bbfda081343d6cac98802f09d85ec71b8d9a25e))

All of these are ruff's own safe fixes, reviewed one by one: import sorting (I001), PEP 585/604
  annotations (UP006/UP007/UP035/UP045, all valid on the 3.10 floor), the placeholder `pass` after a
  docstring (PIE790), sorted __all__ (RUF022), str.removeprefix (FURB188) and one noqa: F841 that
  ruff 0.16 reports as unused (RUF100).

isort gets known-local-folder for the sibling modules the examples and tests import by path, so they
  group below st_aggrid instead of above it.

No behavior changes: the annotation rewrites are equivalent at runtime on 3.10+, removing `pass`
  after a docstring leaves the docstring as the body, and removeprefix on "ROOT_NODE_ID." matches
  the slice it replaces.

- Bump demo app requirement to v0.2.7
  ([`3090d9a`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/3090d9a483517ad084b83085b0e31a1b998ca66c))

- Bump vulnerable frontend transitives to clear npm audit
  ([`15e6bb0`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/15e6bb0a1ed6c421f08d9d4d76ee11d2be6436bc))

npm audit reported 2 high advisories, both in build tooling only:

- brace-expansion 5.0.6 -> 5.0.8 (rimraf > glob > minimatch) GHSA-3jxr-9vmj-r5cp DoS via
  exponential-time brace expansion GHSA-mh99-v99m-4gvg DoS via unbounded expansion length - postcss
  8.5.17 -> 8.5.23 (vite) GHSA-r28c-9q8g-f849 path traversal via sourceMappingURL auto-loading -
  nanoid 3.3.15 -> 3.3.16 (pulled in by the postcss bump)

Both packages are dev dependencies used at build time and neither is reachable from the shipped
  browser bundle, so users of the published wheel were never exposed. Lockfile only: package.json
  ranges already allowed the fixed versions, so no overrides and no direct dependency bumps were
  needed. Build output is byte identical before and after.

npm audit: 2 high -> 0 vulnerabilities.

- Bump vulnerable transitive pins in lockfiles
  ([`df865ac`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/df865ace93c153b8a23f867b4f2f38c10c3a087b))

Resolves 7 of the 8 open Dependabot alerts, all lockfile-only:

- uv.lock: tornado 6.5.7 (CVE fixes, was < 6.5.6 range x3 plus the 6.5.6 follow-up) and soupsieve
  2.8.4 (memory exhaustion, x2). Both are dev-environment transitives via streamlit and
  beautifulsoup4; the published wheel pins neither. - frontend package-lock.json: @babel/core 7.29.7
  (low, dev transitive).

Not addressed: esbuild GHSA-g7r4-m6w7-qqqr (low; dev-server-only file read on Windows). The fix is
  in esbuild 0.28.1, which vite 7 does not accept; it lands with a future vite 8 upgrade.

Full suite green after the bumps: 31 passed.

- Cap the ruff dev pin to the 0.16 line
  ([`4c912cf`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/4c912cf46a269ded492b39ab6393c929aca2def5))

The ruff action reads this constraint and installs the newest release satisfying it, so an unbounded
  floor hands CI whatever ruff ships next. That is not hypothetical: 0.16.0 grew the default rule
  set from 59 to 413 and turned this repo red on code nobody had touched. An upper bound makes the
  next expansion a deliberate upgrade with its own triage pass instead of a surprise on an unrelated
  PR.

- Clear the remaining ruff findings in the package
  ([`f1eeb23`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/f1eeb235fcb8074315200d3ca25ab4d423d1313f))

Two changes are visible at runtime and are called out here rather than buried:

- LOG015. The four warnings the package emitted went through the root logger, which installs a
  handler on first use and produces a record with no module name, so a host app could neither
  attribute nor silence them. They now go through a module logger (st_aggrid.AgGrid,
  st_aggrid.AgGridReturn). Text is unchanged; anything that configures the root logger still sees
  them by propagation. - TRY002. The four bare `raise Exception(...)` in the gridOptions/data
  parsing path become ValueError, matching the neighboring raise for an invalid gridOptions type,
  and now chain the original with `from`. The messages are byte for byte the same, and `except
  Exception` still catches them. Code that catches ValueError around AgGrid() will now catch these
  four cases too.

The rest is behavior-preserving:

- B023 on AgGridReturn is a false positive: _convert_with_error_policy calls the lambda
  synchronously in the same iteration, so the loop variable cannot change before it runs. The dtype
  is now bound as a default argument, which makes the capture explicit and silences the rule
  honestly instead of ignoring it. - B006 on GridOptionsBuilder.configure_columns is not a live bug:
  the default list is only membership-tested, never mutated or stored, so no state could leak
  between calls. The default is an empty tuple now, which keeps every current call identical,
  including passing None (still a TypeError, as before). - RUF013 makes three implicit Optionals
  explicit, C408 turns dict()/list() calls into literals, and SIM102 collapses two nested ifs in the
  collector factory.

- Clear the remaining ruff findings in the test suite
  ([`5322b29`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/5322b2980caf3453c9540b6b282e1a0ce016ae28))

RUF059: the browser-less tests unpack three values out of _parse_data_and_grid_options and assert on
  one or two of them. The ones a given test does not look at are now underscore-prefixed, which is
  also a better description of what each test is actually checking.

LOG002: e2e_utils named its logger after __file__, so the logger key was an absolute path and the
  record could not be routed by module.

Two findings are suppressed in place, each with the reason at the call site:

- SIM115 on the subprocess stdout TemporaryFile. The file deliberately outlives start() so the child
  can write to it; the class is the context manager that owns it and closes it in stop() and
  terminate(). - SIM118 on `"data" in response.keys()`. That test exists to prove keys() does not
  materialize the data properties, and Mapping.__contains__ goes through __getitem__, so the
  suggested rewrite would test the opposite of what the test is for.

- Cover the frontend-only fixes in the CCv2 e2e suite
  ([`231b735`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/231b73552bc6ff06cf3465c6dcd87890bd9b078d))

Four defects that are only observable in a browser now have guards, each verified by reverting the
  fix, rebuilding the frontend and watching the test fail:

- columns_state was applied only from componentDidUpdate when it differed from prevProps, so a saved
  layout was never applied on mount. The fixture state reverses the column order and hides a column,
  so the header row is unambiguous either way. - MINIMAL routed to the TypeScript LegacyCollector,
  whose payload is {nodes, gridState, ...}, while MinimalResponse reads {data, selectedRows}. The
  test selects a row and asserts both come back, and that the internal id column and the legacy node
  metadata are absent. - a gridOptions change on a rerun pushed the cloned gridOptions into
  updateGridOptions, and under use_json_serialization that object still carries rowData as a raw
  JSON string. AG Grid 35.3 rejects the malformed value and keeps its rows, so the only visible
  symptom is its "rowData must be an array" warning; the test watches the console for it, after
  waiting on the applied rowHeight to prove componentDidUpdate ran at all. A row-count assertion
  here passes against the unfixed code and would have been worthless. - update_mode=MANUAL is now
  exclusive, so the manual grid no longer needs the update_on=["columnPinned"] workaround that
  existed purely to neutralize the default events. Dropping it turns the existing button test into a
  real guard (an edit that reaches Python before the click now means MANUAL is not exclusive) and a
  second test covers selection, the other default trigger.

Raises the Playwright expect timeout for these modules. Every assertion that waits on a Streamlit
  rerun races a full round trip through a page of a dozen AG Grid instances behind a 6 MB bundle,
  and the default 5s ceiling sits close enough to that to flake. It is a ceiling, not a delay.

- Delete the dead CollectorFactory
  ([`47dbf24`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/47dbf2428a0953d02782dde2e215353df9139536))

- Describe DataReturnMode.MINIMAL by what it returns
  ([`d58bfcd`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/d58bfcdfc8b97019dad96f6c12318ec9932053be))

The data return example still called MINIMAL "only the grid's internal state". It returns the
  displayed rows and the selection as plain records and no grid state at all.

- Drop the broken options scraper and three unread JSON files
  ([`00c7df1`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/00c7df1433054a2ba3807e9469bcc157ff5391c2))

- Drop the root import shim and sweep em dashes outside the package
  ([`38df04b`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/38df04b027e5bd0212b20ecd0ffe6a51f4f2dc3e))

- streamlit_aggrid.py was never included in the wheel (pyproject ships only src/st_aggrid), so
  `import streamlit_aggrid` only worked from a checkout. The README already documents st_aggrid as
  the import path. - Replaced em dashes in README, CHANGELOG, skills, examples and tests, and
  removed an emoji from test/grid_performance_1m.py.

- Pin the ruff rule selection instead of inheriting defaults
  ([`d62c02f`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/d62c02f1630bf1c69faf581f914fe2c982c3c33e))

The lint job resolved the `ruff>=0.9.0` dev pin to the newest release, so the active rule set was
  whatever the latest ruff defaulted to. Ruff 0.16.0 raised that default from 59 rules to 413 and
  turned the job red on code nobody had touched: 143 findings against main, 144 against this branch.

The delta of one is not a regression either. This branch adds two B023 and one BLE001 in the
  conversion_errors='ignore' rewrite, and drops a RUF100 and a SIM118 with the deleted root shim.
  The B023 pair is a false positive: _convert_with_error_policy calls the lambda synchronously in
  the same iteration, so the loop variable it closes over cannot change first. The BLE001 is the
  documented behavior, returning the column unchanged when a conversion fails.

Selecting E4, E7, E9 and F pins the suite to ruff's pre-0.16 default, so it no longer moves when a
  new ruff ships. Verified green under 0.16.0, the version CI installs, and under 0.15.13.

Adopting the 0.16 defaults is worth doing, but it needs those 143 findings triaged on their own
  rather than folded into an unrelated PR.

- Relock for the ruff>=0.16 dev floor
  ([`0d717f9`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/0d717f9c67ebbcfbad5ce3aa9e3f40f400d30874))

uv.lock still pinned ruff 0.15.8 against the old >=0.9.0 specifier, which would resolve a ruff that
  does not know the default rule set the config now relies on. The relock also picks up the package
  version bump to 0.2.7 that the release commit wrote to pyproject.toml without touching the lock.

- Remove dead frontend components and unused module-level names
  ([`004fd7c`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/004fd7c6c1bc988493281e630f04336dafd486fd))

- Rename the Smoke job to Python, which is what it runs
  ([`f4151df`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/f4151df50900cfaa0b1d6fae387d486e6719ea5f))

- Restore the released CHANGELOG entries
  ([`a588890`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/a588890d547d668b63420bf8687bb2c109e191d6))

38df04b rewrote the shipped v0.1.1 entry to drop an em dash. python-semantic-release regenerates
  CHANGELOG.md on every release, so editing released history buys nothing and invites a conflict on
  the next run. The no-em-dash rule applies to new content, which the generator writes from commit
  messages.

- Retire the five legacy CCv1 test files
  ([`ef4f42f`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/ef4f42f588b5caaabcb18c69fdf69cb0b1e06cbb))

They drove the CCv1 iframe DOM through frame_locator("iframe"), which the CCv2 component no longer
  produces, so all five were unrunnable and had been sitting behind collect_ignore in conftest since
  the v2 rewrite. Resolved per file, with the reasoning recorded in test_legacy_coverage.py:

- test_grid_initialization.py: four of its six cases already exist as CCv2 tests in
  test_ccv2_e2e.py. The two that did not (data from a .json file, data and gridOptions from separate
  .json files) are ported to Python-level tests, since the file reading happens entirely in Python.
  - test_grid_return.py: basic return and sorting are already covered. Checkbox selection, header
  select-all and DataReturnMode.CUSTOM are browser-side and are ported to test_ccv2_legacy_port.py.
  The grouped-data cases are dropped: row grouping is an AG Grid Enterprise feature and those tests
  ran with enable_enterprise_modules=True against a grid with no license key. Its 30,000 row dummy
  dataset was incidental and no assertion used it. - test_grid_data_render.py: what it was really
  guarding is the Python serialization and hashing of unhashable cell values, which is ported as
  parameterized tests over lists, sets, dicts and empty containers in both serialization modes, plus
  a check that the fallback hash still tracks the data instead of collapsing to a constant. One
  condensed render check survives in the browser suite. - test_grid_drag_and_drop_example.py:
  dropped. It asserted AG Grid's own managed row-drag reordering; the only st-aggrid code it touched
  was gridOptions pass-through, already covered elsewhere. - test_grid_performance.py: dropped. It
  built a one million row grid and asserted wall-clock thresholds with 60 to 120 second waits, which
  measure the CI runner rather than the component.

The ported browser cases get their own fixture page rather than joining ccv2_e2e_app.py, so they do
  not lengthen the reruns that page's round-trip assertions wait on. olympic-winners.json and
  test-gridOptions.json go too: they were fixtures for the deleted apps and nothing else referenced
  them.

- Scope the BLE001 and PYI034 exemptions to the files that need them
  ([`3fdd2a8`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/3fdd2a89b25afc0b780bb5f15fee154ef2853a98))

The BLE001 justification named three error boundaries, but the project-wide ignore also covered two
  plain enum lookups in AgGrid.py: `DataReturnMode[...]` and `GridUpdateMode[...]` inside
  `try/except Exception`. Those raise KeyError and nothing else, so they now catch KeyError and
  chain with `raise ... from ex`, matching what aggrid_utils already does. The ignore moves to
  per-file-ignores for the two files that hold the real boundaries, so a blind except anywhere else
  gets flagged.

PYI034 fired in exactly one file, test/e2e_utils.py, and was ignored project-wide. It moves to
  per-file-ignores as well.

- Select CI test suites by marker instead of by filename
  ([`a45aa74`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/a45aa7471cba59edec2b943c6a544c1af6bb7ed0))

The workflow named two files, so everything else was invisible to CI. test_python_layer.py had never
  run there, and roughly fifty of the tests just added would not have run either: they would have
  looked like coverage while guarding nothing. This is the same failure mode that left five e2e
  files unexecuted, each dropped by a commit that did not think to edit tests.yml.

Marking the two browser suites and selecting on `-m browser` / `-m "not browser"` makes the default
  correct. A new test file now joins the right job by being written, and a silent job means there
  are no tests rather than no wiring.

The browser-less set runs on every Streamlit version in the matrix rather than just one. That is
  where API drift shows up first, and it costs 1.2s for 64 tests.

Split verified: 64 selected without a browser, 20 with, 84 total, so no test falls through the gap.
  Full suite green.

Also corrects the MINIMAL description in the skill file, which claimed the mode returns no row data.
  It never did match the Python contract, and the new lean collector makes the old wording plainly
  wrong.

- Ship only the built bundle from frontend/, not the whole tree
  ([`f74a18f`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/f74a18fa03788415e29bcbdd08b3d0ef6453d00d))

- Upgrade frontend build to vite 8
  ([`8067f3f`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/8067f3f6057e2fdfb1f1c3d634acad335b94f6db))

vite 7.3.5 -> 8.1.4 and @vitejs/plugin-react 5 -> 6. Vite 8 bundles with Rolldown and minifies with
  oxc, so esbuild leaves the dependency tree entirely; that clears the last open Dependabot alert
  (GHSA-g7r4-m6w7-qqqr, dev-server file read), which vite 7 could not take because it did not accept
  esbuild 0.28.1.

Config: minify uses the vite 8 default (oxc) instead of the removed esbuild path, and the old
  esbuild fine-tuning block is dropped; it sat under build where vite never read it, so it was a
  no-op all along.

Production build: 9.0s -> 1.1s, JS bundle 6851 -> 6040 kB (gzip 1661 -> 1503 kB). Full suite green
  against the new bundle: 31 passed (16 unit + 3 smoke + 12 e2e).

- Upgrade pillow and gitpython to clear the pip advisories
  ([`676cdc1`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/676cdc1c04a5013e0d5e975e35a4974aee63baad))

### Documentation

- Note the MANUAL update_mode toolbar override in the show_toolbar docstring
  ([`12cf204`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/12cf204431f6a1c4462d7460842ef13bd870d079))

### Features

- Warn when an update_on entry can never fire
  ([`d00d818`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/d00d8180071de3b928577275249d9847addd99f0))


## v0.2.7 (2026-07-11)

### Bug Fixes

- Wire manual update button and per-grid fullscreen in the toolbar
  ([`a7352c3`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/a7352c31b7d44e501b0ea26815d1bb5180b221e9))

Two toolbar actions were broken in the CCv2 world:

- The manual update button (update_mode=MANUAL) only logged to the console in debug mode; clicking
  it never sent anything to Streamlit. It now calls returnGridValue, so the current grid state
  including local edits round-trips to Python. - The fullscreen button looked up
  document.getElementById with a fixed gridContainer id. CCv2 renders without an iframe, so every
  grid on the page shared that id (invalid DOM) and fullscreen always targeted the first grid. The
  container is now a class and the handler goes through the React ref of its own grid.

Cleanups in the same pass:

- shouldGridReturn is evaluated before collection instead of after, so blocked events no longer pay
  for a full grid walk. - returnGridValue instantiated five collectors per event; it now creates the
  single one the configured data_return_mode needs. - Removed processPreselection, dead since the
  CCv2 rewrite.

New e2e test: edit a cell on a MANUAL grid (no rerun), click the toolbar update button, and assert
  the edit reaches Python. Frontend bundle rebuilt.

### Chores

- Bump demo app requirement to v0.2.6
  ([`9d36128`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/9d361286b2e6a4a7de62112dc4979b807c9507f0))


## v0.2.6 (2026-07-11)

### Bug Fixes

- Parse gridOptions independently of data and repair input edge cases
  ([`9d35b74`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/9d35b74c08cf7284654e845239e81cf98460d1dd))

_parse_data_and_grid_options only parsed string/Path gridOptions in an elif branch reachable when
  data was None, so combining a DataFrame with JSON-string gridOptions crashed on str.get
  downstream. The gridOptions parsing now runs first, for every input combination, and rejects
  unsupported types with a clear message.

Also fixed in the same pass:

- if data: on a DataFrame raised the pandas ambiguous-truth-value error instead of the intended
  message when data and gridOptions.rowData were both supplied; now checks data is not None. -
  AgGrid() with neither data nor gridOptions crashed with NoneType.get; it now renders an empty
  grid. - gridOptions rowData given as a list of record dicts (the AG Grid way) crashed in
  pd.read_json; lists are now accepted alongside JSON strings, and dtypes are captured for
  round-trip conversion. - use_json_serialization=True without data crashed on data.to_json. - The
  deprecated try_to_convert_back_to_original_types flag was silently ignored (hardcoded True);
  opting out now withholds frame_dtypes so conversion is actually skipped. - AgGridReturn
  len()/iter()/keys() used inspect.getmembers(self), which evaluated every property and rebuilt
  DataFrames just to list attribute names; names are now taken from the class unevaluated. -
  GridOptionsBuilder.from_dataframe reported unknown kwargs via print(); now warnings.warn. Removed
  dead defaultColDef block.

New test/test_python_layer.py covers the parsing matrix, the AgGridReturn Mapping interface
  (including a guard that iteration does not trigger property getters), and the builder warning.
  Browser-less, runs in under a second.

### Chores

- Bump demo app requirement to v0.2.5
  ([`a05aeae`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/a05aeaee0ac6e937b4db25d0ff30022299c4b886))


## v0.2.5 (2026-07-11)

### Bug Fixes

- Support Streamlit 1.51 and 1.52 via isolate_styles compat shim
  ([`2b268d6`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/2b268d6cf4a3fbcc3ad0a16bb6237a6bcbb54e0f))

The component registered with st.components.v2.component(..., isolate_styles=False), but that
  keyword only exists on the registration call from Streamlit 1.53. On 1.51 / 1.52 it belongs to the
  per-call renderer instead, so importing st_aggrid raised TypeError even though pyproject declares
  streamlit >= 1.51.

New st_aggrid/_compat.py resolves the difference once at import time and always renders with style
  isolation disabled, whichever Streamlit is installed. Same approach as st-rsuite 0.3.4.

- test/test_registration_smoke.py: browser-less guard that discovery registers the component and the
  shim finds the isolate_styles toggle; verified locally on 1.51.0, 1.52.2 and 1.59.1. - tests.yml:
  new lint (ruff) job and a smoke job across a Streamlit 1.51 -> latest matrix. - e2e go_to_app
  fixture: first-attach timeout 5s -> 15s; cold starts routinely blew it and flaked the whole suite.
  - conftest: drop unused sys import (ruff F401).

### Chores

- Build frontend before smoke matrix in CI
  ([`9280d95`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/9280d95afe775aa49d7f17e4bb246e452ca63964))

The smoke job installs the wheel via the test conftest; without the npm build the wheel ships no
  frontend assets and component discovery cannot resolve asset_dir, failing on every Streamlit
  version.

- Bump demo app requirement to v0.2.4
  ([`510a4cb`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/510a4cbcd9ceff4bd5368d91501eb89d097f10cf))


## v0.2.4 (2026-06-08)

### Bug Fixes

- Emit valid font-family for theme="streamlit" instead of doubled quotes
  ([`dcd77e0`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/dcd77e05bb87229f4c635f39765f746b3241c8bb))

Streamlit injects --st-font on the component host as a CSS-normalized, quoted stack such as '"Source
  Sans", sans-serif'. streamlitFontFamily took the first comma token without stripping the
  surrounding quotes and passed it as {googleFont}, so AG Grid re-quoted the already-quoted name and
  emitted an invalid --ag-font-family of '""Source Sans"", ""Source Sans""'. Browsers drop the
  invalid declaration and the grid falls back to the UA default sans, so theme="streamlit" rendered
  grid text in a different font than the rest of the app.

Parse the full font stack, strip wrapping single/double quotes from each token, and return the plain
  names so AG Grid quotes them once. Drop the googleFont fetch: in CCv2 the grid renders inline in
  the same document where Streamlit already self-hosts the face, so no web-font load is needed. Also
  update the empty-st-font fallback from the stale "Source Sans Pro" to modern Streamlit's
  self-hosted "Source Sans, sans-serif".

Verified in a browser (Streamlit 1.55, built wheel): .ag-cell computed font-family equals
  document.body and --ag-font-family contains no doubled quotes.

### Chores

- Bump demo app requirement to v0.2.3
  ([`21b8d50`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/21b8d501e7190b8afcad64c4cb1383e94b44c891))


## v0.2.3 (2026-06-07)

### Bug Fixes

- Wire columns_auto_size_mode so FIT_CONTENTS sizes columns to content
  ([`c058b8a`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/c058b8ad759b9f17a8e9e713365fa4c786e78a93))

columns_auto_size_mode was exported as an enum but never consumed by AgGrid(), so passing
  ColumnsAutoSizeMode.FIT_CONTENTS had no effect. Columns instead collapsed to a uniform minWidth
  because GridOptionsBuilder.from_dataframe unconditionally injects autoSizeStrategy=fitGridWidth,
  which squishes wide grids.

Add columns_auto_size_mode as an explicit AgGrid() parameter that maps to AG Grid's native
  autoSizeStrategy and overrides any strategy already on gridOptions: NO_AUTOSIZE clears it,
  FIT_ALL_COLUMNS_TO_VIEW maps to fitGridWidth, FIT_CONTENTS maps to fitCellContents.

Add e2e regression guards: FIT_CONTENTS on a wide from_dataframe grid sizes columns to content
  (long-header column far wider than a short one) instead of collapsing; and update_on
  selection/cellValueChanged round-trip to Python (the separately reported update_on issue, which
  does not reproduce on current main).

### Chores

- Bump demo app requirement to v0.2.2
  ([`729958c`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/729958c4d322181256aac09e8b6304972d7f85b7))

- Restrict GITHUB_TOKEN permissions in tests workflow
  ([`675d877`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/675d877a4bb6867a2a4e942583154d758f5ba5e9))

CodeQL actions/missing-workflow-permissions: tests.yml declared no permissions block, so
  GITHUB_TOKEN defaulted to broad scopes. The e2e job only checks out code and runs Playwright
  tests, so contents: read is sufficient (the on-failure artifact upload uses the Actions runtime
  token, not GITHUB_TOKEN scopes). release.yml and publish.yml already set least-privilege
  permissions per job.


## v0.2.2 (2026-06-05)

### Bug Fixes

- Bump bundled lodash to 4.18.1 to patch prototype pollution
  ([`fb248cd`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/fb248cd46b624fa4fd80bbb28f86efd23649a5c7))

lodash is bundled into the shipped component JS (used for debounce, isEqual, omit, isEmpty,
  cloneDeep), so this is the one dependency advisory that actually reaches end users of the wheel.

- 4.17.23 -> 4.18.1 - GHSA-f23m-r3pf-42rh: prototype pollution via array path bypass in _.unset and
  _.omit (this code uses _.omit on internal grid options) - GHSA-r5fr-rjxr-66jc: code injection via
  _.template (not imported here, but patched anyway since the full library is bundled)

Frontend rebuilds and typechecks clean against vite 7.3.5; the CI publish job rebuilds the bundle on
  release, so the published wheel picks up the patched library.

### Chores

- Bump demo app requirement to v0.2.1
  ([`86b472e`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/86b472ef57e878e752dca4a5456ed229666d16db))

- Patch build-time frontend deps (vite, postcss, brace-expansion)
  ([`7f1849b`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/7f1849b4b59be3b6b1181c353d1999037f75d50f))

Regenerate frontend package-lock.json to pull patched build tooling. These are dev/build-only and
  are not bundled into the shipped component, so no runtime exposure for end users:

- vite 7.3.1 -> 7.3.5 (dev-server arbitrary file read, server.fs.deny bypass, optimized-deps path
  traversal; only affects `vite dev`, which this project never runs; the build uses `vite build`
  library mode) - postcss 8.5.8 -> 8.5.15 (XSS via unescaped </style> in CSS stringify) -
  brace-expansion 5.0.5 -> 5.0.6 (large numeric range DoS)

- Refresh uv.lock transitive deps to patched versions
  ([`8faf0e3`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/8faf0e3ae5b2003902a6fbbde05caf2db24f9e52))

Dev/CI lockfile only. The published wheel pins none of these (it declares streamlit>=1.51,
  pandas>=1.4.0, python-decouple), so end users resolve their own versions and are unaffected.
  Surgical uv lock --upgrade-package for the flagged transitive/dev deps:

- urllib3 2.6.3 -> 2.7.0 (decompression-bomb safeguard bypass; sensitive headers forwarded across
  origins on proxied low-level redirects) - gitpython 3.1.46 -> 3.1.50 (command injection via
  options bypass; newline-injection RCE via core.hooksPath; path traversal) - pillow 12.1.1 ->
  12.2.0 (OOB write on PSD; FITS decompression bomb; integer/heap overflows; PDF trailer parse DoS)
  - idna 3.11 -> 3.18 (idna.encode bypass of the CVE-2024-3651 fix) - pytest 9.0.2 -> 9.0.3
  (vulnerable tmpdir handling)

Also corrects the editable self-version pin to 0.2.1.


## v0.2.1 (2026-06-05)

### Bug Fixes

- Sanitize NaN/Inf in row data so grids with missing values render
  ([`2b5ca1b`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/2b5ca1b0fcf24d8097ed426b0be53f49fe5a45bd))

DataFrames containing missing values (None/NaN/NaT) failed to render at all. pandas stores a missing
  numeric value as float NaN, and the default data path built row_data via data.to_dict("records"),
  which keeps that NaN. Streamlit then serialized the component payload with a bare NaN token, which
  the frontend JSON.parse rejects, so AG Grid never mounted and the user saw a SyntaxError instead
  of a grid.

The existing _sanitize_nan_inf helper was only applied to gridOptions, not to the row data. The
  use_json_serialization="auto" fallback did not catch this either, because it only triggers on a
  Python-side serialization exception and NaN floats do not raise one.

Apply _sanitize_nan_inf to the records list so missing values become null in the payload. Add a CCv2
  e2e regression test that renders a DataFrame with None in both a text and a numeric column and
  asserts the grid mounts with all rows.

Fixes the rendering failure reported in streamlit/streamlit#15435.

### Chores

- Bump demo app requirement to v0.2.0
  ([`dd81ed1`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/dd81ed18cbdc0670f51c669f1a7e1243496b577f))

- Replace broken static.streamlit.io badge with shields.io
  ([`3171d4e`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/3171d4ed608de0fae7f111c2d97916d7f011f706))


## v0.2.0 (2026-05-13)

### Chores

- Add e2e tests for the CCv2 AgGrid component
  ([`72b3b89`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/72b3b8974eb1e854b4c90c6156997a0a14563ffa))

Adds the first end-to-end test suite for the v2 component (Playwright + pytest, real Streamlit
  server, real Chromium, exercises the full Python -> component -> DOM stack).

- test/test_ccv2_e2e.py covers component attachment (no iframe), init from DataFrame / JSON /
  gridOptions-only / empty, Python<->frontend data roundtrip, and sort-by-header interaction. -
  test/ccv2_e2e_app.py is the Streamlit fixture app the tests load. - test/conftest.py
  force-installs a freshly built wheel before each session because Streamlit's CCv2 manifest scanner
  cannot locate src/st_aggrid/pyproject.toml through an editable install (dist name
  streamlit-aggrid-v2 doesn't match importable package name st_aggrid, so _pyproject_via_import_spec
  returns None). The legacy CCv1 iframe-pattern tests under test/test_grid_*.py are excluded via
  collect_ignore until they're ported.

- Add tests CI workflow
  ([`85ee50d`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/85ee50def3cd4eadaedb99f07fd844f698a1e918))

Runs the CCv2 e2e suite (test/test_ccv2_e2e.py) on every push to main and on PRs targeting main. The
  workflow builds the frontend first because the test conftest builds the wheel via 'uv build' and
  hatchling silently produces an empty wheel if src/st_aggrid/frontend/build/ is missing. Playwright
  Chromium is installed with --with-deps so the runner has the system libs the browser needs.

- Bump demo app requirement to v0.1.5
  ([`714dea5`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/714dea5c028e76e7fc267831f8b749dbdd816df5))

### Features

- Upgrade AG Grid to v35.3.0
  ([`d80eabf`](https://github.com/lperezmo/streamlit-aggrid-v2/commit/d80eabfa565c59182ebbe479aaf7ebc24cca907b))

Bumps the bundled AG Grid from v34.3.1 to v35.3.0 and AG Charts Enterprise from 12.3.1 to 13.3.0.
  Per AG Grid's upgrade guide there are no API removals or deprecations in v35; cellDataType was
  stripped from columnTypes and colId from autoGroupColumnDef (we reference neither). No Python API
  changes.

Highlights unlocked by the bump: - Formulas + Formula Editor (35.0 / 35.1) - allowFormula on
  columnDef enables spreadsheet-style =SUM(...) cells with autocomplete and fill-handle. - Column
  Selection (35.0) - cellSelection.columnSelection lets users click column headers to select whole
  columns. - BigInt cell type, Named Date Ranges, Theme Builder Imports, Excel Data Protection
  (35.1). - Compact Group Column, Aggregation Editing (35.2). - Quick Access Toolbar, Cell Notes,
  Server-Side Grand Total Row (35.3).

A new showcase page (Enterprise > What's new in v35) demonstrates Formulas and Column Selection with
  runnable examples.

README updates: - bumped AG Grid version mention to 35.3.0. - comparison table corrected: original
  streamlit-aggrid is on AG Grid v34 (not v31), and is still actively maintained on the CCv1 / v34
  line rather than 'inactive since 2023'.


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
