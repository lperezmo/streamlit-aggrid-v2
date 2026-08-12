import assert from "node:assert/strict"
import test from "node:test"

import { deepMap } from "../.test-build/utils.js"
import {
  neutralizeCsvFormula,
  protectCsvExportParams,
} from "../.test-build/utils/csvExport.js"

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
