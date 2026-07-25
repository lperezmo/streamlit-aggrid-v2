"""Generate src/st_aggrid/_event_catalog.py from the bundled AG Grid types.

The catalog of event names that ``update_on`` accepts has to come from the
exact ag-grid-community version the frontend bundles, or validation warns on
events that are perfectly valid. It used to come from JSON scraped off the AG
Grid docs site; that snapshot drifted 20 events behind before it was deleted,
and the scraper itself had rotted into returning "[]" (see issue #12).

These three declarations carry the same information, in the installed package:

    eventTypes.d.ts          _PUBLIC_EVENTS      grid api events
    interfaces/iColumn.d.ts  ColumnEventName     Column instance events
    interfaces/iRowNode.d.ts RowNodeEventType    RowNode instance events

``_PUBLIC_EVENTS`` is the authority for what ``update_on`` may listen to.
``AgEventType`` would be wrong: it unions in ``_INTERNAL_EVENTS``, which
``api.addEventListener`` does accept but which AG Grid documents as removable
at any time, so those should not be advertised as valid.

The other two exist to tell a user who passes ``widthChanged`` that the name is
real but fires on a Column rather than the grid, which is a different mistake
from a typo and deserves a different message.

Usage:
    python scripts/gen_event_catalog.py            # rewrite the module
    python scripts/gen_event_catalog.py --check    # fail if it is out of date

``--check`` is what CI runs, so bumping ag-grid-community without regenerating
turns the build red instead of silently shipping a stale catalog. Every parse
below fails loudly for the same reason: a renamed constant must break the
build, never quietly yield an empty set.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AG_GRID = ROOT / "src/st_aggrid/frontend/node_modules/ag-grid-community"
TYPES = AG_GRID / "dist/types/src"
TARGET = ROOT / "src/st_aggrid/_event_catalog.py"

# Below these counts something has gone wrong with the parse rather than with
# AG Grid: the real lists have been in this ballpark for many major versions.
MINIMUMS = {"grid": 80, "internal": 40, "column": 10, "row": 15}


class GenerationError(RuntimeError):
    """Raised when the types cannot be parsed, so the caller fails loudly."""


def _read(relative: str) -> str:
    path = TYPES / relative
    if not path.is_file():
        raise GenerationError(
            f"{path} is missing. Run `npm ci` in src/st_aggrid/frontend first; "
            "the catalog is generated from the installed ag-grid-community."
        )
    return path.read_text(encoding="utf-8")


def _quoted(fragment: str, source: str) -> set[str]:
    """Every quoted string literal in a fragment of TypeScript.

    The fragment is validated as a whole rather than harvested from, because
    harvesting fails silently in both directions. A JSDoc comment inside the
    brackets contributes its own quoted words, so a deprecation note naming an
    old event would add a name that does not exist and quietly stop warning
    about it. An event name containing a character outside ``[A-Za-z0-9]`` would
    match nothing and be dropped, so a real event would be reported to users as
    "not an AG Grid event". Neither shows up in the count checks: one name off
    stays far above the floors.

    So: strip comments, then require that what is left is nothing but quoted
    literals and separators. Anything else means the declaration changed shape
    and the parser needs a human, which is the whole point of failing loudly.
    """
    without_comments = re.sub(r"/\*.*?\*/", " ", fragment, flags=re.DOTALL)
    without_comments = re.sub(r"//[^\n]*", " ", without_comments)

    names = set(re.findall(r"""['"]([^'"]+)['"]""", without_comments))
    residue = re.sub(r"""['"][^'"]*['"]""", " ", without_comments)
    if residue.strip(" \t\r\n,|;"):
        raise GenerationError(
            f"unexpected syntax in the {source} declaration: "
            f"{residue.strip()[:120]!r}. It is no longer a plain list of string "
            "literals, so this parser could silently add or drop an event name. "
            "Inspect the declaration and update the parser."
        )
    for name in names:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", name):
            raise GenerationError(
                f"{source} contains {name!r}, which does not look like an event "
                "name. Either the declaration changed shape or AG Grid started "
                "using a naming style this generator does not handle."
            )
    return names


def _readonly_tuple(constant: str) -> set[str]:
    """A `declare const NAME: readonly ['a', 'b', ...];` declaration."""
    text = _read("eventTypes.d.ts")
    # Declared as `export declare const _PUBLIC_EVENTS: readonly [...]`, so
    # there is a colon rather than an assignment between name and value.
    match = re.search(
        rf"{re.escape(constant)}\s*:\s*readonly\s*\[(.*?)\]\s*;", text, re.DOTALL
    )
    if not match:
        raise GenerationError(
            f"could not find `{constant}: readonly [...]` in eventTypes.d.ts. "
            "AG Grid may have renamed or restructured it; check the file and "
            "update this parser."
        )
    return _quoted(match.group(1), constant)


def _string_union(relative: str, alias: str) -> set[str]:
    """A `type Alias = 'a' | 'b' | ...;` declaration."""
    text = _read(relative)
    match = re.search(rf"type\s+{re.escape(alias)}\s*=\s*([^;]+);", text)
    if not match:
        raise GenerationError(
            f"could not find `type {alias} = ...` in {relative}. AG Grid may "
            "have renamed or restructured it; check the file and update this "
            "parser."
        )
    return _quoted(match.group(1), alias)


def ag_grid_version() -> str:
    manifest = AG_GRID / "package.json"
    if not manifest.is_file():
        raise GenerationError(f"{manifest} is missing; run `npm ci` first")
    version = json.loads(manifest.read_text(encoding="utf-8")).get("version")
    if not version:
        raise GenerationError(f"{manifest} declares no version")
    return version


def build() -> str:
    grid = _readonly_tuple("_PUBLIC_EVENTS")
    internal = _readonly_tuple("_INTERNAL_EVENTS")
    column = _string_union("interfaces/iColumn.d.ts", "ColumnEventName")
    row = _string_union("interfaces/iRowNode.d.ts", "RowNodeEventType")

    for label, names in (
        ("grid", grid),
        ("internal", internal),
        ("column", column),
        ("row", row),
    ):
        if len(names) < MINIMUMS[label]:
            raise GenerationError(
                f"parsed only {len(names)} {label} events, expected at least "
                f"{MINIMUMS[label]}. The declaration probably changed shape; "
                "a partial parse must not become a shipped catalog."
            )

    # A name in both lists is dispatched on the grid api too, so it is a valid
    # update_on value and must not be reported as instance-only. sortChanged
    # and rowSelected are the obvious cases.
    column_only = column - grid
    row_only = row - grid
    # Same rule for the internal list: AgEventType unions it with the public
    # one, and nothing in AG Grid stops addEventListener from taking an internal
    # name, so these very likely do fire. They are still not usable, because
    # GridApi.addEventListener is typed to the public set and AG Grid documents
    # these as removable without notice. They get their own message rather than
    # being called "not an AG Grid event", which would be false.
    internal_only = internal - grid - column_only - row_only

    def block(names: set[str]) -> str:
        return "\n".join(f'        "{n}",' for n in sorted(names))

    version = ag_grid_version()
    return f'''"""Event names accepted by ``update_on``, generated from the AG Grid types.

