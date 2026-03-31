import { GridOptions } from "ag-grid-community"
import { cloneDeep } from "lodash"
import { deepMap } from "../utils"
import { parseJsCodeFromPython } from "./gridUtils"
import { columnFormaters } from "../customColumns"
import { ThemeParser } from "../ThemeParser"


export function parseGridOptions(componentData: any, parentElement?: Element | ShadowRoot | null){
    let gridOptions: GridOptions = cloneDeep(componentData.gridOptions)

    if (componentData.allow_unsafe_jscode) {
        console.warn("flag allow_unsafe_jscode is on.")
        gridOptions = deepMap(gridOptions, parseJsCodeFromPython, ["rowData"])
    }

    if (!("getRowId" in gridOptions)) {
        console.warn("getRowId was not set. Auto Rows hashes will be used as row ids.")
    }

    //adds custom columnFormatters
    gridOptions.columnTypes = Object.assign(
        gridOptions.columnTypes || {},
        columnFormaters
    )

    //processTheming
    const themeParser = new ThemeParser()
    let agGridTheme = componentData.theme
    const themeHost = (parentElement as any)?.host ?? parentElement ?? document.documentElement
    gridOptions.theme = themeParser.parse(agGridTheme, themeHost)

    return gridOptions
}

export function parseData(componentData: any){

    var rowData = componentData.row_data
    var gridOptions_rowData = componentData.gridOptions?.rowData

    // If row_data is directly available (JSON records from Python), use it
    if (rowData && Array.isArray(rowData)) {
        return rowData
    }

    // If data is null but gridOptions.rowData contains JSON string, parse it
    if (gridOptions_rowData && typeof gridOptions_rowData === 'string') {
        try {
            return JSON.parse(gridOptions_rowData)
        } catch (e) {
            console.error('Failed to parse gridOptions.rowData as JSON:', e)
            throw e
        }
    }

    return rowData || []
}