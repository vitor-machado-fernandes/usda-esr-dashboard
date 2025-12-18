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