Do not edit by hand. Regenerate with::

    python scripts/gen_event_catalog.py

Generated from ag-grid-community {version}, the version pinned in
src/st_aggrid/frontend/package.json. CI runs the generator with ``--check``, so
this file cannot drift from the bundled AG Grid without failing the build.
"""

# The ag-grid-community release these names were read from. Reported in the
# warning text so a user who hits it can tell which catalog was consulted.
AG_GRID_VERSION = "{version}"

# _PUBLIC_EVENTS: what api.addEventListener publicly supports, and therefore
# exactly what update_on may name.
GRID_EVENTS = frozenset(
    {{
{block(grid)}
    }}
)

# Real event names that fire on a Column instance rather than the grid api, so
# update_on can never receive them. Names that are also grid events (sortChanged,
# columnValueChanged and friends) are excluded: those are valid update_on values.
COLUMN_ONLY_EVENTS = frozenset(
    {{
{block(column_only)}
    }}
)

# The same, for events dispatched on a RowNode. rowSelected is absent because it
# is also a grid event.
ROW_NODE_ONLY_EVENTS = frozenset(
    {{
{block(row_only)}
    }}
)

# _INTERNAL_EVENTS. AgEventType unions these with the public set and the event
# service does not validate names, so listening for one very likely does work
# today. They are still not supportable: GridApi.addEventListener is typed to the
# public set and AG Grid marks these removable without notice. Telling a caller
# such a name "is not an AG Grid event" would be false, so it gets its own
# message.
INTERNAL_EVENTS = frozenset(
    {{
{block(internal_only)}
    }}
)
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if the committed catalog differs from a fresh parse",
    )
    args = parser.parse_args()

    try:
        generated = build()
    except GenerationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.check:
        current = TARGET.read_text(encoding="utf-8") if TARGET.is_file() else ""
        if current != generated:
            print(
                f"error: {TARGET.relative_to(ROOT)} is out of date with the "
                "bundled ag-grid-community.\n"
                "Run: python scripts/gen_event_catalog.py",
                file=sys.stderr,
            )
            return 1
        print(f"{TARGET.relative_to(ROOT)} is current")
        return 0

    # newline="\n" because the default translates to os.linesep, so the same
    # command would write CRLF on Windows and LF on Linux. The repo has no
    # .gitattributes, so which one landed in a commit would depend on the
    # contributor's core.autocrlf, and a regen on the other platform would show
    # up as a whole-file diff. --check never notices, since read_text normalizes
    # newlines on the way in.
    TARGET.write_text(generated, encoding="utf-8", newline="\n")
    print(f"wrote {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
