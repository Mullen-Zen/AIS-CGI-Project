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
#todo: sidebar and navigation

# --- main app ---
#todo: main app

# row 1: key metrics
#todo: metrics

# row 2: visualizations
#todo: visualizations

# row 3: prescriptive engine
#todo: engine