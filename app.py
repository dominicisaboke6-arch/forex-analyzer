import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
import pytz
import pandas as pd
import numpy as np
import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh
from twelvedata import TDClient

# ---------------------------------------------------------
# 1. PAGE CONFIG & STYLING
# ---------------------------------------------------------
st.set_page_config(
    page_title="MINION | Live Gold & Multi-Asset Market Scanner",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st_autorefresh(interval=10000, key="minion_live_poll")

API_KEY = "a8c4eb7e1e424e479ea4c2f57b80fa65"
eat_tz = pytz.timezone("Africa/Nairobi")

st.markdown("""
<style>
    .stApp { background-color: #0b0e14; color: #d0d7de; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    
    @keyframes marquee {
        0% { transform: translateX(100%); }
        100% { transform: translateX(-100%); }
    }
    .ticker-box {
        width: 100%;
        overflow: hidden;
        background: #121722;
        border: 1px solid #1f2838;
        border-radius: 6px;
        padding: 6px 0;
        margin-bottom: 12px;
        white-space: nowrap;
    }
    .ticker-content {
        display: inline-block;
        animation: marquee 35s linear infinite;
        font-family: monospace;
        font-size: 12px;
        color: #e6edf3;
    }
    .ticker-content:hover { animation-play-state: paused; cursor: pointer; }
    
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
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. REAL-TIME NEWS RSS ENGINE
# ---------------------------------------------------------
@st.cache_data(ttl=300)
def fetch_live_market_news(query="gold price XAUUSD Fed"):
    try:
        url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        with urllib.request.urlopen(req, timeout=5) as response:
            xml_data = response.read()
        
        root = ET.fromstring(xml_data)
        items = root.findall('.//channel/item')
        
        news_items = []
        for item in items[:6]:
            title = item.find('title').text if item.find('title') is not None else ""
            link = item.find('link').text if item.find('link') is not None else "#"
            source = item.find('source').text if item.find('source') is not None else "Market News"
            
            t_lower = title.lower()
            if any(w in t_lower for w in ['surge', 'gain', 'jump', 'rise', 'bull', 'rally', 'high', 'up']):
                sentiment, badge = "BULLISH", "▲"
            elif any(w in t_lower for w in ['fall', 'drop', 'slump', 'bear', 'plunge', 'dip', 'sink', 'low', 'down']):
                sentiment, badge = "BEARISH", "▼"
            else:
                sentiment, badge = "NEUTRAL", "◆"
                
            news_items.append({
                "title": title,
                "source": source,
                "link": link,
                "sentiment": sentiment,
                "badge": badge
            })
        return news_items
    except Exception:
        return []

live_news = fetch_live_market_news("gold price XAUUSD Fed")

# ---------------------------------------------------------
# 3. STATE INITIALIZATION
# ---------------------------------------------------------
if "executed_signals" not in st.session_state:
    st.session_state.executed_signals = []
if "last_executed_candle" not in st.session_state:
    st.session_state.last_executed_candle = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "🤖 **MINION Local Quant Engine Active** (No API Key Required). I am connected to your live price feed. Ask me for market outlook, trade bias, RSI/MACD breakdown, or strategy advice!"}
    ]

# ---------------------------------------------------------
# 4. TOP BANNER & TICKER
# ---------------------------------------------------------
st.markdown("""
<div class="minion-header">
    <div>
        <span class="minion-logo">MN | MINION</span>
        <span class="minion-sub"> &nbsp;INSTITUTIONAL MULTI-TF ALPHA ENGINE</span>
    </div>
    <div>
        <span style="background: #1f2838; padding: 4px 10px; border-radius: 4px; font-size: 11px; color: #00ffcc; font-family: monospace;">● LOCAL QUANT ENGINE ONLINE</span>
    </div>
</div>
""", unsafe_allow_html=True)

if live_news:
    ticker_text = " &nbsp;&nbsp;&nbsp;&nbsp; 🚀 &nbsp;&nbsp;&nbsp;&nbsp; ".join(
        [f"<b>{item['badge']} [{item['source']}]</b> {item['title']}" for item in live_news]
    )
    st.markdown(f'<div class="ticker-box"><div class="ticker-content">{ticker_text}</div></div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# 5. CONFIGURATION CONTROLS
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
# 6. REAL-TIME DATA & INDICATOR ENGINE
# ---------------------------------------------------------
@st.cache_data(ttl=8, show_spinner=False)
def fetch_realtime_data(symbol, interval, key):
    try:
        td = TDClient(apikey=key)
        ts = td.time_series(symbol=symbol, interval=interval, outputsize=80, timezone="Africa/Nairobi")
        df = ts.as_pandas()
        if df.empty: return None, "No feed data returned."
        df = df[["open", "high", "low", "close"]].astype(float)
        df.columns = ["Open", "High", "Low", "Close"]
        return df.sort_index(), None
    except Exception as e:
        return None, str(e)

raw_df, err = fetch_realtime_data(curr_info["td"], td_interval, API_KEY)

if err or raw_df is None:
    st.error(f"⚠️ Feed Sync Error: {err}")
    st.stop()

# Technical Indicators
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
ema8 = float(latest["EMA_8"])
ema21 = float(latest["EMA_21"])
ema50 = float(latest["EMA_50"])

# Confluence Evaluation
buy_score, sell_score = 50, 50
if ema8 > ema21 > ema50: buy_score += 20
elif ema8 < ema21 < ema50: sell_score += 20

if macd_h > 0: buy_score += 15
else: sell_score += 15

if 50 < rsi < 75: buy_score += 15
elif 25 < rsi < 50: sell_score += 15

# ---------------------------------------------------------
# 7. SIGNAL EXECUTION
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
# 8. LOCAL NATIVE QUANT AI ENGINE (NO API KEY NEEDED)
# ---------------------------------------------------------
def local_quant_ai_response(user_query, context):
    q = user_query.lower()
    
    symbol = context["symbol"]
    horizon = context["horizon"]
    curr_price = context["price"]
    c_rsi = context["rsi"]
    c_macd = context["macd_h"]
    b_score = context["buy_score"]
    s_score = context["sell_score"]
    
    # Determine Bias
    if b_score > s_score:
        bias = "🟢 BULLISH"
        confidence = b_score
    elif s_score > b_score:
        bias = "🔴 BEARISH"
        confidence = s_score
    else:
        bias = "🟡 NEUTRAL / CONSOLIDATION"
        confidence = 50

    # Dynamic Analysis Generation
    if any(k in q for k in ["bias", "trend", "outlook", "direction", "predict", "buy", "sell"]):
        return f"""### 📊 Quantitative Analysis: {symbol}
* **Current Horizon**: {horizon}
* **Market Price**: `${curr_price:.2f}`
* **Algorithmic Bias**: **{bias}** (Confidence: `{confidence}/100`)

**Key Drivers:**
* **EMA Alignment**: {"Bullish Alignment (EMA8 > EMA21 > EMA50)" if context["ema8"] > context["ema21"] else "Bearish / Cross Phase"}
* **RSI Momentum**: `{c_rsi:.1f}` ({"Overbought (>70)" if c_rsi > 70 else ("Oversold (<30)" if c_rsi < 30 else "Neutral Zone")})
* **MACD Delta**: `{c_macd:.4f}` ({"Positive Momentum" if c_macd > 0 else "Negative Momentum"})

💡 **Execution Recommendation**: {"Look for pullback long entries near EMA support." if b_score > s_score else "Look for short entries near resistance."}"""

    elif any(k in q for k in ["rsi", "indicator", "macd", "technical"]):
        return f"""### 📉 Technical Indicator Breakdown
* **RSI (14)**: `{c_rsi:.2f}` — {"Showing strong buyer control." if c_rsi > 55 else ("Sellers dominating price action." if c_rsi < 45 else "RSI hovering in equilibrium.")}
* **MACD Histogram**: `{c_macd:.4f}` — {"Histogram expanding above zero." if c_macd > 0 else "Histogram beneath baseline."}
* **EMA Structure**:
  * **EMA 8**: `${context['ema8']:.2f}`
  * **EMA 21**: `${context['ema21']:.2f}`
  * **EMA 50**: `${context['ema50']:.2f}`"""

    elif any(k in q for k in ["risk", "stop", "sl", "tp", "target"]):
        tp_long = curr_price + (curr_price * 0.003)
        sl_long = curr_price - (curr_price * 0.0015)
        return f"""### 🛡️ Institutional Risk & Levels
* **Spot Price**: `${curr_price:.2f}`
* **Suggested Long TP Target**: `${tp_long:.2f}`
* **Suggested Long Stop Loss**: `${sl_long:.2f}`
* **Risk-to-Reward Ratio**: `1 : 2.0`
⚠️ *Always adhere to maximum 1% risk per trade execution.*"""

    else:
        return f"""### 🤖 MINION Local Quant AI
I am evaluating **{symbol}** on the **{horizon}** timeframe.

* **Current Price**: `${curr_price:.2f}`
* **Algorithmic Signal**: **{bias}** (`{confidence}/100`)
* **RSI**: `{c_rsi:.1f}` | **MACD**: `{c_macd:.4f}`

*You can ask me questions like:*
1. "What is the market bias right now?"
2. "Show technical indicator breakdown."
3. "Give me stop loss and take profit targets."
"""

# ---------------------------------------------------------
# 9. MINION DASHBOARD GRID
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

# --- RIGHT COLUMN: SIGNALS, NEWS & AI CHAT ---
with col_right:
    # 1. LIVE SIGNALS PANEL
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

    # 2. BREAKING NEWS PANEL
    st.markdown("<h4 style='color:#f5c518; margin-bottom:8px; font-size:14px;'>📰 BREAKING NEWS & SENTIMENT</h4>", unsafe_allow_html=True)
    
    if live_news:
        for article in live_news[:3]:
            sent_color = "#00ffaa" if article['sentiment'] == "BULLISH" else ("#ff4d4d" if article['sentiment'] == "BEARISH" else "#ffaa00")
            
            st.markdown(f"""
            <div style="background-color:#121722; border:1px solid #1f2838; padding:10px 12px; border-radius:6px; margin-bottom:8px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span style="color:{sent_color}; font-weight:bold; font-size:11px;">{article['badge']} {article['sentiment']}</span> 
                        <span style="color:#6b778d; font-size:11px; margin-left:4px;">{article['source']}</span>
                    </div>
                </div>
                <a href="{article['link']}" target="_blank" style="color:#ffffff; font-weight:bold; font-size:12px; text-decoration:none; display:block; margin-top:4px;">
                    {article['title']}
                </a>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Fetching real-time market news...")

    st.divider()

    # 3. AI ASSISTANT CHAT
    st.markdown("<h4 style='color:#f5c518; margin-bottom:4px; font-size:14px;'>🤖 MINION AI ASSISTANT</h4>", unsafe_allow_html=True)

    chat_container = st.container(height=190)
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if user_input := st.chat_input("Ask MINION AI..."):
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_input)
        
        live_context = {
            "symbol": selected_asset,
            "horizon": execution_mode,
            "price": price,
            "rsi": rsi,
            "macd_h": macd_h,
            "ema8": ema8,
            "ema21": ema21,
            "ema50": ema50,
            "buy_score": buy_score,
            "sell_score": sell_score
        }
        
        ai_response = local_quant_ai_response(user_input, live_context)
        
        with chat_container:
            with st.chat_message("assistant"):
                st.markdown(ai_response)
        
        st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
        st.rerun()
