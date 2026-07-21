import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

# Optional ML Library Guards
try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION & INITIALIZATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="MINION Institutional Multi-TF Alpha Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st_autorefresh(interval=15000, key="minion_institutional_refresh")

st.markdown("""
<style>
    .stApp { background-color: #07090e; color: #e1e6ed; }
    div[data-testid="stSidebar"] { background-color: #11141d; }
    .minion-header {
        background: linear-gradient(135deg, #1b263b 0%, #0d1117 100%);
        border: 1px solid #00ffcc;
        border-radius: 12px;
        padding: 18px;
        text-align: center;
        margin-bottom: 15px;
        box-shadow: 0 0 25px rgba(0, 255, 204, 0.12);
    }
    .minion-title {
        color: #00ffcc;
        font-size: 26px;
        font-weight: 800;
        letter-spacing: 2px;
        margin: 0;
        font-family: 'Courier New', monospace;
    }
    .minion-subtitle {
        color: #8892b0;
        font-size: 13px;
        margin-top: 4px;
    }
</style>
""", unsafe_allow_html=True)

if "master_history" not in st.session_state:
    st.session_state.master_history = []
if "last_signal_id" not in st.session_state:
    st.session_state.last_signal_id = None

# ---------------------------------------------------------
# 2. BRANDING & CLOCK HEADER
# ---------------------------------------------------------
st.markdown("""
<div class="minion-header">
    <div class="minion-title">⚡ MINION INSTITUTIONAL SCALP & HOLD ENGINE ⚡</div>
    <div class="minion-subtitle">Multi-TF Alignment • Live Twelve Data Feed • Dynamic Scoring • State Guard</div>
</div>
""", unsafe_allow_html=True)

clock_html = """
<div style="background-color: #10141d; border: 1px solid #1f2838; padding: 8px 12px; border-radius: 6px; text-align: center; margin-bottom: 12px;">
    <span style="color: #777; font-size: 12px; font-weight: bold; font-family: monospace;">SYSTEM TICK:</span>
    <span id="live_clock" style="color: #00ffcc; font-size: 15px; font-weight: bold; font-family: monospace; margin-left: 8px;">--:--:--</span>
</div>
<script>
function updateClock() {
    const now = new Date();
    const optionsEAT = { timeZone: 'Africa/Nairobi', hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' };
    document.getElementById("live_clock").innerText = new Intl.DateTimeFormat('en-GB', optionsEAT).format(now) + " EAT";
}
setInterval(updateClock, 1000);
updateClock();
</script>
"""
components.html(clock_html, height=45)

# ---------------------------------------------------------
# 3. SIDEBAR CONTROLS
# ---------------------------------------------------------
st.sidebar.header("🔑 Data Feed")
api_key = st.sidebar.text_input("Twelve Data API Key", type="password")

st.sidebar.header("🎯 Scalp & Hold Horizon")
execution_mode = st.sidebar.selectbox(
    "Select Strategy Horizon",
    [
        "1-Minute Micro Scalp (1m Hold)",
        "5-Minute Fast Scalp (5m Hold)",
        "15-Minute Scalp Trend (15m Hold)",
        "30-Minute Intraday Hold (30m Hold)"
    ]
)

selected_asset = st.sidebar.selectbox(
    "Market Asset Pair",
    ["Gold (Spot XAU/USD)", "EUR/USD", "GBP/USD"]
)

# Twelve Data symbols + TradingView symbols
asset_map = {
    "Gold (Spot XAU/USD)": {"td": "XAU/USD", "tv": "OANDA:XAUUSD", "dec": 2},
    "EUR/USD": {"td": "EUR/USD", "tv": "FX:EURUSD", "dec": 4},
    "GBP/USD": {"td": "GBP/USD", "tv": "FX:GBPUSD", "dec": 4}
}
curr_info = asset_map[selected_asset]

if "1-Minute" in execution_mode:
    interval, max_hold, td_interval = "1m", 1, "1min"
elif "5-Minute" in execution_mode:
    interval, max_hold, td_interval = "5m", 5, "5min"
elif "15-Minute" in execution_mode:
    interval, max_hold, td_interval = "15m", 15, "15min"
else:
    interval, max_hold, td_interval = "30m", 30, "30min"

min_score_threshold = st.sidebar.slider("Min Component Score Threshold (/100)", 50, 90, 68)

if not api_key:
    st.warning("👈 Enter your Twelve Data API key in the sidebar to start receiving live data.")
    st.stop()

# ---------------------------------------------------------
# 4. LIVE DATA ENGINE (Twelve Data)
# ---------------------------------------------------------
@st.cache_data(ttl=15, show_spinner=False)
def fetch_live_market_data(symbol, td_interval, key):
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": td_interval,
        "outputsize": 150,
        "apikey": key,
        "timezone": "UTC"
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        payload = resp.json()
    except Exception as e:
        return None, f"Network error contacting Twelve Data: {e}"

    if payload.get("status") == "error" or "values" not in payload:
        return None, payload.get("message", "Unknown error from Twelve Data (check symbol/plan limits).")

    df = pd.DataFrame(payload["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime").sort_index()
    df = df.rename(columns={
        "open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"
    })
    for c in ["Open", "High", "Low", "Close"]:
        df[c] = df[c].astype(float)
    df["Volume"] = df["Volume"].astype(float) if "Volume" in df.columns else 0.0

    return df[["Open", "High", "Low", "Close", "Volume"]], None

with st.spinner("Syncing data with live market feeds..."):
    raw_df, fetch_error = fetch_live_market_data(curr_info["td"], td_interval, api_key)

if
