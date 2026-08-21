type ExportProcessCellCallback = (params: any) => any
type ExportProcessHeaderCallback = (params: any) => any

/**
 * Keep untrusted strings inert when a CSV is opened in spreadsheet software.
 *
 * Numbers are deliberately left alone, including negative numbers. Strings are
 * data, so formula-looking strings are prefixed with an apostrophe. Leading
 * whitespace and control characters are ignored when looking for a formula
 * prefix because spreadsheet parsers may ignore them too.
 */
export function neutralizeCsvFormula(value: any): any {
  if (typeof value !== "string" || value.length === 0) {
    return value
  }

  const firstSignificant = value.replace(/^[\s\u0000-\u001f]+/, "")[0]
  const startsWithControl = value[0] === "\t" || value[0] === "\r"

  if (startsWithControl || "=+-@".includes(firstSignificant ?? "")) {
    return `'${value}`
  }

  return value
}

function composeProtectedCellCallback(
  original: ExportProcessCellCallback | undefined
): ExportProcessCellCallback {
  return (cellParams: any) => {
    const value = original ? original(cellParams) : cellParams.value
    return neutralizeCsvFormula(value)
  }
}

/**
 * Headers come from user data exactly like cells do (a DataFrame column can be
 * named "=HYPERLINK(...)"), so they get the same treatment.
 */
function composeProtectedHeaderCallback(
  original: ExportProcessHeaderCallback | undefined
): ExportProcessHeaderCallback {
  return (headerParams: any) => {
    const value = original ? original(headerParams) : headerParams.value
    const neutralized = neutralizeCsvFormula(value)
    return typeof neutralized === "string" ? neutralized : String(neutralized ?? "")
  }
}

/**
 * Compose formula protection after an application's own export callbacks,
 * covering cell values, column headers, and column-group headers. Applying it
 * to defaultCsvExportParams covers both the toolbar and AG Grid's context-menu
 * CSV export paths.
 */
export function protectExportParams(params: any = {}): any {
  const originalProcessCellCallback: ExportProcessCellCallback | undefined =
    typeof params?.processCellCallback === "function"
      ? params.processCellCallback
      : undefined

  const originalProcessHeaderCallback: ExportProcessHeaderCallback | undefined =
    typeof params?.processHeaderCallback === "function"
      ? params.processHeaderCallback
      : undefined

  const protectedParams: any = {
    ...params,
    processCellCallback: composeProtectedCellCallback(originalProcessCellCallback),
    processHeaderCallback: composeProtectedHeaderCallback(originalProcessHeaderCallback),
  }

  // Group headers can also carry data-derived names (e.g. pandas MultiIndex
  // columns become column groups), so protect them on the same terms. The
  // documented AG Grid default is the group's display name.
  const originalProcessGroupHeaderCallback: ExportProcessHeaderCallback | undefined =
    typeof params?.processGroupHeaderCallback === "function"
      ? params.processGroupHeaderCallback
      : undefined

  protectedParams.processGroupHeaderCallback = (groupParams: any) => {
    const value = originalProcessGroupHeaderCallback
      ? originalProcessGroupHeaderCallback(groupParams)
      : groupParams.displayName
    const neutralized = neutralizeCsvFormula(value)
    return typeof neutralized === "string" ? neutralized : String(neutralized ?? "")
  }

  return protectedParams
}

export function protectCsvExportParams(params: any = {}): any {
  return protectExportParams(params)
}

export function protectExcelExportParams(params: any = {}): any {
  return protectExportParams(params)
}

/**
 * Attach the neutralizing callbacks to a gridOptions object unless the app
 * opted out with allow_unsafe_csv_formulas. Covers both export formats: the
 * same formula-injection tricks that work on CSV work on Excel exports.
 */
export function applyExportFormulaProtection(
  gridOptions: any,
  allowUnsafeFormulas: boolean | undefined
): void {
  if (allowUnsafeFormulas) {
    return
  }
  gridOptions.defaultCsvExportParams = protectCsvExportParams(
    gridOptions.defaultCsvExportParams
  )
  gridOptions.defaultExcelExportParams = protectExcelExportParams(
    gridOptions.defaultExcelExportParams
  )
}
