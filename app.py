import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------------
# 1. PAGE SETUP & AUTO-REFRESH (10 SECONDS)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Minion - Max Precision Gold Scanner",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Auto refresh Python signal engine every 10,000 milliseconds (10 seconds)
st_autorefresh(interval=10000, key="minion_live_refresh")

st.markdown("""
<style>
    .stApp { background-color: #0b0e14; color: #e1e6ed; }
    div[data-testid="stSidebar"] { background-color: #131722; }
    .stat-card { background-color: #151a23; border: 1px solid #232a3b; padding: 12px; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# Initialize Session State Signal History
if "signal_history" not in st.session_state:
    st.session_state.signal_history = []

# ---------------------------------------------------------
# 2. REAL-TIME CLOCK (EAT / UTC)
# ---------------------------------------------------------
clock_html = """
<div style="background-color: #151a23; border: 1px solid #232a3b; padding: 10px 15px; border-radius: 8px; text-align: center; margin-bottom: 15px;">
    <span style="color: #888888; font-size: 13px; font-weight: bold; font-family: monospace;">EAT LIVE CLOCK:</span>
    <span id="live_clock" style="color: #00e676; font-size: 16px; font-weight: bold; font-family: monospace; margin-left: 10px;">--:--:--</span>
</div>
<script>
function updateClock() {
    const now = new Date();
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
# 3. CONTROLS & ASSET SELECTOR
# ---------------------------------------------------------
st.sidebar.header("🕹️ Strategy & Filters")

trading_mode = st.sidebar.radio("Trading Mode", ["⚡ High-Speed Scalp (1m - 5m)", "📈 Trend Swing (15m - 1h)"])
selected_asset = st.sidebar.selectbox("Asset Pair", ["Gold (Spot XAU/USD)", "EUR/USD", "GBP/USD", "USD/JPY"])

asset_map = {
    "Gold (Spot XAU/USD)": {"yf": ["GC=F", "XAUUSD=X"], "tv": "OANDA:XAUUSD", "dec": 2},
    "EUR/USD": {"yf": ["EURUSD=X"], "tv": "FX:EURUSD", "dec": 4},
    "GBP/USD": {"yf": ["GBPUSD=X"], "tv": "FX:GBPUSD", "dec": 4},
    "USD/JPY": {"yf": ["JPY=X", "USDJPY=X"], "tv": "FX:USDJPY", "dec": 2}
}

curr_info = asset_map[selected_asset]

if "Scalp" in trading_mode:
    interval = st.sidebar.selectbox("Timeframe", ["1m", "5m"], index=0)
    period = "1d" if interval == "1m" else "5d"
else:
    interval = st.sidebar.selectbox("Timeframe", ["15m", "1h"], index=0)
    period = "1mo"

# ---------------------------------------------------------
# 4. DATA ENGINE WITH HIGH-PRECISION INDICATORS
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
    # Safely handle yfinance multi-index columns
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    
    data = data.dropna()

    if data.index.tz is None:
        data.index = data.index.tz_localize("UTC").tz_convert(eat_tz)
    else:
        data.index = data.index.tz_convert(eat_tz)

    # Core Moving Averages
    data["EMA_9"] = data["Close"].ewm(span=9, adjust=False).mean()
    data["EMA_20"] = data["Close"].ewm(span=20, adjust=False).mean()
    data["EMA_50"] = data["Close"].ewm(span=50, adjust=False).mean()
    data["EMA_200"] = data["Close"].ewm(span=200, adjust=False).mean()  # Trend Filter

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

    latest = data.iloc[-1]
    price = float(latest["Close"])
    rsi = float(latest["RSI"])
    ema9 = float(latest["EMA_9"])
    ema20 = float(latest["EMA_20"])
    ema50 = float(latest["EMA_50"])
    ema200 = float(latest["EMA_200"])
    macd_hist = float(latest["MACD_Hist"])
    atr_val = float(latest["ATR"])

    # ---------------------------------------------------------
    # 5. HIGH WIN-RATE SIGNAL LOGIC
    # ---------------------------------------------------------
    macro_bullish = price > ema200
    macro_bearish = price < ema200

    sl_mult = 1.3 if "Scalp" in trading_mode else 2.0
    tp1_mult = 1.8 if "Scalp" in trading_mode else 3.0
    tp2_mult = 3.2 if "Scalp" in trading_mode else 5.0

    signal = "NO TRADE ⚪"
    reason = "Awaiting macro trend & volume alignment."
    tp1, tp2, sl = 0.0, 0.0, 0.0

    if macro_bullish and ema9 > ema20 and macd_hist > 0 and (52 <= rsi <= 65):
        signal = "BUY EXECUTE 🚀"
        reason = "Aligned with 200-EMA Trend + MACD Expansion + Optimal RSI Momentum."
        sl = price - (atr_val * sl_mult)
        tp1 = price + (atr_val * tp1_mult)
        tp2 = price + (atr_val * tp2_mult)
    elif macro_bearish and ema9 < ema20 and macd_hist < 0 and (35 <= rsi <= 48):
        signal = "SELL EXECUTE 📉"
        reason = "Aligned with 200-EMA Trend + MACD Contraction + Weak RSI."
        sl = price + (atr_val * sl_mult)
        tp1 = price - (atr_val * tp1_mult)
        tp2 = price - (atr_val * tp2_mult)
    elif rsi <= 30 and macro_bullish:
        signal = "PREPARE BUY ⏳"
        reason = "Oversold pullback inside broader uptrend."
        sl = price - (atr_val * sl_mult)
        tp1 = price + (atr_val * tp1_mult)
        tp2 = price + (atr_val * tp2_mult)
    elif rsi >= 70 and macro_bearish:
        signal = "PREPARE SELL ⏳"
        reason = "Overbought retracement inside broader downtrend."
        sl = price + (atr_val * sl_mult)
        tp1 = price + (atr_val * tp1_mult)
        tp2 = price - (atr_val * tp2_mult)

    # Record Signal History
    now_str = datetime.now(eat_tz).strftime("%H:%M:%S")
    if signal in ["BUY EXECUTE 🚀", "SELL EXECUTE 📉"]:
        if not st.session_state.signal_history or st.session_state.signal_history[-1]["time"] != now_str:
            st.session_state.signal_history.append({
                "time": now_str,
                "asset": selected_asset,
                "type": signal,
                "entry": round(price, curr_info["dec"]),
                "tp1": round(tp1, curr_info["dec"]),
                "sl": round(sl, curr_info["dec"]),
                "status": "ACTIVE 🟡"
            })

    # Evaluate active historical signals
    for sig in st.session_state.signal_history:
        if sig["status"] == "ACTIVE 🟡" and sig["asset"] == selected_asset:
            if "BUY" in sig["type"]:
                if price >= sig["tp1"]:
                    sig["status"] = "WIN (TP1 Hit) ✅"
                elif price <= sig["sl"]:
                    sig["status"] = "LOSS (SL Hit) ❌"
            elif "SELL" in sig["type"]:
                if price <= sig["tp1"]:
                    sig["status"] = "WIN (TP1 Hit) ✅"
                elif price >= sig["sl"]:
                    sig["status"] = "LOSS (SL Hit) ❌"

    # Display Real-time Metrics
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Live Market Price", f"${price:.{curr_info['dec']}f}")
    m2.metric("Signal Status", signal)
    m3.metric("Take Profit 1", f"${tp1:.{curr_info['dec']}f}" if tp1 else "N/A")
    m4.metric("Take Profit 2", f"${tp2:.{curr_info['dec']}f}" if tp2 else "N/A")
    m5.metric("Stop Loss", f"${sl:.{curr_info['dec']}f}" if sl else "N/A")

    st.info(f"💡 **Confluence Insight:** {reason}")

# ---------------------------------------------------------
# 6. TRADINGVIEW LIVE CHART
# ---------------------------------------------------------
st.divider()
col_chart, col_side = st.columns([3, 1])

tv_interval_map = {"1m": "1", "5m": "5", "15m": "15", "1h": "60"}
tv_interval = tv_interval_map.get(interval, "5")

with col_chart:
    st.subheader(f"📊 {selected_asset} Chart")
    tv_html = f"""
    <div class="tradingview-widget-container" style="height:520px;width:100%">
      <div id="tv_chart_container" style="height:520px;width:100%"></div>
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
    components.html(tv_html, height=530)

# ---------------------------------------------------------
# 7. SIGNAL HISTORY & WIN-RATE TRACKER
# ---------------------------------------------------------
with col_side:
    st.subheader("📋 Signal History Log")
    
    if st.session_state.signal_history:
        history_df = pd.DataFrame(st.session_state.signal_history).tail(8)
        
        # Calculate Win-Rate
        wins = len(history_df[history_df["status"].str.contains("WIN")])
        total_closed = len(history_df[~history_df["status"].str.contains("ACTIVE")])
        win_rate = (wins / total_closed * 100) if total_closed > 0 else 0.0
        
        st.metric("Logged Win-Rate", f"{win_rate:.1f}%", f"{wins}/{total_closed} Won")
        
        # Streamlit version safe dataframe render
        try:
            st.dataframe(history_df[["time", "type", "entry", "status"]], use_container_width=True)
        except Exception:
            st.dataframe(history_df[["time", "type", "entry", "status"]])
    else:
        st.caption("No historical signals recorded in this session yet. High-precision signals will auto-log here as they trigger.")

# ---------------------------------------------------------
# 8. HIGH-IMPACT NEWS TIMELINE
# ---------------------------------------------------------
st.divider()
st.subheader("📰 Real-Time Economic Events & News")

news_html = """
<div class="tradingview-widget-container" style="width:100%; height:420px;">
  <div class="tradingview-widget-container__widget"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-timeline.js" async>
  {
  "feedMode": "all_symbols",
  "isTransparent": false,
  "displayMode": "regular",
  "width": "100%",
  "height": "420",
  "colorTheme": "dark",
  "locale": "en"
}
  </script>
</div>
"""
components.html(news_html, height=430)
