"""
AI Toolkit demo -- natural language grid manipulation via OpenAI.

The input bar and controls are embedded directly in the AG Grid component.
Python handles the LLM call and sends the state update back to the grid.

Requires:
  - OPENAI_API_KEY in .streamlit/secrets.toml
  - pip install openai
  - Enterprise modules (AI Toolkit is enterprise-only)
"""

import streamlit as st
import pandas as pd
import json

from st_aggrid import AgGrid, GridOptionsBuilder

st.caption(
    "Integrate AG Grid with an LLM, enabling natural language queries "
    "to filter, sort, group, aggregate, and resize columns."
)

# -- Check for API key --------------------------------------------------------
api_key = st.secrets.get("OPENAI_API_KEY", "")
if not api_key:
    st.info(
        "Set `OPENAI_API_KEY` in `.streamlit/secrets.toml` to enable this demo.\n\n"
        "```toml\nOPENAI_API_KEY = \"sk-...\"\n```"
    )
    st.stop()

# -- Sample data ---------------------------------------------------------------
@st.cache_data
def get_data():
    return pd.DataFrame(
        {
            "Athlete": [
                "Michael Phelps", "Usain Bolt", "Simone Biles", "Katie Ledecky",
                "Mo Farah", "Allyson Felix", "Nadia Comaneci", "Carl Lewis",
                "Serena Williams", "Eliud Kipchoge", "Shelly-Ann Fraser-Pryce",
                "Tadej Pogacar", "Sydney McLaughlin", "Caeleb Dressel",
                "Elaine Thompson-Herah",
            ],
            "Age": [23, 29, 19, 19, 33, 30, 14, 23, 30, 31, 27, 22, 21, 24, 29],
            "Country": [
                "United States", "Jamaica", "United States", "United States",
                "Great Britain", "United States", "Romania", "United States",
                "United States", "Kenya", "Jamaica",
                "Slovenia", "United States", "United States", "Jamaica",
            ],
            "Sport": [
                "Swimming", "Athletics", "Gymnastics", "Swimming",
                "Athletics", "Athletics", "Gymnastics", "Athletics",
                "Tennis", "Athletics", "Athletics",
                "Cycling", "Athletics", "Swimming", "Athletics",
            ],
            "Gold": [8, 3, 4, 2, 2, 3, 5, 2, 1, 1, 2, 0, 1, 5, 3],
            "Silver": [0, 0, 1, 2, 0, 3, 3, 1, 0, 1, 2, 0, 0, 0, 0],
            "Bronze": [0, 0, 2, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 0, 0],
            "Total": [8, 3, 7, 4, 2, 7, 9, 4, 1, 3, 4, 1, 1, 5, 3],
        }
    )


df = get_data()

# -- Session state init --------------------------------------------------------
if "ai_state_update" not in st.session_state:
    st.session_state.ai_state_update = None
if "ai_response" not in st.session_state:
    st.session_state.ai_response = None

# -- Grid config ---------------------------------------------------------------
gb = GridOptionsBuilder.from_dataframe(df)
gb.configure_default_column(
    filterable=True,
    sortable=True,
    enableRowGroup=True,
    enableValue=True,
    enablePivot=True,
    flex=1,
    minWidth=100,
    resizable=True,
)
gb.configure_column("Athlete", minWidth=200, filter="agTextColumnFilter", enablePivot=False)
gb.configure_column("Age", width=90, filter="agNumberColumnFilter", enableRowGroup=False)
gb.configure_column("Country", minWidth=150, filter="agSetColumnFilter", enablePivot=True)
gb.configure_column("Sport", minWidth=150, filter="agSetColumnFilter", enablePivot=True)
for medal_col in ["Gold", "Silver", "Bronze", "Total"]:
    gb.configure_column(medal_col, width=100, filter="agNumberColumnFilter", aggFunc="sum")
gb.configure_grid_options(sideBar={"toolPanels": ["columns", "filters"]})
grid_options = gb.build()

