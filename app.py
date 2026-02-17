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
)

st.set_page_config(
    page_title="Horizon | Degree Saturation Prediction and Analysis",
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
    st.title("CGI Competition Degree Value Analysis Tool")
    st.markdown("Compare the investment required for a student's degree against market saturation and projected future demand.")
    st.divider()

    target_year = st.slider("Expected Graduation Year", min_value=2026, max_value=2034, value=2028, step=1)
    st.caption(f"Forecasting supply for {target_year}")
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
    # st.info(f"**CIP Code for Selected Degree:** {selected_cip}")

    st.divider()
    st.caption("Data Sources: data.gov, IPEDS (Completions, 2016-24), BLS (Occupational Projections 2024-2034).")

# --- main app ---

# get metrics for selected degree
degree_row = master_df[master_df['CIP_Code'] == selected_cip].iloc[0]
saturation_index = degree_row['Saturation_Index']
job_growth = degree_row['Job_Growth_Rate']
annual_openings = degree_row['Annual_Openings']

# run prediction model
current_grads = degree_row['Graduates']
future_grads, slope, history_df = predict_future_supply(supply_history, selected_cip, projection_years=target_year - 2024)

sentiment = get_sentiment_blurb(saturation_index, job_growth)

# header
st.title(selected_degree+".")
st.markdown(f"Market Status: **{degree_row['Saturation_Tag']}**")
st.markdown(f"*{sentiment}*")

# row 1: key metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    slope_color = "inverse" if (slope is not None and slope < 0) else "normal"
    verb = "Rose" if slope > 0 else "Fell" if slope < 0 else "Stable"
    arrow = "up" if slope > 0 else "down" if slope < 0 else "off"
    st.metric(
        label = "Current Annual Graduates",
        value = format_number(current_grads),
        delta = f"{verb} by {abs(slope):.0f} this year" if slope is not None else "N/A",
        delta_color=slope_color,
        delta_arrow=f"{arrow}"
    )

with col2:
    st.metric(
        label = f"Projected Annual Graduates ({target_year})",
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
    color = get_saturation_color(saturation_index)
    arrow = "up" if saturation_index >= 1.0 else "down" if saturation_index < 1.0 else "off"

    st.metric(
        label="Saturation Index",
        value=f"{saturation_index:.2f}" if pd.notna(saturation_index) else "N/A",
        delta=f"{degree_row['Saturation_Tag']}",
        delta_color=color,
        delta_arrow=arrow,
        help="Ratio of graduates to job openings. The larger the number, the more difficult the market is considered to enter."
    )

st.divider()

# row 2: visualizations
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("Supply vs. Demand Horizon")
    projection_row = pd.DataFrame({
        'Year': [target_year],
        'Graduates': [future_grads],
        'Type': ['Projected']
    })
    history_df['Type'] = 'Historical'
    chart_data = pd.concat([history_df[['Year', 'Graduates', 'Type']], projection_row])

    line = alt.Chart(chart_data).mark_line(point=True).encode(
        x=alt.X('Year:O', axis=alt.Axis(format='d')),
        y=alt.Y('Graduates', title='Number of Graduates', scale=alt.Scale(type='linear')),
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

    st.altair_chart((line + rule + text).interactive(), width='stretch')

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
            width='stretch',
            height=300
        )
    else:
        st.warning("No direct job mappings found in BLS crosswalk.")

st.divider()

# row 3: prescriptive engine
if saturation_index > 1.2:
    st.error(f"{selected_degree} is currently oversaturated (Index: {saturation_index:.2f}).")
    st.markdown("### Alternatives with Lower Saturation")
    st.markdown(f"Consider these related majors in **{get_cip_family(selected_cip)}** that have better market ratios:")
    
    recommendations = get_alternatives(selected_cip, master_df)

    if not recommendations.empty:
        rec_cols = st.columns(3)
        for i, (index, row) in enumerate(recommendations.iterrows()):
            # Predict future graduates for this alternative
            alternative_future_grads, _, _ = predict_future_supply(supply_history, row['CIP_Code'], projection_years=target_year - 2024)
            
            col = rec_cols[i % 3]
            with col:
                with st.container(border=True):
                    st.subheader(row['CIP_Title'])
                    st.metric(
                        "Saturation Index", 
                        f"{row['Saturation_Index']:.2f}", 
                        delta="Alternative", 
                        delta_color="normal",
                        delta_arrow="off",
                        help="Though these markets may also be saturated, they are less so than the current selection."
                    )
                    st.write(f"**Openings:** {format_number(row['Annual_Openings'])}")
                    st.write(f"**Grads ({target_year}):** {format_number(alternative_future_grads)}")
    else:
        st.info("No direct pivots found in this specific family. Consider looking at broader adjacent fields.")

elif pd.isna(saturation_index):
    st.warning("Insufficient data to calculate saturation (Likely 0 recorded job openings).")

else:
    st.success(f"{selected_degree} has a healthy supply/demand ratio.")
    st.markdown("You are entering a market that needs your skills. Focus on internships to secure your spot.")

st.divider()
st.caption("Note: This is an educational and research tool. Always consider multiple factors when making educational and career decisions.")