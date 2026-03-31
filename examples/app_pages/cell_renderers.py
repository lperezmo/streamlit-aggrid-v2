"""Cell Renderers — buttons, badges, and progress bars inside cells."""

import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from utils.data import get_sample_data

df = get_sample_data()

st.markdown(
    "Use `JsCode` cell renderers to embed interactive elements like buttons, "
    "badges, and progress bars directly inside grid cells. "
    "Enable `allow_unsafe_jscode=True` to use them."
)

# -- Cell renderer definitions ------------------------------------------------

# Rating as star badges
rating_renderer = JsCode("""
class RatingRenderer {
    init(params) {
        this.eGui = document.createElement('span');
        const val = params.value || 0;
        const fullStars = Math.floor(val);
        const halfStar = val % 1 >= 0.5;
        let stars = '';
        for (let i = 0; i < fullStars; i++) stars += '\u2605';
        if (halfStar) stars += '\u00BD';
        const color = val >= 4.5 ? '#22c55e' : val >= 4.0 ? '#eab308' : '#ef4444';
        this.eGui.innerHTML = `<span style="color:${color}; font-size:14px;">${stars}</span> <span style="opacity:0.7">${val}</span>`;
    }
    getGui() { return this.eGui; }
    refresh() { return false; }
}
""")

# Department as colored badge
badge_renderer = JsCode("""
class BadgeRenderer {
    init(params) {
        this.eGui = document.createElement('span');
        const colors = {
            Engineering: { bg: 'rgba(59,130,246,0.15)', text: '#3b82f6' },
            Sales:       { bg: 'rgba(234,179,8,0.15)',  text: '#ca8a04' },
            Marketing:   { bg: 'rgba(168,85,247,0.15)', text: '#a855f7' },
        };
        const c = colors[params.value] || { bg: 'rgba(128,128,128,0.15)', text: '#888' };
        this.eGui.innerHTML = `<span style="
            background:${c.bg}; color:${c.text};
            padding:2px 10px; border-radius:12px;
            font-size:12px; font-weight:600;
        ">${params.value}</span>`;
    }
    getGui() { return this.eGui; }
    refresh() { return false; }
}
""")

# Salary as progress bar
salary_renderer = JsCode("""
class SalaryBarRenderer {
    init(params) {
        this.eGui = document.createElement('div');
        const val = params.value || 0;
        const max = 180000;
        const pct = Math.min((val / max) * 100, 100);
        const color = pct > 70 ? '#22c55e' : pct > 40 ? '#3b82f6' : '#eab308';
        this.eGui.innerHTML = `
            <div style="display:flex; align-items:center; gap:8px; height:100%;">
                <div style="flex:1; background:rgba(128,128,128,0.15); border-radius:4px; height:8px; overflow:hidden;">
                    <div style="width:${pct}%; height:100%; background:${color}; border-radius:4px;"></div>
                </div>
                <span style="font-size:12px; min-width:65px; text-align:right;">$${val.toLocaleString()}</span>
            </div>`;
    }
    getGui() { return this.eGui; }
    refresh() { return false; }
}
""")

# Remote status with icon
remote_renderer = JsCode("""
class RemoteRenderer {
    init(params) {
        this.eGui = document.createElement('span');
        if (params.value === true || params.value === 'True' || params.value === 'true') {
            this.eGui.innerHTML = '<span style="color:#22c55e;">\u2714 Remote</span>';
        } else {
            this.eGui.innerHTML = '<span style="color:inherit; opacity:0.5;">\u2716 Office</span>';
        }
    }
    getGui() { return this.eGui; }
    refresh() { return false; }
}
""")

# -- Grid config --------------------------------------------------------------
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_column("Name", pinned="left", width=160)
gb.configure_column("Department", cellRenderer=badge_renderer, width=140)
gb.configure_column("Title", flex=1)
gb.configure_column("Salary", cellRenderer=salary_renderer, width=220)
gb.configure_column("Years", width=80, type=["numericColumn"])
gb.configure_column("Rating", cellRenderer=rating_renderer, width=140)
gb.configure_column("Remote", cellRenderer=remote_renderer, width=110)

grid_options = gb.build()

# -- Render -------------------------------------------------------------------
st.space("small")
with st.container(border=True):
    AgGrid(
        df,
        gridOptions=grid_options,
        allow_unsafe_jscode=True,
        height=420,
        key="renderer_grid",
    )

# -- Code --------------------------------------------------------------------
with st.expander("Code", icon=":material/code:"):
    st.code(
        '''from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# Define a cell renderer using JsCode (AG Grid class-based component)
badge_renderer = JsCode("""
class BadgeRenderer {
    init(params) {
        this.eGui = document.createElement('span');
        const colors = {
            Engineering: { bg: 'rgba(59,130,246,0.15)', text: '#3b82f6' },
            Sales:       { bg: 'rgba(234,179,8,0.15)',  text: '#ca8a04' },
        };
        const c = colors[params.value] || { bg: '#eee', text: '#888' };
        this.eGui.innerHTML = `<span style="
            background:${c.bg}; color:${c.text};
            padding:2px 10px; border-radius:12px;
        ">${params.value}</span>`;
    }
    getGui() { return this.eGui; }
    refresh() { return false; }
}
""")

gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_column("Department", cellRenderer=badge_renderer)
AgGrid(df, gridOptions=gb.build(), allow_unsafe_jscode=True)''',
        language="python",
    )
