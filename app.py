import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

# Page setup - Dark Theme AURUM inspired
st.set_page_config(
    page_title="AURUM - Pro XAU/USD Scanner",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for AURUM-style dark UI
st.markdown("""
<style>
    .stApp { background-color: #0b0e14; color: #e1e6ed; }
    .metric-card { background-color: #151a23; padding: 15px; border-radius: 8px; border: 1px solid #232a3b; }
    .status-badge { padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 12px; display: inline-block; }
    .badge-buy { background-color: #00c853; color: #000; }
    .badge-sell { background-color: #ff1744; color: #fff; }
    .badge-prep { background-color: #ffd600; color: #000; }
    .badge-neutral { background-color: #37474f; color: #fff; }
</style>
""", unsafe_allow_html=True)

# Timezone Handling (EAT / Nairobi)
eat_tz = pytz.timezone("Africa/Nairobi")
utc_now = datetime.now(pytz.utc)
eat_now = utc_now.astimezone(eat_tz)

# ---------------------------------------------------------
# 1. FOREX TRADING SESSIONS ENGINE
# ---------------------------------------------------------
def get_active_sessions(utc_time):
    hour = utc_time.hour
    sessions = []
    if 22 <= hour or hour < 7:
        sessions.append("SYDNEY 🇦🇺")
    if 0 <= hour < 9:
        sessions.append("TOKYO / ASIAN 🇯🇵")
    if 8 <= hour < 17:
        sessions.append("LONDON 🇬🇧")
    if 13 <= hour < 22:
        sessions.append("NEW YORK 🇺🇸")
    return " | ".join(sessions) if sessions else "OFF-PEAK 🌙"

active_sessions_str = get_active_sessions(utc_now)

# Top Banner Header
st.title("⚜️ AURUM - Live Gold & Forex Scanner")
st.caption(f"🕒 **EAT Time:** `{eat_now.strftime('%Y-%m-%d %H:%M:%S')}` | 🌍 **Active Sessions:** `{active_sessions_str}`")

# ---------------------------------------------------------
# 2. CONTROLS & SIDEBAR
# ---------------------------------------------------------
st.sidebar.header("🕹️ Strategy & Market Controls")

trading_mode = st.sidebar.radio("Trading Mode", ["⚡ Scalping (1m - 5m)", "📈 Day Trading (15m - 1h)"])
selected_asset = st.sidebar.selectbox("Asset", ["Gold (Spot XAU/USD)", "EUR/USD", "GBP/USD", "USD/JPY"])

asset_map = {
    "Gold (Spot XAU/USD)": {"yf": ["GC=F", "XAUUSD=X"], "tv": "OANDA:XAUUSD", "dec": 2},
    "EUR/USD": {"yf": ["EURUSD=X"], "tv": "FX:EURUSD", "dec": 4},
    "GBP/USD": {"yf": ["GBPUSD=X"], "tv": "FX:GBPUSD", "dec": 4},
    "USD/JPY": {"yf": ["JPY=X", "USDJPY=X"], "tv": "FX:USDJPY", "dec": 2}
}

curr_info = asset_map[selected_asset]

if trading_mode.startswith("⚡"):
    interval = st.sidebar.selectbox("Timeframe", ["1m", "5m"], index=0)
    period = "1d" if interval == "1m" else "5d"
else:
    interval = st.sidebar.selectbox("Timeframe", ["15m", "1h"], index=0)
    period = "1mo"

# ---------------------------------------------------------
# 3. DATA FETCHING WITH FALLBACK
# ---------------------------------------------------------
data = pd.DataFrame()
for ticker in curr_info["yf"]:
    try:
        df = yf.download(ticker, period=period, interval=interval, auto_adjust=False, progress=False)
        if not df.empty:
            data = df
            break
    except Exception:
        continue

if data.empty:
    st.warning("⚠️ Market feed syncing... Interactive charts remain fully active below.")
    st.stop()

if isinstance(data.columns, pd.MultiIndex):
    data.columns = data.columns.get_level_values(0)

data = data.dropna()

# Convert Index to EAT
if data.index.tz is None:
    data.index = data.index.tz_localize("UTC").tz_convert(eat_tz)
else:
    data.index = data.index.tz_convert(eat_tz)

# ---------------------------------------------------------
# 4. ADVANCED TECHNICAL ANALYSIS ENGINE
# ---------------------------------------------------------
# EMAs
data["EMA_9"] = data["Close"].ewm(span=9, adjust=False).mean()
data["EMA_20"] = data["Close"].ewm(span=20, adjust=False).mean()
data["EMA_50"] = data["Close"].ewm(span=50, adjust=False).mean()

# RSI (14)
delta = data["Close"].diff()
gain = delta.where(delta > 0, 0)
loss = -delta.where(delta < 0, 0)
avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
rs = avg_gain / avg_loss
data["RSI"] = 100 - (100 / (1 + rs))

# MACD (12, 26, 9)
data["EMA_12"] = data["Close"].ewm(span=12, adjust=False).mean()
data["EMA_26"] = data["Close"].ewm(span=26, adjust=False).mean()
data["MACD"] = data["EMA_12"] - data["EMA_26"]
data["MACD_Signal"] = data["MACD"].ewm(span=9, adjust=False).mean()
data["MACD_Hist"] = data["MACD"] - data["MACD_Signal"]

# Average True Range (ATR 14)
high_low = data["High"] - data["Low"]
high_close = (data["High"] - data["Close"].shift()).abs()
low_close = (data["Low"] - data["Close"].shift()).abs()
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
data["ATR"] = tr.ewm(span=14, adjust=False).mean()

# Auto Fibonacci Retracement & Extension (Lookback 50 bars)
lookback = min(50, len(data))
recent_df = data.tail(lookback)
swing_high = float(recent_df["High"].max())
swing_low = float(recent_df["Low"].min())
diff = swing_high - swing_low

fib_382 = swing_high - (diff * 0.382)
fib_500 = swing_high - (diff * 0.500)
fib_618 = swing_high - (diff * 0.618)
fib_ext_1618 = swing_high + (diff * 0.618)  # Bullish extension target

# Order Blocks (Supply & Demand Zones)
demand_zone_low = swing_low
demand_zone_high = swing_low + (data["ATR"].iloc[-1] * 1.2)
supply_zone_low = swing_high - (data["ATR"].iloc[-1] * 1.2)
supply_zone_high = swing_high

# Divergence Detection (Simple 10-bar slope check)
price_slope = data["Close"].iloc[-1] - data["Close"].iloc[-10]
rsi_slope = data["RSI"].iloc[-1] - data["RSI"].iloc[-10]

bullish_div = price_slope < 0 and rsi_slope > 0
bearish_div = price_slope > 0 and rsi_slope < 0

# ---------------------------------------------------------
# 5. SIGNAL GENERATOR (BUY / SELL / PREPARE / TP / SL)
# ---------------------------------------------------------
latest = data.iloc[-1]
price = float(latest["Close"])
atr = float(latest["ATR"])
rsi = float(latest["RSI"])
ema9 = float(latest["EMA_9"])
ema20 = float(latest["EMA_20"])
ema50 = float(latest["EMA_50"])
macd_hist = float(latest["MACD_Hist"])

# Dynamic Risk Multipliers
sl_mult = 1.2 if "Scalping" in trading_mode else 2.0
tp1_mult = 1.8 if "Scalping" in trading_mode else 3.0
tp2_mult = 3.0 if "Scalping" in trading_mode else 5.0

signal = "NEUTRAL ⚪"
action_reason = "Consolidating near key structural levels."
tp1, tp2, sl = 0.0, 0.0, 0.0

if (ema9 > ema20 and macd_hist > 0 and rsi > 50 and rsi < 68) or bullish_div:
    signal = "BUY EXECUTE 🚀"
    action_reason = "Bullish momentum aligned across EMA + MACD + RSI."
    sl = price - (atr * sl_mult)
    tp1 = price + (atr * tp1_mult)
    tp2 = fib_ext_1618
elif (ema9 < ema20 and macd_hist < 0 and rsi < 50 and rsi > 32) or bearish_div:
    signal = "SELL EXECUTE 📉"
    action_reason = "Bearish momentum aligned across EMA + MACD + RSI."
    sl = price + (atr * sl_mult)
    tp1 = price - (atr * tp1_mult)
    tp2 = fib_618
elif rsi <= 35:
    signal = "PREPARE TO BUY ⏳"
    action_reason = "Price approaching Demand/Oversold Zone."
    sl = price - (atr * sl_mult)
    tp1 = price + (atr * tp1_mult)
    tp2 = swing_high
elif rsi >= 65:
    signal = "PREPARE TO SELL ⏳"
    action_reason = "Price approaching Supply/Overbought Zone."
    sl = price + (atr * sl_mult)
    tp1 = price - (atr * tp1_mult)
    tp2 = swing_low

# ---------------------------------------------------------
# 6. UI DISPLAY MODULES
# ---------------------------------------------------------
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Live Market Price", f"${price:.{curr_info['dec']}f}")
m2.metric("Signal Status", signal)
m3.metric("Take Profit 1 (TP1)", f"${tp1:.{curr_info['dec']}f}" if tp1 else "N/A")
m4.metric("Take Profit 2 (TP2)", f"${tp2:.{curr_info['dec']}f}" if tp2 else "N/A")
m5.metric("Stop Loss (SL)", f"${sl:.{curr_info['dec']}f}" if sl else "N/A")

st.info(f"💡 **Trading Execution Insight:** {action_reason}")

# Main Layout
col_chart, col_side = st.columns([3, 1])

with col_chart:
    st.subheader(f"📊 Live TradingView Chart ({selected_asset})")
    tv_html = f"""
    <div class="tradingview-widget-container" style="height:540px;width:100%">
      <div id="tv_chart" style="height:540px;width:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true,
        "symbol": "{curr_info['tv']}",
        "interval": "5" if "{interval}" == "5m" else "1",
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
    components.html(tv_html, height=550)

with col_side:
    st.subheader("🎯 Key Level Matrix")
    
    st.markdown("**Fibonacci Retracements:**")
    st.write(f"• **161.8% Ext:** `${fib_ext_1618:.2f}`")
    st.write(f"• **38.2% Fib:** `${fib_382:.2f}`")
    st.write(f"• **50.0% Fib:** `${fib_500:.2f}`")
    st.write(f"• **61.8% Fib:** `${fib_618:.2f}`")
    
    st.divider()
    
    st.markdown("**Order Blocks (Supply / Demand):**")
    st.write(f"🔴 **Supply Zone:** `${supply_zone_low:.2f} - ${supply_zone_high:.2f}`")
    st.write(f"🟢 **Demand Zone:** `${demand_zone_low:.2f} - ${demand_zone_high:.2f}`")
    
    st.divider()
    
    st.markdown("**Indicator Readings:**")
    st.write(f"• **RSI (14):** `{rsi:.1f}`")
    st.write(f"• **MACD Hist:** `{macd_hist:.3f}`")
    st.write(f"• **ATR (14):** `${atr:.2f}`")

# ---------------------------------------------------------
# 7. HIGH IMPACT GOLD NEWS FEED
# ---------------------------------------------------------
st.divider()
st.subheader("📰 Real-Time Market News Feed")

try:
    gc_ticker = yf.Ticker("GC=F")
    news_items = gc_ticker.news[:4]
    
    if news_items:
        cols = st.columns(len(news_items))
        for idx, item in enumerate(news_items):
            with cols[idx]:
                title = item.get('title', 'Market News Update')
                publisher = item.get('publisher', 'Financial Source')
                link = item.get('link', '#')
                st.markdown(f"**[{title}]({link})**")
                st.caption(f"Source: {publisher}")
    else:
        st.write("No major high-impact headlines published in the last hour.")
except Exception:
    st.write("Live market headlines updating...")
