"""Shared sample data for the showcase app."""

import pandas as pd
import streamlit as st


@st.cache_data
def get_sample_data() -> pd.DataFrame:
    """Employee dataset used across demo pages."""
    return pd.DataFrame(
        {
            "Name": [
                "Alice Johnson", "Bob Smith", "Charlie Davis", "Diana Lee",
                "Eve Martinez", "Frank Wilson", "Grace Kim", "Henry Brown",
                "Iris Chen", "Jack Taylor", "Karen White", "Leo Garcia",
            ],
            "Department": [
                "Engineering", "Sales", "Engineering", "Marketing",
                "Sales", "Engineering", "Marketing", "Sales",
                "Engineering", "Marketing", "Sales", "Engineering",
            ],
            "Title": [
                "Senior Engineer", "Account Executive", "Staff Engineer", "Marketing Lead",
                "Sales Manager", "Junior Engineer", "Content Strategist", "Account Executive",
                "Principal Engineer", "Brand Manager", "Sales Director", "Senior Engineer",
            ],
            "Salary": [
                125_000, 85_000, 155_000, 95_000,
                110_000, 72_000, 78_000, 88_000,
                175_000, 92_000, 130_000, 128_000,
            ],
            "Years": [8, 3, 12, 5, 7, 1, 4, 3, 15, 6, 9, 7],
            "Rating": [4.5, 3.8, 4.9, 4.2, 4.0, 3.5, 4.1, 3.9, 4.8, 4.3, 4.6, 4.4],
            "Remote": [True, False, True, True, False, False, True, False, True, True, False, True],
        }
    )
