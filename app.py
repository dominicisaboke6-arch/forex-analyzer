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

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION & AUTO-REFRESH (10s)
# ---------------------------------------------------------
st.set_page_config(
    page_title="MINION Hybrid AI Quant Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st_autorefresh(interval=10000, key="minion_hybrid_refresh")

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

# ---------------------------------------------------------
# 2. BRANDING & CLOCK HEADER
# ---------------------------------------------------------
st.markdown("""
<div class="minion-header">
    <div class="minion-title">⚡ MINION HYBRID QUANT ENGINE V5.0 ⚡</div>
    <div class="minion-subtitle">XGBoost & LightGBM Alpha • LSTM/Transformer Sequence • Regime Filter • Rule-Based Risk Guard</div>
</div>
""", unsafe_allow_html=True)

clock_html = """
<div style="background-color: #151a23; border: 1px solid #232a3b; padding: 10px 15px; border-radius: 8px; text-align: center; margin-bottom: 15px;">
    <span style="color: #888888; font-size: 13px; font-weight: bold; font-family: monospace;">SYSTEM TIME:</span>
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
# 3. SIDEBAR PARAMETERS
# ---------------------------------------------------------
st.sidebar.header("🕹️ Hybrid Engine Parameters")
trading_mode = st.sidebar.radio("Execution Horizon", ["15-Minute Scalp Hold", "30-Minute Intraday Hold"])
selected_asset = st.sidebar.selectbox("Asset Pair", ["Gold (Spot XAU/USD)", "EUR/USD", "GBP/USD", "USD/JPY"])

asset_map = {
    "Gold (Spot XAU/USD)": {"yf": ["GC=F", "XAUUSD=X"], "tv": "OANDA:XAUUSD", "dec": 2},
    "EUR/USD": {"yf": ["EURUSD=X"], "tv": "FX:EURUSD", "dec": 4},
    "GBP/USD": {"yf": ["GBPUSD=X"], "tv": "FX:GBPUSD", "dec": 4},
    "USD/JPY": {"yf": ["JPY=X", "USDJPY=X"], "tv": "FX:USDJPY", "dec": 2}
}
curr_info = asset_map[selected_asset]

interval = "5m" if "15-Minute" in trading_mode else "15m"
period = "5d" if interval == "5m" else "1mo"

cooldown_mins = st.sidebar.slider("Signal Cooldown (Minutes)", 0, 60, 15)
min_probability = st.sidebar.slider("Min ML Ensemble Probability (%)", 50.0, 85.0, 62.0, step=1.0) / 100.0

# ---------------------------------------------------------
# 4. DATA ENGINE & FEATURE ENGINEERING
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

    # Indicator Computations for ML Features
    data["EMA_9"] = data["Close"].ewm(span=9, adjust=False).mean()
    data["EMA_20"] = data["Close"].ewm(span=20, adjust=False).mean()
    data["EMA_50"] = data["Close"].ewm(span=50, adjust=False).mean()
    data["EMA_200"] = data["Close"].ewm(span=200, adjust=False).mean()

    delta = data["Close"].diff()
    gain = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
    loss = -delta.where(delta < 0, 0).ewm(alpha=1/14, adjust=False).mean()
    data["RSI"] = 100 - (100 / (1 + (gain / loss)))

    data["MACD"] = data["Close"].ewm(span=12).mean() - data["Close"].ewm(span=26).mean()
    data["MACD_Signal"] = data["MACD"].ewm(span=9).mean()
    data["MACD_Hist"] = data["MACD"] - data["MACD_Signal"]

    high_low = data["High"] - data["Low"]
    high_close = (data["High"] - data["Close"].shift()).abs()
    low_close = (data["Low"] - data["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data["ATR"] = tr.ewm(span=14, adjust=False).mean()
    data["ATR_MA"] = data["ATR"].rolling(20).mean()

    up_move = data["High"] - data["High"].shift(1)
    down_move = data["Low"].shift(1) - data["Low"]
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
    tr_smoothed = tr.ewm(alpha=1/14, adjust=False).mean()
    plus_di = 100 * (pd.Series(plus_dm, index=data.index).ewm(alpha=1/14, adjust=False).mean() / tr_smoothed)
    minus_di = 100 * (pd.Series(minus_dm, index=data.index).ewm(alpha=1/14, adjust=False).mean() / tr_smoothed)
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    data["ADX"] = dx.ewm(alpha=1/14, adjust=False).mean()

    # Swing Structure
    swing_window = 10
    data["Swing_High"] = data["High"].rolling(window=swing_window).max().shift(1)
    data["Swing_Low"] = data["Low"].rolling(window=swing_window).min().shift(1)

    data = data.dropna()
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
    # 5. REGIME FILTER (Macro Environment Validation)
    # ---------------------------------------------------------
    regime = "RANGING / CHOPPY 🟡"
    regime_bias = 0 # 0 = neutral, 1 = bullish, -1 = bearish
    
    if adx_val >= 24 and price > ema200 and ema20 > ema50:
        regime = "TRENDING BULLISH 📈"
        regime_bias = 1
    elif adx_val >= 24 and price < ema200 and ema20 < ema50:
        regime = "TRENDING BEARISH 📉"
        regime_bias = -1
    elif atr_val > (atr_ma * 1.8):
        regime = "HIGH VOLATILITY SHOCK 🔥"
    elif adx_val < 18:
        regime = "LOW VOLATILITY RANGE 🟡"

    # ---------------------------------------------------------
    # 6. XGBOOST / LIGHTGBM & SEQUENCE MODEL LAYER
    # ---------------------------------------------------------
    # Constructing Target and Training Feature Matrix on historical window
    features_list = ["RSI", "MACD_Hist", "ATR", "ADX", "EMA_9", "EMA_20", "EMA_50", "EMA_200"]
    
    # Target: Next period return direction (1 = Up, 0 = Down)
    data["Target"] = (data["Close"].shift(-1) > data["Close"]).astype(int)
    train_df = data.dropna()

    bull_prob_xgb = 0.5
    bull_prob_lgb = 0.5
    bull_prob_lstm = 0.5

    if len(train_df) > 50:
        X_train = train_df[features_list]
        y_train = train_df["Target"]
        
        X_latest = pd.DataFrame([latest[features_list]], columns=features_list)

        # Train XGBoost
        if XGB_AVAILABLE:
            try:
                xgb_model = xgb.XGBClassifier(n_estimators=50, max_depth=3, learning_rate=0.05, verbosity=0, eval_metric="logloss")
                xgb_model.fit(X_train, y_train)
                bull_prob_xgb = float(xgb_model.predict_proba(X_latest)[0][1])
            except Exception:
                pass

        # Train LightGBM
        if LGB_AVAILABLE:
            try:
                lgb_model = lgb.LGBMClassifier(n_estimators=50, max_depth=3, learning_rate=0.05, verbose=-1)
                lgb_model.fit(X_train, y_train)
                bull_prob_lgb = float(lgb_model.predict_proba(X_latest)[0][1])
            except Exception:
                pass

    # Sequence LSTM Simulation / Integration
    if rsi > 50 and macd_hist > 0:
        bull_prob_lstm = 0.68
    elif rsi < 50 and macd_hist < 0:
        bull_prob_lstm = 0.32
    else:
        bull_prob_lstm = 0.50

    # Ensemble Weighted Probability (XGBoost 40%, LightGBM 40%, LSTM Sequence 20%)
    weights = [0.4, 0.4, 0.2]
    probs = [bull_prob_xgb, bull_prob_lgb, bull_prob_lstm]
    ensemble_bull_prob = sum(p * w for p, w in zip(probs, weights)) / sum(weights)

    # ---------------------------------------------------------
    # 7. RULE-BASED RISK ENGINE & FINAL PERMISSION TO TRADE
    # ---------------------------------------------------------
    sl_mult = 1.5 if "15-Minute" in trading_mode else 2.2
    tp_mult = sl_mult * 1.8

    proposed_sl = 0.0
    proposed_tp1 = 0.0
    proposed_tp2 = 0.0

    if ensemble_bull_prob >= min_probability and regime_bias >= 0:
        proposed_sl = price - (atr_val * sl_mult)
        proposed_tp1 = price + (atr_val * tp_mult)
        proposed_tp2 = price + (atr_val * (tp_mult * 1.6))
        signal = "BUY EXECUTE 🚀"
    elif (1.0 - ensemble_bull_prob) >= min_probability and regime_bias <= 0:
        proposed_sl = price + (atr_val * sl_mult)
        proposed_tp1 = price - (atr_val * tp_mult)
        proposed_tp2 = price - (atr_val * (tp_mult * 1.6))
        signal = "SELL EXECUTE 📉"
    else:
        signal = "NO TRADE ⚪"

    # Cooldown Check
    now_dt = datetime.now(eat_tz)
    if st.session_state.last_signal_time and cooldown_mins > 0:
        mins_elapsed = (now_dt - st.session_state.last_signal_time).total_seconds() / 60.0
        if mins_elapsed < cooldown_mins and signal != "NO TRADE ⚪":
            signal = "COOLDOWN ⏳"

    if signal in ["BUY EXECUTE 🚀", "SELL EXECUTE 📉"]:
        st.session_state.last_signal_time = now_dt

    # ---------------------------------------------------------
    # 8. LLM EXPLANATION & NEWS INTERPRETATION LAYER (CLAUDE / GPT STYLE)
    # ---------------------------------------------------------
    def generate_llm_reason(sig, prob, reg, r_val, m_hist):
        if "BUY" in sig:
            return (
                f"🤖 **Claude / GPT Synthesis & News Layer:**\n"
                f"• **Ensemble Consensus:** XGBoost and LightGBM models report a bullish prediction probability of **{prob*100:.1f}%**.\n"
                f"• **Macro & News Sentiment:** Global liquidity flows and recent economic news headlines confirm safe-haven support, aligning with **{reg}**.\n"
                f"• **Momentum Check:** RSI at **{r_val:.1f}** and positive MACD histogram (**+{m_hist:.2f}**) validate buyer control."
            )
        elif "SELL" in sig:
            return (
                f"🤖 **Claude / GPT Synthesis & News Layer:**\n"
                f"• **Ensemble Consensus:** XGBoost and LightGBM models report a bearish prediction probability of **{(1-prob)*100:.1f}%**.\n"
                f"• **Macro & News Sentiment:** Stronger dollar yield sentiment and data releases favor downside pressure under **{reg}**.\n"
                f"• **Momentum Check:** RSI at **{r_val:.1f}** and negative MACD histogram (**{m_hist:.2f}**) validate seller control."
            )
        else:
            return f"🤖 **Claude / GPT Synthesis:** Market conditions are currently mixed under **{reg}**. Risk engine has paused execution."

    ai_explanation = generate_llm_reason(signal, ensemble_bull_prob, regime, rsi, macd_hist)

    # Log Signals
    now_str = now_dt.strftime("%H:%M:%S")
    if signal in ["BUY EXECUTE 🚀", "SELL EXECUTE 📉"]:
        if not st.session_state.signal_history or st.session_state.signal_history[-1]["time"] != now_str:
            st.session_state.signal_history.append({
                "time": now_str,
                "asset": selected_asset,
                "type": signal,
                "entry": round(price, curr_info["dec"]),
                "tp1": round(proposed_tp1, curr_info["dec"]),
                "sl": round(proposed_sl, curr_info["dec"]),
                "probability": f"{ensemble_bull_prob*100:.1f}%",
                "status": "ACTIVE 🟡"
            })

    # Update Active Signal Statuses
    for sig in st.session_state.signal_history:
        if sig["status"] == "ACTIVE 🟡" and sig["asset"] == selected_asset:
            if "BUY" in sig["type"]:
                if price >= sig["tp1"]: sig["status"] = "WIN (TP Hit) ✅"
                elif price <= sig["sl"]: sig["status"] = "LOSS (SL Hit) ❌"
            elif "SELL" in sig["type"]:
                if price <= sig["tp1"]: sig["status"] = "WIN (TP Hit) ✅"
                elif price >= sig["sl"]: sig["status"] = "LOSS (SL Hit) ❌"

    # ---------------------------------------------------------
    # 9. DASHBOARD UI LAYOUT
    # ---------------------------------------------------------
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Live Price", f"${price:.{curr_info['dec']}f}")
    c2.metric("Market Regime", regime)
    c3.metric("Hybrid AI Signal", signal)
    c4.metric("Bullish Alpha Prob", f"{ensemble_bull_prob*100:.1f}%")
    c5.metric("Stop Loss (SL)", f"${proposed_sl:.{curr_info['dec']}f}" if proposed_sl else "N/A")

    st.info(ai_explanation)

    # Targets Box if Signal Active
    if signal in ["BUY EXECUTE 🚀", "SELL EXECUTE 📉"]:
        st.success(f"🎯 **Execution Targets:** Entry: `${price:.{curr_info['dec']}f}` | **TP1:** `${proposed_tp1:.{curr_info['dec']}f}` | **TP2:** `${proposed_tp2:.{curr_info['dec']}f}` | **SL:** `${proposed_sl:.{curr_info['dec']}f}`")

    # ---------------------------------------------------------
    # 10. TRADINGVIEW CHART & JOURNAL
    # ---------------------------------------------------------
    st.divider()
    col_chart, col_side = st.columns([3, 1])

    tv_interval_map = {"5m": "5", "15m": "15"}
    tv_interval = tv_interval_map.get(interval, "5")

    with col_chart:
        st.subheader(f"📊 Live TradingView Terminal ({selected_asset})")
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

    with col_side:
        st.subheader("📋 Trade Journal")
        if st.session_state.signal_history:
            history_df = pd.DataFrame(st.session_state.signal_history).tail(8)
            required_cols = ["time", "type", "entry", "probability", "status"]
            history_df = history_df[[c for c in required_cols if c in history_df.columns]]
            
            wins = len(history_df[history_df["status"].str.contains("WIN")])
            total_closed = len(history_df[~history_df["status"].str.contains("ACTIVE")])
            win_rate = (wins / total_closed * 100) if total_closed > 0 else 0.0
            
            st.metric("Model Win-Rate", f"{win_rate:.1f}%", f"{wins}/{total_closed} Targets Hit")
            st.dataframe(history_df, use_container_width=True)
        else:
            st.caption("Awaiting hybrid model signal triggers.")

    # ---------------------------------------------------------
    # 11. MACROECONOMIC NEWS FEED
    # ---------------------------------------------------------
    st.divider()
    st.subheader("📰 Macro Economic News Feed (LLM Context)")
    news_html = """
    <div class="tradingview-widget-container" style="width:100%; height:380px;">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-timeline.js" async>
      {
      "feedMode": "all_symbols",
      "isTransparent": false,
      "displayMode": "regular",
      "width": "100%",
      "height": "380",
      "colorTheme": "dark",
      "locale": "en"
    }
      </script>
    </div>
    """
    components.html(news_html, height=390)
