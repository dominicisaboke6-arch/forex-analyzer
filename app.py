import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import pytz

# Page configuration
st.set_page_config(
    page_title="Forex & Gold Live EAT Scalper",
    layout="wide"
)

# Auto-refresh app every 5 seconds for fast real-time updates
st_autorefresh(interval=5000, key="eat_refresh")

# Timezone Handling for East Africa Time (EAT)
eat_tz = pytz.timezone("Africa/Nairobi")
eat_now = datetime.now(eat_tz)
formatted_eat_time = eat_now.strftime("%Y-%m-%d %H:%M:%S")

st.title("⚡ Forex & Gold Real-Time Scalper")
st.caption(f"🕒 **Current East Africa Time (EAT):** `{formatted_eat_time} EAT`")

# Updated instrument definitions mapped directly to SPOT Forex/Gold prices
instruments = {
    "Gold (Spot XAU/USD)": {"symbol": "XAUUSD=X", "decimals": 2},
    "EUR/USD": {"symbol": "EURUSD=X", "decimals": 4},
    "GBP/USD": {"symbol": "GBPUSD=X", "decimals": 4},
    "USD/JPY": {"symbol": "JPY=X", "decimals": 2}
}

selected = st.selectbox("Choose market", list(instruments.keys()))
symbol = instruments[selected]["symbol"]
decimals = instruments[selected]["decimals"]

# Timeframes
interval = st.selectbox(
    "Candle timeframe",
    ["1m", "5m", "15m", "1h", "1d"],
    index=0  # Default to 1m for scalping
)

# Determine period based on timeframe limits
period_map = {
    "1m": "1d",
    "5m": "5d",
    "15m": "1mo",
    "1h": "1mo",
    "1d": "1y"
}
period = period_map[interval]

# Fetch market data
data = yf.download(
    symbol,
    period=period,
    interval=interval,
    auto_adjust=False,
    progress=False
)

if data.empty:
    st.error("Market data currently unavailable or the market is closed.")
    st.stop()

if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)

data = data.dropna()

# Convert Index to East Africa Time (EAT) for chart alignment
if data.index.tz is None:
    data.index = data.index.tz_localize("UTC").tz_convert(eat_tz)
else:
    data.index = data.index.tz_convert(eat_tz)

# -----------------------------
# INDICATORS (EMA & RSI)
# -----------------------------
data["EMA_9"] = data["Close"].ewm(span=9, adjust=False).mean()
data["EMA_20"] = data["Close"].ewm(span=20, adjust=False).mean()
data["EMA_50"] = data["Close"].ewm(span=50, adjust=False).mean()

# RSI (Standard Wilder's)
delta = data["Close"].diff()
gain = delta.where(delta > 0, 0)
loss = -delta.where(delta < 0, 0)
avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
rs = avg_gain / avg_loss
data["RSI"] = 100 - (100 / (1 + rs))

# -----------------------------
# SCALPING PREDICTOR
# -----------------------------
latest = data.iloc[-1]
price = float(latest["Close"])
ema9 = float(latest["EMA_9"])
ema20 = float(latest["EMA_20"])
ema50 = float(latest["EMA_50"])
rsi = float(latest["RSI"])

# Signal Generation
scalp_signal = "NEUTRAL ⚪"
scalp_reason = "Waiting for moving averages alignment."

if ema9 > ema20 and ema20 > ema50 and rsi > 50 and rsi < 70:
    scalp_signal = "SCALP BUY 🚀"
    scalp_reason = "Bullish Stack (EMA 9 > 20 > 50) & Strong RSI."
elif ema9 < ema20 and ema20 < ema50 and rsi < 50 and rsi > 30:
    scalp_signal = "SCALP SELL 📉"
    scalp_reason = "Bearish Stack (EMA 9 < 20 < 50) & Weakening RSI."
elif rsi >= 70:
    scalp_signal = "OVERBOUGHT ⚠️"
    scalp_reason = "RSI > 70. Watch out for a pull back down."
elif rsi <= 30:
    scalp_signal = "OVERSOLD ⚠️"
    scalp_reason = "RSI < 30. Watch out for a bounce back up."

# Metric dashboard
col1, col2, col3, col4 = st.columns(4)
col1.metric("Live Spot Price", f"{price:.{decimals}f}")
col2.metric("RSI (14)", f"{rsi:.1f}")
col3.metric("Scalp Signal", scalp_signal)
col4.metric("Timeframe", interval)

st.info(f"**Scalp Insight:** {scalp_reason}")
st.divider()

# -----------------------------
# CANDLESTICK CHART (EAT STAMPED)
# -----------------------------
st.subheader("Real-Time Candlestick Chart (EAT Timezone)")

fig = go.Figure()

fig.add_trace(
    go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='Price'
    )
)

fig.add_trace(go.Scatter(x=data.index, y=data['EMA_9'], line=dict(color='yellow', width=1), name='EMA 9'))
fig.add_trace(go.Scatter(x=data.index, y=data['EMA_20'], line=dict(color='orange', width=1.5), name='EMA 20'))
fig.add_trace(go.Scatter(x=data.index, y=data['EMA_50'], line=dict(color='cyan', width=1.5), name='EMA 50'))

fig.update_layout(
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    height=550,
    margin=dict(l=10, r=10, t=20, b=10)
)

st.plotly_chart(fig, use_container_width=True)

with st.expander("View Recent EAT Scalp Data"):
    st.dataframe(data.tail(15)[["Open", "High", "Low", "Close", "EMA_9", "EMA_20", "RSI"]])
