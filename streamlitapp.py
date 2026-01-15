import os
import streamlit as st
import pandas as pd
from datetime import datetime

from usda_api import get_esr_exports
from esr_views import (
    build_last_week,
    treemap_net_sales,
    commitments_hbar,
    commitments_table
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
st.write("""
**Fundamental Analysis: Commodity Exports**

We have previously established that prices are inversely related to the availability of stocks (or better, stocks/use).
After all, the more of a commodity is stored in a bin/tank/warehouse somewhere, the less likely it is for consumers to panic-buy, and send prices soaring.

We have also seen that, per the WASDE balance sheet, exports are a key component of demand. Luckily, every Thursday at 7:30am CT, the USDA releases the Export Sales Report (ESR).
This report allows the public to monitor the pace in which American companies are selling, and shipping, commodity to different foreign nations.


**How it works**
The USDA requires physical traders to report sales and shipments weekly.
- New sales → Outstanding Sales  
- Shipments → Accumulated Exports  
- Outstanding + Accumulated = Total Commitments  

Moreover, large daily sales (≥100k MT) trigger a next-day *Flash Sales* report.

The below treemap shows weekly sales by destination.
The seasonal chart compares the current MY to the previous five.
""")

from esr_views import weekly_sales_table

st.dataframe(
    weekly_sales_table(last_week),
    use_container_width=True,
    hide_index=True,
)


plot1_1, plot1_2 = st.columns([1, 1])

with plot1_1:
    st.plotly_chart(
        treemap_net_sales(last_week, week_ending),
        use_container_width=True,
    )

with plot1_2:
    st.subheader("Cumulative Commitments: CMY vs 5 previous years")
    st.pyplot(seasonal_commitments_plot(df))


st.write("""
The chart and table below combine destination and total commitments.
You can better visualize which destinations are the most relevant - and maybe as importantly which ones are missing.

Try changing the *week ending* date to see how market dynamics shift over time.
""")

plot2_1, plot2_2 = st.columns([1, 1])

with plot2_1:
    st.subheader("Commitments by Destination")
    st.pyplot(commitments_hbar(last_week))

with plot2_2:
    st.subheader(" ")
    st.dataframe(
        commitments_table(last_week),
        use_container_width=True,
        height=375,
        hide_index=True
    )



from usda_api import get_wasde_export

wasde_year = datetime.today().year
wasde_export = get_wasde_export(API_KEY, wasde_year)


from datetime import datetime

def weeks_left_cmy(latest_week_date: datetime) -> int:
    end_year = (
        datetime.today().year
        if datetime.today().month < 8
        else datetime.today().year + 1
    )

    end = datetime(end_year, 7, 31)
    delta = end - latest_week_date

    return max(int(delta.days / 7), 0)

latest_week_date = last_week["weekEndingDate"].iloc[0]
weeks_left_CMY = weeks_left_cmy(latest_week_date)

commitments = float(last_week["currentMYTotalCommitment"].sum())

need_to_sell = wasde_export - commitments
avg_weekly = need_to_sell / weeks_left_CMY if weeks_left_CMY > 0 else 0

fwd_sales_df = pd.DataFrame([{
    "CMY Commitments": commitments,
    "WASDE Exports": wasde_export,
    "Weeks Left CMY": weeks_left_CMY,
    "Avg Weekly Sales Needed": avg_weekly,
}])

def fmt_m(x):
    return f"{x/1_000_000:.2f}M"

display_df = fwd_sales_df.copy()
display_df["CMY Commitments"] = display_df["CMY Commitments"].map(fmt_m)
display_df["WASDE Exports"] = display_df["WASDE Exports"].map(fmt_m)
display_df["Avg Weekly Sales Needed"] = display_df["Avg Weekly Sales Needed"].map(fmt_m)

st.subheader("Path to WASDE Exports")
st.write("""
Last but not least, it is helpful to know how much commodity need to be sold per week, on average, for sales to reach the WASDE's export number.
Although not an apples to apples comparison (sales >= exports), it is helpful in checking if the WASDE number is feasible.
If recent weekly sales > such average, the USDA might choose to raise exports, and lower ending stocks.
You should also keep an eye on the pace of exports. If shipments are too slow, ending stocks will be higher than initially expected. And so forth.
""")
st.dataframe(display_df, use_container_width=True, hide_index=True)
