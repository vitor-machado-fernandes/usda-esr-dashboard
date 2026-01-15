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

    title = ("US Cotton Sales (running bales) - Week Ending {pd.to_datetime(week_ending).date()}."    )

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
    last_week[["countryDescription", "accumulatedExports", "outstandingSales"]]
    .sort_values("accumulatedExports", ascending=False)
    .head(20)                      # 👈 top 20
    .sort_values("accumulatedExports")  # 👈 re-sort for barh
)

    country = df["countryDescription"]
    shipped = df["accumulatedExports"] / 1_000  # thousands of bales
    outst = df["outstandingSales"] / 1_000

    fig, ax = plt.subplots(figsize=(6, 5))

    p1 = ax.barh(country, shipped, color="#588157")
    p2 = ax.barh(country, outst, left=shipped, color="#a3b18a")

    ax.legend((p1[0], p2[0]), ("Shipments", "Outstanding"))
    ax.set_xlabel("Thousands of Bales")
    #ax.set_title("US Cotton Commitments per Destination")
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(lambda x, _: f"{x:,.0f}"))

    return fig


def seasonal_commitments_plot(df_totals):
    data = df_totals[["weekEndingDate", "accumulatedExports", "outstandingSales"]]

    weekly = (
        data.groupby("weekEndingDate")[["accumulatedExports", "outstandingSales"]]
        .sum()
        .reset_index()
    )

    weekly["MY"] = (
        weekly["weekEndingDate"].dt.year
        + (
            (weekly["weekEndingDate"].dt.month > 8)
            | (
                (weekly["weekEndingDate"].dt.month == 8)
                & (weekly["weekEndingDate"].dt.day >= 6)
            )
        ).astype(int)
    )

    weekly = weekly.sort_values(["MY", "weekEndingDate"])
    weekly["MktingWeek"] = weekly.groupby("MY").cumcount() + 1

    # Current MY
    CMY = datetime.today().year if datetime.today().month < 8 else datetime.today().year + 1
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

    ax.set_xlim(0.5, 50)
    #ax.set_ylim(0, 20_000_000)

    #ax.set_title("Cumulative Commitments: CMY vs 5 previous years", fontsize=15, fontweight="bold")
    ax.set_ylabel("Thousand Bales")
    ax.legend()

    ax.yaxis.set_major_formatter(
        mtick.FuncFormatter(lambda x, _: f"{x/1e3:,.0f}")
    )

    # --- X axis as months ---
    week_to_month = {
        1:'Aug',2:'Aug',3:'Aug',4:'Aug',
        5:'Sep',6:'Sep',7:'Sep',8:'Sep',
        9:'Oct',10:'Oct',11:'Oct',12:'Oct',
        13:'Nov',14:'Nov',15:'Nov',16:'Nov',
        17:'Dec',18:'Dec',19:'Dec',20:'Dec',
        21:'Jan',22:'Jan',23:'Jan',24:'Jan',
        25:'Feb',26:'Feb',27:'Feb',28:'Feb',
        29:'Mar',30:'Mar',31:'Mar',32:'Mar',
        33:'Apr',34:'Apr',35:'Apr',36:'Apr',
        37:'May',38:'May',39:'May',40:'May',
        41:'Jun',42:'Jun',43:'Jun',44:'Jun',
        45:'Jul',46:'Jul',47:'Jul',48:'Jul',
        49:'Jul',50:'Jul',51:'Jul',52:'Jul'
    }

    weeks = np.arange(1, 53)
    month_labels = [week_to_month[w] for w in weeks]

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