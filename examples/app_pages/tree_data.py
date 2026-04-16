"""Tree data + inline buttons — AG Grid treeData with custom button cell renderers.

Shows hierarchical file data via `treeData` + `getDataPath` and three mutually-
exclusive action buttons per row (Delete / Audit / Approve). A single flag per
row disables the other two; row styling reflects the chosen action.
"""

import pandas as pd
import streamlit as st

from st_aggrid import AgGrid, JsCode

st.markdown(
    "Hierarchical data via `treeData` + `getDataPath`. Each leaf row has three "
    "mutually exclusive action buttons; clicking one disables the others and "
    "color-codes the row. Aggregated `size` rolls up to group nodes."
)

files = [
    {
        "path": ["Desktop", "ProjectAlpha", "Proposal.docx"],
        "size": 512000,
        "created": "2023-07-10",
        "modified": "2023-08-01",
    },
    {
        "path": ["Desktop", "ProjectAlpha", "Timeline.xlsx"],
        "size": 1048576,
        "created": "2023-07-12",
        "modified": "2023-08-03",
    },
    {
        "path": ["Desktop", "ToDoList.txt"],
        "size": 51200,
        "created": "2023-08-05",
        "modified": "2023-08-10",
    },
    {
        "path": ["Desktop", "MeetingNotes_August.pdf"],
        "size": 460800,
        "created": "2023-08-15",
        "modified": "2023-08-15",
    },
    {
        "path": ["Documents", "Work", "ProjectAlpha", "Proposal.docx"],
        "size": 512000,
        "created": "2023-07-10",
        "modified": "2023-08-01",
    },
    {
        "path": ["Documents", "Work", "ProjectAlpha", "Timeline.xlsx"],
        "size": 1048576,
        "created": "2023-07-12",
        "modified": "2023-08-03",
    },
    {
        "path": ["Documents", "Work", "ProjectBeta", "Report.pdf"],
        "size": 1024000,
        "created": "2023-06-22",
        "modified": "2023-07-15",
    },
    {
        "path": ["Documents", "Work", "ProjectBeta", "Budget.xlsx"],
        "size": 1048576,
        "created": "2023-06-25",
        "modified": "2023-07-18",
    },
    {
        "path": ["Documents", "Work", "Meetings", "TeamMeeting_August.pdf"],
        "size": 512000,
        "created": "2023-08-20",
        "modified": "2023-08-21",
    },
    {
        "path": ["Documents", "Work", "Meetings", "ClientMeeting_July.pdf"],
        "size": 1048576,
        "created": "2023-07-15",
        "modified": "2023-07-16",
    },
    {
        "path": ["Documents", "Personal", "Taxes", "2022.pdf"],
        "size": 1024000,
        "created": "2023-04-10",
        "modified": "2023-04-10",
    },
    {
        "path": ["Documents", "Personal", "Taxes", "2021.pdf"],
        "size": 1048576,
        "created": "2022-04-05",
        "modified": "2022-04-06",
    },
    {
        "path": ["Documents", "Personal", "Taxes", "2020.pdf"],
        "size": 1024000,
        "created": "2021-04-03",
        "modified": "2021-04-03",
    },
    {
        "path": ["Pictures", "Vacation2019", "Beach.jpg"],
        "size": 1048576,
        "created": "2019-07-10",
        "modified": "2019-07-12",
    },
    {
        "path": ["Pictures", "Vacation2019", "Mountain.png"],
        "size": 2048000,
        "created": "2019-07-11",
        "modified": "2019-07-13",
    },
    {
        "path": ["Pictures", "Family", "Birthday2022.jpg"],
        "size": 3072000,
        "created": "2022-12-15",
        "modified": "2022-12-20",
    },
    {
        "path": ["Pictures", "Family", "Christmas2021.png"],
        "size": 2048000,
        "created": "2021-12-25",
        "modified": "2021-12-26",
    },
    {
        "path": ["Videos", "Vacation2019", "Beach.mov"],
        "size": 4194304,
        "created": "2019-07-10",
        "modified": "2019-07-12",
    },
    {
        "path": ["Videos", "Vacation2019", "Hiking.mp4"],
        "size": 4194304,
        "created": "2019-07-15",
        "modified": "2019-07-16",
    },
    {
        "path": ["Videos", "Family", "Birthday2022.mp4"],
        "size": 6291456,
        "created": "2022-12-15",
        "modified": "2022-12-20",
    },
    {
        "path": ["Videos", "Family", "Christmas2021.mov"],
        "size": 6291456,
        "created": "2021-12-25",
        "modified": "2021-12-26",
    },
    {
        "path": ["Downloads", "SoftwareInstaller.exe"],
        "size": 2097152,
        "created": "2023-08-01",
        "modified": "2023-08-01",
    },
    {
        "path": ["Downloads", "Receipt_OnlineStore.pdf"],
        "size": 1048576,
        "created": "2023-08-05",
        "modified": "2023-08-05",
    },
    {
        "path": ["Downloads", "Ebook.pdf"],
        "size": 1048576,
        "created": "2023-08-08",
        "modified": "2023-08-08",
    },
]

