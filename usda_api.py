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

        df_year = pd.DataFrame(r.json())
        df_year["MY"] = year

        dfs.append(df_year)

    df = pd.concat(dfs, ignore_index=True)
    df["weekEndingDate"] = pd.to_datetime(df["weekEndingDate"])

    return df


import requests
import pandas as pd


EXPORTS_ID = 88

def get_wasde_export(api_key: str, psd_code: int, year: int) -> float:
    headers = {"X-Api-Key": api_key, "accept": "application/json"}

    def fetch(y):
        url = f"https://api.fas.usda.gov/api/psd/commodity/{psd_code}/country/US/year/{year}"
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        return pd.DataFrame(r.json())

    df = fetch(year)
    if df.empty or "attributeId" not in df.columns:
        df = fetch(year-1)

    if df.empty or "attributeId" not in df.columns:
        raise ValueError(f"No PSD data for {psd_code} in {year} or {year-1}")

    return df.loc[df["attributeId"] == EXPORTS_ID, "value"].iloc[0] * 1000



