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
        "nextMYOutstandingSales",
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
        "cum_exports": last_week["accumulatedExports"].sum(),
        "outstanding": last_week["outstandingSales"].sum(),
        "commitment": last_week["currentMYTotalCommitment"].sum(),
        "nmy_outstanding": last_week["nextMYOutstandingSales"].sum(),
    }


def weekly_sales_table(last_week: pd.DataFrame) -> pd.DataFrame:
    k = compute_kpis(last_week)
    return pd.DataFrame([{
        "CMY Net New Sales": k["net_new_sales"],
        "Shipments": k["shipments"],
        "Cancellations": k["cancel"],
        "NMY New Sales": k["nmy_net_new_sales"],
    }])

def total_exports_table(last_week: pd.DataFrame) -> pd.DataFrame:
    k = compute_kpis(last_week)
    return pd.DataFrame([{
        "Accumulated Exports": k["cum_exports"],
        "Outstanding Sales": k["outstanding"],
        "Total Commitment": k["commitment"],
        "Next MY Sales": k["nmy_outstanding"],
    }])


def treemap_net_sales(last_week: pd.DataFrame, week_ending) :
    """
    Treemap of current MY net sales by country.
    """
    k = compute_kpis(last_week)

    fig = px.treemap(
        last_week,
        path=["countryDescription"],
        values="currentMYNetSales",
        color="currentMYNetSales",
        color_continuous_scale="Oranges"
    )

    fig.update_traces(texttemplate="%{label}<br>%{value:,.0f}")
    fig.update_coloraxes(showscale=False)
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))


    return fig



def commitments_hbar(last_week, unit_k="Thousands of Bales"):
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
    ax.set_xlabel(unit_k)
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    return fig


def seasonal_commitments_plot(df_totals, wasde_export=None, my_start_month=8, unit_k="Thousands of Bales"):
    # --- safety check ---
    if "MY" not in df_totals.columns:
        raise ValueError("df_totals must contain column 'MY'. Add it in get_esr_exports() by stamping the loop year.")

    data = df_totals[["MY", "weekEndingDate", "accumulatedExports", "outstandingSales"]].copy()
    data["weekEndingDate"] = pd.to_datetime(data["weekEndingDate"])

    # Aggregate to one row per (MY, weekEndingDate)
    weekly = (
        data.groupby(["MY", "weekEndingDate"], as_index=False)[["accumulatedExports", "outstandingSales"]]
        .sum()
    )

    # Week index within each MY (this is your x-axis)
    weekly = weekly.sort_values(["MY", "weekEndingDate"])
    weekly["MktingWeek"] = weekly.groupby("MY").cumcount() + 1

    # Define CMY as the MY associated with the latest report week we actually have
    latest_date = weekly["weekEndingDate"].max()
    CMY = int(weekly.loc[weekly["weekEndingDate"] == latest_date, "MY"].mode().iloc[0])

    cmy_df = weekly[weekly["MY"] == CMY].copy()

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
    prev_years = sorted([y for y in weekly["MY"].unique() if y < CMY])[-5:]
    colors = cm.Greys(np.linspace(0.3, 0.8, len(prev_years)))

    for y, c in zip(prev_years, colors):
        d = weekly[weekly["MY"] == y]
        total = d["accumulatedExports"] + d["outstandingSales"]
        ax.plot(d["MktingWeek"], total, color=c, linewidth=1.5)
        ax.text(
            d["MktingWeek"].max() + 0.3,
            total.iloc[-1],
            str(y),
            color=c,
            fontsize=9,
            va="center"
        )


    # x-axis range: avoid clipping 53-week years
    xmax = int(max(52, weekly["MktingWeek"].max()))
    ax.set_xlim(0.5, xmax)

    ax.set_ylabel(unit_k)

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

    # Keep your existing “thousands” formatting
    ax.yaxis.set_major_formatter(
        mtick.FuncFormatter(lambda x, _: f"{x/1e3:,.0f}")
    )

    # --- X axis as months (same logic you had, but sized to xmax) ---
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    ordered = months[my_start_month-1:] + months[:my_start_month-1]

    weeks = np.arange(1, xmax + 1)
    month_labels = [ordered[min((w - 1)//4, 11)] for w in weeks]

    ax.set_xticks(weeks[::4])
    ax.set_xticklabels(month_labels[::4])
    fig.tight_layout()

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


def seasonal_line_plot(
    df_totals: pd.DataFrame,
    value_col: str,
    title: str,
    my_start_month: int = 8,
    unit_k: str = "Thousands of Bales",
    years: int = 5,
):
    if "MY" not in df_totals.columns:
        raise ValueError("df_totals must contain column 'MY'.")

    data = df_totals[["MY", "weekEndingDate", value_col]].copy()
    data["weekEndingDate"] = pd.to_datetime(data["weekEndingDate"])

    weekly = (
        data.groupby(["MY", "weekEndingDate"], as_index=False)[value_col]
        .sum()
        .sort_values(["MY", "weekEndingDate"])
    )
    weekly["MktingWeek"] = weekly.groupby("MY").cumcount() + 1

    latest_date = weekly["weekEndingDate"].max()
    CMY = int(weekly.loc[weekly["weekEndingDate"] == latest_date, "MY"].mode().iloc[0])

    plot_years = sorted([y for y in weekly["MY"].unique() if y <= CMY])[-years:]
    colors = cm.Greys(np.linspace(0.3, 0.8, len(plot_years)))

    fig, ax = plt.subplots(figsize=(5.2, 3.4))  # consistent size across all 5

    for y, c in zip(plot_years, colors):
        d = weekly[weekly["MY"] == y]
        series = d[value_col] / 1_000  # display in thousands
        ax.plot(d["MktingWeek"], series, color=c, linewidth=1.8)

        # label at the end
        ax.text(
            d["MktingWeek"].max() + 0.3,
            series.iloc[-1],
            str(y),
            color=c,
            fontsize=8,
            va="center"
        )

    xmax = int(max(52, weekly["MktingWeek"].max()))
    ax.set_xlim(0.5, xmax + 2)

    ax.set_title(title, fontsize=11)
    ax.set_ylabel(unit_k)
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    # month labels (same logic you already use)
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    ordered = months[my_start_month-1:] + months[:my_start_month-1]
    weeks = np.arange(1, xmax + 1)
    month_labels = [ordered[min((w - 1)//4, 11)] for w in weeks]
    ax.set_xticks(weeks[::4])
    ax.set_xticklabels(month_labels[::4], fontsize=8)

    fig.tight_layout()
    return fig
