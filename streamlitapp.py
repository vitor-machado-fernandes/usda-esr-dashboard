import os
import streamlit as st
import pandas as pd
from datetime import datetime

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1000px;
            padding-left: 2rem;
            padding-right: 2rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

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

# Units (for labeling)
is_cotton = commodity.lower().startswith("cotton")
unit = "Bales" if is_cotton else "Tons"
unit_k = f"Thousands of {unit}"

start_year = 2021
end_year = datetime.today().year+1

psd_map = {
    "Cotton": "2631000",
    "Corn": "0440000",
    "Soybeans": "2222000",
    "All Wheat": "0410000",
    "Soybean Meal": "0813100",
    "Soybean Oil": "4232000",   # <-- put your correct PSD code if different
}

# ---------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------
@st.cache_data(show_spinner=True)
def load_esr(api_key, code, y0, y1):
    return get_esr_exports(api_key, code, y0, y1)

df = load_esr(API_KEY, commodity_code, start_year, end_year)
df["Cancel"] = df["grossNewSales"] - df["currentMYNetSales"]


# ---------------------------------------------------------------------
# Date selection
# ---------------------------------------------------------------------
dates = sorted(df["weekEndingDate"].dt.date.unique())
picked = st.selectbox("Week ending", ["Latest"] + [str(d) for d in dates])
selected_date = None if picked == "Latest" else picked

# ---------------------------------------------------------------------
# Build current-MY snapshot
# ---------------------------------------------------------------------
my_start_month_map = {
    "Cotton": 8,
    "Corn": 9,
    "Soybeans": 9,
    "All Wheat": 6,
    "Soybean Cake & Meal": 10,
    "Soybean Oil": 10,
}


last_week = build_last_week(df, "country_codes.xlsx", selected_date)
week_ending = last_week["weekEndingDate"].iloc[0]


from usda_api import get_wasde_export

wasde_year = datetime.today().year - 1
wasde_export = get_wasde_export(API_KEY, psd_map[commodity], wasde_year)


from datetime import datetime

# Define how many weeks left on MY

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
shipments = float(last_week["accumulatedExports"].sum())

need_to_ship = wasde_export - shipments
avg_weekly = need_to_ship / weeks_left_CMY if weeks_left_CMY > 0 else 0

fwd_sales_df = pd.DataFrame([{
    "CMY Commitments": commitments,
    "CMY Exported": shipments,
    "WASDE Export Forecast": wasde_export,
    "Weeks Left CMY": weeks_left_CMY,
    "Avg Weekly Shipments Needed": avg_weekly,
}])

def fmt_m(x):
    return f"{x/1_000_000:.2f}M"


# ---------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------
st.write("""
**Fundamental Analysis: Commodity Exports**

We know that prices are inversely related to the availability of stocks (or better, stocks/use).
After all, the more of a commodity is stored in a bin/tank/warehouse somewhere, the less likely it is for consumers to panic-buy, and send prices soaring.

We have also seen that, per the WASDE balance sheet, exports are a key component of demand. Luckily for us, every Thursday at 7:30am CT, the USDA releases the Export Sales Report (ESR).
This report allows the public to monitor the pace in which American companies are selling, and shipping, commodity to different foreign nations.


**How it works**
         
The USDA requires physical traders to report sales and shipments weekly.
- New sales → Outstanding Sales  
- Shipments → Accumulated Exports  
- Outstanding + Accumulated = Total Commitments  

Moreover, large daily sales (≥100k MT) trigger a next-day *Flash Sales* report.


Anyhow, below you will find the **weekly** numbers for the **Export Sales Report** (in bales for cotton, and tons for grains):
""")

from esr_views import weekly_sales_table

weekly_df = weekly_sales_table(last_week).copy()

for c in weekly_df.columns:
    weekly_df[c] = weekly_df[c].map(lambda x: f"{x:,.0f}")

st.dataframe(weekly_df, hide_index=True)

st.write("""
And the **cumulative numbers** for the Marketing Year (MY):
""")

from esr_views import total_exports_table

weekly_df_2 = total_exports_table(last_week).copy()

