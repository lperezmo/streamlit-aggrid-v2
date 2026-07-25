"""The generator has to fail loudly on a declaration it cannot parse.

``--check`` in CI compares the committed catalog against the output of the same
parser that produced it, so it cannot detect a parser that is quietly wrong.
That matters more than usual here: the thing this generator replaced was a
scraper that stopped matching the page it read and returned ``"[]"`` for years
without anyone noticing, and the JSON it had produced drifted 20 events behind
the shipped AG Grid.

So the property under test is not "it parses today's files", which
test_event_catalog.py already covers from the other end. It is that a
declaration which changed shape produces an error rather than a subtly wrong
catalog. Fixtures are synthetic and minimal: the point is the shape, and the
real 100 KB files would obscure it.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

_SCRIPT = (
    pathlib.Path(__file__).resolve().parent.parent / "scripts" / "gen_event_catalog.py"
)

# Enough names to clear the generator's own minimum counts, which exist to catch
# a parse that collapsed entirely. Padding is generated rather than spelled out
# so a reader is not left counting string literals.
GRID = [f"gridEvent{i}" for i in range(85)] + ["sortChanged", "rowSelected"]
INTERNAL = [f"internalEvent{i}" for i in range(45)]
COLUMN = [f"columnEvent{i}" for i in range(11)] + ["sortChanged"]
ROW = [f"rowEvent{i}" for i in range(16)] + ["rowSelected"]


def _quoted_list(names):
    return ", ".join(f'"{n}"' for n in names)


def _union(names):
    return " | ".join(f"'{n}'" for n in names)


def write_fake_ag_grid(
    root, *, event_types=None, column=None, row=None, version="35.3.0"
):
    """A minimal node_modules/ag-grid-community the generator can be pointed at."""
    types = root / "dist" / "types" / "src"
    (types / "interfaces").mkdir(parents=True, exist_ok=True)

    (root / "package.json").write_text(
        json.dumps({"version": version}), encoding="utf-8"
    )
    (types / "eventTypes.d.ts").write_text(
        event_types
        if event_types is not None
        else (
            f"export declare const _PUBLIC_EVENTS: readonly [{_quoted_list(GRID)}];\n"
            f"declare const _INTERNAL_EVENTS: readonly [{_quoted_list(INTERNAL)}];\n"
        ),
        encoding="utf-8",
    )
    (types / "interfaces" / "iColumn.d.ts").write_text(
        column
        if column is not None
        else f"export type ColumnEventName = {_union(COLUMN)};\n",
        encoding="utf-8",
    )
    (types / "interfaces" / "iRowNode.d.ts").write_text(
        row if row is not None else f"export type RowNodeEventType = {_union(ROW)};\n",
        encoding="utf-8",
    )
    return root


@pytest.fixture
def generator(tmp_path):
    """A fresh import of the script, aimed at a fixture tree.

    Imported by path because scripts/ is deliberately not a package: it is dev
    tooling and is not shipped in the wheel.
    """
    spec = importlib.util.spec_from_file_location("gen_event_catalog", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def aim_at(**kwargs):
        fake = write_fake_ag_grid(tmp_path / "ag-grid-community", **kwargs)
        module.AG_GRID = fake
        module.TYPES = fake / "dist" / "types" / "src"
        return module

    return aim_at


def test_a_well_formed_tree_produces_the_expected_sets(generator):
    module = generator()
    out = module.build()

    assert 'AG_GRID_VERSION = "35.3.0"' in out
    assert '"gridEvent0",' in out
    # In both the grid list and the Column list, so it belongs only to the grid:
    # it is a usable update_on value and must not be reported as Column-only.
    assert (
        out.index("GRID_EVENTS")
        < out.index('"sortChanged",')
        < out.index("COLUMN_ONLY_EVENTS")
    )
    assert out.count('"sortChanged",') == 1
    assert out.count('"rowSelected",') == 1


def test_a_renamed_constant_is_an_error_not_an_empty_catalog(generator):
    module = generator(
        event_types="export declare const _EVENTS_RENAMED_IN_V36: readonly [];\n"
    )
    with pytest.raises(module.GenerationError, match="_PUBLIC_EVENTS"):
        module.build()


def test_a_collapsed_parse_is_an_error(generator):
    """The floors exist for the case where the declaration is found but yields
    almost nothing, which would otherwise ship a catalog that warns about
    everything."""
    module = generator(
        event_types=(
            'export declare const _PUBLIC_EVENTS: readonly ["onlyOne"];\n'
            f"declare const _INTERNAL_EVENTS: readonly [{_quoted_list(INTERNAL)}];\n"
        )
    )
    with pytest.raises(module.GenerationError, match="expected at least"):
        module.build()


def test_an_unexpected_name_shape_is_an_error(generator):
    """A name outside [A-Za-z0-9] used to be dropped silently, because the
    literal pattern simply did not match it. A dropped name is the worst case:
    a real, working event gets reported to users as not existing."""
    module = generator(
        event_types=(
            f'export declare const _PUBLIC_EVENTS: readonly ["cell-clicked", {_quoted_list(GRID)}];\n'
            f"declare const _INTERNAL_EVENTS: readonly [{_quoted_list(INTERNAL)}];\n"
        )
    )
    with pytest.raises(module.GenerationError, match="cell-clicked"):
        module.build()


def test_a_nested_generic_in_a_union_is_an_error(generator):
    """Harvesting quoted literals out of the fragment would take 'notAnEvent'
    along, and a bogus Column-only name means a valid grid event could be
    reported as unusable."""
    module = generator(
        column=(
            "export type ColumnEventName = Extract<keyof Foo, 'notAnEvent'> | "
            f"{_union(COLUMN)};\n"
        )
    )
    with pytest.raises(module.GenerationError, match="unexpected syntax"):
        module.build()


@pytest.mark.parametrize(
    "comment",
    [
        # Inline, the way a JSDoc block annotates one entry.
        '/** @deprecated renamed from "legacyName" in v36 */',
        # On its own line, which is the only way a // comment can appear inside a
        # multi-line array without commenting out the rest of that line.
        '// was "legacyName"\n',
    ],
)
def test_a_comment_naming_an_old_event_does_not_add_it(generator, comment):
    """Comments are stripped rather than rejected: AG Grid is free to document
    its own declarations, and a name mentioned in prose is not an event. Left
    unstripped it would enter the catalog, and update_on would then go quiet
    about a name that does not exist, which is the original bug.
    """
    module = generator(
        event_types=(
            "export declare const _PUBLIC_EVENTS: readonly [\n"
            f"    {comment}\n"
            f"    {_quoted_list(GRID)}\n"
            "];\n"
            f"declare const _INTERNAL_EVENTS: readonly [{_quoted_list(INTERNAL)}];\n"
        )
    )
    out = module.build()

    assert "legacyName" not in out
    assert '"gridEvent0",' in out


def test_a_missing_install_says_to_run_npm_ci(generator, tmp_path):
    """The likely first failure for a new contributor, so the message has to name
    the command rather than surface a bare path error."""
    module = generator()
    module.TYPES = tmp_path / "nonexistent" / "src"
    with pytest.raises(module.GenerationError, match="npm ci"):
        module.build()


def test_the_generated_module_is_importable_python(generator):
    """A generated file that does not parse would only be discovered by whatever
    imported it next."""
    module = generator()
    namespace = {}
    exec(compile(module.build(), "_event_catalog.py", "exec"), namespace)  # noqa: S102

    assert namespace["AG_GRID_VERSION"] == "35.3.0"
    assert "sortChanged" in namespace["GRID_EVENTS"]
    assert namespace["GRID_EVENTS"].isdisjoint(namespace["COLUMN_ONLY_EVENTS"])
    assert namespace["GRID_EVENTS"].isdisjoint(namespace["ROW_NODE_ONLY_EVENTS"])
    assert namespace["GRID_EVENTS"].isdisjoint(namespace["INTERNAL_EVENTS"])
