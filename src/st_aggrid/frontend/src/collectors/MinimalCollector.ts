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
 * Selections are read from getSelectedNodes() rather than picked up during that
 * walk, so a selected row that a filter is currently hiding is still reported,
 * matching every other data return mode.
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

    // Single pass, in the order the grid displays rows.
    //
    // The test is on node.data, not on node.group. Under row grouping the two
    // agree: AG Grid synthesizes the group rows and they carry no data, so
    // they are skipped either way. Under treeData they do not. There the
    // parents are rows the caller supplied and node.data holds their values,
    // so keying off node.group silently returned the leaves only and a tree
    // grid in MINIMAL mode lost every parent row. LegacyCollector emits all of
    // them, so this was data loss unique to MINIMAL.
    api.forEachNodeAfterFilterAndSort((node: IRowNode) => {
      if (node.data == null) {
        return
      }
      data.push(this.stripInternalFields(node.data))
    })

    // Asked for directly rather than inferred from the walk above. AG Grid does
    // not deselect a row when a filter hides it, so collecting selections during
    // a post-filter walk silently dropped any selected row that was currently
    // filtered out, while every other data return mode still reported it:
    // LegacyCollector walks forEachNode (all rows) and Python filters on
    // isSelected. getSelectedNodes() costs the size of the selection rather
    // than another pass over the rows, so parity is cheap here.
    //
    // A row can therefore be in selectedRows without being in data. That is the
    // same shape LegacyCollector already produces under FILTERED_AND_SORTED,
    // where data is filtered but selections are not.
    const selectedRows = api
      // getSelectedNodes() includes group nodes. The synthesized ones carry no
      // row values and would arrive as if they were data, so they are dropped
      // on the same node.data test the display walk uses, which keeps a
      // selected treeData parent (a real row) in the result.
      .getSelectedNodes()
      .filter((node: IRowNode) => node.data != null)
      .map((node: IRowNode) => this.stripInternalFields(node.data))

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
