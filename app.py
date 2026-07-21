import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import pytz

# Page setup
st.set_page_config(
    page_title="Forex & Gold Real-Time Scalper",
    layout="wide"
)

# Auto-refresh every 15 seconds to update Python signals
st_autorefresh(interval=15000, key="datarefresh")

# Timezone setup for East Africa Time (EAT)
eat_tz = pytz.timezone("Africa/Nairobi")
eat_now = datetime.now(eat_tz)
formatted_eat_time = eat_now.strftime("%Y-%m-%d %H:%M:%S")

st.title("⚡ Real-Time Forex & Gold Scalping Analyzer")
st.caption(f"🕒 **Current Local Time:** `{formatted_eat_time} EAT`")

# Instruments mapping (Python ticker fallback list : TradingView symbol)
instruments = {
    "Gold (Spot XAU/USD)": {
        "yf_tickers": ["GC=F", "XAUUSD=X"],
        "tv_symbol": "OANDA:XAUUSD"
    },
    "EUR/USD": {
        "yf_tickers": ["EURUSD=X"],
        "tv_symbol": "FX:EURUSD"
    },
    "GBP/USD": {
        "yf_tickers": ["GBPUSD=X"],
        "tv_symbol": "FX:GBPUSD"
    },
    "USD/JPY": {
        "yf_tickers": ["JPY=X", "USDJPY=X"],
        "tv_symbol": "FX:USDJPY"
    }
}

col_m, col_t = st.columns([2, 1])
with col_m:
    selected = st.selectbox("Choose Asset", list(instruments.keys()))
with col_t:
    interval = st.selectbox("Signal Timeframe", ["1m", "5m", "15m", "1h"], index=0)

yf_tickers = instruments[selected]["yf_tickers"]
tv_symbol = instruments[selected]["tv_symbol"]

# Map period for Yahoo Finance
period_map = {"1m": "1d", "5m": "5d", "15m": "1mo", "1h": "1mo"}
period = period_map[interval]

# -----------------------------
# FETCH DATA WITH FALLBACK
# -----------------------------
data = pd.DataFrame()
for ticker in yf_tickers:
    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False
        )
        if not df.empty:
            data = df
            break
    except Exception:
        continue

if data.empty:
    st.warning("⚠️ Data syncing... The chart below remains live.")
else:
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data = data.dropna()

    # Convert Index to EAT Timezone
    if data.index.tz is None:
        data.index = data.index.tz_localize("UTC").tz_convert(eat_tz)
    else:
        data.index = data.index.tz_convert(eat_tz)

    # -----------------------------
    # INDICATORS & SCALPER LOGIC
    # -----------------------------
    data["EMA_9"] = data["Close"].ewm(span=9, adjust=False).mean()
    data["EMA_20"] = data["Close"].ewm(span=20, adjust=False).mean()
    data["EMA_50"] = data["Close"].ewm(span=50, adjust=False).mean()

    # RSI Calculation
    delta = data["Close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss
    data["RSI"] = 100 - (100 / (1 + rs))

    # Signal Evaluation
    latest = data.iloc[-1]
    price = float(latest["Close"])
    ema9 = float(latest["EMA_9"])
    ema20 = float(latest["EMA_20"])
    ema50 = float(latest["EMA_50"])
    rsi = float(latest["RSI"])

    scalp_signal = "NEUTRAL ⚪"
    scalp_reason = "Waiting for EMA alignment."

    if ema9 > ema20 and ema20 > ema50 and 50 < rsi < 70:
        scalp_signal = "SCALP BUY 🚀"
        scalp_reason = "Bullish stack (EMA 9 > 20 > 50) + healthy RSI momentum."
    elif ema9 < ema20 and ema20 < ema50 and 30 < rsi < 50:
        scalp_signal = "SCALP SELL 📉"
        scalp_reason = "Bearish stack (EMA 9 < 20 < 50) + weakening RSI momentum."
    elif rsi >= 70:
        scalp_signal = "OVERBOUGHT ⚠️"
        scalp_reason = "RSI >= 70. Watch for potential pullbacks."
    elif rsi <= 30:
        scalp_signal = "OVERSOLD ⚠️"
        scalp_reason = "RSI <= 30. Watch for potential oversold bounces."

    # Top Metrics Bar
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ref Spot Price", f"${price:.2f}")
    m2.metric("RSI (14)", f"{rsi:.1f}")
    m3.metric("Scalp Signal", scalp_signal)
    m4.metric("Timeframe", interval)

    st.info(f"💡 **Scalp Insight:** {scalp_reason}")

st.divider()

# -----------------------------
# TRADINGVIEW LIVE WIDGET
# -----------------------------
st.subheader("📊 Live TradingView Chart")

tv_html = f"""
<div class="tradingview-widget-container" style="height:550px;width:100%">
  <div id="tv_chart" style="height:550px;width:100%"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <script type="text/javascript">
  new TradingView.widget({{
    "autosize": true,
    "symbol": "{tv_symbol}",
    "interval": "1",
    "timezone": "Africa/Nairobi",
    "theme": "dark",
    "style": "1",
    "locale": "en",
    "toolbar_bg": "#f1f3f6",
    "enable_publishing": false,
    "allow_symbol_change": true,
    "container_id": "tv_chart"
  }});
  </script>
</div>
"""
components.html(tv_html, height=560)