FLAGGED = "flagged"
ACTION_FIELDS = ["To Delete", "To Audit", "To Approve"]

df = pd.DataFrame(files)
for field in ACTION_FIELDS:
    df[field] = ""

size_formatter = JsCode("""
function(params) {
    if (params.value == null) return '';
    const kb = params.value / 1024;
    return kb > 1024 ? (+(kb / 1024).toFixed(2)) + ' MB' : (+kb.toFixed(2)) + ' KB';
}
""")

get_data_path = JsCode("function(data) { return data.path; }")

btn_renderer = JsCode("""
class BtnCellRenderer {
    init(params) {
        this.params = params;
        this.eGui = document.createElement('div');
        this.eGui.style.display = 'flex';
        this.eGui.style.alignItems = 'center';
        this.eGui.style.justifyContent = 'center';
        this.eGui.style.height = '100%';
        this.render();
    }
    render() {
        this.eGui.innerHTML = '';
        if (!this.params.node || this.params.node.group || !this.params.data) return;

        const FLAGGED = 'flagged';
        const siblings = this.params.siblingFields || [];
        const field = this.params.colDef.field;
        const activeColor = this.params.activeColor;
        const label = this.params.label;

        const myFlagged = this.params.value === FLAGGED;
        const otherFlagged = siblings.some(f => f !== field && this.params.data[f] === FLAGGED);
        const disabled = otherFlagged && !myFlagged;

        let bg, cursor, text, opacity;
        if (myFlagged) {
            bg = activeColor;
            text = 'Undo';
            cursor = 'pointer';
            opacity = '1';
        } else if (disabled) {
            bg = 'rgba(128,128,128,0.25)';
            text = label;
            cursor = 'not-allowed';
            opacity = '0.45';
        } else {
            bg = 'rgba(128,128,128,0.45)';
            text = label;
            cursor = 'pointer';
            opacity = '1';
        }

        this.eGui.innerHTML = `
            <button ${disabled ? 'disabled' : ''} style="
                color: white;
                background: ${bg};
                border: none;
                border-radius: 4px;
                padding: 3px 12px;
                cursor: ${cursor};
                font-size: 12px;
                font-weight: 600;
                opacity: ${opacity};
            ">${text}</button>`;

        if (!disabled) {
            this.eGui.querySelector('button')
                .addEventListener('click', () => this.toggle(myFlagged));
        }
    }
    toggle(myFlagged) {
        const FLAGGED = 'flagged';
        this.params.setValue(myFlagged ? '' : FLAGGED);
        const siblings = this.params.siblingFields || [];
        const columns = siblings
            .map(f => this.params.api.getColumn(f))
            .filter(c => c != null);
        this.params.api.refreshCells({
            rowNodes: [this.params.node],
            columns: columns,
            force: true,
        });
    }
    getGui() { return this.eGui; }
    refresh() { return false; }
}
""")

