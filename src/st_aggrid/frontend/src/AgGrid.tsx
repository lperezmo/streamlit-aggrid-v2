import { AgGridReact } from "ag-grid-react"
import React, { ReactNode } from "react"

import type { AgGridDataShape, AgGridStateShape } from "./index"
import type { FrontendRendererArgs } from "@streamlit/component-v2-lib"

import {
  AllCommunityModule,
  CellValueChangedEvent,
  DetailGridInfo,
  GetRowIdParams,
  GridApi,
  GridReadyEvent,
  ModuleRegistry,
} from "ag-grid-community"

import { AgChartsEnterpriseModule } from "ag-charts-enterprise"
import { AllEnterpriseModule, LicenseManager } from "ag-grid-enterprise"

import debounce from 'lodash/debounce'
import isEqual from 'lodash/isEqual'
import omit from 'lodash/omit'

import { ThemeParser } from "./ThemeParser"
import { CustomCollector, LegacyCollector } from "./collectors"
import type { CollectorContext } from "./collectors"

import "@fontsource/source-sans-pro"
import "./AgGrid.css"

import GridToolBar from "./components/GridToolBar"
import AiToolkitBar from "./components/AiToolkitBar"

import {
  addCustomCSS,
  injectProAssets,
  parseJsCodeFromPython,
} from "./utils/gridUtils"

import { State } from "./types/AgGridTypes"
import { parseGridOptions, parseData } from "./utils/parsers"

export interface AgGridProps {
  componentData: AgGridDataShape
  setStateValue: FrontendRendererArgs<AgGridStateShape>['setStateValue']
  parentElement: Element | ShadowRoot
}

class AgGrid extends React.Component<AgGridProps, State> {
  public state: State

  private gridContainerRef: React.RefObject<HTMLDivElement>
  private gridApiRef: GridApi | undefined = undefined
  private isGridAutoHeightOn: boolean
  private themeParser: ThemeParser | undefined = undefined
  private shouldGridReturn: Function | undefined = undefined
  private collectGridReturn: Function | undefined = undefined
  private eventCleanupFns: Array<() => void> = []
  private aiToolkitSchema: any = null

  constructor(props: AgGridProps) {
    super(props)
    this.gridContainerRef = React.createRef()

    const cd = props.componentData

    if (cd.custom_css) {
      addCustomCSS(cd.custom_css)
    }

    if (cd.pro_assets && Array.isArray(cd.pro_assets)) {
      cd.pro_assets.forEach((asset: any) => {
        injectProAssets(asset?.js, asset?.css)
      })
    }
    const enableEnterpriseModules = cd.enable_enterprise_modules
    if (enableEnterpriseModules === "enterprise+AgCharts") {
      ModuleRegistry.registerModules([
        AllEnterpriseModule.with(AgChartsEnterpriseModule),
      ])
      if (cd.license_key) {
        LicenseManager.setLicenseKey(cd.license_key)
      }
    } else if (
      enableEnterpriseModules === true ||
      enableEnterpriseModules === "enterpriseOnly"
    ) {
      ModuleRegistry.registerModules([AllEnterpriseModule])
      if (cd.license_key) {
        LicenseManager.setLicenseKey(cd.license_key)
      }
    } else {
      ModuleRegistry.registerModules([AllCommunityModule])
    }

    var go = parseGridOptions(cd, props.parentElement)
    go.rowData = parseData(cd)

    const StreamlitAgGridPro = (window as any)?.StreamlitAgGridPro
    if (StreamlitAgGridPro) {
      StreamlitAgGridPro.returnGridValue = this.returnGridValue.bind(this)

      if (
        StreamlitAgGridPro.extenders &&
        Array.isArray(StreamlitAgGridPro.extenders)
      ) {
        StreamlitAgGridPro.extenders.forEach((extender: (go: any) => void) => {
          if (typeof extender === "function") {
            extender(go)
          }
        })
      }
    }

    this.isGridAutoHeightOn =
      cd.gridOptions?.domLayout === "autoHeight"

    if (!("getRowId" in go)) {
      if (
        Array.isArray(go.rowData) &&
        go.rowData.length > 0 &&
        go.rowData[0].hasOwnProperty("::auto_unique_id::")
      ) {
        go.getRowId = (params: GetRowIdParams) =>
          params.data["::auto_unique_id::"] as string
      }
    }

    this.shouldGridReturn = cd.should_grid_return
      ? parseJsCodeFromPython(cd.should_grid_return)
      : null
    this.collectGridReturn = cd.custom_jscode_for_grid_return
      ? parseJsCodeFromPython(cd.custom_jscode_for_grid_return)
      : null

    this.state = {
      gridHeight: cd.height,
      gridOptions: go,
      isRowDataEdited: false,
      api: undefined,
      enterprise_features_enabled: cd.enable_enterprise_modules,
      debug: cd.debug || false,
      editedRows: new Set(),
    } as State

    if (this.state.debug) {
      console.log("***Received Props", props)
      console.log("*** Processed State", this.state)
    }
  }

