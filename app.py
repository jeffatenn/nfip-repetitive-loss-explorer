import streamlit as st
from data import load_data, get_states, get_counties, filter_data, summarize
from map_utils import build_map
from streamlit_folium import st_folium

st.set_page_config(
    page_title="NFIP Repetitive Loss Explorer",
    page_icon="🌊",
    layout="wide"
)
st.title("🌊 NFIP Repetitive Loss Explorer")
st.caption(
    "Source: FEMA OpenFEMA NfipMultipleLossProperties v1 | "
    "Public data — not an official federal report"
)

df = load_data()

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")

    # Geography
    st.subheader("Geography")
    state = st.selectbox("State", get_states(df))
    counties = get_counties(df, state)
    county = st.selectbox("County", ["All Counties"] + counties)

    st.divider()

    # Loss filters
    st.subheader("Loss Characteristics")
    min_losses = st.slider(
        "Minimum total losses",
        min_value=2,
        max_value=int(df['totalLosses'].max()),
        value=2,
        step=1,
        help="NFIP defines repetitive loss as 2+ claims — slider starts at 2"
    )

    st.divider()

    # Property type filters
    st.subheader("Property Type")

    # Flood zone multiselect — populated from actual data for the selected state
    state_df = df[df['stateAbbreviation'] == state]
    available_zones = sorted(state_df['floodZone'].dropna().unique())
    selected_zones = st.multiselect(
        "Flood Zone",
        options=available_zones,
        default=[],
        placeholder="All zones",
        help="Leave empty to include all flood zones"
    )

    # Occupancy type multiselect
    available_occ = sorted(df['occupancyType'].dropna().unique())
    selected_occ = st.multiselect(
        "Occupancy Type",
        options=available_occ,
        default=[],
        placeholder="All occupancy types",
        help="Leave empty to include all occupancy types"
    )

    st.divider()

    # Status filters
    st.subheader("Status")
    show_srl_only    = st.checkbox("Severe Repetitive Loss only")
    show_mitigated   = st.checkbox("Mitigated properties only")
    show_still_insured = st.checkbox("Still insured only")


# ── Filter logic ───────────────────────────────────────────────────────────
# Geography
if county == "All Counties":
    filtered = df[df['stateAbbreviation'] == state].copy()
else:
    filtered = filter_data(df, state, county)

# Loss threshold
filtered = filtered[filtered['totalLosses'] >= min_losses]

# Flood zone
if selected_zones:
    filtered = filtered[filtered['floodZone'].isin(selected_zones)]

# Occupancy type
if selected_occ:
    filtered = filtered[filtered['occupancyType'].isin(selected_occ)]

# Status checkboxes
if show_srl_only:
    filtered = filtered[filtered['nfipSrl'] == True]
if show_mitigated:
    filtered = filtered[filtered['mitigatedIndicator'] == True]
if show_still_insured:
    filtered = filtered[filtered['insuredIndicator'] == True]


# ── Metric cards ───────────────────────────────────────────────────────────
label = "All Counties" if county == "All Counties" else f"{county} County"
st.subheader(f"{label}, {state}")

summary = summarize(filtered)
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total RL Properties",  f"{summary['total_properties']:,}")
c2.metric("NFIP Repetitive Loss", f"{summary['nfip_rl']:,}")
c3.metric("Severe Repetitive Loss", f"{summary['nfip_srl']:,}")
c4.metric("Mitigated",            f"{summary['mitigated']:,}")
c5.metric("Still Insured",        f"{summary['still_insured']:,}")


# ── Map ────────────────────────────────────────────────────────────────────
st.subheader("Property Map")
MAP_LIMIT = 5_000
if len(filtered) == 0:
    st.info("No properties match the current filters.")
elif len(filtered) > MAP_LIMIT:
    st.warning(
        f"{len(filtered):,} properties selected — map limited to {MAP_LIMIT:,} "
        f"for performance. Use filters to narrow the selection, or download the full CSV below."
    )
    m = build_map(filtered.head(MAP_LIMIT))
    st_folium(m, width=900, height=500)
else:
    m = build_map(filtered)
    st_folium(m, width=900, height=500)


# ── Detail table ───────────────────────────────────────────────────────────
st.subheader("Property Detail")
display_cols = [
    'reportedCity', 'zipCode', 'floodZone',
    'occupancyType', 'totalLosses',
    'nfipRl', 'nfipSrl', 'mitigatedIndicator', 'insuredIndicator'
]
# Only show columns that actually exist in the dataframe
display_cols = [c for c in display_cols if c in filtered.columns]

st.dataframe(
    filtered[display_cols].sort_values('totalLosses', ascending=False),
    use_container_width=True,
    hide_index=True
)


# ── CSV download ───────────────────────────────────────────────────────────
csv = filtered.to_csv(index=False).encode('utf-8')
county_label = "all" if county == "All Counties" else county
st.download_button(
    label=f"Download filtered data as CSV ({len(filtered):,} rows)",
    data=csv,
    file_name=f"rl_{state}_{county_label}.csv",
    mime="text/csv"
)