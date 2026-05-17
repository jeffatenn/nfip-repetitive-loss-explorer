import pandas as pd
import streamlit as st
from pathlib import Path

PARQUET_PATH = Path("data/rl_properties.parquet")

@st.cache_data
def load_data():
    df = pd.read_parquet(PARQUET_PATH)
    # Normalize boolean columns — API returns True/False
    for col in ['nfipRl', 'nfipSrl', 'fmaRl', 'fmaSrl',
                 'insuredIndicator', 'mitigatedIndicator']:
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