  private attachStreamlitRerunToEvents(api: GridApi) {
    const updateEvents = this.props.componentData.update_on

    updateEvents.forEach((element: any) => {
      if (Array.isArray(element)) {
        const [eventName, timeout] = element
        const handler = debounce(
          (e: any) => {
            this.returnGridValue(e, eventName)
          },
          timeout,
          {
            leading: false,
            trailing: true,
            maxWait: timeout,
          }
        )
        api.addEventListener(eventName, handler)
        this.eventCleanupFns.push(() => api.removeEventListener(eventName, handler))
      } else {
        const handler = (e: any) => {
          this.returnGridValue(e, element)
        }
        api.addEventListener(element, handler)
        this.eventCleanupFns.push(() => api.removeEventListener(element, handler))
      }
      if (this.state.debug) {
        console.log(`Attached grid return event: ${element}`)
      }
    })
  }

  public componentWillUnmount() {
    this.eventCleanupFns.forEach(fn => fn())
    this.eventCleanupFns = []
  }

  private async returnGridValue(
    eventData: any,
    streamlitRerunEventTriggerName: string
  ) {
    if (this.state.debug) {
      console.log(`refreshing grid from ${streamlitRerunEventTriggerName}`)
      console.log("dataReturnMode is ", this.props.componentData.data_return_mode)
    }

    // Create collector context
    const context: CollectorContext = {
      state: this.state,
      componentData: this.props.componentData,
      eventData: eventData,
      streamlitRerunEventTriggerName: streamlitRerunEventTriggerName,
    }

    const collectorFactory = {
      AS_INPUT: new LegacyCollector(),
      FILTERED: new LegacyCollector(),
      FILTERED_AND_SORTED: new LegacyCollector(),
      MINIMAL: new LegacyCollector(),
      CUSTOM: new CustomCollector(this.collectGridReturn || (() => {})),
    }

    try {
      // Determine and create appropriate collector
      const collector =
        collectorFactory[
          this.props.componentData.data_return_mode as keyof typeof collectorFactory
        ]

      // Process response using collector
      const result = await collector.processResponse(context)

      if (result.success) {
        // Inject AI Toolkit schema if enabled
        if (this.props.componentData.ai_toolkit && this.aiToolkitSchema && result.data) {
          result.data.structuredSchema = this.aiToolkitSchema
        }

        if (this.state.debug) {
          console.log(
            `Grid response processed by ${collector.getCollectorType()}:`,
            result.data
          )
        }
        // Check shouldGridReturn before sending value back to Python
        if (this.shouldGridReturn) {
          const shouldReturn = this.shouldGridReturn({ streamlitRerunEventTriggerName, eventData });
          if (!shouldReturn) {
            if (this.state.debug) {
              console.log(`shouldGridReturn blocked return for event: ${streamlitRerunEventTriggerName}`);
            }
            return; // Don't send value back
          }
        }
        this.props.setStateValue("grid_return", result.data)
      } else {
        console.error(`Collector processing failed: ${result.error}`)
        // Fallback to no return to avoid breaking the UI
      }
    } catch (error) {
      console.error("Error in returnGridValue collector processing:", error)
      // Fallback to no return to avoid breaking the UI
    }
  }

