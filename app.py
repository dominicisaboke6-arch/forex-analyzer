import streamlit as st
import pandas as pd
import yfinance as yf

# ==========================================
# 1. STREAMLIT PAGE CONFIG
# ==========================================
st.set_page_config(
    page_title="Multi-TF Alpha Engine (yfinance)", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. INDICATOR ENGINE (EMA & ATR)
# ==========================================
def apply_technical_indicators(df):
    """Computes technical metrics (EMA 20/50, ATR 14) on price data."""
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
# 3. YFINANCE DATA FETCH ENGINE
# ==========================================
@st.cache_data(ttl=15, show_spinner=False)
def fetch_yfinance_data(ticker="GC=F", interval="5m", period="5d"):
    """
    Fetches market prices via Yahoo Finance (No login / API key needed).
    """
    try:
        data = yf.Ticker(ticker)
        df = data.history(period=period, interval=interval)

        if df.empty:
            return None, f"No market data returned for ticker: {ticker}"

        # Clean columns and handle multi-index structure if returned
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        df = apply_technical_indicators(df)
        return df, None

    except Exception as e:
        return None, f"yfinance error: {str(e)}"

# Asset mapping to standard Yahoo Finance symbols
SYMBOL_MAP = {
    "XAU_USD (Gold Spot)": "GC=F",
    "EUR_USD": "EURUSD=X",
    "GBP_USD": "GBPUSD=X",
    "USD_JPY": "JPY=X",
    "S&P 500": "^GSPC",
    "Nasdaq 100": "^IXIC"
}

# Granularity mapping
TIMEFRAME_MAP = {
    "M1 (1 Min)": ("1m", "1d"),
    "M5 (5 Min)": ("5m", "5d"),
    "M15 (15 Min)": ("15m", "1mo"),
    "H1 (1 Hour)": ("60m", "2mo"),
    "D (1 Day)": ("1d", "1y")
}

# ==========================================
# 4. STREAMLIT UI & INTERACTIVE DASHBOARD
# ==========================================
st.title("⚡ Institutional Alpha Engine")

# Parameter Selection Controls
c1, c2, c3, c4 = st.columns(4)

with c1:
    selected_asset = st.selectbox("Asset Pair", list(SYMBOL_MAP.keys()))
    ticker_symbol = SYMBOL_MAP[selected_asset]

with c2:
    selected_tf = st.selectbox("Timeframe", list(TIMEFRAME_MAP.keys()), index=1)
    interval, period = TIMEFRAME_MAP[selected_tf]

with c3:
    position_size = st.number_input("Position Size (Units)", value=1, step=1)

with c4:
    st.write("")
    st.write("")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()

# Fetch Data
df, err = fetch_yfinance_data(ticker=ticker_symbol, interval=interval, period=period)

if err:
    st.error(err)
else:
    # Summary Metrics
    latest_close = df["Close"].iloc[-1]
    prev_close = df["Close"].iloc[-2]
    price_delta = round(latest_close - prev_close, 2)
    latest_atr = df["ATR_14"].iloc[-1] if "ATR_14" in df.columns else 0.0

    m1, m2, m3 = st.columns(3)
    m1.metric(f"Live {selected_asset} Price", f"${latest_close:,.2f}", delta=f"{price_delta}")
    m2.metric("ATR (14 Volatility)", f"{latest_atr:.2f}")
    m3.metric("Feed Status", "yfinance Active", delta_color="normal")

    # Price & Moving Average Line Chart
    st.subheader(f"Price Structure ({selected_asset} - {selected_tf})")
    st.line_chart(df[["Close", "EMA_20", "EMA_50"]].dropna())

    # Raw Data Table
    with st.expander("📊 View Raw Market Data & Indicators"):
        st.dataframe(df.tail(20), use_container_width=True)

    # Simulated Execution Panel
    st.markdown("---")
    st.subheader("Paper Trading Execution Desk")
    
    col_buy, col_sell = st.columns(2)

    with col_buy:
        if st.button(f"🚀 BUY {selected_asset}", use_container_width=True, type="primary"):
            st.success(f"SIMULATED ORDER FILLED: Long {position_size} unit(s) of {selected_asset} at ${latest_close:,.2f}")

    with col_sell:
        if st.button(f"🔻 SELL {selected_asset}", use_container_width=True):
            st.error(f"SIMULATED ORDER FILLED: Short {position_size} unit(s) of {selected_asset} at ${latest_close:,.2f}")