for c in weekly_df_2.columns:
    weekly_df_2[c] = weekly_df_2[c].map(lambda x: f"{x:,.0f}")

st.dataframe(weekly_df_2, hide_index=True)


### Line Charts ###
st.subheader("Seasonal Weekly Pace (last 5 MYs)")
st.write(
"""
Below you can see seasonal charts for New CMY Sales, Shipments, Cancelations; as well as Next Marketing Year New Sales, and Outstanding Sales. 
"""
)

from esr_views import seasonal_line_plot

my_start = my_start_month_map[commodity]

row1 = st.columns(3, gap="small")
with row1[0]:
    st.pyplot(seasonal_line_plot(df, "currentMYNetSales", "Net New Sales", my_start, unit_k), use_container_width=True)
with row1[1]:
    st.pyplot(seasonal_line_plot(df, "weeklyExports", "Shipments", my_start, unit_k), use_container_width=True)
with row1[2]:
    st.pyplot(seasonal_line_plot(df, "Cancel", "Cancellations", my_start, unit_k), use_container_width=True)

row2 = st.columns(2, gap="small")
with row2[0]:
    st.pyplot(seasonal_line_plot(df, "nextMYNetSales", "NMY New Sales", my_start, unit_k), use_container_width=True)
with row2[1]:
    st.pyplot(seasonal_line_plot(df, "nextMYOutstandingSales", "NMY Outstanding", my_start, unit_k), use_container_width=True)


### Treemap and Seasonal Cumulative
st.markdown("<br>", unsafe_allow_html=True)
st.write("""
The below **treemap** shows weekly sales (tons for grains, bales for cotton) by destination.       
The **seasonal chart** compares the current MY to the previous five (1,000s of tons for grains, 1,000s of bales for cotton).
""")
TITLE_H = 100  # pixels; tweak 60–90 until perfect

col1, col2 = st.columns(2, gap="small")

with col1:
    st.markdown(
        f"<div style='height:{TITLE_H}px'><h3>US {commodity} Sales ({unit}) - Week Ending {pd.to_datetime(week_ending).date()}.</h3></div>",
        unsafe_allow_html=True    )
    st.plotly_chart(treemap_net_sales(last_week, week_ending), use_container_width=True)

with col2:
    st.markdown(
        f"<div style='height:{TITLE_H}px'><h3>Cumulative Commitments: CMY vs 5 previous years</h3></div>",
        unsafe_allow_html=True
    )
    my_start = my_start_month_map[commodity]
    st.pyplot(seasonal_commitments_plot(df, wasde_export, my_start_month=my_start, unit_k=unit_k), use_container_width=True)



st.write("""
The chart and table below combine destination and total commitments.
You can better visualize which destinations are the most relevant - and maybe as importantly which ones are missing.

Try changing the *week ending* date to see how market dynamics shift over time.
""")

plot2_1, plot2_2 = st.columns([1, 1])

with plot2_1:
    st.subheader(f"{commodity} Commitments by Destination")
    st.pyplot(commitments_hbar(last_week, unit_k=unit_k))

with plot2_2:
    st.subheader(" ")
    st.dataframe(
        commitments_table(last_week),
        use_container_width=True,
        height=325,
        hide_index=True
    )




st.subheader("Path to WASDE Exports")
st.write("""
Last but not least, it is helpful to know how much commodity need to be shipped per week, on average, for the WASDE's forecasted export number to be met.
If the average of weekly shipments needed is high vs what is actually being shipped, the USDA may need to reduce the exports forecast - which will then result in higher ending stocks. 
Also, keep in mind that before a commodity is shipped, it needs to be sold. Slow sales will likely result in reduced shipments.
""")

display_df = fwd_sales_df.copy()
display_df["CMY Commitments"] = display_df["CMY Commitments"].map(fmt_m)
display_df["CMY Exported"] = display_df["CMY Exported"].map(fmt_m)
display_df["WASDE Export Forecast"] = display_df["WASDE Export Forecast"].map(fmt_m)
display_df["Avg Weekly Shipments Needed"] = display_df["Avg Weekly Shipments Needed"].map(fmt_m)

st.dataframe(display_df, use_container_width=True, hide_index=True)


