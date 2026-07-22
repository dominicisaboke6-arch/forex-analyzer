import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh
import yfinance as yf

# Optional ML & GenAI Guards
try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION & INITIALIZATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="MINION Multi-TF Alpha Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Auto-refresh timer for live polling (every 15 seconds)
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
    .ai-box {
        background-color: #0d131f;
        border-left: 4px solid #00ffcc;
        padding: 15px;
        border-radius: 4px;
        margin-bottom: 15px;
        font-family: monospace;
        font-size: 13px;
    }
</style>
""", unsafe_allow_html=True)

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
    <div class="minion-subtitle">Multi-Indicator Confluence • Scalp & Hold Horizon • Free Data Feed • AI Breakdown</div>
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
# 3. SIDEBAR CONTROLS (HORIZON & STRATEGY SELECTION)
# ---------------------------------------------------------
st.sidebar.header("🎯 Strategy & Horizon Setup")
execution_mode = st.sidebar.selectbox(
    "Select Operating Horizon",
    [
        "1-Minute Micro Scalp (Scalp Mode)",
        "5-Minute Momentum Scalp (Scalp Mode)",
        "15-Minute Trend Scalp (Scalp/Hold)",
        "1-Hour Swing Position (Hold Mode)",
        "4-Hour Macro Trend (Hold Mode)"
    ]
)

selected_asset = st.sidebar.selectbox(
    "Market Asset Pair",
    ["Gold (Spot XAU/USD)", "EUR/USD", "GBP/USD"]
)

asset_map = {
    "Gold (Spot XAU/USD)": {"yf": "GC=F", "tv": "OANDA:XAUUSD", "dec": 2},
    "EUR/USD": {"yf": "EURUSD=X", "tv": "FX:EURUSD", "dec": 4},
    "GBP/USD": {"yf": "GBPUSD=X", "tv": "FX:GBPUSD", "dec": 4}
}
curr_info = asset_map[selected_asset]

if "1-Minute" in execution_mode:
    interval, yf_interval, atr_mult_tp = "1m", "1m", 1.5
elif "5-Minute" in execution_mode:
    interval, yf_interval, atr_mult_tp = "5m", "5m", 1.8
elif "15-Minute" in execution_mode:
    interval, yf_interval, atr_mult_tp = "15m", "15m", 2.2
elif "1-Hour" in execution_mode:
    interval, yf_interval, atr_mult_tp = "1h", "1h", 3.0
else:
    interval, yf_interval, atr_mult_tp = "4h", "1h", 4.5

min_score_threshold = st.sidebar.slider("Min Component Score Threshold (/100)", 50, 90, 68)

# ---------------------------------------------------------
# 4. FREE LIVE DATA ENGINE (yfinance)
# ---------------------------------------------------------
@st.cache_data(ttl=15, show_spinner=False)
def fetch_free_live_data(ticker, period_interval):
    try:
        period_val = "5d" if period_interval in ["1m", "5m", "15m"] else "60d"
        df = yf.download(ticker, period=period_val, interval=period_interval, progress=False)
        if df.empty:
            return None, "No data returned from Yahoo Finance."
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
        return df, None
    except Exception as e:
        return None, f"Data Fetch Error: {e}"

with st.spinner("Syncing comprehensive data feeds..."):
    raw_df, fetch_error = fetch_free_live_data(curr_info["yf"], yf_interval)

if fetch_error:
    st.error(f"⚠️ Live Feed Error: {fetch_error}")
    st.stop()

# ---------------------------------------------------------
# 5. TECHNICAL INDICATORS & CONFLUENCE SCORING
# ---------------------------------------------------------
eat_tz = pytz.timezone("Africa/Nairobi")

def process_all_indicators(df):
    if df.empty: 
        return df
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC").tz_convert(eat_tz)
    else:
        df.index = df.index.tz_convert(eat_tz)
        
    df["EMA_8"] = df["Close"].ewm(span=8, adjust=False).mean()
    df["EMA_21"] = df["Close"].ewm(span=21, adjust=False).mean()
    df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["SMA_200"] = df["Close"].rolling(window=200).mean()
    
    delta = df["Close"].diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
    loss = -delta.where(delta < 0, 0).ewm(alpha=1/14, adjust=False).mean()
    df["RSI"] = 100 - (100 / (1 + (gain / loss)))
    
    df["MACD"] = df["Close"].ewm(span=12).mean() - df["Close"].ewm(span=26).mean()
    df["MACD_Sig"] = df["MACD"].ewm(span=9).mean()
    df["MACD_Hist"] = df["MACD"] - df["MACD_Sig"]
    
    df["BB_Mid"] = df["Close"].rolling(window=20).mean()
    bb_std = df["Close"].rolling(window=20).std()
    df["BB_Upper"] = df["BB_Mid"] + (bb_std * 2)
    df["BB_Lower"] = df["BB_Mid"] - (bb_std * 2)
    
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - df["Close"].shift()).abs(),
        (df["Low"] - df["Close"].shift()).abs()
    ], axis=1).max(axis=1)
    df["ATR"] = tr.ewm(span=14, adjust=False).mean()
    return df.dropna()

active_df = process_all_indicators(raw_df)

if not active_df.empty:
    latest = active_df.iloc[-1]
    price = float(latest["Close"])
    atr = float(latest["ATR"])
    rsi = float(latest["RSI"])
    macd_hist = float(latest["MACD_Hist"])

    def evaluate_confluence(row, df_sub):
        b_score, s_score = 50, 50
        reasons_buy = []
        reasons_sell = []

        if row["EMA_8"] > row["EMA_21"] > row["EMA_50"]:
            b_score += 15
            reasons_buy.append("EMA Ribbon aligned bullish (8 > 21 > 50)")
        elif row["EMA_8"] < row["EMA_21"] < row["EMA_50"]:
            s_score += 15
            reasons_sell.append("EMA Ribbon aligned bearish (8 < 21 < 50)")

        if row["MACD_Hist"] > 0:
            b_score += 15
            reasons_buy.append("MACD momentum is positive")
        else:
            s_score += 15
            reasons_sell.append("MACD momentum is negative")

        if 50 < row["RSI"] < 75:
            b_score += 10
            reasons_buy.append(f"RSI bullish zone ({row['RSI']:.1f})")
        elif 25 < row["RSI"] < 50:
            s_score += 10
            reasons_sell.append(f"RSI bearish zone ({row['RSI']:.1f})")

        if row["Close"] <= row["BB_Lower"]:
            b_score += 10
            reasons_buy.append("Price testing lower Bollinger Band (Mean Reversion / Bounce)")
        elif row["Close"] >= row["BB_Upper"]:
            s_score += 10
            reasons_sell.append("Price testing upper Bollinger Band (Overextended)")

        return b_score, s_score, reasons_buy, reasons_sell

    buy_score, s_score, buy_reasons, sell_reasons = evaluate_confluence(latest, active_df)

    ml_win_prob = 0.55
    if XGB_AVAILABLE and len(active_df) > 30:
        try:
            feat_cols = ["RSI", "MACD_Hist", "ATR", "EMA_8", "EMA_21", "EMA_50"]
            train_sub = active_df.copy()
            tp_forward = train_sub["Close"] + (train_sub["ATR"] * atr_mult_tp)
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
    active_reasons = []

    if buy_score >= min_score_threshold and buy_score >= s_score:
        signal = "BUY EXECUTE 🚀"
        sl = price - (atr * 1.0)
        tp1 = price + (atr * atr_mult_tp)
        tp2 = price + (atr * (atr_mult_tp * 1.6))
        active_reasons = buy_reasons
    elif s_score >= min_score_threshold and s_score > buy_score:
        signal = "SELL EXECUTE 📉"
        sl = price + (atr * 1.0)
        tp1 = price - (atr * atr_mult_tp)
        tp2 = price - (atr * (atr_mult_tp * 1.6))
        active_reasons = sell_reasons

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
                "score": f"Buy:{buy_score} | Sell:{s_score}",
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

    # ---------------------------------------------------------
    # 6. DASHBOARD DISPLAY & AI EXPLANATION LAYER
    # ---------------------------------------------------------
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Live Price", f"${price:.{curr_info['dec']}f}")
    col2.metric("Horizon Mode", execution_mode.split("(")[1].replace(")", ""))
    col3.metric("Signal Output", signal)
    col4.metric("Confluence Score", f"B:{buy_score} | S:{s_score}")
    col5.metric("AI Confidence Edge", f"{ml_win_prob*100:.1f}%")

    st.markdown("### 🤖 AI Market Analyst Explanation")
    reason_bullet_str = "".join([f"<li>{r}</li>" for r in active_reasons]) if active_reasons else "<li>Market conditions are currently mixed; awaiting clearer confirmation across indicators.</li>"
    
    ai_explanation_html = f"""
    <div class="ai-box">
        <b>Current Analysis Breakdown ({selected_asset} @ {interval}):</b><br>
        The engine scanned price action using multi-indicator confluence (EMA ribbons, RSI momentum, MACD histogram, and Bollinger Band boundaries).<br><br>
        <b>Detected Factors:</b>
        <ul>
            {reason_bullet_str}
        </ul>
        <b>Execution Outlook:</b> Current sentiment score yields a <b>{max(buy_score, s_score)}/100</b> rating with an estimated model win probability of <b>{ml_win_prob*100:.1f}%</b> under a {execution_mode}.
    </div>
    """
    st.markdown(ai_explanation_html, unsafe_allow_html=True)

    st.divider()
    chart_col, journal_col = st.columns([3, 1])
    tv_tf = {"1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240"}.get(interval, "1")

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
            cols = ["time", "horizon", "action", "entry", "tp1", "sl", "status"]
            j_df = j_df[[c for c in cols if c in j_df.columns]]
            
            wins = len(j_df[j_df["status"].str.contains("WIN")])
            total_closed = len(j_df[~j_df["status"].str.contains("ACTIVE")])
            win_rate = (wins / total_closed * 100) if total_closed > 0 else 0.0
            
            st.metric("Model Win-Rate", f"{win_rate:.1f}%", f"{wins}/{total_closed} Completed")
            st.dataframe(j_df, use_container_width=True)
        else:
            st.caption("Awaiting signals.")
else:
    st.error("⚠️ Unable to process indicator data.")
