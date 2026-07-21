from streamlit_autorefresh import st_autorefresh
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

# Page configuration
st.set_page_config( # Refresh the Python signal engine every 15 seconds (15000 ms)
st_autorefresh(interval=15000, key="minion_autorefresh")
    page_title="Minion - Pro Gold & Forex Scanner",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark Theme CSS
st.markdown("""
<style>
    .stApp { background-color: #0b0e14; color: #e1e6ed; }
    .metric-card { background-color: #151a23; padding: 15px; border-radius: 8px; border: 1px solid #232a3b; }
    div[data-testid="stSidebar"] { background-color: #131722; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. REAL-TIME RUNNING CLOCK (EAT / Nairobi + UTC)
# ---------------------------------------------------------
clock_html = """
<div style="background-color: #151a23; border: 1px solid #232a3b; padding: 10px 15px; border-radius: 8px; text-align: center; margin-bottom: 15px;">
    <span style="color: #888888; font-size: 13px; font-weight: bold; font-family: monospace;">REAL-TIME EAT MARKET CLOCK:</span>
    <span id="live_clock" style="color: #00e676; font-size: 16px; font-weight: bold; font-family: monospace; margin-left: 10px;">--:--:--</span>
</div>
<script>
function updateClock() {
    const now = new Date();
    // Options for East Africa Time (Africa/Nairobi - UTC+3)
    const optionsEAT = { timeZone: 'Africa/Nairobi', hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' };
    const eatStr = new Intl.DateTimeFormat('en-GB', optionsEAT).format(now) + " EAT";
    const utcStr = now.toISOString().replace('T', ' ').substring(0, 19) + " UTC";
    document.getElementById("live_clock").innerText = eatStr + "  |  " + utcStr;
}
setInterval(updateClock, 1000);
updateClock();
</script>
"""
components.html(clock_html, height=55)

# ---------------------------------------------------------
# 2. FOREX TRADING SESSIONS ENGINE
# ---------------------------------------------------------
utc_now = datetime.now(pytz.utc)

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

# Header
st.title("⚡ Minion - Live Gold & Forex Terminal")
st.caption(f"🌍 **Active Market Sessions:** `{active_sessions_str}`")

# ---------------------------------------------------------
# 3. SIDEBAR & TRADING PARAMETERS
# ---------------------------------------------------------
st.sidebar.header("🕹️ Strategy & Market Controls")

trading_mode = st.sidebar.radio("Trading Mode", ["⚡ Scalping Mode (1m - 5m)", "📈 Day Trading Mode (15m - 1h)"])
selected_asset = st.sidebar.selectbox("Asset / Currency Pair", ["Gold (Spot XAU/USD)", "EUR/USD", "GBP/USD", "USD/JPY"])

asset_map = {
    "Gold (Spot XAU/USD)": {"yf": ["GC=F", "XAUUSD=X"], "tv": "OANDA:XAUUSD", "dec": 2},
    "EUR/USD": {"yf": ["EURUSD=X"], "tv": "FX:EURUSD", "dec": 4},
    "GBP/USD": {"yf": ["GBPUSD=X"], "tv": "FX:GBPUSD", "dec": 4},
    "USD/JPY": {"yf": ["JPY=X", "USDJPY=X"], "tv": "FX:USDJPY", "dec": 2}
}

curr_info = asset_map[selected_asset]

if "Scalping" in trading_mode:
    interval = st.sidebar.selectbox("Timeframe", ["1m", "5m"], index=0)
    period = "1d" if interval == "1m" else "5d"
else:
    interval = st.sidebar.selectbox("Timeframe", ["15m", "1h"], index=0)
    period = "1mo"

# ---------------------------------------------------------
# 4. DATA FETCHING WITH FALLBACK ENGINE
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

eat_tz = pytz.timezone("Africa/Nairobi")

if not data.empty:
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data = data.dropna()

    if data.index.tz is None:
        data.index = data.index.tz_localize("UTC").tz_convert(eat_tz)
    else:
        data.index = data.index.tz_convert(eat_tz)

    # ---------------------------------------------------------
    # 5. TECHNICAL INDICATORS & MARKET STRUCTURE
    # ---------------------------------------------------------
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

    # ATR (14)
    high_low = data["High"] - data["Low"]
    high_close = (data["High"] - data["Close"].shift()).abs()
    low_close = (data["Low"] - data["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data["ATR"] = tr.ewm(span=14, adjust=False).mean()

    # Auto Fibonacci Levels (50-bar lookback)
    lookback = min(50, len(data))
    recent_df = data.tail(lookback)
    swing_high = float(recent_df["High"].max())
    swing_low = float(recent_df["Low"].min())
    diff = swing_high - swing_low

    fib_382 = swing_high - (diff * 0.382)
    fib_500 = swing_high - (diff * 0.500)
    fib_618 = swing_high - (diff * 0.618)
    fib_ext_1618 = swing_high + (diff * 0.618)

    # Order Blocks (Supply & Demand)
    atr_val = float(data["ATR"].iloc[-1])
    demand_zone_low = swing_low
    demand_zone_high = swing_low + (atr_val * 1.2)
    supply_zone_low = swing_high - (atr_val * 1.2)
    supply_zone_high = swing_high

    # Divergence Check
    price_slope = data["Close"].iloc[-1] - data["Close"].iloc[-10]
    rsi_slope = data["RSI"].iloc[-1] - data["RSI"].iloc[-10]
    bullish_div = price_slope < 0 and rsi_slope > 0
    bearish_div = price_slope > 0 and rsi_slope < 0

    # ---------------------------------------------------------
    # 6. SIGNAL & RISK CALCULATOR (EXECUTE / PREPARE / TP / SL)
    # ---------------------------------------------------------
    latest = data.iloc[-1]
    price = float(latest["Close"])
    rsi = float(latest["RSI"])
    ema9 = float(latest["EMA_9"])
    ema20 = float(latest["EMA_20"])
    ema50 = float(latest["EMA_50"])
    macd_hist = float(latest["MACD_Hist"])

    sl_mult = 1.2 if "Scalping" in trading_mode else 2.0
    tp1_mult = 1.8 if "Scalping" in trading_mode else 3.0

    signal = "NEUTRAL ⚪"
    action_reason = "Price consolidating near key structural boundaries."
    tp1, tp2, sl = 0.0, 0.0, 0.0

    if (ema9 > ema20 and macd_hist > 0 and 50 < rsi < 68) or bullish_div:
        signal = "BUY EXECUTE 🚀"
        action_reason = "Bullish momentum confirmed (EMA + MACD + RSI Divergence)."
        sl = price - (atr_val * sl_mult)
        tp1 = price + (atr_val * tp1_mult)
        tp2 = fib_ext_1618
    elif (ema9 < ema20 and macd_hist < 0 and 32 < rsi < 50) or bearish_div:
        signal = "SELL EXECUTE 📉"
        action_reason = "Bearish momentum confirmed (EMA + MACD + RSI Divergence)."
        sl = price + (atr_val * sl_mult)
        tp1 = price - (atr_val * tp1_mult)
        tp2 = fib_618
    elif rsi <= 35:
        signal = "PREPARE TO BUY ⏳"
        action_reason = "Price inside Demand / Oversold Order Block."
        sl = price - (atr_val * sl_mult)
        tp1 = price + (atr_val * tp1_mult)
        tp2 = swing_high
    elif rsi >= 65:
        signal = "PREPARE TO SELL ⏳"
        action_reason = "Price inside Supply / Overbought Order Block."
        sl = price + (atr_val * sl_mult)
        tp1 = price - (atr_val * tp1_mult)
        tp2 = swing_low

    # Metrics Panel
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Live Market Price", f"${price:.{curr_info['dec']}f}")
    m2.metric("Signal Status", signal)
    m3.metric("Take Profit 1 (TP1)", f"${tp1:.{curr_info['dec']}f}" if tp1 else "N/A")
    m4.metric("Take Profit 2 (TP2)", f"${tp2:.{curr_info['dec']}f}" if tp2 else "N/A")
    m5.metric("Stop Loss (SL)", f"${sl:.{curr_info['dec']}f}" if sl else "N/A")

    st.info(f"💡 **Trading Insight:** {action_reason}")
else:
    st.warning("⚠️ Data feed syncing... Live TradingView chart below is fully active.")

st.divider()

# ---------------------------------------------------------
# 7. TRADINGVIEW CHART & KEY MATRIX
# ---------------------------------------------------------
col_chart, col_side = st.columns([3, 1])

tv_interval_map = {"1m": "1", "5m": "5", "15m": "15", "1h": "60"}
tv_interval = tv_interval_map.get(interval, "5")

with col_chart:
    st.subheader(f"📊 {selected_asset} Interactive TradingView Chart")
    tv_html = f"""
    <div class="tradingview-widget-container" style="height:540px;width:100%">
      <div id="tv_chart_container" style="height:540px;width:100%"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true,
        "symbol": "{curr_info['tv']}",
        "interval": "{tv_interval}",
        "timezone": "Africa/Nairobi",
        "theme": "dark",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "container_id": "tv_chart_container"
      }});
      </script>
    </div>
    """
    components.html(tv_html, height=550)

with col_side:
    st.subheader("🎯 Key Level Matrix")
    if not data.empty:
        st.markdown("**Fibonacci Levels:**")
        st.write(f"• **161.8% Target:** `${fib_ext_1618:.2f}`")
        st.write(f"• **38.2% Fib:** `${fib_382:.2f}`")
        st.write(f"• **50.0% Fib:** `${fib_500:.2f}`")
        st.write(f"• **61.8% Fib:** `${fib_618:.2f}`")
        st.divider()
        st.markdown("**Order Blocks (Supply / Demand):**")
        st.write(f"🔴 **Supply Zone:** `${supply_zone_low:.2f} - ${supply_zone_high:.2f}`")
        st.write(f"🟢 **Demand Zone:** `${demand_zone_low:.2f} - ${demand_zone_high:.2f}`")
        st.divider()
        st.markdown("**Indicators:**")
        st.write(f"• **RSI (14):** `{rsi:.1f}`")
        st.write(f"• **MACD Hist:** `{macd_hist:.3f}`")
        st.write(f"• **ATR (14):** `${atr_val:.2f}`")

# ---------------------------------------------------------
# 8. HIGH-IMPACT NEWS TIMELINE (Forex Factory / FXStreet / Reuters Feed)
# ---------------------------------------------------------
st.divider()
st.subheader("📰 Real-Time Forex & Gold Market News")

news_html = """
<div class="tradingview-widget-container" style="width:100%; height:450px;">
  <div class="tradingview-widget-container__widget"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-timeline.js" async>
  {
  "feedMode": "all_symbols",
  "isTransparent": false,
  "displayMode": "regular",
  "width": "100%",
  "height": "450",
  "colorTheme": "dark",
  "locale": "en"
}
  </script>
</div>
"""
components.html(news_html, height=460)
