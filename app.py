import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# Page setup
st.set_page_config(
    page_title="Forex & Gold Market Scalper",
    layout="wide"
)

# Auto-refresh app every 15 seconds for near real-time data
st_autorefresh(interval=15000, key="datarefresh")

st.title("⚡ Forex & Gold Real-Time Scalping Analyzer")

# Instruments mapping to symbols and decimal precision
instruments = {
    "Gold (XAU/USD)": {"symbol": "GC=F", "decimals": 2},
    "EUR/USD": {"symbol": "EURUSD=X", "decimals": 4},
    "GBP/USD": {"symbol": "GBPUSD=X", "decimals": 4},
    "USD/JPY": {"symbol": "JPY=X", "decimals": 2}
}

selected = st.selectbox("Choose market", list(instruments.keys()))
symbol = instruments[selected]["symbol"]
decimals = instruments[selected]["decimals"]

# Timeframes including Scalping options (15m, 5m, 1m)
interval = st.selectbox(
    "Candle timeframe",
    ["1m", "5m", "15m", "1h", "1d"],
    index=2  # Default to 15m
)

# Set period limits based on Yahoo Finance intraday constraints
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
    st.error("No market data found. The market might be closed or data unavailable.")
    st.stop()

if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)

data = data.dropna()

# -----------------------------
# INDICATORS (EMAs & RSI)
# -----------------------------
data["EMA_9"] = data["Close"].ewm(span=9, adjust=False).mean()
data["EMA_20"] = data["Close"].ewm(span=20, adjust=False).mean()
data["EMA_50"] = data["Close"].ewm(span=50, adjust=False).mean()

# Fast RSI
delta = data["Close"].diff()
gain = delta.where(delta > 0, 0)
loss = -delta.where(delta < 0, 0)
avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
rs = avg_gain / avg_loss
data["RSI"] = 100 - (100 / (1 + rs))

# ATR
data["High-Low"] = data["High"] - data["Low"]
data["High-Close"] = abs(data["High"] - data["Close"].shift())
data["Low-Close"] = abs(data["Low"] - data["Close"].shift())
data["TR"] = data[["High-Low", "High-Close", "Low-Close"]].max(axis=1)
data["ATR"] = data["TR"].ewm(alpha=1/14, adjust=False).mean()

# -----------------------------
# SCALPING PREDICTOR LOGIC
# -----------------------------
latest = data.iloc[-1]
price = float(latest["Close"])
ema9 = float(latest["EMA_9"])
ema20 = float(latest["EMA_20"])
ema50 = float(latest["EMA_50"])
rsi = float(latest["RSI"])

# Scalper Trigger Conditions (Momentum Crossover Strategy)
scalp_signal = "NEUTRAL ⚪"
scalp_reason = "Waiting for alignment."

if ema9 > ema20 and ema20 > ema50 and rsi > 50 and rsi < 70:
    scalp_signal = "SCALP BUY 🚀"
    scalp_reason = "Bullish momentum stack (EMA 9 > 20 > 50) & strong RSI health."
elif ema9 < ema20 and ema20 < ema50 and rsi < 50 and rsi > 30:
    scalp_signal = "SCALP SELL 📉"
    scalp_reason = "Bearish momentum stack (EMA 9 < 20 < 50) & weakening RSI."
elif rsi >= 70:
    scalp_signal = "OVERBOUGHT ⚠️"
    scalp_reason = "RSI is above 70. Look out for quick mean-reversion pullbacks."
elif rsi <= 30:
    scalp_signal = "OVERSOLD ⚠️"
    scalp_reason = "RSI is below 30. Potential oversold bounce expected."

# Metrics Bar
col1, col2, col3, col4 = st.columns(4)
col1.metric("Current Price", f"{price:.{decimals}f}")
col2.metric("RSI (14)", f"{rsi:.1f}")
col3.metric("Scalp Signal", scalp_signal)
col4.metric("Timeframe", interval)

st.info(f"**Scalp Insight:** {scalp_reason}")
st.divider()

# -----------------------------
# REAL-TIME CANDLESTICK CHART
# -----------------------------
st.subheader("Interactive Real-Time Chart")

fig = go.Figure()

# Add Candlesticks
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

# Add EMA Overlays
fig.add_trace(go.Scatter(x=data.index, y=data['EMA_9'], line=dict(color='yellow', width=1), name='EMA 9'))
fig.add_trace(go.Scatter(x=data.index, y=data['EMA_20'], line=dict(color='orange', width=1.5), name='EMA 20'))
fig.add_trace(go.Scatter(x=data.index, y=data['EMA_50'], line=dict(color='cyan', width=1.5), name='EMA 50'))

# Dark Theme & Responsive Layout
fig.update_layout(
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    height=550,
    margin=dict(l=10, r=10, t=30, b=10)
)

st.plotly_chart(fig, use_container_width=True)

# Raw Candle Data
with st.expander("View Recent Scalping Data"):
    st.dataframe(data.tail(20)[["Open", "High", "Low", "Close", "EMA_9", "EMA_20", "RSI"]])
