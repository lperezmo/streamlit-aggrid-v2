import type {
  FrontendRenderer,
  FrontendRendererArgs,
} from "@streamlit/component-v2-lib"
import { StrictMode } from "react"
import { createRoot, Root } from "react-dom/client"

import AgGrid from "./AgGrid"

// CCv2 state shape: what we send back to Python via setStateValue
export type AgGridStateShape = {
  grid_return: any
}

// CCv2 data shape: what Python sends to us via data={}
export type AgGridDataShape = {
  row_data: any[] | null
  data_hash: string
  gridOptions: any
  height: number
  data_return_mode: string
  frame_dtypes: string
  allow_unsafe_jscode: boolean
  columns_state: any
  custom_css: any
  enable_enterprise_modules: boolean | string
  license_key: string | null
  manual_update: boolean
  pro_assets: any[] | null
  show_download_button: boolean
  show_search: boolean
  show_toolbar: boolean
  custom_jscode_for_grid_return: string | null
  should_grid_return: string | null
  theme: any
  debug: boolean
  update_on: any[]
  use_json_serialization: boolean | string
  server_sync_strategy: string
}

// Track React roots per component instance
const reactRoots: WeakMap<FrontendRendererArgs["parentElement"], Root> =
  new WeakMap()

const AgGridRoot: FrontendRenderer<AgGridStateShape, AgGridDataShape> = (
  args
) => {
  const { data, parentElement, setStateValue } = args

  // Get the root div defined in our html='<div id="root"></div>'
  const rootElement = parentElement.querySelector("#root")

  if (!rootElement) {
    throw new Error("Unexpected: React root element not found")
  }

  let reactRoot = reactRoots.get(parentElement)
  if (!reactRoot) {
    reactRoot = createRoot(rootElement)
    reactRoots.set(parentElement, reactRoot)
  }

  reactRoot.render(
    <StrictMode>
      <AgGrid componentData={data} setStateValue={setStateValue} parentElement={parentElement} />
    </StrictMode>
  )

  return () => {
    const root = reactRoots.get(parentElement)
    if (root) {
      root.unmount()
      reactRoots.delete(parentElement)
    }
  }
}

export default AgGridRoot
