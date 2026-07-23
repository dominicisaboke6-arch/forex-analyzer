import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
from streamlit_autorefresh import st_autorefresh
from twelvedata import TDClient

# ---------------------------------------------------------
# 1. PAGE CONFIG & MINION STYLING
# ---------------------------------------------------------
st.set_page_config(
    page_title="MINION | Live Gold & Multi-Asset Market Scanner",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Auto-refresh timer for live feed polling (every 10 seconds)
st_autorefresh(interval=10000, key="minion_live_poll")

# Hardcoded Twelve Data API Key
API_KEY = "a8c4eb7e1e424e479ea4c2f57b80fa65"
eat_tz = pytz.timezone("Africa/Nairobi")

st.markdown("""
<style>
    /* Dark MINION Theme Styling */
    .stApp { background-color: #0b0e14; color: #d0d7de; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    
    /* Top Ticker Bar */
    .ticker-bar {
        background-color: #121722;
        border-bottom: 1px solid #1f2838;
        padding: 6px 12px;
        font-size: 11px;
        font-family: monospace;
        display: flex;
        justify-content: space-between;
        margin-bottom: 12px;
        border-radius: 4px;
    }
    .ticker-item { margin-right: 15px; }
    .bullish { color: #00ffaa; }
    .bearish { color: #ff4d4d; }
    
    /* MINION Header */
    .minion-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background-color: #0e121a;
        padding: 10px 18px;
        border: 1px solid #232d3f;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .minion-logo { color: #f5c518; font-weight: 900; font-size: 22px; letter-spacing: 2px; }
    .minion-sub { color: #6b778d; font-size: 11px; font-weight: 600; letter-spacing: 1px; }

    /* Clean 3-Column Signal Card Styling */
    .aurum-sig-card {
        background-color: #121722;
        border: 1px solid #1f2838;
        border-radius: 6px;
        padding: 10px 14px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .sig-buy-badge { background-color: #00ffaa; color: #000; font-weight: 800; padding: 3px 8px; border-radius: 4px; font-size: 11px; }
    .sig-sell-badge { background-color: #ff4d4d; color: #fff; font-weight: 800; padding: 3px 8px; border-radius: 4px; font-size: 11px; }
    .sig-price-center { color: #f5c518; font-family: monospace; font-size: 15px; font-weight: bold; }
    .sig-latest-pill { background-color: #f5c518; color: #000; font-weight: 800; font-size: 9px; padding: 1px 5px; border-radius: 3px; margin-left: 6px; }
    .sig-time-right { color: #6b778d; font-size: 11px; font-family: monospace; }

    /* Scanning Live Bottom Footer */
    .scanning-footer {
        background: linear-gradient(90deg, #ff0055 0%, #ff2e63 100%);
        color: #ffffff;
        font-weight: 800;
        letter-spacing: 3px;
        text-align: center;
        padding: 10px;
        border-radius: 8px;
        font-size: 14px;
        margin-top: 15px;
        box-shadow: 0 0 15px rgba(255, 0, 85, 0.4);
    }
    
    /* Hide Streamlit default chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. STATE INITIALIZATION
# ---------------------------------------------------------
if "executed_signals" not in st.session_state:
    st.session_state.executed_signals = []
if "last_executed_candle" not in st.session_state:
    st.session_state.last_executed_candle = None

# ---------------------------------------------------------
# 3. TOP MINION BANNER & MACRO NEWS TICKER
# ---------------------------------------------------------
st.markdown("""
<div class="minion-header">
    <div>
        <span class="minion-logo">MN | MINION</span>
        <span class="minion-sub"> &nbsp;INSTITUTIONAL MULTI-TF ALPHA ENGINE</span>
    </div>
    <div>
        <span style="background: #1f2838; padding: 4px 10px; border-radius: 4px; font-size: 11px; color: #00ffcc; font-family: monospace;">● SCANNER ONLINE</span>
    </div>
</div>
<div class="ticker-bar">
    <span class="ticker-item"><span class="bullish">▲</span> Gold ETF Holdings Increase</span>
    <span class="ticker-item"><span class="bearish">▼</span> US Dollar Gains on GDP Report</span>
    <span class="ticker-item"><span class="bullish">▲</span> Gold Rises on Inflation Data</span>
    <span class="ticker-item"><span class="bullish">◆</span> Fed Keeps Rates Unchanged</span>
    <span class="ticker-item"><span class="bullish">▲</span> Central Banks Buy Gold Reserves</span>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. CONFIGURATION CONTROLS
# ---------------------------------------------------------
with st.expander("⚙️ Controls & Strategy Configuration", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        selected_asset = st.selectbox("Asset Pair", ["Gold (Spot XAU/USD)", "EUR/USD", "GBP/USD"])
    with c2:
        execution_mode = st.selectbox("Timeframe Horizon", ["5-Minute Scalp", "1-Minute Micro", "15-Minute Trend", "1-Hour Swing"])
    with c3:
        min_threshold = st.slider("Min Confluence Threshold Score (/100)", 50, 90, 65)

asset_map = {
    "Gold (Spot XAU/USD)": {"td": "XAU/USD", "tv": "OANDA:XAUUSD", "dec": 2},
    "EUR/USD": {"td": "EUR/USD", "tv": "FX:EURUSD", "dec": 4},
    "GBP/USD": {"td": "GBP/USD", "tv": "FX:GBPUSD", "dec": 4}
}
curr_info = asset_map[selected_asset]

td_interval_map = {"5-Minute Scalp": "5min", "1-Minute Micro": "1min", "15-Minute Trend": "15min", "1-Hour Swing": "1h"}
tv_interval_map = {"5-Minute Scalp": "5", "1-Minute Micro": "1", "15-Minute Trend": "15", "1-Hour Swing": "60"}

td_interval = td_interval_map[execution_mode]
tv_tf = tv_interval_map[execution_mode]

# ---------------------------------------------------------
# 5. REAL-TIME DATA & INDICATOR ENGINE
# ---------------------------------------------------------
@st.cache_data(ttl=8, show_spinner=False)
def fetch_realtime_data(symbol, interval, key):
    try:
        td = TDClient(apikey=key)
        ts = td.time_series(symbol=symbol, interval=interval, outputsize=80, timezone="Africa/Nairobi")
        df = ts.as_pandas()
        if df.empty: return None, "No feed data."
        df = df[["open", "high", "low", "close"]].astype(float)
        df.columns = ["Open", "High", "Low", "Close"]
        return df.sort_index(), None
    except Exception as e:
        return None, str(e)

raw_df, err = fetch_realtime_data(curr_info["td"], td_interval, API_KEY)

if err or raw_df is None:
    st.error(f"⚠️ Feed Sync Error: {err}")
    st.stop()

# Indicator Calculation
raw_df["EMA_8"] = raw_df["Close"].ewm(span=8, adjust=False).mean()
raw_df["EMA_21"] = raw_df["Close"].ewm(span=21, adjust=False).mean()
raw_df["EMA_50"] = raw_df["Close"].ewm(span=50, adjust=False).mean()

delta = raw_df["Close"].diff()
gain = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
loss = -delta.where(delta < 0, 0).ewm(alpha=1/14, adjust=False).mean()
raw_df["RSI"] = 100 - (100 / (1 + (gain / loss)))

raw_df["MACD"] = raw_df["Close"].ewm(span=12).mean() - raw_df["Close"].ewm(span=26).mean()
raw_df["MACD_Sig"] = raw_df["MACD"].ewm(span=9).mean()
raw_df["MACD_Hist"] = raw_df["MACD"] - raw_df["MACD_Sig"]

df = raw_df.dropna()
latest = df.iloc[-1]
latest_candle_time = str(df.index[-1])

price = float(latest["Close"])
rsi = float(latest["RSI"])
macd_h = float(latest["MACD_Hist"])

# Confluence Evaluation
buy_score, sell_score = 50, 50
if latest["EMA_8"] > latest["EMA_21"] > latest["EMA_50"]: buy_score += 20
elif latest["EMA_8"] < latest["EMA_21"] < latest["EMA_50"]: sell_score += 20

if macd_h > 0: buy_score += 15
else: sell_score += 15

if 50 < rsi < 75: buy_score += 15
elif 25 < rsi < 50: sell_score += 15

# ---------------------------------------------------------
# 6. STRICT 1 SIGNAL EXECUTION PER CANDLE LOGIC
# ---------------------------------------------------------
if st.session_state.last_executed_candle != latest_candle_time:
    if buy_score >= min_threshold and buy_score >= sell_score:
        st.session_state.last_executed_candle = latest_candle_time
        st.session_state.executed_signals.insert(0, {
            "type": "BUY",
            "price": f"${price:.{curr_info['dec']}f}",
            "time": datetime.now(eat_tz).strftime("%H:%M:%S"),
            "candle": latest_candle_time
        })
    elif sell_score >= min_threshold and sell_score > buy_score:
        st.session_state.last_executed_candle = latest_candle_time
        st.session_state.executed_signals.insert(0, {
            "type": "SELL",
            "price": f"${price:.{curr_info['dec']}f}",
            "time": datetime.now(eat_tz).strftime("%H:%M:%S"),
            "candle": latest_candle_time
        })

st.session_state.executed_signals = st.session_state.executed_signals[:5]

# ---------------------------------------------------------
# 7. MINION DASHBOARD GRID
# ---------------------------------------------------------
col_left, col_right = st.columns([2.6, 1.2])

# --- LEFT COLUMN: LIVE TRADINGVIEW CHART ---
with col_left:
    tv_html = f"""
    <div class="tradingview-widget-container" style="height:540px;width:100%">
      <div id="tv_minion_chart" style="height:540px;width:100%"></div>
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
        "toolbar_bg": "#0b0e14",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "container_id": "tv_minion_chart"
      }});
      </script>
    </div>
    """
    components.html(tv_html, height=545)
    
    st.markdown('<div class="scanning-footer">• SCANNING LIVE •</div>', unsafe_allow_html=True)

# --- RIGHT COLUMN: SIGNALS, NEWS & OMNI-MARKET AI CHAT ---
with col_right:
    # 1. LIVE SIGNALS PANEL (Cleaned HTML String to Prevent Tag Leaking)
    st.markdown("<h4 style='color:#f5c518; margin-bottom:8px; font-size:14px;'>⚡ LIVE EXECUTED SIGNALS</h4>", unsafe_allow_html=True)
    
    if st.session_state.executed_signals:
        for idx, sig in enumerate(st.session_state.executed_signals):
            badge_cls = "sig-buy-badge" if sig["type"] == "BUY" else "sig-sell-badge"
            latest_html = '<span class="sig-latest-pill">LATEST</span>' if idx == 0 else ""
            
            card_html = f'<div class="aurum-sig-card"><span class="{badge_cls}">{sig["type"]}</span><span class="sig-price-center">{sig["price"]} {latest_html}</span><span class="sig-time-right">{sig["time"]}</span></div>'
            st.markdown(card_html, unsafe_allow_html=True)
    else:
        st.info("Scanning candle close for threshold confluence setup...")

    st.divider()

    # 2. BREAKING NEWS & SENTIMENT PANEL
    st.markdown("<h4 style='color:#f5c518; margin-bottom:8px; font-size:14px;'>📰 BREAKING NEWS & SENTIMENT</h4>", unsafe_allow_html=True)
    st.markdown("""
    <div style="background-color:#121722; border:1px solid #1f2838; padding:10px 12px; border-radius:6px; margin-bottom:8px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <span style="color:#00ffaa; font-weight:bold; font-size:11px;">▲ BULLISH</span> 
                <span style="color:#6b778d; font-size:11px; margin-left:4px;">Reuters</span>
            </div>
            <span style="color:#6b778d; font-size:10px; font-family:monospace;">just now</span>
        </div>
        <div style="color:#ffffff; font-weight:bold; font-size:12px; margin-top:4px;">Gold Rises on Weakening US Dollar & Treasury Yields</div>
        <div style="color:#8892b0; font-size:11px; margin-top:2px;">Gold prices increased as the US dollar weakened against major currencies.</div>
    </div>
    
    <div style="background-color:#121722; border:1px solid #1f2838; padding:10px 12px; border-radius:6px; margin-bottom:12px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <span style="color:#ffaa00; font-weight:bold; font-size:11px;">◆ NEUTRAL</span> 
                <span style="color:#6b778d; font-size:11px; margin-left:4px;">Bloomberg</span>
            </div>
            <span style="color:#6b778d; font-size:10px; font-family:monospace;">just now</span>
        </div>
        <div style="color:#ffffff; font-weight:bold; font-size:12px; margin-top:4px;">Fed Holds Interest Rates Steady Pending Macro CPI Data</div>
        <div style="color:#8892b0; font-size:11px; margin-top:2px;">The Federal Reserve's decision to keep interest rates steady had little direct impact on gold prices.</div>
    </div>
    """, unsafe_allow_html=True)

    # 3. OMNI-MARKET AI ASSISTANT CHAT
    st.markdown("<h4 style='color:#f5c518; margin-bottom:4px; font-size:14px;'>🤖 MINION AI ASSISTANT</h4>", unsafe_allow_html=True)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "I'm scanning the gold market live. I'll flag anything worth acting on - or just ask me what's happening right now."}
        ]

    chat_container = st.container(height=180)
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    if query := st.chat_input("Ask anything..."):
        st.session_state.chat_history.append({"role": "user", "content": query})
        
        q_lower = query.lower()
        
        if "price" in q_lower or ("gold" in q_lower and "what" in q_lower):
            ans = f"Current live price for {selected_asset} is **${price:.{curr_info['dec']}f}** on the {execution_mode} timeframe."
        elif "signal" in q_lower or "latest" in q_lower:
            if st.session_state.executed_signals:
                top_sig = st.session_state.executed_signals[0]
                ans = f"The latest executed signal is **{top_sig['type']}** at **{top_sig['price']}** (Time: {top_sig['time']})."
            else:
                ans = "No signal executed yet for the current bar setup."
        elif "rsi" in q_lower:
            ans = f"The current 14-period RSI indicator is reading **{rsi:.1f}**."
        elif "fed" in q_lower or "rate" in q_lower or "news" in q_lower or "dollar" in q_lower:
            ans = "Central bank policy directly impacts Gold ($XAU/USD). Rate pauses or cuts typically weaken the US Dollar, creating bullish momentum for non-yielding assets like Gold."
        elif "strategy" in q_lower or "how" in q_lower:
            ans = f"MINION evaluates EMA ribbon crossovers (8/21/50), MACD histogram momentum, and RSI boundaries. A signal executes strictly once per candle when confluence reaches {min_threshold}/100."
        else:
            ans = f"Regarding your question: Gold is currently trading at **${price:.{curr_info['dec']}f}** with RSI at **{rsi:.1f}**. Ensure strict risk-to-reward parameters when acting on signals!"

        st.session_state.chat_history.append({"role": "assistant", "content": ans})
        st.rerun()
