import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import matplotlib.cm as cm
from datetime import datetime


def build_last_week(
    df_totals: pd.DataFrame,
    country_codes_path: str,
    selected_date=None
) -> pd.DataFrame:
    """
    Filters ESR data to a single week (latest or selected)
    and merges country descriptions.
    """
    cols = [
        "weekEndingDate",
        "countryCode",
        "weeklyExports",
        "grossNewSales",
        "currentMYNetSales",
        "nextMYNetSales",
        "currentMYTotalCommitment",
        "accumulatedExports",
        "outstandingSales",
    ]

    df = df_totals[cols].copy()
    df["Cancel"] = df["grossNewSales"] - df["currentMYNetSales"]

    if selected_date is None:
        selected_date = df["weekEndingDate"].max()

    last_week = df[df["weekEndingDate"] == pd.to_datetime(selected_date)].copy()

    countries = pd.read_excel(country_codes_path)[
        ["countryCode", "countryDescription"]
    ]
    countries["countryDescription"] = countries["countryDescription"].str.strip()

    last_week = last_week.merge(countries, on="countryCode", how="left")

    # Clean country names (as in your notebook)
    last_week.loc[
        last_week["countryDescription"] == "CHINA, PEOPLES REPUBLIC OF",
        "countryDescription",
    ] = "CHINA"

    last_week.loc[
        last_week["countryDescription"] == "KOREA, REPUBLIC OF",
        "countryDescription",
    ] = "S. KOREA"

    return last_week



def compute_kpis(last_week: pd.DataFrame) -> dict:
    """Aggregates headline ESR numbers."""
    return {
        "gross_new_sales": last_week["grossNewSales"].sum(),
        "net_new_sales": last_week["currentMYNetSales"].sum(),
        "cancel": last_week["Cancel"].sum(),
        "shipments": last_week["weeklyExports"].sum(),
        "nmy_net_new_sales": last_week["nextMYNetSales"].sum(),
    }


def weekly_sales_table(last_week: pd.DataFrame) -> pd.DataFrame:
    k = compute_kpis(last_week)
    return pd.DataFrame([{
        "CMY Net New Sales": k["net_new_sales"],
        "Shipments": k["shipments"],
        "Cancellations": k["cancel"],
        "NMY New Sales": k["nmy_net_new_sales"],
    }])


def treemap_net_sales(last_week: pd.DataFrame, week_ending) :
    """
    Treemap of current MY net sales by country.
    """
    k = compute_kpis(last_week)

    title = (f"US Cotton Sales (running bales) - Week Ending {pd.to_datetime(week_ending).date()}.")

    fig = px.treemap(
        last_week,
        path=["countryDescription"],
        values="currentMYNetSales",
        color="currentMYNetSales",
        color_continuous_scale="Oranges",
        title=title,
    )

    fig.update_traces(texttemplate="%{label}<br>%{value:,.0f}")
    fig.update_coloraxes(showscale=False)
    fig.update_layout(height=525)

    return fig




def commitments_hbar(last_week):
    df = (
    last_week[["countryDescription", "accumulatedExports", "outstandingSales", "currentMYTotalCommitment"]]
    .sort_values("currentMYTotalCommitment", ascending=False)
    .head(20)                      # 👈 top 20
    .sort_values("currentMYTotalCommitment")  # 👈 re-sort for barh
)

    country = df["countryDescription"]
    shipped = df["accumulatedExports"] / 1_000  # thousands of bales
    outst = df["outstandingSales"] / 1_000

    fig, ax = plt.subplots(figsize=(6, 5))

    p1 = ax.barh(country, shipped, color="#588157")
    p2 = ax.barh(country, outst, left=shipped, color="#a3b18a")

    ax.legend((p1[0], p2[0]), ("Shipments", "Outstanding"))
    ax.set_xlabel("Thousands of Bales")
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    return fig


def seasonal_commitments_plot(df_totals, wasde_export=None, my_start_month=8):
    data = df_totals[["weekEndingDate", "accumulatedExports", "outstandingSales"]]

    weekly = (
        data.groupby("weekEndingDate")[["accumulatedExports", "outstandingSales"]]
        .sum()
        .reset_index()
    )

    # Marketing year label = year in which the MY ends
    weekly["MY"] = weekly["weekEndingDate"].dt.year + (weekly["weekEndingDate"].dt.month >= my_start_month).astype(int)

    weekly = weekly.sort_values(["MY", "weekEndingDate"])
    weekly["MktingWeek"] = weekly.groupby("MY").cumcount() + 1

    # Current MY
    CMY = datetime.today().year + (datetime.today().month >= my_start_month)
    cmy_df = weekly[weekly["MY"] == CMY]

    fig, ax = plt.subplots(figsize=(10, 7))

    ax.bar(
        cmy_df["MktingWeek"],
        cmy_df["accumulatedExports"],
        label="CMY Acc Exports",
        color="#E48912",
    )
    ax.bar(
        cmy_df["MktingWeek"],
        cmy_df["outstandingSales"],
        bottom=cmy_df["accumulatedExports"],
        label="CMY Outstanding",
        color="#4A9ACF",
    )

    # Prior 5 MYs
    prev_years = sorted(weekly["MY"].unique())
    prev_years = [y for y in prev_years if y < CMY][-5:]
    colors = cm.Greys(np.linspace(0.3, 0.8, len(prev_years)))

    for y, c in zip(prev_years, colors):
        d = weekly[weekly["MY"] == y]
        total = d["accumulatedExports"] + d["outstandingSales"]
        ax.plot(d["MktingWeek"], total, color=c, linewidth=1.5)

    ax.set_xlim(0.5, 52)
    ax.set_ylabel("Thousand Bales")
    
    # WASDE line
    if wasde_export is not None:
        ax.axhline(
            y=wasde_export,
            color="black",
            linestyle="--",
            linewidth=1.2,
            label=f"WASDE: {wasde_export/1e3:,.0f}",
        )

    ax.legend()

    ax.yaxis.set_major_formatter(
        mtick.FuncFormatter(lambda x, _: f"{x/1e3:,.0f}")
    )

    # --- X axis as months ---
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    ordered = months[my_start_month-1:] + months[:my_start_month-1]

    weeks = np.arange(1, 53)
    month_labels = []
    for w in weeks:
        month_labels.append(ordered[min((w-1)//4, 11)]) # 4 weeks per month bucket

    ax.set_xticks(weeks[::4])
    ax.set_xticklabels(month_labels[::4])

    return fig

def commitments_table(last_week: pd.DataFrame) -> pd.DataFrame:
    df = (
        last_week[[
            "countryDescription",
            "accumulatedExports",
            "outstandingSales",
            "currentMYTotalCommitment",
        ]]
        .dropna(subset=["countryDescription"])
        .sort_values("currentMYTotalCommitment", ascending=False)
    )

    df[[
        "accumulatedExports",
        "outstandingSales",
        "currentMYTotalCommitment",
    ]] /= 1_000  # thousands of bales

    df = df.rename(columns={
        "countryDescription": "Country",
        "accumulatedExports": "Shipments",
        "outstandingSales": "Outstanding",
        "currentMYTotalCommitment": "Total Commitments",
    })

    return df