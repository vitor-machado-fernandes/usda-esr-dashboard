import requests
import pandas as pd


def get_esr_exports(api_key: str, commodity_code: int, start_year: int, end_year: int) -> pd.DataFrame:
    """
    Downloads USDA ESR export data for a commodity across multiple market years
    and returns a single concatenated DataFrame.
    """
    headers = {
        "X-Api-Key": api_key,
        "accept": "application/json"
    }

    dfs = []

    for year in range(start_year, end_year + 1):
        url = (
            "https://api.fas.usda.gov/api/esr/exports/"
            f"commodityCode/{commodity_code}/allCountries/marketYear/{year}"
        )
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        dfs.append(pd.DataFrame(r.json()))

    df = pd.concat(dfs, ignore_index=True)
    df["weekEndingDate"] = pd.to_datetime(df["weekEndingDate"])

    return df


import requests
import pandas as pd

PSD_COTTON = 2631000
PSD_CORN = 0440000
PSD_SOYBEANS = 2222000
PSD_WHEAT = 0410000
PSD_SOYMEAL = 081310
EXPORTS_ID = 88

def get_wasde_export(api_key: str, year: int) -> float:
    headers = {"X-Api-Key": api_key, "accept": "application/json"}
    url = f"https://api.fas.usda.gov/api/psd/commodity/{PSD_COTTON}/country/US/year/{year}"

    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    df = pd.DataFrame(r.json())

    if df.empty:
        r = requests.get(
            f"https://api.fas.usda.gov/api/psd/commodity/{PSD_COTTON}/country/US/year/{year-1}",
            headers=headers,
            timeout=30,
        )
        r.raise_for_status()
        df = pd.DataFrame(r.json())

    return df.loc[df["attributeId"] == EXPORTS_ID, "value"].iloc[0] * 1000



