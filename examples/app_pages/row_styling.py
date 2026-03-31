"""Row Styling — conditional row and cell coloring."""

import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from utils.data import get_sample_data

df = get_sample_data()

st.markdown(
    "Style rows and cells conditionally using `getRowStyle`, `rowClassRules`, "
    "or `cellStyle`. Colors use semi-transparent values to work in both light and dark mode."
)

# -- Style mode picker -------------------------------------------------------
style_mode = st.radio(
    "Styling approach",
    options=["Row class rules", "getRowStyle callback", "Cell-level styling", "All combined"],
    horizontal=True,
)

# -- Grid config --------------------------------------------------------------
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_column("Name", pinned="left", width=160)
gb.configure_column(
    "Salary",
    type=["numericColumn"],
    valueFormatter="'$' + x.toLocaleString()",
    width=130,
)
gb.configure_column("Rating", type=["numericColumn"], width=100)
gb.configure_column("Years", type=["numericColumn"], width=90)
gb.configure_column("Remote", width=100)

grid_options = gb.build()

# -- Style definitions (dark/light mode friendly with rgba) --------------------

if style_mode == "Row class rules" or style_mode == "All combined":
    # rowClassRules use expression strings — `data` is available as shorthand
    grid_options["rowClassRules"] = {
        "high-performer": "data.Rating >= 4.5",
        "low-performer": "data.Rating < 3.8",
    }

    # Inject matching CSS classes using custom_css
    custom_css = {
        ".high-performer": {
            "background-color": "rgba(34, 197, 94, 0.12) !important",
            "border-left": "3px solid #22c55e !important",
        },
        ".low-performer": {
            "background-color": "rgba(239, 68, 68, 0.1) !important",
            "border-left": "3px solid #ef4444 !important",
        },
    }
else:
    custom_css = {}

if style_mode == "getRowStyle callback" or style_mode == "All combined":
    grid_options["getRowStyle"] = JsCode("""
    function(params) {
        if (params.data.Years >= 10) {
            return {
                'background-color': 'rgba(59, 130, 246, 0.1)',
                'font-weight': '600'
            };
        }
        return null;
    }
    """).js_code

if style_mode == "Cell-level styling" or style_mode == "All combined":
    # Apply cellStyle to the Salary column
    for col_def in grid_options["columnDefs"]:
        if col_def.get("field") == "Salary":
            col_def["cellStyle"] = JsCode("""
            function(params) {
                const val = params.value;
                if (val >= 150000) return { color: '#22c55e', fontWeight: 'bold' };
                if (val >= 100000) return { color: '#3b82f6' };
                if (val < 80000)  return { color: '#ef4444', fontStyle: 'italic' };
                return null;
            }
            """).js_code

        if col_def.get("field") == "Remote":
            col_def["cellStyle"] = JsCode("""
            function(params) {
                const isRemote = params.value === true || params.value === 'True';
                return {
                    'background-color': isRemote
                        ? 'rgba(34, 197, 94, 0.1)'
                        : 'rgba(239, 68, 68, 0.06)',
                };
            }
            """).js_code

# -- Descriptions -------------------------------------------------------------
st.space("small")
if style_mode == "Row class rules":
    st.info("**rowClassRules**: Rating >= 4.5 gets green highlight, < 3.8 gets red. Uses CSS classes injected via `custom_css`.")
elif style_mode == "getRowStyle callback":
    st.info("**getRowStyle**: Employees with 10+ years get a blue tinted row with bold text.")
elif style_mode == "Cell-level styling":
    st.info("**cellStyle**: Salary cells colored by value (green/blue/red). Remote column gets conditional background.")
else:
    st.info("**All combined**: Row class rules + getRowStyle + cell-level styling applied together.")

# -- Render -------------------------------------------------------------------
with st.container(border=True):
    AgGrid(
        df,
        gridOptions=grid_options,
        allow_unsafe_jscode=True,
        custom_css=custom_css,
        height=420,
        key="row_style_grid",
    )

# -- Code --------------------------------------------------------------------
with st.expander("Code", icon=":material/code:"):
    st.code(
        '''from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

gb = GridOptionsBuilder.from_dataframe(df)
grid_options = gb.build()

# Row class rules — expression strings (data.Field shorthand)
grid_options["rowClassRules"] = {
    "high-performer": "data.Rating >= 4.5",
    "low-performer": "data.Rating < 3.8",
}
custom_css = {
    ".high-performer": {
        "background-color": "rgba(34, 197, 94, 0.12) !important",
        "border-left": "3px solid #22c55e !important",
    },
}

# getRowStyle — JS callback returning style object
grid_options["getRowStyle"] = JsCode("""
function(params) {
    if (params.data.Years >= 10) {
        return { 'background-color': 'rgba(59,130,246,0.1)' };
    }
    return null;
}
""").js_code

# cellStyle — per-column JS callback
gb.configure_column("Salary", cellStyle=JsCode("""
function(params) {
    if (params.value >= 150000) return { color: '#22c55e', fontWeight: 'bold' };
    return null;
}
"""))

AgGrid(df, gridOptions=grid_options,
       allow_unsafe_jscode=True, custom_css=custom_css)''',
        language="python",
    )
