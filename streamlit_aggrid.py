# Backward-compatibility shim: ``import streamlit_aggrid`` still works.
# The actual package lives under ``st_aggrid``.
from st_aggrid import *  # noqa: F401,F403