  private defineContainerHeight() {
    if (this.isGridAutoHeightOn) {
      return {
        width: "100%",
      }
    } else {
      return {
        width: "100%",
        height: this.props.componentData.height,
      }
    }
  }

  public componentDidUpdate(prevProps: any, prevState: State, snapshot?: any) {
    if (this.state.debug) {
      console.log("********** componentDidUpdate.prevProps")
      console.log(prevProps)
      console.log("********** componentDidUpdate.this")
      console.log(this)
    }

    //Check update on grid options. TODO: exclude `initial` options
    const prevGridOptions = omit(prevProps.componentData?.gridOptions, "rowData")
    const currGridOptions = omit(this.props.componentData.gridOptions, "rowData")

    if (!isEqual(prevGridOptions, currGridOptions)) {
      let go = parseGridOptions(this.props.componentData, this.props.parentElement)
      this.gridApiRef?.updateGridOptions(go)
    }

    //Theme object Changes here
    if (
      !isEqual(this.props.componentData.theme, prevProps.componentData?.theme)
    ) {
      let agGridTheme = this.props.componentData.theme
      const themeParser = new ThemeParser()
      const themeHost = (this.props.parentElement as any)?.host ?? this.props.parentElement
      this.gridApiRef?.updateGridOptions({
        theme: themeParser.parse(agGridTheme, themeHost),
      })
    }

    //Check if data changed and updates

    const serverSyncStragegy = this.props.componentData?.server_sync_strategy
    if (serverSyncStragegy === "client_wins") {
      if (!this.state.isRowDataEdited) {
        if (this.props.componentData.data_hash !== prevProps.componentData?.data_hash) {
          const rowData = parseData(this.props.componentData) || []
          this.gridApiRef?.updateGridOptions({ rowData })
        }
      }
    } else if (serverSyncStragegy === "server_wins") {
      const rowData = parseData(this.props.componentData) || []
      this.gridApiRef?.stopEditing(true)
      this.gridApiRef?.updateGridOptions({ rowData })
    }

    // AI Toolkit: apply state update from Python
    if (this.props.componentData.ai_toolkit && this.gridApiRef) {
      const prevAiUpdate = prevProps.componentData?.ai_state_update
      const currAiUpdate = this.props.componentData.ai_state_update
      if (currAiUpdate && !isEqual(prevAiUpdate, currAiUpdate)) {
        try {
          const { gridState, propertiesToIgnore } = currAiUpdate
          if (this.state.debug) {
            console.log("AI Toolkit: applying state update", gridState, "ignoring", propertiesToIgnore)
          }
          ;(this.gridApiRef as any).setState(gridState, propertiesToIgnore)
        } catch (e) {
          console.error("AI Toolkit: setState() failed", e)
        }
      }
    }

    //check if columnStates changed
    if (!isEqual(prevProps.componentData?.columns_state, this.props.componentData.columns_state)) {
      const columnsState = this.props.componentData.columns_state
      if (columnsState != null) {
        this.gridApiRef?.applyColumnState({
          state: columnsState,
          applyOrder: true,
        })
      }
    }
  }

