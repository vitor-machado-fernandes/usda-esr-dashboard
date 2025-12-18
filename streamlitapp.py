import os
import streamlit as st
import pandas as pd
from datetime import datetime

from usda_api import get_esr_exports
from esr_views import (
    build_last_week,
    treemap_net_sales,
    commitments_hbar
)
from esr_views import seasonal_commitments_plot

# ---------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------
st.set_page_config(layout="wide")
st.title("USDA Export Sales Report Dashboard")

# ---------------------------------------------------------------------
# API key
# ---------------------------------------------------------------------
API_KEY = st.secrets.get("USDA_API_KEY", os.getenv("USDA_API_KEY", ""))

# ---------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------
commodity_map = {
    "Cotton": 1404,
    "Corn": 401,
    "Soybeans": 801,
    "All Wheat": 107,
    "Soybean Cake & Meal": 901,
    "Soybean Oil": 902
}

commodity = st.selectbox("Commodity", list(commodity_map.keys()))
commodity_code = commodity_map[commodity]

start_year, end_year = st.slider(
    "Market years",
    2021,
    datetime.today().year + 1,
    (2021, 2026),
)

# ---------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------
@st.cache_data(show_spinner=True)
def load_esr(api_key, code, y0, y1):
    return get_esr_exports(api_key, code, y0, y1)

df = load_esr(API_KEY, commodity_code, start_year, end_year)

# ---------------------------------------------------------------------
# Date selection
# ---------------------------------------------------------------------
dates = sorted(df["weekEndingDate"].dt.date.unique())
picked = st.selectbox("Week ending", ["Latest"] + [str(d) for d in dates])
selected_date = None if picked == "Latest" else picked

# ---------------------------------------------------------------------
# Build current-MY snapshot
# ---------------------------------------------------------------------
last_week = build_last_week(df, "country_codes.xlsx", selected_date)
week_ending = last_week["weekEndingDate"].iloc[0]


# ---------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    st.plotly_chart(
        treemap_net_sales(last_week, week_ending),
        use_container_width=True,
    )

with col2:
    st.subheader("Commitments")
    st.pyplot(commitments_hbar(last_week))

with col3:
    st.subheader("Seasonal")
    st.pyplot(seasonal_commitments_plot(df))

