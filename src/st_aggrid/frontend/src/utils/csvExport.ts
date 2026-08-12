type CsvProcessCellCallback = (params: any) => any

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
 * Applying it to defaultCsvExportParams covers both the toolbar and AG Grid's
 * context-menu CSV export paths.
 */
export function protectCsvExportParams(params: any = {}): any {
  const originalProcessCellCallback: CsvProcessCellCallback | undefined =
    typeof params?.processCellCallback === "function"
      ? params.processCellCallback
      : undefined

  return {
    ...params,
    processCellCallback: (cellParams: any) => {
      const value = originalProcessCellCallback
        ? originalProcessCellCallback(cellParams)
        : cellParams.value
      return neutralizeCsvFormula(value)
    },
  }
}