  private onGridReady(event: GridReadyEvent) {
    this.gridApiRef = event.api
    this.setState({ api: event.api })

    if (this.props.componentData.server_sync_strategy === "client_wins") {
      const cellEditHandler = (event: CellValueChangedEvent) => {
        console.warn(
          "server_sync_strategy is 'client_wins' and Data was edited on Grid. Ignoring further changes from Streamlit server."
        )
        let editedRows = new Set(this.state.editedRows).add(event.node.id)
        this.setState({ isRowDataEdited: true, editedRows: editedRows })
      }
      this.gridApiRef!.addEventListener("cellValueChanged", cellEditHandler)
      this.eventCleanupFns.push(() => this.gridApiRef?.removeEventListener("cellValueChanged", cellEditHandler))
    }

    //Attach events
    this.attachStreamlitRerunToEvents(this.gridApiRef!)

    if (this.state.enterprise_features_enabled) {
      this.gridApiRef?.forEachDetailGridInfo((i: DetailGridInfo) => {
        if (i.api !== undefined) {
          this.attachStreamlitRerunToEvents(i.api)
        }
      })
    }

    // AI Toolkit: generate schema and trigger initial return
    if (this.props.componentData.ai_toolkit && this.gridApiRef) {
      try {
        this.aiToolkitSchema = (this.gridApiRef as any).getStructuredSchema()
        if (this.state.debug) {
          console.log("AI Toolkit: schema generated", this.aiToolkitSchema)
        }
        // Trigger initial return so Python gets the schema immediately
        this.returnGridValue({}, "gridReady")
      } catch (e) {
        console.warn("AI Toolkit: getStructuredSchema() not available", e)
      }
    }

    //If there is any event onGridReady in gridOptions, fire it
    let { onGridReady } = this.state.gridOptions
    onGridReady && onGridReady(event)
  }

  private processPreselection() {
    //TODO: do not pass grid Options that doesn't exist in aggrid (preSelectAllRows,  preSelectedRows)
    var preSelectAllRows =
      this.props.componentData.gridOptions["preSelectAllRows"] || false

    if (preSelectAllRows) {
      this.gridApiRef?.selectAll()
    } else {
      var preselectedRows = this.props.componentData.gridOptions["preSelectedRows"]
      if (preselectedRows && preselectedRows.length > 0) {
        for (var idx in preselectedRows) {
          this.gridApiRef
            ?.getRowNode(preselectedRows[idx])
            ?.setSelected(true, false)
        }
      }
    }
  }

  private handleAiSubmit = (query: string) => {
    // Send query to Python via state - Python will handle the LLM call
    this.props.setStateValue("grid_return", {
      ...(this.state.api ? {
        gridState: this.state.api.getState(),
        columnsState: this.state.api.getColumnState(),
      } : {}),
      aiQuery: query,
      structuredSchema: this.aiToolkitSchema,
    })
  }

  private handleAiReset = () => {
    if (this.gridApiRef) {
      ;(this.gridApiRef as any).setState({
        columnVisibility: { hiddenColIds: [] },
        columnPinning: { leftColIds: [], rightColIds: [] },
        sort: { sortModel: [] },
        filter: { filterModel: {} },
        rowGroup: { groupColIds: [] },
      })
      // Trigger a return to update Python side
      this.returnGridValue({}, "aiReset")
    }
  }

  public render = (): ReactNode => {
    let manualUpdate = this.props.componentData.manual_update === true

    const aiResponse = this.props.componentData.ai_response
    return (
      <div
        id="gridContainer"
        ref={this.gridContainerRef}
        style={this.defineContainerHeight()}
      >
        {this.props.componentData.ai_toolkit && (
          <AiToolkitBar
            onSubmit={this.handleAiSubmit}
            onReset={this.handleAiReset}
            status={aiResponse?.status || null}
            explanation={aiResponse?.explanation || ""}
            prompt={aiResponse?.prompt || ""}
          />
        )}
        <GridToolBar
          showManualUpdateButton={manualUpdate}
          enabled={this.props.componentData.show_toolbar ?? true}
          showSearch={this.props.componentData.show_search ?? true}
          showDownloadButton={this.props.componentData.show_download_button ?? true}
          onQuickSearchChange={(value) => {
            this.gridApiRef?.setGridOption("quickFilterText", value)
            this.gridApiRef?.hideOverlay()
          }}
          onDownloadClick={() => {
            this.gridApiRef?.exportDataAsCsv()
          }}
          onManualUpdateClick={() => {
            if (this.state.debug) {
              console.log("Manual update triggered")
            }
          }}
        />
        <AgGridReact
          onGridReady={(e: GridReadyEvent<any, any>) => this.onGridReady(e)}
          gridOptions={this.state.gridOptions}
        ></AgGridReact>
      </div>
    )
  }
}

export default AgGrid
