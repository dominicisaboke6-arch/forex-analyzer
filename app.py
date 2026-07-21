import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

# Optional MT5 Library Import Guard
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

# ---------------------------------------------------------
# 1. PAGE SETUP & AUTO-REFRESH (10 SECONDS)
# ---------------------------------------------------------
st.set_page_config(
    page_title="MINION - Unfiltered Quant Signal Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Refresh signal engine every 10 seconds
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
# 2. BRANDING HEADER
# ---------------------------------------------------------
st.markdown("""
<div class="minion-header">
    <div class="minion-title">⚡ MINION QUANT ENGINE V4.1 ⚡</div>
    <div class="minion-subtitle">Structure-Driven Direct Signal Execution • Market Regime • Risk Filter • MT5 Ready</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. REAL-TIME EAT & UTC CLOCK WIDGET
# ---------------------------------------------------------
clock_html = """
<div style="background-color: #151a23; border: 1px solid #232a3b; padding: 10px 15px; border-radius: 8px; text-align: center; margin-bottom: 15px;">
    <span style="color: #888888; font-size: 13px; font-weight: bold; font-family: monospace;">LIVE TIME:</span>
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
st.sidebar.header("🕹️ Execution Engine Settings")

trading_mode = st.sidebar.radio("Execution Mode", ["📈 High Confluence Scalp (5m)", "📊 Macro Trend Swing (15m/1h)"])
selected_asset = st.sidebar.selectbox("Asset Pair", ["Gold (Spot XAU/USD)", "EUR/USD", "GBP/USD", "USD/JPY"])

asset_map = {
    "Gold (Spot XAU/USD)": {"yf": ["GC=F", "XAUUSD=X"], "tv": "OANDA:XAUUSD", "mt5": "XAUUSD", "dec": 2},
    "EUR/USD": {"yf": ["EURUSD=X"], "tv": "FX:EURUSD", "mt5": "EURUSD", "dec": 4},
    "GBP/USD": {"yf": ["GBPUSD=X"], "tv": "FX:GBPUSD", "mt5": "GBPUSD", "dec": 4},
    "USD/JPY": {"yf": ["JPY=X", "USDJPY=X"], "tv": "FX:USDJPY", "mt5": "USDJPY", "dec": 2}
}

curr_info = asset_map[selected_asset]

if "Scalp" in trading_mode:
    interval = st.sidebar.selectbox("Timeframe", ["5m", "1m"], index=0)
    period = "5d" if interval == "5m" else "1d"
else:
    interval = st.sidebar.selectbox("Timeframe", ["15m", "1h"], index=0)
    period = "1mo"

cooldown_period_mins = st.sidebar.slider("Signal Cooldown (Minutes)", 0, 60, 15)
min_rr_threshold = st.sidebar.slider("Min Risk-to-Reward Ratio (1:X)", 1.0, 3.0, 1.5, step=0.1)

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 MetaTrader 5 Direct Bridge")
enable_mt5 = st.sidebar.checkbox("Enable Auto-Execution on MT5", value=False)
mt5_lot_size = st.sidebar.number_input("MT5 Order Lot Size", min_value=0.01, max_value=10.0, value=0.01, step=0.01)

# Helper function for MT5 execution
def send_mt5_order(symbol_name, action, volume, sl_val, tp_val):
    if not MT5_AVAILABLE:
        st.sidebar.error("MetaTrader5 python package not installed.")
        return False
    if not mt5.initialize():
        st.sidebar.error("MT5 terminal not running or algorithmic trading disabled.")
        return False

    mt5_sym = curr_info["mt5"]
    mt5.symbol_select(mt5_sym, True)
    tick = mt5.symbol_info_tick(mt5_sym)
    if not tick:
        mt5.shutdown()
        return False

    price_act = tick.ask if action == "BUY" else tick.bid
    order_type = mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL

    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": mt5_sym,
        "volume": float(volume),
        "type": order_type,
        "price": float(price_act),
        "sl": float(sl_val),
        "tp": float(tp_val),
        "deviation": 20,
        "magic": 202607,
        "comment": "MINION Signal Engine",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    res = mt5.order_send(req)
    mt5.shutdown()
    return res.retcode == mt5.TRADE_RETCODE_DONE if res else False

# ---------------------------------------------------------
# 5. DATA FETCHING & INDICATOR ENGINE
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

    # RSI
    delta = data["Close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss
    data["RSI"] = 100 - (100 / (1 + rs))

    # MACD
    data["EMA_12"] = data["Close"].ewm(span=12, adjust=False).mean()
    data["EMA_26"] = data["Close"].ewm(span=26, adjust=False).mean()
    data["MACD"] = data["EMA_12"] - data["EMA_26"]
    data["MACD_Signal"] = data["MACD"].ewm(span=9, adjust=False).mean()
    data["MACD_Hist"] = data["MACD"] - data["MACD_Signal"]

    # ATR
    high_low = data["High"] - data["Low"]
    high_close = (data["High"] - data["Close"].shift()).abs()
    low_close = (data["Low"] - data["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data["ATR"] = tr.ewm(span=14, adjust=False).mean()
    data["ATR_MA"] = data["ATR"].rolling(window=20).mean()

    # ADX Calculation
    up_move = data["High"] - data["High"].shift(1)
    down_move = data["Low"].shift(1) - data["Low"]
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr_smoothed = tr.ewm(alpha=1/14, adjust=False).mean()
    plus_di = 100 * (pd.Series(plus_dm, index=data.index).ewm(alpha=1/14, adjust=False).mean() / tr_smoothed)
    minus_di = 100 * (pd.Series(minus_dm, index=data.index).ewm(alpha=1/14, adjust=False).mean() / tr_smoothed)

    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    data["ADX"] = dx.ewm(alpha=1/14, adjust=False).mean()

    # Market Structure (Swings & Setups)
    swing_window = 10
    data["Swing_High"] = data["High"].rolling(window=swing_window).max().shift(1)
    data["Swing_Low"] = data["Low"].rolling(window=swing_window).min().shift(1)

    latest = data.iloc[-1]
    prev_1 = data.iloc[-2]

    price = float(latest["Close"])
    high_p = float(latest["High"])
    low_p = float(latest["Low"])
    rsi = float(latest["RSI"])
    ema9 = float(latest["EMA_9"])
    ema20 = float(latest["EMA_20"])
    ema50 = float(latest["EMA_50"])
    ema200 = float(latest["EMA_200"])
    macd_hist = float(latest["MACD_Hist"])
    atr_val = float(latest["ATR"])
    atr_ma = float(latest["ATR_MA"]) if not pd.isna(latest["ATR_MA"]) else atr_val
    adx_val = float(latest["ADX"]) if not pd.isna(latest["ADX"]) else 20.0
    swing_high = float(latest["Swing_High"])
    swing_low = float(latest["Swing_Low"])

    # ---------------------------------------------------------
    # LAYER 1: MARKET REGIME DETECTOR
    # ---------------------------------------------------------
    regime = "RANGING / CHOPPY 🟡"
    if adx_val >= 25 and price > ema200 and ema20 > ema50:
        regime = "TRENDING BULLISH 📈"
    elif adx_val >= 25 and price < ema200 and ema20 < ema50:
        regime = "TRENDING BEARISH 📉"
    elif atr_val > (atr_ma * 1.8):
        regime = "HIGH VOLATILITY 🔥"
    elif adx_val < 20:
        regime = "RANGING / CHOPPY 🟡"
    else:
        regime = "TRANSITION / CONSOLIDATION 🔄"

    # ---------------------------------------------------------
    # LAYER 2: SETUP DETECTOR (MARKET STRUCTURE)
    # ---------------------------------------------------------
    bos_bullish = price > swing_high
    bos_bearish = price < swing_low

    choch_bullish = (prev_1["Close"] < swing_low) and (price > ema20)
    choch_bearish = (prev_1["Close"] > swing_high) and (price < ema20)

    sweep_bullish = (low_p < swing_low) and (price > swing_low)
    sweep_bearish = (high_p > swing_high) and (price < swing_high)

    valid_setup = "NONE"
    setup_description = "No structural setup detected."

    if bos_bullish:
        valid_setup = "BULLISH_BOS"
        setup_description = f"Bullish Break of Structure (BOS) above ${swing_high:.{curr_info['dec']}f}"
    elif bos_bearish:
        valid_setup = "BEARISH_BOS"
        setup_description = f"Bearish Break of Structure (BOS) below ${swing_low:.{curr_info['dec']}f}"
    elif sweep_bullish:
        valid_setup = "BULLISH_SWEEP"
        setup_description = "Liquidity Sweep of Swing Low with Bullish Rejection."
    elif sweep_bearish:
        valid_setup = "BEARISH_SWEEP"
        setup_description = "Liquidity Sweep of Swing High with Bearish Rejection."
    elif choch_bullish:
        valid_setup = "BULLISH_CHOCH"
        setup_description = "Change of Character (CHoCH) shift to Bullish."
    elif choch_bearish:
        valid_setup = "BEARISH_CHOCH"
        setup_description = "Change of Character (CHoCH) shift to Bearish."

    # Calculated conviction score for reference
    score = 0
    if "BULLISH" in regime and "BULLISH" in valid_setup: score += 35
    if "BEARISH" in regime and "BEARISH" in valid_setup: score += 35
    if valid_setup != "NONE": score += 25
    if (ema9 > ema20 and macd_hist > 0) if "BULLISH" in valid_setup else (ema9 < ema20 and macd_hist < 0): score += 20
    if (50 <= rsi <= 68) if "BULLISH" in valid_setup else (32 <= rsi <= 50): score += 20
    confidence_pct = min(score, 100)

    # ---------------------------------------------------------
    # LAYER 3: RISK & EXECUTION FILTER
    # ---------------------------------------------------------
    sl_mult = 1.5 if "Scalp" in trading_mode else 2.2
    tp1_mult = sl_mult * min_rr_threshold

    proposed_sl = 0.0
    proposed_tp = 0.0
    risk_passed = False
    risk_reason = "Awaiting structure setup."

    if "BULLISH" in valid_setup:
        proposed_sl = price - (atr_val * sl_mult)
        proposed_tp = price + (atr_val * tp1_mult)
    elif "BEARISH" in valid_setup:
        proposed_sl = price + (atr_val * sl_mult)
        proposed_tp = price - (atr_val * tp1_mult)

    sl_dist = abs(price - proposed_sl)
    tp_dist = abs(proposed_tp - price)
    calculated_rr = (tp_dist / sl_dist) if sl_dist > 0 else 0.0

    if atr_val > (atr_ma * 2.2):
        risk_passed = False
        risk_reason = "REJECTED: Extreme volatility spike detected."
    elif calculated_rr < min_rr_threshold and valid_setup != "NONE":
        risk_passed = False
        risk_reason = f"REJECTED: Risk-Reward ({calculated_rr:.2f}) below threshold ({min_rr_threshold:.1f})."
    elif valid_setup == "NONE":
        risk_passed = False
        risk_reason = "Awaiting market structure setup (BOS / CHoCH / Sweep)."
    else:
        risk_passed = True
        risk_reason = f"APPROVED: Structure verified | RRR = 1:{calculated_rr:.2f}"

    # ---------------------------------------------------------
    # DIRECT SIGNAL GENERATION (THRESHOLD LIMITATION REMOVED)
    # ---------------------------------------------------------
    now_dt = datetime.now(eat_tz)
    cooldown_active = False
    mins_since_last = 0.0

    if st.session_state.last_signal_time and cooldown_period_mins > 0:
        mins_since_last = (now_dt - st.session_state.last_signal_time).total_seconds() / 60.0
        if mins_since_last < cooldown_period_mins:
            cooldown_active = True

    signal = "NO TRADE ⚪"
    reason = risk_reason
    tp1, tp2, sl = 0.0, 0.0, 0.0

    if cooldown_active:
        signal = "COOLDOWN ⏳"
        reason = f"Cooldown lock active. Next entry allowed in {int(cooldown_period_mins - mins_since_last)}m."
    elif risk_passed and valid_setup != "NONE":
        if "BULLISH" in valid_setup:
            signal = "BUY EXECUTE 🚀"
            reason = f"Direct Setup Signal ({valid_setup}) | Regime: {regime}"
            sl = proposed_sl
            tp1 = proposed_tp
            tp2 = price + (atr_val * (tp1_mult * 1.6))
            st.session_state.last_signal_time = now_dt
            
            if enable_mt5:
                send_mt5_order(selected_asset, "BUY", mt5_lot_size, sl, tp1)

        elif "BEARISH" in valid_setup:
            signal = "SELL EXECUTE 📉"
            reason = f"Direct Setup Signal ({valid_setup}) | Regime: {regime}"
            sl = proposed_sl
            tp1 = proposed_tp
            tp2 = price - (atr_val * (tp1_mult * 1.6))
            st.session_state.last_signal_time = now_dt

            if enable_mt5:
                send_mt5_order(selected_asset, "SELL", mt5_lot_size, sl, tp1)

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
            
            st.session_state.ml_dataset.append({
                "timestamp": now_str,
                "price": price,
                "rsi": rsi,
                "macd_hist": macd_hist,
                "atr": atr_val,
                "adx": adx_val,
                "regime": regime,
                "setup": valid_setup,
                "confidence_score": confidence_pct,
                "signal": signal
            })

    # Update Active Signal Statuses
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

    # Dashboard Metrics
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Live Price", f"${price:.{curr_info['dec']}f}")
    c2.metric("Market Regime", regime)
    c3.metric("Signal Output", signal)
    c4.metric("Take Profit (TP1)", f"${tp1:.{curr_info['dec']}f}" if tp1 else "N/A")
    c5.metric("Stop Loss (SL)", f"${sl:.{curr_info['dec']}f}" if sl else "N/A")

    st.info(f"💡 **Engine Decision:** {reason} | **Structure:** {setup_description}")

# ---------------------------------------------------------
# 6. LIVE TRADINGVIEW CHART
# ---------------------------------------------------------
st.divider()
col_chart, col_side = st.columns([3, 1])

tv_interval_map = {"1m": "1", "5m": "5", "15m": "15", "1h": "60"}
tv_interval = tv_interval_map.get(interval, "5")

with col_chart:
    st.subheader(f"📊 Real-Time Chart ({selected_asset})")
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
# 7. TRADE JOURNAL & ACCURACY
# ---------------------------------------------------------
with col_side:
    st.subheader("📋 Trade Journal")
    
    if st.session_state.signal_history:
        history_df = pd.DataFrame(st.session_state.signal_history).tail(8)
        
        required_cols = ["time", "type", "entry", "confidence", "status"]
        for col in required_cols:
            if col not in history_df.columns:
                history_df[col] = "N/A"
        
        history_df = history_df[required_cols]
        
        wins = len(history_df[history_df["status"].str.contains("WIN")])
        total_closed = len(history_df[~history_df["status"].str.contains("ACTIVE")])
        win_rate = (wins / total_closed * 100) if total_closed > 0 else 0.0
        
        st.metric("Session Win-Rate", f"{win_rate:.1f}%", f"{wins}/{total_closed} Targets Hit")
        st.dataframe(history_df, use_container_width=True)
    else:
        st.caption("No trade setups triggered yet in this session.")

# ---------------------------------------------------------
# 8. ECONOMIC NEWS TIMELINE
# ---------------------------------------------------------
st.divider()
st.subheader("📰 Macro Economic News Feed")

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
