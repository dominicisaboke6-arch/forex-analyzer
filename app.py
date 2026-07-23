import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# ==========================================
# 1. CONFIGURATION & SECRETS MANAGEMENT
# ==========================================
# In production, store these in st.secrets or environment variables
OANDA_API_TOKEN = st.sidebar.text_input("OANDA API Token", type="password")
OANDA_ACCOUNT_ID = st.sidebar.text_input("OANDA Account ID")
ENVIRONMENT = st.sidebar.selectbox("Environment", ["practice", "live"])

# Determine base URL based on environment
if ENVIRONMENT == "practice":
    BASE_URL = f"https://api-fxpractice.oanda.com/v20/accounts/{OANDA_ACCOUNT_ID}"
else:
    BASE_URL = f"https://api-fxtrade.oanda.com/v20/accounts/{OANDA_ACCOUNT_ID}"

HEADERS = {
    "Authorization": f"Bearer {OANDA_API_TOKEN}",
    "Content-Type": "application/json"
}

# ==========================================
# 2. NATIVE OANDA DATA ENGINE
# ==========================================
@st.cache_data(ttl=5, show_spinner=False)
def fetch_oanda_candles(instrument="XAU_USD", granularity="M5", count=100):
    """
    Fetches real-time candlestick data directly from OANDA.
    Granularities: S5, M1, M5, M15, H1, D, etc.
    """
    if not OANDA_API_TOKEN or not OANDA_ACCOUNT_ID:
        return None, "Please provide valid OANDA API credentials in the sidebar."
        
    url = f"https://api-fxpractice.oanda.com/v20/instruments/{instrument}/candles"
    if ENVIRONMENT == "live":
        url = f"https://api-fxtrade.oanda.com/v20/instruments/{instrument}/candles"

    params = {
        "granularity": granularity,
        "count": count,
        "price": "M"  # Midpoint prices
    }

    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        data = response.json()

        if response.status_code != 200:
            return None, f"OANDA Error: {data.get('errorMessage', 'Failed to fetch data')}"

        candles = data.get("candles", [])
        parsed_data = []

        for c in candles:
            if c["complete"]:
                parsed_data.append({
                    "Timestamp": pd.to_datetime(c["time"]),
                    "Open": float(c["mid"]["o"]),
                    "High": float(c["mid"]["h"]),
                    "Low": float(c["mid"]["l"]),
                    "Close": float(c["mid"]["c"]),
                    "Volume": int(c["volume"])
                })

        df = pd.DataFrame(parsed_data)
        if not df.empty:
            df.set_index("Timestamp", inplace=True)
            
        return df, None

    except Exception as e:
        return None, str(e)


# ==========================================
# 3. NATIVE OANDA TRADE EXECUTION ENGINE
# ==========================================
def execute_oanda_order(instrument="XAU_USD", units=1, stop_loss=None, take_profit=None):
    """
    Executes a direct market order on OANDA.
    units: Positive (+1) for BUY/LONG, Negative (-1) for SELL/SHORT.
    """
    if not OANDA_API_TOKEN or not OANDA_ACCOUNT_ID:
        return False, "Missing API credentials."

    url = f"{BASE_URL}/orders"

    order_payload = {
        "order": {
            "units": str(units),
            "instrument": instrument,
            "timeInForce": "FOK",  # Fill or Kill
            "type": "MARKET",
            "positionFill": "DEFAULT"
        }
    }

    # Optional Stop Loss / Take Profit configuration
    if stop_loss:
        order_payload["order"]["stopLossOnFill"] = {"price": f"{stop_loss:.2f}"}
    if take_profit:
        order_payload["order"]["takeProfitOnFill"] = {"price": f"{take_profit:.2f}"}

    try:
        response = requests.post(url, headers=HEADERS, json=order_payload, timeout=10)
        res_data = response.json()

        if response.status_code in [200, 201]:
            trans = res_data.get("orderFillTransaction") or res_data.get("orderCreateTransaction")
            return True, f"Order Executed! Transaction ID: {trans.get('id')}"
        else:
            return False, f"Execution Failed: {res_data.get('errorMessage', response.text)}"

    except Exception as e:
        return False, str(e)


# ==========================================
# 4. STREAMLIT APP INTERFACE
# ==========================================
st.title("⚡ Direct OANDA Alpha Engine")

# Controls
col1, col2, col3 = st.columns(3)
with col1:
    symbol = st.selectbox("Instrument", ["XAU_USD", "EUR_USD", "GBP_USD"])
with col2:
    timeframe = st.selectbox("Timeframe", ["M1", "M5", "M15", "H1"], index=1)
with col3:
    trade_units = st.number_input("Units (Lots/Units)", value=1, step=1)

# Fetch Data Button / Engine Trigger
df, err = fetch_oanda_candles(instrument=symbol, granularity=timeframe, count=50)

if err:
    st.error(err)
else:
    # Display Price Banner
    latest_close = df["Close"].iloc[-1]
    prev_close = df["Close"].iloc[-2]
    delta = round(latest_close - prev_close, 2)
    st.metric(label=f"Live {symbol} Price", value=f"${latest_close:.2f}", delta=delta)

    # Show Candlestick Data Table / Chart
    st.subheader("Price Feed (OANDA)")
    st.line_chart(df["Close"])

    st.markdown("---")
    st.subheader("Manual & Automated Execution Panel")
    
    col_buy, col_sell = st.columns(2)
    
    with col_buy:
        if st.button(f"🚀 BUY {symbol}", use_container_width=True):
            success, msg = execute_oanda_order(instrument=symbol, units=abs(trade_units))
            if success:
                st.success(msg)
            else:
                st.error(msg)
                
    with col_sell:
        if st.button(f"🔻 SELL {symbol}", use_container_width=True):
            success, msg = execute_oanda_order(instrument=symbol, units=-abs(trade_units))
            if success:
                st.success(msg)
            else:
                st.error(msg)
