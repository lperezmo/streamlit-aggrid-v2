import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"
import test from "node:test"

import { deepMap } from "../.test-build/utils.js"
import {
  applyExportFormulaProtection,
  neutralizeCsvFormula,
  protectCsvExportParams,
} from "../.test-build/utils/csvExport.js"
import { STREAMLIT_THEME_VARS } from "../.test-build/streamlitThemeVars.js"

const marker = "::JSCODE::(() => 'executed')()::JSCODE::"

test("deepMap keeps every rowData subtree opaque", () => {
  const input = {
    trusted: marker,
    nested: {
      rowData: [{ value: marker, children: [{ value: marker }] }],
    },
    array: [{ detail: { rowData: [{ value: marker }] } }],
  }

  const mapped = deepMap(
    input,
    value => (value === marker ? "executed" : value),
    ["rowData"]
  )

  assert.equal(mapped.trusted, "executed")
  assert.equal(mapped.nested.rowData[0].value, marker)
  assert.equal(mapped.nested.rowData[0].children[0].value, marker)
  assert.equal(mapped.array[0].detail.rowData[0].value, marker)
})

test("CSV formula neutralization preserves ordinary and numeric values", () => {
  for (const dangerous of [
    "=1+1",
    "+SUM(A1:A2)",
    "-1+2",
    "@SUM(A1:A2)",
    "\t=1+1",
    "\r=1+1",
    "  =1+1",
    "\n\t@SUM(A1:A2)",
  ]) {
    assert.equal(neutralizeCsvFormula(dangerous), `'${dangerous}`)
  }

  for (const benign of ["plain text", "1+1", "'=-already-text", ""]) {
    assert.equal(neutralizeCsvFormula(benign), benign)
  }
  assert.equal(neutralizeCsvFormula(-42), -42)
  assert.equal(neutralizeCsvFormula(0), 0)
  assert.equal(neutralizeCsvFormula(null), null)
})

test("application CSV callbacks run before final neutralization", () => {
  let calls = 0
  const original = {
    fileName: "custom.csv",
    processCellCallback: params => {
      calls += 1
      return `=${params.value}`
    },
  }

  const protectedParams = protectCsvExportParams(original)

  assert.equal(protectedParams.fileName, "custom.csv")
  assert.equal(protectedParams.processCellCallback({ value: "2+2" }), "'=2+2")
  assert.equal(calls, 1)
  assert.notEqual(protectedParams, original)
})

test("default protection touches cell values but leaves AG Grid's header resolution alone", () => {
  // AG Grid v35 invokes processHeaderCallback with just { column } and
  // processGroupHeaderCallback with just { columnGroup }: there is no value
  // field to neutralize, and replicating its display-name resolution would
  // regress headerValueGetter and aggregation naming. So with no user
  // callbacks, only processCellCallback may be installed.
  const protectedParams = protectCsvExportParams()

  assert.equal(protectedParams.processCellCallback({ value: "=cmd" }), "'=cmd")
  assert.equal(protectedParams.processHeaderCallback, undefined)
  assert.equal(protectedParams.processGroupHeaderCallback, undefined)
  assert.equal(protectedParams.processRowGroupCallback, undefined)
})

test("application header callbacks compose with neutralization", () => {
  const column = { getColDef: () => ({ headerName: "=HYPERLINK(A1)" }) }
  const protectedParams = protectCsvExportParams({
    processHeaderCallback: params => params.column.getColDef().headerName,
  })
  assert.equal(protectedParams.processHeaderCallback({ column }), "'=HYPERLINK(A1)")
})

test("supplied group-header and row-group callbacks are composed too", () => {
  const protectedParams = protectCsvExportParams({
    processGroupHeaderCallback: () => "@evil",
    processRowGroupCallback: () => "\t=cmd",
  })
  assert.equal(
    protectedParams.processGroupHeaderCallback({ columnGroup: {} }),
    "'@evil"
  )
  assert.equal(protectedParams.processRowGroupCallback({ node: {} }), "'\t=cmd")
})

test("allow_unsafe_csv_formulas gates protection on the export format it guards", () => {
  const safe = {}
  applyExportFormulaProtection(safe, false)
  assert.equal(typeof safe.defaultCsvExportParams?.processCellCallback, "function")

  // Existing user params survive composition.
  const withUserParams = { defaultCsvExportParams: { fileName: "a.csv" } }
  applyExportFormulaProtection(withUserParams, false)
  assert.equal(withUserParams.defaultCsvExportParams.fileName, "a.csv")

  const unsafe = {}
  applyExportFormulaProtection(unsafe, true)
  assert.equal(unsafe.defaultCsvExportParams, undefined)
})

test("every --st-* variable ThemeParser reads is in STREAMLIT_THEME_VARS", () => {
  // The recipes and the staleness signature live in different code paths; a
  // new getPropertyValue('--st-...') without a matching entry here would be
  // read but never trigger a repaint.
  const parserSource = readFileSync(
    join(dirname(fileURLToPath(import.meta.url)), "../src/ThemeParser.tsx"),
    "utf8"
  )
  const referencedVars = [...parserSource.matchAll(/['"`](--st-[a-z0-9-]+)['"`]/g)].map(m => m[1])

  assert.ok(referencedVars.length > 0, "no --st-* literals found; did ThemeParser move?")

  const declared = new Set(STREAMLIT_THEME_VARS)
  const undeclared = [...new Set(referencedVars)].filter(name => !declared.has(name))
  assert.deepEqual(
    undeclared,
    [],
    "ThemeParser reads --st-* variables missing from streamlitThemeVars.ts"
  )
})
