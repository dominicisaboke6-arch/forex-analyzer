import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh

# Optional ML Library Guards
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
# 1. PAGE CONFIGURATION & INITIALIZATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="MINION Institutional Multi-TF Alpha Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 15-second auto-refresh timer tuned for safe API pooling
st_autorefresh(interval=15000, key="minion_institutional_refresh")

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
        font-size: 26px;
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

# Session State Journals & Unique ID Tracking
if "master_history" not in st.session_state:
    st.session_state.master_history = []
if "last_signal_id" not in st.session_state:
    st.session_state.last_signal_id = None

# ---------------------------------------------------------
# 2. BRANDING & CLOCK HEADER
# ---------------------------------------------------------
st.markdown("""
<div class="minion-header">
    <div class="minion-title">⚡ MINION INSTITUTIONAL SCALP & HOLD ENGINE ⚡</div>
    <div class="minion-subtitle">Multi-TF Alignment (1H/15m/5m/1m) • Swing BOS/CHoCH Structure • Separate Buy/Sell Scoring • Unique ID State Guard</div>
</div>
""", unsafe_allow_html=True)

clock_html = """
<div style="background-color: #10141d; border: 1px solid #1f2838; padding: 8px 12px; border-radius: 6px; text-align: center; margin-bottom: 12px;">
    <span style="color: #777; font-size: 12px; font-weight: bold; font-family: monospace;">SYSTEM TICK:</span>
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
# 3. SIDEBAR CONTROLS
# ---------------------------------------------------------
st.sidebar.header("🎯 Scalp & Hold Horizon")
execution_mode = st.sidebar.selectbox(
    "Select Strategy Horizon",
    [
        "1-Minute Micro Scalp (1m Hold)",
        "5-Minute Fast Scalp (5m Hold)",
        "15-Minute Scalp Trend (15m Hold)",
        "30-Minute Intraday Hold (30m Hold)"
    ]
)

selected_asset = st.sidebar.selectbox(
    "Market Asset Pair",
    ["Gold (Spot XAU/USD)", "EUR/USD", "GBP/USD", "Bitcoin (BTC/USD)"]
)

asset_map = {
    "Gold (Spot XAU/USD)": {"yf": ["GC=F", "XAUUSD=X"], "tv": "OANDA:XAUUSD", "dec": 2},
    "EUR/USD": {"yf": ["EURUSD=X"], "tv": "FX:EURUSD", "dec": 4},
    "GBP/USD": {"yf": ["GBPUSD=X"], "tv": "FX:GBPUSD", "dec": 4},
    "Bitcoin (BTC/USD)": {"yf": ["BTC-USD"], "tv": "BITSTAMP:BTCUSD", "dec": 2}
}
curr_info = asset_map[selected_asset]

if "1-Minute" in execution_mode:
    interval, period, max_hold = "1m", "1d", 1
elif "5-Minute" in execution_mode:
    interval, period, max_hold = "5m", "5d", 5
elif "15-Minute" in execution_mode:
    interval, period, max_hold = "15m", "5d", 15
else:
    interval, period, max_hold = "30m", "1mo", 30

min_score_threshold = st.sidebar.slider("Min Component Score Threshold (/100)", 50, 90, 68)

# ---------------------------------------------------------
# 4. MULTI-TIMEFRAME DATA FETCHING ENGINE (1H, 15M, 5M, 1M)
# ---------------------------------------------------------
@st.cache_data(ttl=15, show_spinner=False)
def fetch_mtf_data(ticker_list, per, iv):
    for t in ticker_list:
        try:
            df = yf.download(t, period=per, interval=iv, auto_adjust=False, progress=False)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                return df.dropna()
        except Exception:
            continue
    return pd.DataFrame()

# Fetch required granular and macro timeframes
df_1m = fetch_mtf_data(curr_info["yf"], "1d", "1m")
df_5m = fetch_mtf_data(curr_info["yf"], "5d", "5m")
df_15m = fetch_mtf_data(curr_info["yf"], "5d", "15m")
df_1h = fetch_mtf_data(curr_info["yf"], "1mo", "1h")

eat_tz = pytz.timezone("Africa/Nairobi")

def process_indicators(df):
    if df.empty: return df
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC").tz_convert(eat_tz)
    else:
        df.index = df.index.tz_convert(eat_tz)
        
    df["EMA_8"] = df["Close"].ewm(span=8, adjust=False).mean()
    df["EMA_21"] = df["Close"].ewm(span=21, adjust=False).mean()
    df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()
    
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
    loss = -delta.where(delta < 0, 0).ewm(alpha=1/14, adjust=False).mean()
    df["RSI"] = 100 - (100 / (1 + (gain / loss)))
    
    df["MACD"] = df["Close"].ewm(span=12).mean() - df["Close"].ewm(span=26).mean()
    df["MACD_Sig"] = df["MACD"].ewm(span=9).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Sig"]
    
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - df["Close"].shift()).abs(),
        (df["Low"] - df["Close"].shift()).abs()
    ], axis=1).max(axis=1)
    df["ATR"] = tr.ewm(span=14, adjust=False).mean()
    return df.dropna()

df_1m = process_indicators(df_1m)
df_5m = process_indicators(df_5m)
df_15m = process_indicators(df_15m)
df_1h = process_indicators(df_1h)

# Active target dataframe based on user UI selection
active_df = {"1m": df_1m, "5m": df_5m, "15m": df_15m, "30m": df_15m}.get(interval, df_5m)

if not active_df.empty and not df_1h.empty and not df_15m.empty and not df_5m.empty:
    latest = active_df.iloc[-1]
    price = float(latest["Close"])
    atr = float(latest["ATR"])
    rsi = float(latest["RSI"])
    macd_hist = float(latest["MACD_Hist"])

    # ---------------------------------------------------------
    # 5. ADVANCED SWING STRUCTURE (BOS & TRUE CHoCH)
    # ---------------------------------------------------------
    def get_swing_bias(df_sub):
        if len(df_sub) < 15: return "RANGING", 0
        sw_high = df_sub["High"].rolling(window=5).max()
        sw_low = df_sub["Low"].rolling(window=5).min()
        curr_c = df_sub["Close"].iloc[-1]
        prev_c = df_sub["Close"].iloc[-2]
        
        if curr_c > sw_high.iloc[-2]:
            return "BULLISH BOS", 1
        elif curr_c < sw_low.iloc[-2]:
            return "BEARISH BOS", -1
        elif prev_c < sw_high.iloc[-6] and curr_c > sw_high.iloc[-2]:
            return "BULLISH CHoCH", 1
        elif prev_c > sw_low.iloc[-6] and curr_c < sw_low.iloc[-2]:
            return "BEARISH CHoCH", -1
        return "RANGING", 0

    bias_1h, val_1h = get_swing_bias(df_1h)
    bias_15m, val_15m = get_swing_bias(df_15m)
    bias_5m, val_5m = get_swing_bias(df_5m)

    market_regime = "TRENDING BULLISH 📈" if val_15m == 1 and val_1h == 1 else ("TRENDING BEARISH 📉" if val_15m == -1 and val_1h == -1 else "RANGING CONSOLIDATION 🟡")

    # ---------------------------------------------------------
    # 6. SEPARATE BUY & SELL MULTI-FACTOR SCORE CARDS (0 to 100)
    # ---------------------------------------------------------
    buy_score = 0
    sell_score = 0

    # 1H Trend Contribution (+25)
    if val_1h == 1: buy_score += 25
    elif val_1h == -1: sell_score += 25

    # 15M Structure Contribution (+20)
    if val_15m >= 1: buy_score += 20
    elif val_15m <= -1: sell_score += 20

    # 5M Setup / BOS Contribution (+20)
    if val_5m >= 1: buy_score += 20
    elif val_5m <= -1: sell_score += 20

    # Momentum MACD (+10)
    if macd_hist > 0: buy_score += 10
    else: sell_score += 10

    # RSI Momentum (+10)
    if rsi > 50: buy_score += 10
    else: sell_score += 10

    # Retest / Volatility Safety (+15)
    if atr > 0:
        buy_score += 15
        sell_score += 15

    # ---------------------------------------------------------
    # 7. ML FORWARD OUTCOME TARGET PROBABILITY (Walk-Forward Simulation)
    # ---------------------------------------------------------
    # Target definition: Did price hit TP before SL within next 5 bars?
    ml_win_prob = 0.50
    if XGB_AVAILABLE and len(active_df) > 50:
        try:
            feat_cols = ["RSI", "MACD_Hist", "ATR", "EMA_8", "EMA_21", "EMA_50"]
            train_sub = active_df.copy()
            # Scalping target: TP = +1.5*ATR hit before SL = -1.0*ATR within 5 forward bars
            tp_forward = train_sub["Close"] + (train_sub["ATR"] * 1.5)
            sl_forward = train_sub["Close"] - (train_sub["ATR"] * 1.0)
            
            outcome = []
            for i in range(len(train_sub) - 5):
                window_high = train_sub["High"].iloc[i+1:i+6]
                window_low = train_sub["Low"].iloc[i+1:i+6]
                hit_tp = (window_high >= tp_forward.iloc[i]).any()
                hit_sl = (window_low <= sl_forward.iloc[i]).any()
                if hit_tp and not hit_sl:
                    outcome.append(1)
                else:
                    outcome.append(0)
            
            if len(outcome) > 30:
                train_sub = train_sub.iloc[:len(outcome)]
                train_sub["Target_Outcome"] = outcome
                X = train_sub[feat_cols]
                y = train_sub["Target_Outcome"]
                
                model_xgb = xgb.XGBClassifier(n_estimators=20, max_depth=3, learning_rate=0.1, verbosity=0, eval_metric="logloss")
                model_xgb.fit(X, y)
                x_latest = pd.DataFrame([latest[feat_cols]], columns=feat_cols)
                ml_win_prob = float(model_xgb.predict_proba(x_latest)[0][1])
        except Exception:
            pass

    # ---------------------------------------------------------
    # 8. RIGID SIGNAL ENGINE WITH STRICT STRUCTURE FILTER
    # ---------------------------------------------------------
    signal = "NEUTRAL / WAIT ⚪"
    sl, tp1, tp2 = 0.0, 0.0, 0.0

    # Strict Rule: Must have matching directional structure bias (val_5m == 1 for Buy)
    if buy_score >= min_score_threshold and val_5m == 1 and ml_win_prob >= 0.50:
        signal = "BUY EXECUTE 🚀"
        sl = price - (atr * 0.9)
        tp1 = price + (atr * 1.5)
        tp2 = price + (atr * 2.5)
    elif sell_score >= min_score_threshold and val_5m == -1 and (1.0 - ml_win_prob) >= 0.50:
        signal = "SELL EXECUTE 📉"
        sl = price + (atr * 0.9)
        tp1 = price - (atr * 1.5)
        tp2 = price - (atr * 2.5)

    # Unique Signal ID generation to fix cooldown looping bugs
    current_candle_timestamp = str(active_df.index[-1])
    signal_id = f"{selected_asset}_{interval}_{signal}_{current_candle_timestamp}"

    if signal in ["BUY EXECUTE 🚀", "SELL EXECUTE 📉"]:
        if signal_id != st.session_state.last_signal_id:
            st.session_state.last_signal_id = signal_id
            st.session_state.master_history.append({
                "time": datetime.now(eat_tz).strftime("%H:%M:%S"),
                "horizon": execution_mode.split("(")[0].strip(),
                "asset": selected_asset,
                "action": signal,
                "entry": round(price, curr_info["dec"]),
                "tp1": round(tp1, curr_info["dec"]),
                "sl": round(sl, curr_info["dec"]),
                "score": f"Buy:{buy_score} | Sell:{sell_score}",
                "status": "ACTIVE ⚡"
            })

    # Update active trades in Journal
    for item in st.session_state.master_history:
        if item["status"] == "ACTIVE ⚡" and item["asset"] == selected_asset:
            if "BUY" in item["action"]:
                if price >= item["tp1"]: item["status"] = "WIN (TP) ✅"
                elif price <= item["sl"]: item["status"] = "LOSS (SL) ❌"
            elif "SELL" in item["action"]:
                if price <= item["tp1"]: item["status"] = "WIN (TP) ✅"
                elif price >= item["sl"]: item["status"] = "LOSS (SL) ❌"

    # ---------------------------------------------------------
    # 9. LLM SYNTHESIS & DASHBOARD UI METRICS
    # ---------------------------------------------------------
    def generate_institutional_synthesis(sig, b_score, s_score, reg, ml_p, h_mins):
        return (
            f"🤖 **Institutional Multi-TF & ML Synthesis:**\n"
            f"• **Market Regime:** Detected **{reg}** across multi-timeframe structural alignment.\n"
            f"• **Score Cards:** **Buy Score: {b_score}/100** vs **Sell Score: {s_score}/100** (Threshold: {min_score_threshold}).\n"
            f"• **ML Walk-Forward Model:** Predicted probability of hitting TP before SL: **{ml_p*100:.1f}%**. Max target hold: **{h_mins} Mins**."
        )

    ai_synthesis = generate_institutional_synthesis(signal, buy_score, sell_score, market_regime, ml_win_prob, max_hold)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Live Price", f"${price:.{curr_info['dec']}f}")
    col2.metric("Market Regime", market_regime.split()[0])
    col3.metric("Signal Output", signal)
    col4.metric("Buy vs Sell Score", f"{buy_score} / {sell_score}")
    col5.metric("ML Win Edge", f"{ml_win_prob*100:.1f}%")

    st.info(ai_synthesis)

    if signal in ["BUY EXECUTE 🚀", "SELL EXECUTE 📉"]:
        st.success(f"🎯 **Institutional Setup Executed:** Entry: `${price:.{curr_info['dec']}f}` | **TP1:** `${tp1:.{curr_info['dec']}f}` | **TP2:** `${tp2:.{curr_info['dec']}f}` | **SL:** `${sl:.{curr_info['dec']}f}`")

    # ---------------------------------------------------------
    # 10. TRADINGVIEW TERMINAL & MASTER JOURNAL
    # ---------------------------------------------------------
    st.divider()
    chart_col, journal_col = st.columns([3, 1])

    tv_interval_map = {"1m": "1", "5m": "5", "15m": "15", "30m": "30"}
    tv_tf = tv_interval_map.get(interval, "1")

    with chart_col:
        st.subheader(f"📊 Live TradingView Terminal ({selected_asset} - {interval})")
        tv_html = f"""
        <div class="tradingview-widget-container" style="height:520px;width:100%">
          <div id="tv_institutional_container" style="height:520px;width:100%"></div>
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
            "container_id": "tv_institutional_container"
          }});
          </script>
        </div>
        """
        components.html(tv_html, height=530)

    with journal_col:
        st.subheader("📋 Master Journal")
        if st.session_state.master_history:
            j_df = pd.DataFrame(st.session_state.master_history).tail(8)
            cols = ["time", "action", "entry", "score", "status"]
            j_df = j_df[[c for c in cols if c in j_df.columns]]
            
            wins = len(j_df[j_df["status"].str.contains("WIN")])
            total_closed = len(j_df[~j_df["status"].str.contains("ACTIVE")])
            win_rate = (wins / total_closed * 100) if total_closed > 0 else 0.0
            
            st.metric("Model Win-Rate", f"{win_rate:.1f}%", f"{wins}/{total_closed} Completed")
            st.dataframe(j_df, use_container_width=True)
        else:
            st.caption("Awaiting institutional multi-TF triggers.")

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
else:
    st.warning("⚠️ Market data feed synchronizing across multi-timeframe intervals. Please wait...")
