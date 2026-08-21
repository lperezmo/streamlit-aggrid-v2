type ExportProcessCallback = (params: any) => any

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

/**
 * Compose formula protection after an application's own export callback.
 */
function composedCellCallback(original: ExportProcessCallback | undefined): ExportProcessCallback {
  return (cellParams: any) => {
    const value = original ? original(cellParams) : cellParams.value
    return neutralizeCsvFormula(value)
  }
}

/**
 * Header and group-header callbacks get the same treatment, but only when the
 * application supplied one. When it did not, AG Grid resolves header names
 * itself from headerName/headerValueGetter/aggregation naming, and its export
 * params carry just `{ column }` / `{ columnGroup }` - no value field - so
 * installing our own unconditional callback cannot reproduce that resolution
 * and would blank every exported header. Applications exporting untrusted
 * column names should either sanitize them upstream or pass their own
 * processHeaderCallback / processGroupHeaderCallback, which this composes
 * neutralization after.
 */
function composedHeaderCallback(original: ExportProcessCallback | undefined): ExportProcessCallback {
  return (headerParams: any) => {
    const value = original ? original(headerParams) : headerParams.value
    const neutralized = neutralizeCsvFormula(value)
    return typeof neutralized === "string" ? neutralized : String(neutralized ?? "")
  }
}

/**
 * Compose formula protection after an application's own export callbacks.
 *
 * Cell values are protected unconditionally (AG Grid hands us the raw value);
 * header, group-header, and row-group callbacks are wrapped only when present,
 * so AG Grid's built-in header-name resolution stays untouched otherwise.
 * Applying this to defaultCsvExportParams covers both the toolbar and AG
 * Grid's context-menu CSV export paths.
 *
 * Excel exports are deliberately left alone: xlsx stores strings as inline
 * string cells that spreadsheet software never evaluates as formulas, so
 * neutralization there would only corrupt displayed values.
 */
export function protectCsvExportParams(params: any = {}): any {
  const protectedParams: any = {
    ...params,
    processCellCallback: composedCellCallback(
      typeof params?.processCellCallback === "function"
        ? params.processCellCallback
        : undefined
    ),
  }

  const wrapIfSupplied = (key: string) => {
    if (typeof params?.[key] === "function") {
      protectedParams[key] = composedHeaderCallback(params[key])
    }
  }
  wrapIfSupplied("processHeaderCallback")
  wrapIfSupplied("processGroupHeaderCallback")
  wrapIfSupplied("processRowGroupCallback")

  return protectedParams
}

/**
 * Attach the neutralizing callbacks to a gridOptions object unless the app
 * opted out with allow_unsafe_csv_formulas.
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
}
