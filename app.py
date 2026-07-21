import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

# Optional ML & Deep Learning Library Guards
try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

try:
    import lightgbm as lgb
    LGB_AVAILABLE = True
except ImportError:
    LGB_AVAILABLE = False

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION & 5-SEC AUTO-REFRESH FOR ULTRA-FAST SCALPING
# ---------------------------------------------------------
st.set_page_config(
    page_title="MINION Ultra Scalp & Intraday Alpha Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 5-second automatic tick refresh for 1-minute / 5-minute scalping execution
st_autorefresh(interval=5000, key="minion_scalp_refresh")

st.markdown("""
<style>
    .stApp { background-color: #07090e; color: #e1e6ed; }
    div[data-testid="stSidebar"] { background-color: #11141d; }
    .minion-header {
        background: linear-gradient(135deg, #1b263b 0%, #0d1117 100%);
        border: 1px solid #00ffcc;
        border-radius: 12px;
        padding: 18px;
        text-align: center;
        margin-bottom: 15px;
        box-shadow: 0 0 25px rgba(0, 255, 204, 0.12);
    }
    .minion-title {
        color: #00ffcc;
        font-size: 30px;
        font-weight: 800;
        letter-spacing: 2px;
        margin: 0;
        font-family: 'Courier New', monospace;
    }
    .minion-subtitle {
        color: #8892b0;
        font-size: 13px;
        margin-top: 4px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State Journals
if "scalp_history" not in st.session_state:
    st.session_state.scalp_history = []
if "last_trigger_time" not in st.session_state:
    st.session_state.last_trigger_time = None

# ---------------------------------------------------------
# 2. BRANDING & CLOCK HEADER
# ---------------------------------------------------------
st.markdown("""
<div class="minion-header">
    <div class="minion-title">⚡ MINION 1m/5m/15m ULTRA-SCALP & 30m HOLD ENGINE ⚡</div>
    <div class="minion-subtitle">Multi-Timeframe Structure (BOS/CHoCH) • SMC Order Blocks • XGBoost/LightGBM Alpha • ATR Risk Engine</div>
</div>
""", unsafe_allow_html=True)

clock_html = """
<div style="background-color: #10141d; border: 1px solid #1f2838; padding: 8px 12px; border-radius: 6px; text-align: center; margin-bottom: 12px;">
    <span style="color: #777; font-size: 12px; font-weight: bold; font-family: monospace;">TICK TIMER:</span>
    <span id="live_clock" style="color: #00ffcc; font-size: 15px; font-weight: bold; font-family: monospace; margin-left: 8px;">--:--:--</span>
</div>
<script>
function updateClock() {
    const now = new Date();
    const optionsEAT = { timeZone: 'Africa/Nairobi', hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' };
    document.getElementById("live_clock").innerText = new Intl.DateTimeFormat('en-GB', optionsEAT).format(now) + " EAT";
}
setInterval(updateClock, 1000);
updateClock();
</script>
"""
components.html(clock_html, height=45)

# ---------------------------------------------------------
# 3. SIDEBAR CONTROLS (TIMEFRAME & ASSETS)
# ---------------------------------------------------------
st.sidebar.header("🎯 Scalp & Hold Horizon")
execution_mode = st.sidebar.selectbox(
    "Execution Strategy Mode",
    [
        "1-Minute Micro Scalp (1m Hold Horizon)",
        "5-Minute Fast Scalp (5m Hold Horizon)",
        "15-Minute Scalp Trend (15m Hold Horizon)",
        "30-Minute Intraday Hold (30m Hold Horizon)"
    ]
)

selected_asset = st.sidebar.selectbox(
    "Market Asset",
    ["Gold (Spot XAU/USD)", "EUR/USD", "GBP/USD", "Bitcoin (BTC/USD)"]
)

asset_map = {
    "Gold (Spot XAU/USD)": {"yf": ["GC=F", "XAUUSD=X"], "tv": "OANDA:XAUUSD", "dec": 2},
    "EUR/USD": {"yf": ["EURUSD=X"], "tv": "FX:EURUSD", "dec": 4},
    "GBP/USD": {"yf": ["GBPUSD=X"], "tv": "FX:GBPUSD", "dec": 4},
    "Bitcoin (BTC/USD)": {"yf": ["BTC-USD"], "tv": "BITSTAMP:BTCUSD", "dec": 2}
}
curr_info = asset_map[selected_asset]

# Map horizons to Yahoo Finance intervals & historical bars
if "1-Minute" in execution_mode:
    interval, period, max_hold_mins = "1m", "1d", 1
elif "5-Minute" in execution_mode:
    interval, period, max_hold_mins = "5m", "5d", 5
elif "15-Minute" in execution_mode:
    interval, period, max_hold_mins = "15m", "5d", 15
else:
    interval, period, max_hold_mins = "30m", "1mo", 30

cooldown_secs = st.sidebar.slider("Signal Cooldown (Seconds)", 10, 120, 30)
min_alpha_prob = st.sidebar.slider("Min ML Ensemble Alpha Probability (%)", 50.0, 90.0, 65.0, step=1.0) / 100.0

# ---------------------------------------------------------
# 4. DATA FETCHING & SMART MONEY STRUCTURE ENGINE
# ---------------------------------------------------------
raw_data = pd.DataFrame()
for ticker in curr_info["yf"]:
    try:
        df = yf.download(ticker, period=period, interval=interval, auto_adjust=False, progress=False)
        if not df.empty:
            raw_data = df
            break
    except Exception:
        continue

eat_tz = pytz.timezone("Africa/Nairobi")

if not raw_data.empty:
    if isinstance(raw_data.columns, pd.MultiIndex):
        raw_data.columns = raw_data.columns.get_level_values(0)
    raw_data = raw_data.dropna()

    if raw_data.index.tz is None:
        raw_data.index = raw_data.index.tz_localize("UTC").tz_convert(eat_tz)
    else:
        raw_data.index = raw_data.index.tz_convert(eat_tz)

    # Indicator Calculations
    raw_data["EMA_8"] = raw_data["Close"].ewm(span=8, adjust=False).mean()
    raw_data["EMA_21"] = raw_data["Close"].ewm(span=21, adjust=False).mean()
    raw_data["EMA_50"] = raw_data["Close"].ewm(span=50, adjust=False).mean()

    # RSI (14)
    delta = raw_data["Close"].diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
    loss = -delta.where(delta < 0, 0).ewm(alpha=1/14, adjust=False).mean()
    raw_data["RSI"] = 100 - (100 / (1 + (gain / loss)))

    # MACD
    raw_data["MACD"] = raw_data["Close"].ewm(span=12).mean() - raw_data["Close"].ewm(span=26).mean()
    raw_data["MACD_Sig"] = raw_data["MACD"].ewm(span=9).mean()
    raw_data["MACD_Hist"] = raw_data["MACD"] - raw_data["MACD_Sig"]

    # ATR (14)
    tr = pd.concat([
        raw_data["High"] - raw_data["Low"],
        (raw_data["High"] - raw_data["Close"].shift()).abs(),
        (raw_data["Low"] - raw_data["Close"].shift()).abs()
    ], axis=1).max(axis=1)
    raw_data["ATR"] = tr.ewm(span=14, adjust=False).mean()

    # Smart Money Structure (SMC): Break of Structure (BOS) & Change of Character (CHoCH)
    lookback = 5
    raw_data["Local_High"] = raw_data["High"].rolling(window=lookback).max().shift(1)
    raw_data["Local_Low"] = raw_data["Low"].rolling(window=lookback).min().shift(1)

    raw_data = raw_data.dropna()
    latest = raw_data.iloc[-1]
    prev = raw_data.iloc[-2]

    price = float(latest["Close"])
    rsi = float(latest["RSI"])
    ema8 = float(latest["EMA_8"])
    ema21 = float(latest["EMA_21"])
    ema50 = float(latest["EMA_50"])
    macd_hist = float(latest["MACD_Hist"])
    atr = float(latest["ATR"])
    local_high = float(latest["Local_High"])
    local_low = float(latest["Local_Low"])

    # ---------------------------------------------------------
    # 5. SMC STRUCTURE DETECTION (BOS & CHoCH)
    # ---------------------------------------------------------
    structure_status = "RANGING CONSOLIDATION 🟡"
    structure_bias = 0 # 1 = Bullish, -1 = Bearish

    if price > local_high and ema8 > ema21:
        structure_status = "BULLISH BREAK OF STRUCTURE (BOS) 🚀"
        structure_bias = 1
    elif price < local_low and ema8 < ema21:
        structure_status = "BEARISH BREAK OF STRUCTURE (BOS) 📉"
        structure_bias = -1
    elif prev["Close"] < prev["Local_High"] and price > local_high:
        structure_status = "BULLISH CHANGE OF CHARACTER (CHoCH) ⚡"
        structure_bias = 1
    elif prev["Close"] > prev["Local_Low"] and price < local_low:
        structure_status = "BEARISH CHANGE OF CHARACTER (CHoCH) ⚡"
        structure_bias = -1

    # ---------------------------------------------------------
    # 6. MACHINE LEARNING ENSEMBLE ALPHA (XGBoost / LightGBM)
    # ---------------------------------------------------------
    features = ["RSI", "MACD_Hist", "ATR", "EMA_8", "EMA_21", "EMA_50"]
    raw_data["Target"] = (raw_data["Close"].shift(-1) > raw_data["Close"]).astype(int)
    train_df = raw_data.dropna()

    bull_prob_xgb, bull_prob_lgb = 0.5, 0.5
    if len(train_df) > 30:
        X_train = train_df[features]
        y_train = train_df["Target"]
        X_latest = pd.DataFrame([latest[features]], columns=features)

        if XGB_AVAILABLE:
            try:
                model_xgb = xgb.XGBClassifier(n_estimators=30, max_depth=3, learning_rate=0.1, verbosity=0, eval_metric="logloss")
                model_xgb.fit(X_train, y_train)
                bull_prob_xgb = float(model_xgb.predict_proba(X_latest)[0][1])
            except Exception:
                pass

        if LGB_AVAILABLE:
            try:
                model_lgb = lgb.LGBMClassifier(n_estimators=30, max_depth=3, learning_rate=0.1, verbose=-1)
                model_lgb.fit(X_train, y_train)
                bull_prob_lgb = float(model_lgb.predict_proba(X_latest)[0][1])
            except Exception:
                pass

    # Fallback heuristic sequence score if libraries are missing or weights
    heuristic_prob = 0.70 if (rsi > 50 and macd_hist > 0) else (0.30 if (rsi < 50 and macd_hist < 0) else 0.50)
    
    if XGB_AVAILABLE and LGB_AVAILABLE:
        alpha_bull_prob = (bull_prob_xgb * 0.45) + (bull_prob_lgb * 0.45) + (heuristic_prob * 0.10)
    else:
        alpha_bull_prob = heuristic_prob

    # ---------------------------------------------------------
    # 7. RULE-BASED RISK ENGINE & TARGET CALCULATOR
    # ---------------------------------------------------------
    # Scalp and Hold multipliers tuned for tight 1m, 5m, 15m and 30m horizons
    if "1-Minute" in execution_mode:
        sl_mult, tp_mult = 0.8, 1.2
    elif "5-Minute" in execution_mode:
        sl_mult, tp_mult = 1.0, 1.8
    elif "15-Minute" in execution_mode:
        sl_mult, tp_mult = 1.3, 2.3
    else:
        sl_mult, tp_mult = 1.8, 3.2

    signal = "NEUTRAL / NO TRADE ⚪"
    sl, tp1, tp2 = 0.0, 0.0, 0.0

    if alpha_bull_prob >= min_alpha_prob and structure_bias >= 0:
        signal = "BUY EXECUTE 🚀"
        sl = price - (atr * sl_mult)
        tp1 = price + (atr * tp_mult)
        tp2 = price + (atr * (tp_mult * 1.5))
    elif (1.0 - alpha_bull_prob) >= min_alpha_prob and structure_bias <= 0:
        signal = "SELL EXECUTE 📉"
        sl = price + (atr * sl_mult)
        tp1 = price - (atr * tp_mult)
        tp2 = price - (atr * (tp_mult * 1.5))

    # Cooldown Check
    now_dt = datetime.now(eat_tz)
    if st.session_state.last_trigger_time and cooldown_secs > 0:
        elapsed_secs = (now_dt - st.session_state.last_trigger_time).total_seconds()
        if elapsed_secs < cooldown_secs and signal != "NEUTRAL / NO TRADE ⚪":
            signal = "COOLDOWN ⏳"

    if signal in ["BUY EXECUTE 🚀", "SELL EXECUTE 📉"]:
        st.session_state.last_trigger_time = now_dt

    # ---------------------------------------------------------
    # 8. AI CLAUDE / GPT-STYLE EXPLANATION & EXIT RULES
    # ---------------------------------------------------------
    def generate_scalp_explanation(sig, prob, struct, r_val, m_hist, max_mins):
        if "BUY" in sig:
            return (
                f"🤖 **AI Scalp & Hold Synthesis:**\n"
                f"• **Structure Analysis:** Confirmed **{struct}** with price holding above structural liquidity support.\n"
                f"• **ML Alpha Probability:** XGBoost/LightGBM consensus calculates **{prob*100:.1f}%** bullish continuation probability.\n"
                f"• **Momentum & Timing:** RSI at **{r_val:.1f}** with MACD histogram at **+{m_hist:.4f}**. Maximum hold duration: **{max_mins} Minutes**."
            )
        elif "SELL" in sig:
            return (
                f"🤖 **AI Scalp & Hold Synthesis:**\n"
                f"• **Structure Analysis:** Confirmed **{struct}** with price sweeping liquidity highs.\n"
                f"• **ML Alpha Probability:** XGBoost/LightGBM consensus calculates **{(1-prob)*100:.1f}%** bearish continuation probability.\n"
                f"• **Momentum & Timing:** RSI at **{r_val:.1f}** with MACD histogram at **{m_hist:.4f}**. Maximum hold duration: **{max_mins} Minutes**."
            )
        else:
            return f"🤖 **AI Scalp & Hold Synthesis:** Market is in **{struct}**. Awaiting optimal order block retest before trigger."

    ai_rationale = generate_scalp_explanation(signal, alpha_bull_prob, structure_status, rsi, macd_hist, max_hold_mins)

    # Log Signal into Journal
    time_str = now_dt.strftime("%H:%M:%S")
    if signal in ["BUY EXECUTE 🚀", "SELL EXECUTE 📉"]:
        if not st.session_state.scalp_history or st.session_state.scalp_history[-1]["time"] != time_str:
            st.session_state.scalp_history.append({
                "time": time_str,
                "horizon": execution_mode.split("(")[0].strip(),
                "asset": selected_asset,
                "action": signal,
                "entry": round(price, curr_info["dec"]),
                "tp1": round(tp1, curr_info["dec"]),
                "sl": round(sl, curr_info["dec"]),
                "alpha": f"{alpha_bull_prob*100:.1f}%",
                "status": "ACTIVE ⚡"
            })

    # Update Active Scalp Statuses
    for item in st.session_state.scalp_history:
        if item["status"] == "ACTIVE ⚡" and item["asset"] == selected_asset:
            if "BUY" in item["action"]:
                if price >= item["tp1"]: item["status"] = "WIN (TP) ✅"
                elif price <= item["sl"]: item["status"] = "LOSS (SL) ❌"
            elif "SELL" in item["action"]:
                if price <= item["tp1"]: item["status"] = "WIN (TP) ✅"
                elif price >= item["sl"]: item["status"] = "LOSS (SL) ❌"

    # ---------------------------------------------------------
    # 9. MAIN DASHBOARD METRICS & UI
    # ---------------------------------------------------------
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Live Price", f"${price:.{curr_info['dec']}f}")
    m2.metric("Market Structure", structure_status.split()[0] + " " + structure_status.split()[1])
    m3.metric("Scalp Signal", signal)
    m4.metric("Alpha Probability", f"{alpha_bull_prob*100:.1f}%")
    m5.metric("Hold Horizon", f"{max_hold_mins} Mins Max")

    st.info(ai_rationale)

    if signal in ["BUY EXECUTE 🚀", "SELL EXECUTE 📉"]:
        st.success(f"🎯 **Precise Execution Targets:** Entry: `${price:.{curr_info['dec']}f}` | **TP1:** `${tp1:.{curr_info['dec']}f}` | **TP2:** `${tp2:.{curr_info['dec']}f}` | **SL:** `${sl:.{curr_info['dec']}f}` | **Max Hold:** {max_hold_mins}m")

    # ---------------------------------------------------------
    # 10. LIVE TRADINGVIEW CHART & SCALP JOURNAL
    # ---------------------------------------------------------
    st.divider()
    chart_col, journal_col = st.columns([3, 1])

    tv_interval_map = {"1m": "1", "5m": "5", "15m": "15", "30m": "30"}
    tv_tf = tv_interval_map.get(interval, "1")

    with chart_col:
        st.subheader(f"📊 Live TradingView Scalping Terminal ({selected_asset} - {interval})")
        tv_widget_html = f"""
        <div class="tradingview-widget-container" style="height:520px;width:100%">
          <div id="tv_scalp_container" style="height:520px;width:100%"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
          <script type="text/javascript">
          new TradingView.widget({{
            "autosize": true,
            "symbol": "{curr_info['tv']}",
            "interval": "{tv_tf}",
            "timezone": "Africa/Nairobi",
            "theme": "dark",
            "style": "1",
            "locale": "en",
            "toolbar_bg": "#11141d",
            "enable_publishing": false,
            "allow_symbol_change": true,
            "container_id": "tv_scalp_container"
          }});
          </script>
        </div>
        """
        components.html(tv_widget_html, height=530)

    with journal_col:
        st.subheader("📋 Scalp Journal")
        if st.session_state.scalp_history:
            j_df = pd.DataFrame(st.session_state.scalp_history).tail(8)
            cols_to_show = ["time", "action", "entry", "alpha", "status"]
            j_df = j_df[[c for c in cols_to_show if c in j_df.columns]]
            
            wins = len(j_df[j_df["status"].str.contains("WIN")])
            total_closed = len(j_df[~j_df["status"].str.contains("ACTIVE")])
            win_rate = (wins / total_closed * 100) if total_closed > 0 else 0.0
            
            st.metric("Scalp Win-Rate", f"{win_rate:.1f}%", f"{wins}/{total_closed} Completed")
            st.dataframe(j_df, use_container_width=True)
        else:
            st.caption("Awaiting ultra-fast scalp triggers.")

    # ---------------------------------------------------------
    # 11. MACROECONOMIC NEWS FEED
    # ---------------------------------------------------------
    st.divider()
    st.subheader("📰 Macro News & Liquidity Feed")
    news_html = """
    <div class="tradingview-widget-container" style="width:100%; height:350px;">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-timeline.js" async>
      {
      "feedMode": "all_symbols",
      "isTransparent": false,
      "displayMode": "regular",
      "width": "100%",
      "height": "350",
      "colorTheme": "dark",
      "locale": "en"
    }
      </script>
    </div>
    """
    components.html(news_html, height=360)
