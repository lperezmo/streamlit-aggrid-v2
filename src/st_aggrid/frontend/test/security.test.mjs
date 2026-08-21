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
  protectExcelExportParams,
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

test("CSV column headers get the same formula treatment as cells", () => {
  const protectedParams = protectCsvExportParams()

  for (const dangerous of ["=HYPERLINK(A1)", "@SUM(1)", "+CMD", "\t=1"]) {
    assert.equal(
      protectedParams.processHeaderCallback({ value: dangerous }),
      `'${dangerous}`
    )
  }
  assert.equal(protectedParams.processHeaderCallback({ value: "normal" }), "normal")
})

test("application header callbacks compose with neutralization", () => {
  const protectedParams = protectCsvExportParams({
    processHeaderCallback: params => `=${params.value}`,
  })
  assert.equal(protectedParams.processHeaderCallback({ value: "x" }), "'=x")
})

test("column group headers are neutralized", () => {
  const bare = protectCsvExportParams()
  assert.equal(bare.processGroupHeaderCallback({ displayName: "=1+1" }), "'=1+1")
  assert.equal(bare.processGroupHeaderCallback({ displayName: "group" }), "group")

  const composed = protectCsvExportParams({
    processGroupHeaderCallback: () => "@evil",
  })
  assert.equal(composed.processGroupHeaderCallback({ displayName: "ignored" }), "'@evil")
})

test("Excel export params get the same protection as CSV", () => {
  const protectedParams = protectExcelExportParams()
  assert.equal(typeof protectedParams.processCellCallback, "function")
  assert.equal(protectedParams.processCellCallback({ value: "=cmd" }), "'=cmd")
  assert.equal(protectedParams.processHeaderCallback({ value: "=cmd" }), "'=cmd")
})

test("allow_unsafe_csv_formulas gates protection on both export formats", () => {
  const safe = {}
  applyExportFormulaProtection(safe, false)
  assert.equal(typeof safe.defaultCsvExportParams?.processCellCallback, "function")
  assert.equal(typeof safe.defaultCsvExportParams?.processHeaderCallback, "function")
  assert.equal(typeof safe.defaultCsvExportParams?.processGroupHeaderCallback, "function")
  assert.equal(typeof safe.defaultExcelExportParams?.processCellCallback, "function")

  // Existing user params survive composition.
  const withUserParams = { defaultCsvExportParams: { fileName: "a.csv" } }
  applyExportFormulaProtection(withUserParams, false)
  assert.equal(withUserParams.defaultCsvExportParams.fileName, "a.csv")

  const unsafe = {}
  applyExportFormulaProtection(unsafe, true)
  assert.equal(unsafe.defaultCsvExportParams, undefined)
  assert.equal(unsafe.defaultExcelExportParams, undefined)
})

test("every --st-* variable ThemeParser reads is in STREAMLIT_THEME_VARS", () => {
  // The recipes and the staleness signature live in different code paths; a
  // new getPropertyValue('--st-...') without a matching entry here would be
  // read but never trigger a repaint.
  const parserSource = readFileSync(
    join(dirname(fileURLToPath(import.meta.url)), "../src/ThemeParser.tsx"),
    "utf8"
  )
  const referencedVars = [...parserSource.matchAll(/'(--st-[a-z0-9-]+)'/g)].map(m => m[1])

  assert.ok(referencedVars.length > 0, "no --st-* literals found; did ThemeParser move?")

  const declared = new Set(STREAMLIT_THEME_VARS)
  const undeclared = [...new Set(referencedVars)].filter(name => !declared.has(name))
  assert.deepEqual(
    undeclared,
    [],
    "ThemeParser reads --st-* variables missing from streamlitThemeVars.ts"
  )
})
