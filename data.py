import pandas as pd
import streamlit as st
import requests
from pathlib import Path

# Local development
#PARQUET_PATH = Path("data/rl_properties.parquet")

# Streamlit Cloud — use this instead
PARQUET_PATH = Path("/tmp/rl_properties.parquet")

OPENFEMA_URL = "https://www.fema.gov/api/open/v1/NfipMultipleLossProperties"
PAGE_SIZE = 10_000

BOOL_COLS = ['nfipRl', 'nfipSrl', 'fmaRl', 'fmaSrl',
             'insuredIndicator', 'mitigatedIndicator']


def fetch_and_cache():
    """
    Pages through the OpenFEMA NfipMultipleLossProperties endpoint
    and saves everything to parquet. Safe to re-run — overwrites the cache.
    """
    PARQUET_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    all_records = []
    skip = 0

    # First request: also grab the total record count from metadata
    params = {
        "$top":     PAGE_SIZE,
        "$skip":    0,
        "$inlinecount": "allpages",
        "$format":  "json",
    }
    resp = requests.get(OPENFEMA_URL, params=params, timeout=60)
    resp.raise_for_status()
    payload = resp.json()

    total = int(payload.get("metadata", {}).get("count", 0))
    all_records.extend(payload.get("NfipMultipleLossProperties", []))
    skip += PAGE_SIZE

    # Page through the rest
    while skip < total:
        params = {
            "$top":    PAGE_SIZE,
            "$skip":   skip,
            "$format": "json",
        }
        resp = requests.get(OPENFEMA_URL, params=params, timeout=60)
        resp.raise_for_status()
        batch = resp.json().get("NfipMultipleLossProperties", [])
        if not batch:
            break
        all_records.extend(batch)
        skip += PAGE_SIZE

    df = pd.DataFrame(all_records)

    # Normalize booleans
    for col in BOOL_COLS:
        if col in df.columns:
            df[col] = df[col].astype(bool)

    # Normalize numeric columns that sometimes come back as strings
    for col in ['totalLosses', 'totalPayments']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    df.to_parquet(PARQUET_PATH, index=False)
    return df


@st.cache_data
def load_data():
    """
    Returns the cached parquet if it exists; otherwise fetches from OpenFEMA first.
    The @st.cache_data decorator means this only runs once per Streamlit session.
    """
    if not PARQUET_PATH.exists():
        st.info("No local cache found — fetching from OpenFEMA (~60–90 seconds)...")
        df = fetch_and_cache()
        st.success(f"Fetched {len(df):,} properties and saved to cache.")
    else:
        df = pd.read_parquet(PARQUET_PATH)
        for col in BOOL_COLS:
            if col in df.columns:
                df[col] = df[col].astype(bool)

    return df


def get_states(df):
    return sorted(df['stateAbbreviation'].dropna().unique())


def get_counties(df, state):
    return sorted(
        df[df['stateAbbreviation'] == state]['county']
        .dropna().unique()
    )


def filter_data(df, state, county):
    mask = (
        (df['stateAbbreviation'] == state) &
        (df['county'] == county)
    )
    return df[mask].copy()


def summarize(df):
    return {
        'total_properties': len(df),
        'nfip_rl':          int(df['nfipRl'].sum()),
        'nfip_srl':         int(df['nfipSrl'].sum()),
        'mitigated':        int(df['mitigatedIndicator'].sum()),
        'still_insured':    int(df['insuredIndicator'].sum()),
        'total_losses':     int(df['totalLosses'].sum()),
    }