row_style = JsCode("""
function(params) {
    if (!params.data) return null;
    const FLAGGED = 'flagged';
    if (params.data['To Delete'] === FLAGGED) {
        return {
            'background-color': 'rgba(239, 68, 68, 0.14)',
            'box-shadow': 'inset 3px 0 0 rgba(239, 68, 68, 0.85)',
        };
    }
    if (params.data['To Audit'] === FLAGGED) {
        return {
            'background-color': 'rgba(234, 179, 8, 0.14)',
            'box-shadow': 'inset 3px 0 0 rgba(234, 179, 8, 0.85)',
        };
    }
    if (params.data['To Approve'] === FLAGGED) {
        return {
            'background-color': 'rgba(34, 197, 94, 0.14)',
            'box-shadow': 'inset 3px 0 0 rgba(34, 197, 94, 0.85)',
        };
    }
    return null;
}
""")


def action_column(field: str, label: str, active_color: str) -> dict:
    return {
        "field": field,
        "headerName": label,
        "cellRenderer": btn_renderer,
        "cellRendererParams": {
            "label": label,
            "activeColor": active_color,
            "siblingFields": ACTION_FIELDS,
        },
        "editable": False,
        "pinned": "right",
        "width": 110,
        "sortable": False,
        "filter": False,
        "suppressMenu": True,
        "resizable": False,
    }


grid_options = {
    "columnDefs": [
        {"field": "created"},
        {"field": "modified"},
        {"field": "size", "aggFunc": "sum", "valueFormatter": size_formatter},
        action_column("To Delete", "Delete", "#dc2626"),
        action_column("To Audit", "Audit", "#ca8a04"),
        action_column("To Approve", "Approve", "#16a34a"),
    ],
    "defaultColDef": {"flex": 1},
    "autoGroupColumnDef": {
        "headerName": "File Explorer",
        "minWidth": 280,
        "cellRendererParams": {"suppressCount": True},
    },
    "treeData": True,
    "groupDefaultExpanded": -1,
    "getDataPath": get_data_path,
    "getRowStyle": row_style,
}

with st.container(border=True):
    result = AgGrid(
        df,
        gridOptions=grid_options,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=True,
        height=600,
        update_on=["cellValueChanged"],
        key="tree_action_grid",
    )

if result.data is not None:
    returned = result.data
    flagged = {f: returned[returned[f] == FLAGGED] for f in ACTION_FIELDS}
    unflagged_mask = (returned[ACTION_FIELDS] != FLAGGED).all(axis=1)
    untouched = returned[unflagged_mask]

    c0, c1, c2, c3 = st.columns(4)
    c0.metric("Untouched", len(untouched))
    c1.metric("To Delete", len(flagged["To Delete"]))
    c2.metric("To Audit", len(flagged["To Audit"]))
    c3.metric("To Approve", len(flagged["To Approve"]))

    for field in ACTION_FIELDS:
        rows = flagged[field]
        if rows.empty:
            continue
        with st.expander(f"{field} ({len(rows)})", expanded=False):
            preview = rows.drop(columns=ACTION_FIELDS).copy()
            preview["path"] = preview["path"].apply(lambda p: "/".join(p))
            st.dataframe(preview, width="stretch", hide_index=True)

with st.expander("Code", icon=":material/code:"):
    st.code(
        '''grid_options = {
    "columnDefs": [...],
    "treeData": True,
    "groupDefaultExpanded": -1,
    "getDataPath": JsCode("function(data) { return data.path; }"),
    "getRowStyle": JsCode("""function(params) { ... }"""),
    "autoGroupColumnDef": {"headerName": "File Explorer", "minWidth": 280},
}

AgGrid(
    df,
    gridOptions=grid_options,
    allow_unsafe_jscode=True,
    enable_enterprise_modules=True,
    update_on=["cellValueChanged"],
)''',
        language="python",
    )