# -- Render grid (AI Toolkit input is embedded in the component) ---------------
result = AgGrid(
    df,
    gridOptions=grid_options,
    key="ai_grid",
    height=500,
    enable_enterprise_modules=True,
    ai_toolkit=True,
    ai_state_update=st.session_state.ai_state_update,
    ai_response=st.session_state.ai_response,
)

# -- Handle AI query from embedded input bar -----------------------------------
ai_query = None
if result is not None and isinstance(result.grid_response, dict):
    ai_query = result.ai_query

if ai_query:
    # Extract schema and state from the same return
    schema = result.structured_schema
    current_state = result.grid_state or {}

    if not schema:
        st.session_state.ai_response = {
            "status": "error",
            "explanation": "Grid schema not available yet. Please try again.",
            "prompt": ai_query,
        }
        st.rerun()

    try:
        import openai
    except ImportError:
        st.error("Install openai: `pip install openai`")
        st.stop()

    # Show processing state immediately
    st.session_state.ai_response = {
        "status": "processing",
        "explanation": "",
        "prompt": ai_query,
    }

    # Build schema wrapper following AG Grid AI Toolkit pattern
    structured_schema = {k: v for k, v in schema.items() if k != "$defs"}
    defs = schema.get("$defs", {})

    llm_schema = {
        "type": "object",
        "$defs": defs,
        "properties": {
            "gridState": structured_schema,
            "propertiesToIgnore": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "aggregation", "filter", "sort", "pivot",
                        "columnVisibility", "columnSizing", "rowGroup",
                    ],
                },
                "description": "List of grid state properties to ignore when applying the new state",
            },
            "explanation": {
                "type": "string",
                "description": "Human-readable explanation of the changes made to the grid state",
            },
        },
        "required": ["gridState", "explanation", "propertiesToIgnore"],
        "additionalProperties": False,
    }

    # Filter current state to only AI-relevant properties
    relevant_keys = [
        "aggregation", "rowGroup", "columnSizing",
        "columnVisibility", "sort", "filter", "pivot",
    ]
    filtered_state = {k: v for k, v in current_state.items() if k in relevant_keys}

    system_prompt = (
        "You are an assistant for a table displaying Olympic medal results. "
        "You help users modify grid configuration to fit their needs.\n\n"
        "The schema provided can be used to manipulate multiple features of the table "
        "to help the user with their query.\n\n"
        f"Current grid state: {json.dumps(filtered_state)}\n\n"
        "Respond with only the necessary state changes, not the complete state. "
        "Provide a clear explanation of what you changed.\n\n"
        "Any unchanged properties that are present in the current state must be "
        "included in `propertiesToIgnore`. Otherwise they will be removed from the state.\n\n"
        "Important: Only modify the properties that the user specifically requested. "
        "If they ask to 'hide the age column', only include columnVisibility in your response, "
        "not other unrelated properties.\n"
        "Where possible, augment the provided state rather than replacing it entirely."
    )

    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": ai_query},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "grid_state_response",
                    "schema": llm_schema,
                },
            },
            max_completion_tokens=4096,
            temperature=0.1,
        )

        reply_text = response.choices[0].message.content
        parsed = json.loads(reply_text)

        grid_state = parsed.get("gridState", {})
        properties_to_ignore = parsed.get("propertiesToIgnore", [])
        explanation = parsed.get("explanation", "Grid updated.")

        if grid_state and len(grid_state) > 0:
            st.session_state.ai_state_update = {
                "gridState": grid_state,
                "propertiesToIgnore": properties_to_ignore,
            }

        st.session_state.ai_response = {
            "status": "success",
            "explanation": explanation,
            "prompt": ai_query,
        }

    except Exception as e:
        st.session_state.ai_response = {
            "status": "error",
            "explanation": str(e),
            "prompt": ai_query,
        }

    st.rerun()

# -- Suggested prompts below the grid -----------------------------------------
st.caption("Suggested prompts:")
sug_cols = st.columns(3)
suggestions = [
    "Show me all the gold medals won by the USA",
    "Sort the competitors with the youngest first",
    "Group by country and show the total medals won",
]
for col, suggestion in zip(sug_cols, suggestions):
    with col:
        st.code(suggestion, language=None)
