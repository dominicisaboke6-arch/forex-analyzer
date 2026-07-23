import streamlit as st
import pandas as pd
import requests

# ==========================================
# 1. DASHBOARD CONFIG & SIDEBAR SETTINGS
# ==========================================
st.set_page_config(
    page_title="Institutional Multi-TF Alpha Engine", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

st.sidebar.title("🔑 OANDA Connection Portal")
OANDA_API_TOKEN = st.sidebar.text_input("API Access Token", type="password")
OANDA_ACCOUNT_ID = st.sidebar.text_input("Account ID")
ENVIRONMENT = st.sidebar.selectbox("Account Environment", ["practice", "live"])

# Configure API base URL according to selected environment
BASE_URL = "https://api-fxpractice.oanda.com" if ENVIRONMENT == "practice" else "https://api-fxtrade.oanda.com"

HEADERS = {
    "Authorization": f"Bearer {OANDA_API_TOKEN}",
    "Content-Type": "application/json"
}

# ==========================================
# 2. INDICATOR CALCULATION ENGINE
# ==========================================
def apply_technical_indicators(df):
    """Computes EMA and ATR metrics for strategy evaluation."""
    if len(df) < 20:
        return df

    # Exponential Moving Averages
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()

    # Average True Range (ATR 14)
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR_14'] = tr.rolling(14).mean()

    return df

# ==========================================
# 3. DIRECT OANDA DATA STREAM ENGINE
# ==========================================
@st.cache_data(ttl=3, show_spinner=False)
def fetch_oanda_candles(instrument="XAU_USD", granularity="M5", count=100):
    """Fetches real-time candlestick data directly from OANDA endpoints."""
    if not OANDA_API_TOKEN or not OANDA_ACCOUNT_ID:
        return None, "Please provide valid OANDA credentials in the sidebar."

    url = f"{BASE_URL}/v3/instruments/{instrument}/candles"
    params = {
        "granularity": granularity,
        "count": count,
        "price": "M"  # Midpoint prices
    }

    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        data = response.json()

        if response.status_code != 200:
            err = data.get("errorMessage", "Failed to communicate with OANDA API.")
            return None, f"OANDA Error: {err}"

        candles = data.get("candles", [])
        if not candles:
            return None, "No candle data returned for this instrument."

        parsed_data = []
        for c in candles:
            parsed_data.append({
                "Timestamp": pd.to_datetime(c["time"]),
                "Open": float(c["mid"]["o"]),
                "High": float(c["mid"]["h"]),
                "Low": float(c["mid"]["l"]),
                "Close": float(c["mid"]["c"]),
                "Volume": int(c["volume"])
            })

        df = pd.DataFrame(parsed_data)
        df.set_index("Timestamp", inplace=True)
        df = apply_technical_indicators(df)
        return df, None

    except Exception as e:
        return None, f"Connection Exception: {str(e)}"

# ==========================================
# 4. DIRECT OANDA EXECUTION ENGINE
# ==========================================
def execute_oanda_order(instrument="XAU_USD", units=1, stop_loss=None, take_profit=None):
    """Submits direct market orders to OANDA without intermediate third parties."""
    if not OANDA_API_TOKEN or not OANDA_ACCOUNT_ID:
        return False, "Missing account credentials."

    url = f"{BASE_URL}/v3/accounts/{OANDA_ACCOUNT_ID}/orders"

    order_payload = {
        "order": {
            "units": str(units),
            "instrument": instrument,
            "timeInForce": "FOK",  # Fill or Kill
            "type": "MARKET",
            "positionFill": "DEFAULT"
        }
    }

    if stop_loss:
        order_payload["order"]["stopLossOnFill"] = {"price": f"{stop_loss:.2f}"}
    if take_profit:
        order_payload["order"]["takeProfitOnFill"] = {"price": f"{take_profit:.2f}"}

    try:
        response = requests.post(url, headers=HEADERS, json=order_payload, timeout=10)
        res_data = response.json()

        if response.status_code in [200, 201]:
            trans = res_data.get("orderFillTransaction") or res_data.get("orderCreateTransaction")
            return True, f"Order Filled! Transaction ID: {trans.get('id')}"
        else:
            return False, f"Execution Refused: {res_data.get('errorMessage', response.text)}"

    except Exception as e:
        return False, f"Order Failure: {str(e)}"

# ==========================================
# 5. STREAMLIT UI & CONTROL DASHBOARD
# ==========================================
st.title("⚡ Institutional Multi-TF Alpha Engine")

# Parameter Control Row
c1, c2, c3, c4 = st.columns(4)
with c1:
    symbol = st.selectbox("Asset Pair", ["XAU_USD", "EUR_USD", "GBP_USD", "USD_JPY"])
with c2:
    timeframe = st.selectbox("Timeframe", ["M1", "M5", "M15", "H1", "H4", "D"], index=1)
with c3:
    trade_units = st.number_input("Position Size (Units)", value=1, step=1)
with c4:
    st.write("")
    st.write("")
    refresh_btn = st.button("🔄 Refresh Market Data", use_container_width=True)

# Fetch Data
df, err = fetch_oanda_candles(instrument=symbol, granularity=timeframe, count=100)

if err:
    st.error(err)
else:
    # Live Price Header Metrics
    latest_close = df["Close"].iloc[-1]
    prev_close = df["Close"].iloc[-2]
    diff = round(latest_close - prev_close, 2)
    latest_atr = df["ATR_14"].iloc[-1] if "ATR_14" in df.columns else 0.0

    m1, m2, m3 = st.columns(3)
    m1.metric(f"Live {symbol} Price", f"${latest_close:,.2f}", delta=f"{diff}")
    m2.metric("ATR (14 Volatility)", f"{latest_atr:.2f}")
    m3.metric("Feed Status", "OANDA v20 Live", delta_color="normal")

    # Interactive Chart View
    st.subheader(f"Market Structure ({symbol} - {timeframe})")
    st.line_chart(df[["Close", "EMA_20", "EMA_50"]].dropna())

    # Raw Data Table Toggle
    with st.expander("📊 View Raw Candle & Indicator Data"):
        st.dataframe(df.tail(20), use_container_width=True)

    # Execution Operations
    st.markdown("---")
    st.subheader("Interactive Execution Desk")
    
    col_buy, col_sell = st.columns(2)

    with col_buy:
        if st.button(f"🚀 BUY / LONG {symbol}", use_container_width=True, type="primary"):
            success, msg = execute_oanda_order(instrument=symbol, units=abs(trade_units))
            if success:
                st.success(msg)
            else:
                st.error(msg)

    with col_sell:
        if st.button(f"🔻 SELL / SHORT {symbol}", use_container_width=True):
            success, msg = execute_oanda_order(instrument=symbol, units=-abs(trade_units))
            if success:
                st.success(msg)
            else:
                st.error(msg)
