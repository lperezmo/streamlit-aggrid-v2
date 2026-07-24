/**
 * Minimal collector for DataReturnMode.MINIMAL
 *
 * The point of MINIMAL is a small wire payload. LegacyCollector sends one
 * object per row carrying id, rowIndex, group, isSelected and a parent path,
 * plus the full grid state, the full column state, the original dtypes and a
 * filtered copy of the event data, and it walks every node three times. This
 * collector sends only the row values the user can actually see, in display
 * order, plus the selected rows, and it walks the grid once.
 *
 * The shape matches what MinimalResponse on the Python side reads:
 * ``data`` and ``selectedRows``.
 */

import { BaseCollector } from "./BaseCollector"
import { CollectorContext, CollectorResult } from "./types"
import { IRowNode } from "ag-grid-community"

export class MinimalCollector extends BaseCollector {
  /**
   * Copy a row's values, dropping the internal columns st-aggrid adds
   * (currently ``::auto_unique_id::``). Values are passed through as-is: no
   * deep walk, which is what keeps this collector cheap.
   */
  private stripInternalFields(data: any): any {
    if (data === null || typeof data !== "object") {
      return data
    }

    const row: any = {}
    for (const key in data) {
      if (Object.prototype.hasOwnProperty.call(data, key) && !key.startsWith("::")) {
        row[key] = data[key]
      }
    }
    return row
  }

  async processResponse(context: CollectorContext): Promise<CollectorResult> {
    const api = context.state?.api

    if (!api) {
      return this.createErrorResult("MinimalCollector: grid api is not available")
    }

    const data: any[] = []
    const selectedRows: any[] = []

    // Single pass, in the order the grid displays rows. Group nodes carry no
    // row values of their own, so they are skipped.
    api.forEachNodeAfterFilterAndSort((node: IRowNode) => {
      if (node.group) {
        return
      }

      const row = this.stripInternalFields(node.data)
      data.push(row)

      if (node.isSelected()) {
        selectedRows.push(row)
      }
    })

    return this.createSuccessResult({
      data: data,
      selectedRows: selectedRows,
      eventTrigger: context.streamlitRerunEventTriggerName,
    })
  }

  getCollectorType(): string {
    return "MinimalCollector"
  }
}
