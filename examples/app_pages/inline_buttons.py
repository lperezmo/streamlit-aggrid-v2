"""Inline Buttons — Delete/Undo toggle pattern with sentinel column."""

import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from utils.data import get_sample_data

df = get_sample_data().copy()

st.markdown(
    "Render **actionable buttons** inside grid cells using a custom JS cell renderer. "
    "This demo shows a Delete/Undo toggle that writes a sentinel value into a hidden column, "
    "letting you collect flagged rows in Python after the user is done."
)

# -- Sentinel column ----------------------------------------------------------
SENTINEL = "marked for deletion"

if "To Be Deleted" not in df.columns:
    df["To Be Deleted"] = ""

# -- JS Cell Renderer ---------------------------------------------------------
btn_renderer = JsCode("""
class BtnCellRenderer {
    init(params) {
        this.params = params;
        this.eGui = document.createElement('div');
        this.eGui.style.display = 'flex';
        this.eGui.style.alignItems = 'center';
        this.eGui.style.height = '100%';
        this.render();
    }

    render() {
        const sentinel = 'marked for deletion';
        const flagged = this.params.value === sentinel;
        this.eGui.innerHTML = `
            <button style="
                color: white;
                background: ${flagged ? '#dc2626' : 'rgba(128,128,128,0.45)'};
                border: none;
                border-radius: 4px;
                padding: 3px 12px;
                cursor: pointer;
                font-size: 12px;
                font-weight: 600;
                transition: background 0.15s;
            ">${flagged ? 'Undo' : 'Delete'}</button>`;
        this.eGui.querySelector('button')
            .addEventListener('click', () => this.toggle(flagged));
    }

    toggle(flagged) {
        const sentinel = 'marked for deletion';
        this.params.setValue(flagged ? '' : sentinel);
        this.params.api.refreshCells({
            rowNodes: [this.params.node],
            force: true,
        });
        this.render();
    }

    getGui() { return this.eGui; }
    refresh() { return false; }
}
""")

# -- Row style: dim deleted rows ----------------------------------------------
deleted_row_style = JsCode("""
function(params) {
    const sentinel = 'marked for deletion';
    if (params.data['To Be Deleted'] === sentinel) {
        return {
            'opacity': '0.4',
            'text-decoration': 'line-through',
            'background-color': 'rgba(239, 68, 68, 0.06)',
        };
    }
    return null;
}
""")

# -- Grid config --------------------------------------------------------------
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_column("Name", pinned="left", width=160)
gb.configure_column(
    "Salary",
    type=["numericColumn"],
    valueFormatter="'$' + x.toLocaleString()",
)
gb.configure_column("Rating", type=["numericColumn"], width=100)
gb.configure_column("Years", type=["numericColumn"], width=90)
gb.configure_column(
    "To Be Deleted",
    headerName="Action",
    cellRenderer=btn_renderer,
    editable=False,
    pinned="right",
    width=100,
    sortable=False,
    filter=False,
    suppressMenu=True,
)

grid_options = gb.build()
grid_options["getRowStyle"] = deleted_row_style.js_code

# -- Render -------------------------------------------------------------------
st.space("small")

with st.container(border=True):
    result = AgGrid(
        df,
        gridOptions=grid_options,
        allow_unsafe_jscode=True,
        height=420,
        update_on=["cellValueChanged"],
        key="delete_undo_grid",
    )

# -- Show results -------------------------------------------------------------
if result.data is not None:
    returned = result.data
    deleted = returned[returned["To Be Deleted"] == SENTINEL]
    kept = returned[returned["To Be Deleted"] != SENTINEL]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Kept rows", len(kept))
    with col2:
        st.metric("Flagged for deletion", len(deleted), delta=f"-{len(deleted)}" if len(deleted) > 0 else None, delta_color="inverse")

    if not deleted.empty:
        with st.expander(f"Rows flagged for deletion ({len(deleted)})", expanded=True):
            st.dataframe(
                deleted.drop(columns=["To Be Deleted"]),
                use_container_width=True,
                hide_index=True,
            )

        if st.button("Confirm delete", type="primary"):
            st.success(f"Deleted {len(deleted)} row(s): {', '.join(deleted['Name'].tolist())}")
            st.caption("In a real app, this is where you'd call your DB delete function.")

# -- How it works -------------------------------------------------------------
with st.expander("How it works", icon=":material/info:"):
    st.markdown("""
**Architecture:**

1. A sentinel column (`To Be Deleted`) is added to the DataFrame, initially empty
2. A JS cell renderer (`BtnCellRenderer`) reads the cell value to show "Delete" or "Undo"
3. On click, `params.setValue()` writes the sentinel string back into the cell
4. `getRowStyle` dims flagged rows with opacity + strikethrough
5. On form submit, Python filters `result.data` to separate kept vs. deleted rows

**Why this works well:**
- No extra state management — the sentinel lives in AG Grid's data model
- Survives filtering and sorting
- Reversible — "Undo" clears the sentinel before any data is committed
- Clean separation — JS handles UI toggling, Python handles actual operations
""")

# -- Code --------------------------------------------------------------------
with st.expander("Code", icon=":material/code:"):
    st.code(
        '''from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

SENTINEL = "marked for deletion"
df["To Be Deleted"] = ""  # add sentinel column

# JS cell renderer: Delete/Undo toggle button
btn_renderer = JsCode("""
class BtnCellRenderer {
    init(params) {
        this.params = params;
        this.eGui = document.createElement('div');
        this.render();
    }
    render() {
        const flagged = this.params.value === 'marked for deletion';
        this.eGui.innerHTML = `<button style="
            color:white; background:${flagged ? '#dc2626' : 'gray'};
            border:none; border-radius:4px; padding:3px 12px; cursor:pointer;
        ">${flagged ? 'Undo' : 'Delete'}</button>`;
        this.eGui.querySelector('button')
            .addEventListener('click', () => this.toggle(flagged));
    }
    toggle(flagged) {
        this.params.setValue(flagged ? '' : 'marked for deletion');
        this.params.api.refreshCells({
            rowNodes: [this.params.node], force: true
        });
        this.render();
    }
    getGui() { return this.eGui; }
    refresh() { return false; }
}
""")

# Dim deleted rows
row_style = JsCode("""
function(params) {
    if (params.data['To Be Deleted'] === 'marked for deletion') {
        return { opacity: '0.4', 'text-decoration': 'line-through' };
    }
    return null;
}
""")

gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_column("To Be Deleted",
    headerName="Action", cellRenderer=btn_renderer,
    editable=False, pinned="right", width=100)

grid_options = gb.build()
grid_options["getRowStyle"] = row_style.js_code

result = AgGrid(df, gridOptions=grid_options,
    allow_unsafe_jscode=True, update_on=["cellValueChanged"])

# Extract flagged rows
deleted = result.data[result.data["To Be Deleted"] == SENTINEL]''',
        language="python",
    )
