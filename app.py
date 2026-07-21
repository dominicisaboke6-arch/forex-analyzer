import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------------
# 1. PAGE SETUP & AUTO-REFRESH (10 SECONDS)
# ---------------------------------------------------------
st.set_page_config(
    page_title="MINION - Quantitative Trading Intelligence Engine",
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
    .minion-header {
        background: linear-gradient(135deg, #1f293d 0%, #11151c 100%);
        border: 1px solid #00e676;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0, 230, 118, 0.15);
    }
    .minion-title {
        color: #00e676;
        font-size: 32px;
        font-weight: 800;
        letter-spacing: 2px;
        margin: 0;
        font-family: 'Trebuchet MS', sans-serif;
    }
    .minion-subtitle {
        color: #8892b0;
        font-size: 14px;
        margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session States
if "signal_history" not in st.session_state:
    st.session_state.signal_history = []
if "last_signal_time" not in st.session_state:
    st.session_state.last_signal_time = None
if "ml_dataset" not in st.session_state:
    st.session_state.ml_dataset = []

# ---------------------------------------------------------
# 2. MINION BRANDING HEADER
# ---------------------------------------------------------
st.markdown("""
<div class="minion-header">
    <div class="minion-title">⚡ MINION QUANT ALPHA V3 ⚡</div>
    <div class="minion-subtitle">Multi-Confluence Structural Signal Engine • High-Timeframe Trend Filters • ML Pipeline Ready</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. REAL-TIME EAT & UTC CLOCK WIDGET
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
# 4. SIDEBAR CONTROLS & PARAMS
# ---------------------------------------------------------
st.sidebar.header("🕹️ Strategy & Filters")

trading_mode = st.sidebar.radio("Execution Strategy", ["📈 High Confluence Scalp (5m)", "📊 Macro Trend Swing (15m/1h)"])
selected_asset = st.sidebar.selectbox("Asset Pair", ["Gold (Spot XAU/USD)", "EUR/USD", "GBP/USD", "USD/JPY"])

asset_map = {
    "Gold (Spot XAU/USD)": {"yf": ["GC=F", "XAUUSD=X"], "tv": "OANDA:XAUUSD", "dec": 2},
    "EUR/USD": {"yf": ["EURUSD=X"], "tv": "FX:EURUSD", "dec": 4},
    "GBP/USD": {"yf": ["GBPUSD=X"], "tv": "FX:GBPUSD", "dec": 4},
    "USD/JPY": {"yf": ["JPY=X", "USDJPY=X"], "tv": "FX:USDJPY", "dec": 2}
}

curr_info = asset_map[selected_asset]

if "Scalp" in trading_mode:
    interval = st.sidebar.selectbox("Timeframe", ["5m", "1m"], index=0)
    period = "5d" if interval == "5m" else "1d"
else:
    interval = st.sidebar.selectbox("Timeframe", ["15m", "1h"], index=0)
    period = "1mo"

cooldown_period_mins = st.sidebar.slider("Signal Cooldown (Minutes)", 5, 60, 20)
min_confluence_cutoff = st.sidebar.slider("Min Confluence Threshold (%)", 50, 90, 70)

# ---------------------------------------------------------
# 5. DATA ENGINE WITH MARKET STRUCTURE & INDICATORS
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

    # Core Indicators
    data["EMA_9"] = data["Close"].ewm(span=9, adjust=False).mean()
    data["EMA_20"] = data["Close"].ewm(span=20, adjust=False).mean()
    data["EMA_50"] = data["Close"].ewm(span=50, adjust=False).mean()
    data["EMA_200"] = data["Close"].ewm(span=200, adjust=False).mean()

    # RSI Calculation
    delta = data["Close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss
    data["RSI"] = 100 - (100 / (1 + rs))

    # MACD Calculation
    data["EMA_12"] = data["Close"].ewm(span=12, adjust=False).mean()
    data["EMA_26"] = data["Close"].ewm(span=26, adjust=False).mean()
    data["MACD"] = data["EMA_12"] - data["EMA_26"]
    data["MACD_Signal"] = data["MACD"].ewm(span=9, adjust=False).mean()
    data["MACD_Hist"] = data["MACD"] - data["MACD_Signal"]

    # ATR Volatility
    high_low = data["High"] - data["Low"]
    high_close = (data["High"] - data["Close"].shift()).abs()
    low_close = (data["Low"] - data["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data["ATR"] = tr.ewm(span=14, adjust=False).mean()

    # Market Structure (Swing Highs / Lows for BOS & CHoCH)
    swing_window = 10
    data["Swing_High"] = data["High"].rolling(window=swing_window).max().shift(1)
    data["Swing_Low"] = data["Low"].rolling(window=swing_window).min().shift(1)

    latest = data.iloc[-1]
    price = float(latest["Close"])
    rsi = float(latest["RSI"])
    ema9 = float(latest["EMA_9"])
    ema20 = float(latest["EMA_20"])
    ema50 = float(latest["EMA_50"])
    ema200 = float(latest["EMA_200"])
    macd_hist = float(latest["MACD_Hist"])
    atr_val = float(latest["ATR"])
    swing_high = float(latest["Swing_High"])
    swing_low = float(latest["Swing_Low"])

    # Structure Breaks
    bos_bullish = price > swing_high
    bos_bearish = price < swing_low

    # ---------------------------------------------------------
    # 6. WEIGHTED CONFLUENCE SCORE & SIGNAL ENGINE
    # ---------------------------------------------------------
    htf_bullish = price > ema200 and ema50 > ema200
    htf_bearish = price < ema200 and ema50 < ema200

    # Calculate Weighted Confluence Score (0 - 100)
    score = 0
    if htf_bullish or htf_bearish: score += 25  # HTF Trend Alignment
    if bos_bullish or bos_bearish: score += 25  # Market Structure Break
    if (htf_bullish and macd_hist > 0) or (htf_bearish and macd_hist < 0): score += 20  # MACD Momentum
    if (htf_bullish and 52 <= rsi <= 68) or (htf_bearish and 32 <= rsi <= 48): score += 20  # RSI Zone
    if ema9 > ema20 if htf_bullish else ema9 < ema20: score += 10  # Moving Average Cross

    confidence_pct = score

    # Check Cooldown State
    now_dt = datetime.now(eat_tz)
    cooldown_active = False
    if st.session_state.last_signal_time:
        mins_since_last = (now_dt - st.session_state.last_signal_time).total_seconds() / 60.0
        if mins_since_last < cooldown_period_mins:
            cooldown_active = True

    # Signal Decision Logic
    signal = "NO TRADE ⚪"
    reason = "Confluence threshold not met or market ranging."
    tp1, tp2, tp3, sl = 0.0, 0.0, 0.0, 0.0

    sl_mult = 1.5 if "Scalp" in trading_mode else 2.2
    tp1_mult = 2.0 if "Scalp" in trading_mode else 3.0
    tp2_mult = 3.5 if "Scalp" in trading_mode else 5.0

    if cooldown_active:
        signal = "COOLDOWN ⏳"
        reason = f"System on buffer after recent entry. Unlocks in {int(cooldown_period_mins - mins_since_last)}m."
    elif confidence_pct >= min_confluence_cutoff:
        if htf_bullish and (bos_bullish or macd_hist > 0):
            signal = "BUY EXECUTE 🚀"
            reason = f"Strong Bullish Confluence ({confidence_pct}% score) + BOS above ${swing_high:.{curr_info['dec']}f}."
            sl = price - (atr_val * sl_mult)
            tp1 = price + (atr_val * tp1_mult)
            tp2 = price + (atr_val * tp2_mult)
            st.session_state.last_signal_time = now_dt
        elif htf_bearish and (bos_bearish or macd_hist < 0):
            signal = "SELL EXECUTE 📉"
            reason = f"Strong Bearish Confluence ({confidence_pct}% score) + BOS below ${swing_low:.{curr_info['dec']}f}."
            sl = price + (atr_val * sl_mult)
            tp1 = price - (atr_val * tp1_mult)
            tp2 = price - (atr_val * tp2_mult)
            st.session_state.last_signal_time = now_dt

    # Log Execution Signals
    now_str = now_dt.strftime("%H:%M:%S")
    if signal in ["BUY EXECUTE 🚀", "SELL EXECUTE 📉"]:
        if not st.session_state.signal_history or st.session_state.signal_history[-1]["time"] != now_str:
            st.session_state.signal_history.append({
                "time": now_str,
                "asset": selected_asset,
                "type": signal,
                "entry": round(price, curr_info["dec"]),
                "tp1": round(tp1, curr_info["dec"]),
                "sl": round(sl, curr_info["dec"]),
                "confidence": f"{confidence_pct}%",
                "status": "ACTIVE 🟡"
            })
            
            # Record Feature Vector for Machine Learning Model Training
            st.session_state.ml_dataset.append({
                "timestamp": now_str,
                "price": price,
                "rsi": rsi,
                "macd_hist": macd_hist,
                "atr": atr_val,
                "confidence_score": confidence_pct,
                "signal": signal
            })

    # Update Active Signal Statuses vs Current Market Price
    for sig in st.session_state.signal_history:
        if sig["status"] == "ACTIVE 🟡" and sig["asset"] == selected_asset:
            if "BUY" in sig["type"]:
                if price >= sig["tp1"]:
                    sig["status"] = "WIN (TP Hit) ✅"
                elif price <= sig["sl"]:
                    sig["status"] = "LOSS (SL Hit) ❌"
            elif "SELL" in sig["type"]:
                if price <= sig["tp1"]:
                    sig["status"] = "WIN (TP Hit) ✅"
                elif price >= sig["sl"]:
                    sig["status"] = "LOSS (SL Hit) ❌"

    # Top Metric Dashboard
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Live Market Price", f"${price:.{curr_info['dec']}f}")
    c2.metric("Signal Status", signal)
    c3.metric("Confluence Conviction", f"{confidence_pct}%")
    c4.metric("Take Profit (Target)", f"${tp1:.{curr_info['dec']}f}" if tp1 else "N/A")
    c5.metric("Stop Loss (Safety)", f"${sl:.{curr_info['dec']}f}" if sl else "N/A")

    st.info(f"💡 **Structural Confluence Analysis:** {reason}")

# ---------------------------------------------------------
# 7. TRADINGVIEW LIVE CHART ENGINE
# ---------------------------------------------------------
st.divider()
col_chart, col_side = st.columns([3, 1])

tv_interval_map = {"1m": "1", "5m": "5", "15m": "15", "1h": "60"}
tv_interval = tv_interval_map.get(interval, "5")

with col_chart:
    st.subheader(f"📊 Live Trading Chart ({selected_asset})")
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
# 8. SIGNAL HISTORY LOG & ACCURACY TRACKER
# ---------------------------------------------------------
with col_side:
    st.subheader("📋 Trade Journal")
    
    if st.session_state.signal_history:
        history_df = pd.DataFrame(st.session_state.signal_history).tail(8)
        
        wins = len(history_df[history_df["status"].str.contains("WIN")])
        total_closed = len(history_df[~history_df["status"].str.contains("ACTIVE")])
        win_rate = (wins / total_closed * 100) if total_closed > 0 else 0.0
        
        st.metric("Win-Rate (Current Session)", f"{win_rate:.1f}%", f"{wins}/{total_closed} Profit Hit")
        
        try:
            st.dataframe(history_df[["time", "type", "entry", "confidence", "status"]], use_container_width=True)
        except Exception:
            st.dataframe(history_df[["time", "type", "entry", "confidence", "status"]])
    else:
        st.caption("No signals triggered yet. High-confluence entries will auto-log here once score reaches your threshold.")

# ---------------------------------------------------------
# 9. ECONOMIC NEWS GUARD & HIGH-IMPACT FEED
# ---------------------------------------------------------
st.divider()
st.subheader("📰 Real-Time Economic Event & Macro Calendar")

news_html = """
<div class="tradingview-widget-container" style="width:100%; height:400px;">
  <div class="tradingview-widget-container__widget"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-timeline.js" async>
  {
  "feedMode": "all_symbols",
  "isTransparent": false,
  "displayMode": "regular",
  "width": "100%",
  "height": "400",
  "colorTheme": "dark",
  "locale": "en"
}
  </script>
</div>
"""
components.html(news_html, height=410)
