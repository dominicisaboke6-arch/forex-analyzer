import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Forex & Gold Market Analyzer",
    layout="wide"
)

st.title("📈 Forex & Gold Market Analyzer")

# Instruments mapping to symbols and their appropriate decimal precision
instruments = {
    "Gold (XAU/USD)": {"symbol": "GC=F", "decimals": 2},
    "EUR/USD": {"symbol": "EURUSD=X", "decimals": 4},
    "GBP/USD": {"symbol": "GBPUSD=X", "decimals": 4},
    "USD/JPY": {"symbol": "JPY=X", "decimals": 2}
}

selected = st.selectbox(
    "Choose market",
    list(instruments.keys())
)

symbol = instruments[selected]["symbol"]
decimals = instruments[selected]["decimals"]

period = st.selectbox(
    "Data period",
    ["1mo", "3mo", "6mo", "1y", "2y"],
    index=1
)

interval = st.selectbox(
    "Candle timeframe",
    ["1h", "1d"],
    index=1
)

# Download candle data
data = yf.download(
    symbol,
    period=period,
    interval=interval,
    auto_adjust=False
)

if data.empty:
    st.error("No market data found.")
    st.stop()

# Fix multi-index columns if needed
if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)

data = data.dropna()

# -----------------------------
# INDICATORS
# -----------------------------

# Moving averages
data["EMA_20"] = data["Close"].ewm(span=20, adjust=False).mean()
data["EMA_50"] = data["Close"].ewm(span=50, adjust=False).mean()

# RSI (Standard Wilder's Smoothing)
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
# CANDLE PATTERN DETECTION
# -----------------------------

def detect_candle_pattern(row):
    candle_body = abs(row["Close"] - row["Open"])
    upper_wick = row["High"] - max(row["Open"], row["Close"])
    lower_wick = min(row["Open"], row["Close"]) - row["Low"]

    # Doji
    if candle_body <= (row["High"] - row["Low"]) * 0.1:
        return "Doji"

    # Bullish candle
    if row["Close"] > row["Open"]:
        if lower_wick > candle_body * 2:
            return "Bullish Pin Bar"
        return "Bullish Candle"

    # Bearish candle
    if row["Close"] < row["Open"]:
        if upper_wick > candle_body * 2:
            return "Bearish Pin Bar"
        return "Bearish Candle"

    return "Neutral"

data["Pattern"] = data.apply(detect_candle_pattern, axis=1)

# -----------------------------
# MARKET ANALYSIS
# -----------------------------

latest = data.iloc[-1]

price = float(latest["Close"])
ema20 = float(latest["EMA_20"])
ema50 = float(latest["EMA_50"])
rsi = float(latest["RSI"])

# Trend
if ema20 > ema50:
    trend = "Bullish"
elif ema20 < ema50:
    trend = "Bearish"
else:
    trend = "Sideways"

# Momentum
if rsi >= 70:
    momentum = "Overbought"
elif rsi <= 30:
    momentum = "Oversold"
else:
    momentum = "Neutral"

# Overall bias
if trend == "Bullish" and rsi < 70:
    bias = "Bullish Bias"
elif trend == "Bearish" and rsi > 30:
    bias = "Bearish Bias"
else:
    bias = "Wait / Mixed Conditions"

# Support & Resistance
support = data["Low"].rolling(20).min().iloc[-1]
resistance = data["High"].rolling(20).max().iloc[-1]

# -----------------------------
# DISPLAY
# -----------------------------

st.subheader(f"{selected} Analysis")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Current Price", f"{price:.{decimals}f}")
col2.metric("Trend", trend)
col3.metric("RSI", f"{rsi:.2f}")
col4.metric("Market Bias", bias)

st.divider()

# Chart
st.subheader("Price Chart")
chart_data = data[["Close", "EMA_20", "EMA_50"]].dropna()
st.line_chart(chart_data)

# Analysis table
st.subheader("Technical Analysis")

analysis = {
    "Trend": trend,
    "Momentum": momentum,
    "Latest Candle": latest["Pattern"],
    "Support": f"{support:.{decimals}f}",
    "Resistance": f"{resistance:.{decimals}f}",
    "ATR Volatility": f"{latest['ATR']:.{decimals}f}",
    "RSI": f"{rsi:.2f}"
}

df_analysis = pd.DataFrame(analysis.items(), columns=["Metric", "Value"])
st.dataframe(df_analysis, hide_index=True, use_container_width=True)

# -----------------------------
# SIMPLE TRADE SCENARIOS
# -----------------------------
st.subheader("Market Scenario")

if bias == "Bullish Bias":
    st.success(
        f"""
        **The market is showing bullish conditions.**  
        Price is trading with the 20 EMA above the 50 EMA. 
        A possible bullish scenario would be a pullback toward support around **{support:.{decimals}f}** followed by bullish confirmation.
        
        *This is analysis only, not a guaranteed trade signal.*
        """
    )
elif bias == "Bearish Bias":
    st.error(
        f"""
        **The market is showing bearish conditions.**  
        Price is trading with the 20 EMA below the 50 EMA. 
        A possible bearish scenario would be a retracement toward resistance around **{resistance:.{decimals}f}** followed by bearish confirmation.
        
        *This is analysis only, not a guaranteed trade signal.*
        """
    )
else:
    st.warning("Market conditions are mixed. It may be better to wait for clearer trend confirmation.")

# Raw candle data
with st.expander("View Raw Candle Data"):
    st.dataframe(data.tail(50))
