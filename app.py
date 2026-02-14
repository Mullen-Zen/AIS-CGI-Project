import streamlit as st
import pandas as pd
import altair as alt
import time

from src.data_loader import get_master_dataframe
from src.model import predict_future_supply, get_alternatives, calculate_market_saturation
from src.utils import (
    get_cip_family,
    format_number,
    get_saturation_color,
    get_sentiment_blurb,
    CIP_FAMILY_MAP
)

st.set_page_config(
    page_title="Degree Market Saturation Prediction and Analysis",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
    .stAlert {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- load data to cache ---
@st.cache_data
def load_app_data():
    master_df, history, details = get_master_dataframe()
    master_df = calculate_market_saturation(master_df)
    master_df['CIP_Family'] = master_df['CIP_Code'].apply(get_cip_family)
    return master_df, history, details

try:
    with st.spinner("Loading market data..."):
        master_df, supply_history, detailed_demand = load_app_data()
except Exception as e:
    st.error(f"Critical Error Loading Data: {e}")
    st.stop()

# --- sidebar and navigation ---
with st.sidebar:
    st.title("Degree Market Saruration Analysis")
    st.markdown("Compare the investment required for your degree against market saturation and projected future demand.")
    st.divider()

    # filter family
    family_options = sorted(master_df['CIP_Family'].unique())
    selected_family = st.selectbox("Select Degree Family", options=family_options)

    # filter specific degree
    family_df = master_df[master_df['CIP_Family'] == selected_family].sort_values('CIP_Code')
    degree_options = family_df['CIP_Title'].unique()
    selected_degree = st.selectbox("Select Specific Degree", degree_options)

    # get code for specified name
    selected_cip = family_df[family_df['CIP_Title'] == selected_degree]['CIP_Code'].iloc[0]
    st.info(f"**CIP Code for Selected Degree:** {selected_cip}")

    st.divider()
    st.caption("Data Sources: data.gov, IPEDS (Completions, 2016-24), BLS (Occupational Projections 2024-2034). Analysis by Garrison Mullen.")

# --- main app ---

# get metrics for selected degree
degree_row = master_df[master_df['CIP_Code'] == selected_cip].iloc[0]
saturation_index = degree_row['Saturation_Index']
job_growth = degree_row['Job_Growth_Rate']
annual_openings = degree_row['Annual_Openings']

# run prediction model
current_grads = degree_row['Graduates']
future_grads, slope, history_df = predict_future_supply(supply_history, selected_cip)

# header
st.title(selected_degree)
st.markdown(f"Market Status: **{degree_row['Saturation_Tag']}**")

# row 1: key metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label = "Current Annual Graduates",
        value = format_number(current_grads),
        delta = f"Trending towards {slope:.0f} this year" if slope is not None else "N/A", #TODO: delta color based on slope direction
    )

with col2:
    st.metric(
        label = "Projected Annual Graduates (2028)", #TODO: adjust prediction year as necessary
        value = format_number(future_grads),
        help = "Linear regression forecast based on historical graduation trends (2016-2024)",
    )

with col3:
    st.metric(
        label="Annual Job Openings (avg)",
        value=format_number(annual_openings),
        help = "Average annual job openings for this degree (2024-2034 projection)"
    )

with col4:
    sentiment = get_sentiment_blurb(saturation_index, job_growth)
    color = get_saturation_color(saturation_index)

    st.metric(
        label="Saturation Index",
        value=f"{saturation_index:.2f}" if pd.notna(saturation_index) else "N/A",
        delta=sentiment, # TODO: text wrap or no clip for legibility
        delta_color=color
    )

st.divider()

# row 2: visualizations
c1, c2 = st.columns([2, 1])

# TODO: either apply logarithmic scale to y-axis on chart or across all data, the diff between a 10-grad surplus and a 100-grad surplus is exponential not linear
with c1:
    st.subheader("Supply vs. Demand Horizon")
    projection_row = pd.DataFrame({
        'Year': [2028], #TODO: year?
        'Graduates': [future_grads],
        'Type': ['Projected']
    })
    history_df['Type'] = 'Historical'
    chart_data = pd.concat([history_df[['Year', 'Graduates', 'Type']], projection_row])

    line = alt.Chart(chart_data).mark_line(point=True).encode(
        x=alt.X('Year:O', axis=alt.Axis(format='d')),
        y=alt.Y('Graduates', title='Number of Graduates'),
        color=alt.Color('Type', scale=alt.Scale(domain=['Historical', 'Projected'], range=['#3182bd', '#9ecae1'])),
    )

    rule = alt.Chart(pd.DataFrame({'y': [annual_openings]})).mark_rule(color='#e6550d', strokeDash=[5, 5]).encode(
        y='y',
        size=alt.value(2)
    )

    text = alt.Chart(pd.DataFrame({'y': [annual_openings]})).mark_text(
        align='left', baseline='bottom', dx=5, color='#e6550d'
    ).encode(
        y='y',
        text=alt.value(f"Market Capacity ({int(annual_openings)} jobs/yr)")
    )

    st.altair_chart((line + rule + text).interactive(), use_container_width=True)

    st.caption(sentiment)

with c2:
    st.subheader("Underlying Jobs")
    st.markdown("The selected degree maps to these careers:")

    jobs_mapped = detailed_demand[detailed_demand['CIP_Code'] == selected_cip].copy()
    if not jobs_mapped.empty:
        jobs_mapped = jobs_mapped.sort_values("Annual_Openings", ascending=False)
        
        st.dataframe(
            jobs_mapped[['SOC_Title', 'Annual_Openings']],
            column_config={
                "SOC_Title": "Job Title",
                "Annual_Openings": st.column_config.NumberColumn("Openings", format="%d")
            },
            hide_index=True,
            use_container_width=True,
            height=300
        )
    else:
        st.warning("No direct job mappings found in BLS crosswalk.")

# row 3: prescriptive engine
#todo: engine