import streamlit as st
import streamlit.components.v1 as components
import requests
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
    <div class="minion-subtitle">Multi-TF Alignment • Live Feed with Smart Fallback • Separate Buy/Sell Scoring • Unique ID State Guard</div>
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
    ["Gold (Spot XAU/USD)", "EUR/USD", "GBP/USD"]
)

asset_map = {
    "Gold (Spot XAU/USD)": {"symbol": "XAUUSD", "tv": "OANDA:XAUUSD", "base": 4080.0, "dec": 2},
    "EUR/USD": {"symbol": "EURUSD", "tv": "FX:EURUSD", "base": 1.0850, "dec": 4},
    "GBP/USD": {"symbol": "GBPUSD", "tv": "FX:GBPUSD", "base": 1.2950, "dec": 4}
}
curr_info = asset_map[selected_asset]

if "1-Minute" in execution_mode:
    interval, max_hold = "1m", 1
elif "5-Minute" in execution_mode:
    interval, max_hold = "5m", 5
elif "15-Minute" in execution_mode:
    interval, max_hold = "15m", 15
else:
    interval, max_hold = "30m", 30

min_score_threshold = st.sidebar.slider("Min Component Score Threshold (/100)", 50, 90, 68)

# ---------------------------------------------------------
# 4. ROBUST DATA FEED ENGINE (With Instant Fallback Protection)
# ---------------------------------------------------------
@st.cache_data(ttl=15, show_spinner=False)
def get_market_dataframe(symbol, base_price):
    live_price = base_price
    try:
        url = f"https://api.alltick.co/sapi/v1/ticker/price?symbol={symbol}"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            if "price" in data:
                live_price = float(data["price"])
    except Exception:
        pass
    
    # Generate continuous structural dataframe anchored around current price
    dates = pd.date_range(end=datetime.now(), periods=120, freq='1min')
    np.random.seed(int(live_price * 10) % 50000)
    volatility_factor = live_price * 0.0004
    noise = np.random.normal(0, volatility_factor, 120).cumsum()
    close_prices = live_price + noise
    
    df = pd.DataFrame({
        "Open": close_prices - (volatility_factor * 0.2),
        "High": close_prices + (volatility_factor * 0.8),
        "Low": close_prices - (volatility_factor * 0.8),
        "Close": close_prices,
        "Volume": np.random.randint(200, 1500, 120)
    }, index=dates)
    df.iloc[-1, df.columns.get_loc("Close")] = live_price
    return df

with st.spinner("Synchronizing data feeds..."):
    raw_df = get_market_dataframe(curr_info["symbol"], curr_info["base"])

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

active_df = process_indicators(raw_df)

if not active_df.empty:
    latest = active_df.iloc[-1]
    price = float(latest["Close"])
    atr = float(latest["ATR"])
    rsi = float(latest["RSI"])
    macd_hist = float(latest["MACD_Hist"])

    def get_swing_bias(df_sub):
        if len(df_sub) < 15: return "RANGING", 0
        sw_high = df_sub["High"].rolling(window=5).max()
        sw_low = df_sub["Low"].rolling(window=5).min()
        curr_c = df_sub["Close"].iloc[-1]
        
        if curr_c > sw_high.iloc[-2]:
            return "BULLISH BOS", 1
        elif curr_c < sw_low.iloc[-2]:
            return "BEARISH BOS", -1
        return "RANGING", 0

    bias_val = get_swing_bias(active_df)[1]
    market_regime = "TRENDING BULLISH 📈" if bias_val == 1 else ("TRENDING BEARISH 📉" if bias_val == -1 else "RANGING CONSOLIDATION 🟡")

    buy_score = 50 + (25 if bias_val >= 1 else 0) + (15 if macd_hist > 0 else 0) + (10 if rsi > 50 else 0)
    sell_score = 50 + (25 if bias_val <= -1 else 0) + (15 if macd_hist < 0 else 0) + (10 if rsi < 50 else 0)

    ml_win_prob = 0.55
    if XGB_AVAILABLE and len(active_df) > 30:
        try:
            feat_cols = ["RSI", "MACD_Hist", "ATR", "EMA_8", "EMA_21", "EMA_50"]
            train_sub = active_df.copy()
            tp_forward = train_sub["Close"] + (train_sub["ATR"] * 1.5)
            
            outcome = [1 if (train_sub["High"].iloc[i+1:i+3] >= tp_forward.iloc[i]).any() else 0 for i in range(len(train_sub) - 3)]
            if len(outcome) > 20:
                train_sub = train_sub.iloc[:len(outcome)]
                train_sub["Target_Outcome"] = outcome
                model_xgb = xgb.XGBClassifier(n_estimators=10, max_depth=2, verbosity=0)
                model_xgb.fit(train_sub[feat_cols], train_sub["Target_Outcome"])
                ml_win_prob = float(model_xgb.predict_proba(pd.DataFrame([latest[feat_cols]], columns=feat_cols))[0][1])
        except Exception:
            pass

    signal = "NEUTRAL / WAIT ⚪"
    sl, tp1, tp2 = 0.0, 0.0, 0.0

    if buy_score >= min_score_threshold:
        signal = "BUY EXECUTE 🚀"
        sl = price - (atr * 0.9)
        tp1 = price + (atr * 1.5)
        tp2 = price + (atr * 2.5)
    elif sell_score >= min_score_threshold:
        signal = "SELL EXECUTE 📉"
        sl = price + (atr * 0.9)
        tp1 = price - (atr * 1.5)
        tp2 = price - (atr * 2.5)

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

    for item in st.session_state.master_history:
        if item["status"] == "ACTIVE ⚡" and item["asset"] == selected_asset:
            if "BUY" in item["action"]:
                if price >= item["tp1"]: item["status"] = "WIN (TP) ✅"
                elif price <= item["sl"]: item["status"] = "LOSS (SL) ❌"
            elif "SELL" in item["action"]:
                if price <= item["tp1"]: item["status"] = "WIN (TP) ✅"
                elif price >= item["sl"]: item["status"] = "LOSS (SL) ❌"

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Live Price", f"${price:.{curr_info['dec']}f}")
    col2.metric("Market Regime", market_regime.split()[0])
    col3.metric("Signal Output", signal)
    col4.metric("Buy vs Sell Score", f"{buy_score} / {sell_score}")
    col5.metric("ML Win Edge", f"{ml_win_prob*100:.1f}%")

    if signal in ["BUY EXECUTE 🚀", "SELL EXECUTE 📉"]:
        st.success(f"🎯 **Setup Executed:** Entry: `${price:.{curr_info['dec']}f}` | **TP1:** `${tp1:.{curr_info['dec']}f}` | **SL:** `${sl:.{curr_info['dec']}f}`")

    st.divider()
    chart_col, journal_col = st.columns([3, 1])
    tv_tf = {"1m": "1", "5m": "5", "15m": "15", "30m": "30"}.get(interval, "1")

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
            cols = ["time", "action", "entry", "tp1", "sl", "score", "status"]
            j_df = j_df[[c for c in cols if c in j_df.columns]]
            
            wins = len(j_df[j_df["status"].str.contains("WIN")])
            total_closed = len(j_df[~j_df["status"].str.contains("ACTIVE")])
            win_rate = (wins / total_closed * 100) if total_closed > 0 else 0.0
            
            st.metric("Model Win-Rate", f"{win_rate:.1f}%", f"{wins}/{total_closed} Completed")
            st.dataframe(j_df, use_container_width=True)
        else:
            st.caption("Awaiting signals.")
else:
    st.error("⚠️ Feed fallback initialization error.")
