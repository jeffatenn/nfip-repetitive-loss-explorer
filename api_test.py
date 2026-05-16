import requests
import pandas as pd
import time

BASE_RL = "https://www.fema.gov/api/open/v1/NfipMultipleLossProperties"

FIELDS = (
    "state,stateAbbreviation,county,fipsCountyCode,"
    "reportedCity,zipCode,latitude,longitude,"
    "floodZone,occupancyType,totalLosses,"
    "nfipRl,nfipSrl,fmaRl,fmaSrl,"
    "insuredIndicator,mitigatedIndicator,"
    "mostRecentDateofLoss,originalConstructionDate"
)

records = []
skip = 0
page_size = 10000
total = 240000
pages = total // page_size
start_time = time.time()

print("=" * 60)
print("Fetching FEMA NfipMultipleLossProperties")
print(f"Target: {total:,} records in {pages} pages of {page_size:,}")
print("=" * 60)

while skip < total:
    page_num = (skip // page_size) + 1
    url = (
        BASE_RL
        + f"?$top={page_size}"
        + f"&$skip={skip}"
        + f"&$select={FIELDS}"
        + "&$format=json"
    )

    try:
        r = requests.get(url, timeout=60)
        batch = r.json()['NfipMultipleLossProperties']
        records.extend(batch)
        skip += page_size

        elapsed = time.time() - start_time
        pct = min(len(records) / total * 100, 100)
        bar = "#" * int(pct / 5) + "-" * (20 - int(pct / 5))
        eta = (elapsed / len(records)) * (total - len(records)) if records else 0

        print(
            f"  Page {page_num:>2}/{pages} "
            f"[{bar}] {pct:5.1f}% "
            f"| {len(records):>7,} records "
            f"| elapsed {elapsed:5.1f}s "
            f"| ETA {eta:5.1f}s"
        )

    except Exception as e:
        print(f"  Page {page_num} FAILED: {e} — retrying in 5s...")
        time.sleep(5)
        continue

    time.sleep(0.5)

df = pd.DataFrame(records)
elapsed_total = time.time() - start_time

print()
print("=" * 60)
print(f"Done in {elapsed_total:.1f}s")
print(f"Total rows loaded:  {len(df):,}")
print(f"Memory usage:       {df.memory_usage(deep=True).sum() / 1e6:.1f} MB")
print()
print(f"nfipRl unique:        {df['nfipRl'].unique()}")
print(f"nfipSrl unique:       {df['nfipSrl'].unique()}")
print(f"mitigatedIndicator:   {df['mitigatedIndicator'].unique()}")
print(f"insuredIndicator:     {df['insuredIndicator'].unique()}")
print()
print("Top 5 states by RL count:")
print(df[df['nfipRl'] == True]['state'].value_counts().head())

df.to_parquet('data/rl_properties.parquet', index=False)
print()
print("Saved to data/rl_properties.parquet")
print("=" * 60)