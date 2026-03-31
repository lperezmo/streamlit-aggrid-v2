"""
st-aggrid Showcase
==================
Interactive demo of AG Grid for Streamlit,
powered by Custom Components v2.
"""

import streamlit as st

# -- Page config (must be first Streamlit call) ------------------------------
st.set_page_config(
    page_title="streamlit-aggrid-v2 | AG Grid for Streamlit",
    page_icon=":material/table_chart:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """<style>.block-container { padding-top: 1rem; }</style>""",
    unsafe_allow_html=True,
)

# -- Navigation --------------------------------------------------------------
page = st.navigation(
    {
        "": [
            st.Page("app_pages/basic_grid.py", title="Basic grid", icon=":material/table_chart:"),
            st.Page("app_pages/editing.py", title="Cell editing", icon=":material/edit:"),
            st.Page("app_pages/selection.py", title="Row selection", icon=":material/check_box:"),
        ],
        "Data": [
            st.Page("app_pages/filtering_sorting.py", title="Filtering & sorting", icon=":material/filter_list:"),
            st.Page("app_pages/floating_filters.py", title="Floating filters", icon=":material/search:"),
            st.Page("app_pages/data_return.py", title="Data return modes", icon=":material/output:"),
        ],
        "Appearance": [
            st.Page("app_pages/themes.py", title="Themes", icon=":material/palette:"),
            st.Page("app_pages/custom_columns.py", title="Column config", icon=":material/view_column:"),
            st.Page("app_pages/cell_renderers.py", title="Cell renderers", icon=":material/widgets:"),
            st.Page("app_pages/row_styling.py", title="Row styling", icon=":material/format_paint:"),
            st.Page("app_pages/inline_buttons.py", title="Inline buttons", icon=":material/smart_button:"),
        ],
        "Enterprise": [
            st.Page("app_pages/enterprise.py", title="Enterprise features", icon=":material/star:"),
        ],
    },
    position="top",
)

# -- Header ------------------------------------------------------------------
_IS_DARK = st.context.theme.type == "dark"
_HEADER_GRADIENT = (
    "linear-gradient(135deg, #60a5fa, #93c5fd)"
    if _IS_DARK
    else "linear-gradient(135deg, #2563eb, #1d4ed8)"
)
st.html(f"""
<div style="text-align:center; padding:1.25rem 0 0.25rem;">
    <h2 style="
        margin:0; font-size:1.5rem; font-weight:700;
        background:{_HEADER_GRADIENT};
        -webkit-background-clip:text; -webkit-text-fill-color:transparent;
        background-clip:text;
    ">streamlit-aggrid-v2</h2>
    <p style="margin:0.3rem 0 0; font-size:0.85rem; opacity:0.7;">
        AG Grid for Streamlit, powered by Components v2
    </p>
</div>
""")

# -- Sidebar -----------------------------------------------------------------
with st.sidebar:
    st.divider()
    st.markdown(
        "**st-aggrid** brings [AG Grid](https://www.ag-grid.com/)'s "
        "enterprise-grade data grid to Streamlit via the new "
        "Components v2 API — no iframes, native theming."
    )
    st.caption(
        "Based on [streamlit-aggrid](https://github.com/PablocFonseca/streamlit-aggrid) "
        "by Pablo Fonseca"
    )

# -- Page title + run --------------------------------------------------------
st.title(f"{page.title}")
page.run()

# -- Footer ------------------------------------------------------------------
st.divider()
st.caption(
    "Built with [streamlit-aggrid-v2](https://github.com/lperezmo/st-aggrid) · "
    "AG Grid v34.3.1 · "
    "Streamlit Custom Components v2"
)
