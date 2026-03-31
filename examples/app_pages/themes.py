"""Themes — built-in and custom AG Grid themes."""

import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, StAggridTheme
from utils.data import get_sample_data

df = get_sample_data()

st.markdown(
    "AG Grid v34 supports four built-in themes plus a custom theme builder. "
    "All themes auto-detect Streamlit's dark/light mode."
)

# -- Theme picker ------------------------------------------------------------
col1, col2 = st.columns([1, 2])

with col1:
    theme_name = st.radio(
        "Built-in theme",
        options=["streamlit", "quartz", "alpine", "balham", "material"],
        index=0,
    )

with col2:
    use_custom = st.toggle("Use custom theme instead", value=False)
    if use_custom:
        base = st.selectbox(
            "Base theme",
            options=["quartz", "alpine", "balham", "material"],
            index=0,
        )
        color_scheme = st.selectbox(
            "Color scheme part (optional)",
            options=[
                "(none)",
                "colorSchemeLight",
                "colorSchemeLightWarm",
                "colorSchemeLightCold",
                "colorSchemeDark",
                "colorSchemeDarkWarm",
                "colorSchemeDarkBlue",
            ],
            index=0,
        )
        icon_set = st.selectbox(
            "Icon set part (optional)",
            options=[
                "(none)",
                "iconSetQuartz",
                "iconSetQuartzLight",
                "iconSetQuartzBold",
                "iconSetAlpine",
                "iconSetMaterial",
                "iconSetQuartzRegular",
            ],
            index=0,
        )
        odd_row = st.color_picker("Odd row background", value="#f0f4ff")
        header_bg = st.color_picker("Header background", value="#1e3a5f")

st.space("small")

# -- Build theme -------------------------------------------------------------
if use_custom:
    parts = []
    if color_scheme != "(none)":
        parts.append(color_scheme)
    if icon_set != "(none)":
        parts.append(icon_set)

    theme = (
        StAggridTheme(base=base)
        .withParams(
            oddRowBackgroundColor=odd_row,
            headerBackgroundColor=header_bg,
            headerTextColor="#ffffff",
        )
    )
    if parts:
        theme = theme.withParts(*parts)
else:
    theme = theme_name

# -- Grid options ------------------------------------------------------------
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_column("Name", pinned="left", width=160)
gb.configure_column("Salary", type=["numericColumn"], valueFormatter="'$' + x.toLocaleString()")
gb.configure_column("Rating", type=["numericColumn"], width=100)
gb.configure_column("Remote", width=100)
grid_options = gb.build()

# -- Render grid -------------------------------------------------------------
with st.container(border=True):
    AgGrid(
        df,
        gridOptions=grid_options,
        theme=theme,
        height=380,
        key="theme_grid",
    )

# -- Code snippet ------------------------------------------------------------
with st.expander("Code", icon=":material/code:"):
    st.code(
        '''from st_aggrid import AgGrid, StAggridTheme

# Built-in themes: "streamlit", "quartz", "alpine", "balham", "material"
AgGrid(df, theme="quartz")

# Custom theme with color scheme and icon set parts
theme = (
    StAggridTheme(base="quartz")
    .withParams(
        oddRowBackgroundColor="#f0f4ff",
        headerBackgroundColor="#1e3a5f",
        headerTextColor="#ffffff",
    )
    .withParts("colorSchemeDarkBlue", "iconSetQuartzBold")
)
AgGrid(df, theme=theme)''',
        language="python",
    )
