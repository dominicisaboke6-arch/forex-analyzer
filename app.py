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
    page_title="MINION | Live Gold & Multi-Asset Alpha Engine",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Set refresh interval to 60 seconds (60000ms) to comply with Twelve Data's 8 req/min limit
st_autorefresh(interval=60000, key="minion_live_poll")

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
        margin-bottom: 10px;
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

    /* PROBABILITY & TOP SIGNAL BAR */
    .top-prob-bar {
        background-color: #121722;
        border: 1px solid #1f2838;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 12px;
    }
    .prob-badge-buy { background: #00ffaa; color: #000; font-weight: 800; padding: 4px 10px; border-radius: 4px; font-size: 12px; }
    .prob-badge-sell { background: #ff4d4d; color: #fff; font-weight: 800; padding: 4px 10px; border-radius: 4px; font-size: 12px; }
    .prob-badge-neutral { background: #ffaa00; color: #000; font-weight: 800; padding: 4px 10px; border-radius: 4px; font-size: 12px; }
    
    .prob-meter-bg {
        width: 100%;
        background-color: #1a2230;
        border-radius: 4px;
        height: 10px;
        display: flex;
        overflow: hidden;
        margin: 6px 0;
    }
    .prob-meter-buy { background-color: #00ffaa; height: 100%; transition: width 0.5s; }
    .prob-meter-sell { background-color: #ff4d4d; height: 100%; transition: width 0.5s; }

    /* SIGNAL CARDS */
    .aurum-sig-card {
        background-color: #121722;
        border: 1px solid #1f2838;
        border-radius: 6px;
        padding: 8px 12px;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .sig-buy-badge { background-color: #00ffaa; color: #000; font-weight: 800; padding: 2px 6px; border-radius: 4px; font-size: 10px; }
    .sig-sell-badge { background-color: #ff4d4d; color: #fff; font-weight: 800; padding: 2px 6px; border-radius: 4px; font-size: 10px; }
    .sig-price-center { color: #f5c518; font-family: monospace; font-size: 13px; font-weight: bold; }
    .sig-latest-pill { background-color: #f5c518; color: #000; font-weight: 800; font-size: 8px; padding: 1px 4px; border-radius: 3px; margin-left: 4px; }
    .sig-time-right { color: #6b778d; font-size: 10px; font-family: monospace; }

    .scanning-footer {
        background: linear-gradient(90deg, #ff0055 0%, #ff2e63 100%);
        color: #ffffff;
        font-weight: 800;
        letter-spacing: 3px;
        text-align: center;
        padding: 8px;
        border-radius: 6px;
        font-size: 12px;
        margin-top: 10px;
        box-shadow: 0 0 12px rgba(255, 0, 85, 0.4);
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

# Calculate News Fundamental Sentiment Shift
bullish_news_count = sum(1 for n in live_news if n['sentiment'] == "BULLISH")
bearish_news_count = sum(1 for n in live_news if n['sentiment'] == "BEARISH")

# ---------------------------------------------------------
# 3. STATE INITIALIZATION (PERSIST HISTORICAL SIGNALS)
# ---------------------------------------------------------
if "signal_history" not in st.session_state:
    st.session_state.signal_history = []
if "last_executed_candle" not in st.session_state:
    st.session_state.last_executed_candle = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "🤖 **MINION Institutional Quant Engine Active**. Real-time probability models, signal persistence, and rate-limit guardrails loaded."}
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
        <span style="background: #1f2838; padding: 4px 10px; border-radius: 4px; font-size: 11px; color: #00ffcc; font-family: monospace;">● LIVE MARKET SCANNER ACTIVE</span>
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
        min_threshold = st.slider("Min Confluence Threshold Score (/100)", 50, 90, 60)

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
# 6. REAL-TIME DATA & INDICATOR ENGINE (WITH RATE LIMIT PROTECTION)
# ---------------------------------------------------------
@st.cache_data(ttl=55, show_spinner=False)
def fetch_realtime_data(symbol, interval, key):
    try:
        td = TDClient(apikey=key)
        ts = td.time_series(symbol=symbol, interval=interval, outputsize=80, timezone="Africa/Nairobi")
        df = ts.as_pandas()
        if df is None or df.empty:
            return None, "Empty dataset returned from feed."
        df = df[["open", "high", "low", "close"]].astype(float)
        df.columns = ["Open", "High", "Low", "Close"]
        return df.sort_index(), None
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "credits" in err_msg.lower():
            return None, "RATE_LIMIT"
        return None, err_msg

raw_df, err = fetch_realtime_data(curr_info["td"], td_interval, API_KEY)

if err == "RATE_LIMIT":
    st.warning("⏱️ **API Credit Threshold Reached**: Twelve Data limits free tier to 8 calls/min. Retrying automatically on the next minute tick...")
    st.stop()
elif err or raw_df is None:
    st.error(f"⚠️ Feed Sync Error: {err}")
    st.stop()

# Indicators & Market Structure Dynamics
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

# ---------------------------------------------------------
# 7. MARKET STRUCTURE & PROBABILITY CALCULATION ENGINE
# ---------------------------------------------------------
buy_score, sell_score = 50, 50

# Market Structure (Trend Stack & Price Position)
if price > ema8 > ema21 > ema50:
    buy_score += 20
    market_struct = "BULLISH EXPANSION (Higher Highs / Higher Lows)"
elif price < ema8 < ema21 < ema50:
    sell_score += 20
    market_struct = "BEARISH EXPANSION (Lower Highs / Lower Lows)"
elif price > ema50:
    buy_score += 10
    market_struct = "BULLISH RECOVERY ABOVE EMA 50"
else:
    sell_score += 10
    market_struct = "BEARISH PRESSURE BELOW EMA 50"

# Technical Momentum (RSI & MACD)
if macd_h > 0: buy_score += 12
else: sell_score += 12

if 50 <= rsi <= 70: buy_score += 10
elif 30 <= rsi < 50: sell_score += 10
elif rsi > 70: sell_score += 5
elif rsi < 30: buy_score += 5

# Fundamental News Sentiment Shift
buy_score += (bullish_news_count * 3)
sell_score += (bearish_news_count * 3)

total_weight = buy_score + sell_score
buy_prob = int(round((buy_score / total_weight) * 100))
sell_prob = 100 - buy_prob

# ---------------------------------------------------------
# 8. SIGNAL GENERATION & PERSISTENCE
# ---------------------------------------------------------
if st.session_state.last_executed_candle != latest_candle_time:
    if buy_score >= min_threshold and buy_prob >= 58:
        st.session_state.last_executed_candle = latest_candle_time
        st.session_state.signal_history.insert(0, {
            "type": "BUY",
            "asset": selected_asset,
            "price": f"${price:.{curr_info['dec']}f}",
            "prob": buy_prob,
            "time": datetime.now(eat_tz).strftime("%H:%M:%S"),
            "candle": latest_candle_time,
            "horizon": execution_mode,
            "structure": market_struct
        })
    elif sell_score >= min_threshold and sell_prob >= 58:
        st.session_state.last_executed_candle = latest_candle_time
        st.session_state.signal_history.insert(0, {
            "type": "SELL",
            "asset": selected_asset,
            "price": f"${price:.{curr_info['dec']}f}",
            "prob": sell_prob,
            "time": datetime.now(eat_tz).strftime("%H:%M:%S"),
            "candle": latest_candle_time,
            "horizon": execution_mode,
            "structure": market_struct
        })

# Keep up to 50 saved historical signals
st.session_state.signal_history = st.session_state.signal_history[:50]
latest_sig = st.session_state.signal_history[0] if st.session_state.signal_history else None

# ---------------------------------------------------------
# 9. LOCAL NATIVE QUANT AI RESPONSE ENGINE
# ---------------------------------------------------------
def local_quant_ai_response(user_query, context):
    q = user_query.lower()
    symbol = context["symbol"]
    horizon = context["horizon"]
    curr_price = context["price"]
    c_rsi = context["rsi"]
    c_macd = context["macd_h"]
    b_prob = context["buy_prob"]
    s_prob = context["sell_prob"]
    m_struct = context["structure"]
    
    bias_str = "🟢 BULLISH" if b_prob > 55 else ("🔴 BEARISH" if s_prob > 55 else "🟡 NEUTRAL / CONSOLIDATION")
    
    if any(k in q for k in ["bias", "trend", "structure", "direction", "analysis", "predict", "buy", "sell"]):
        return f"""### 🏛️ Strategic Market Structure Analysis: {symbol}
* **Execution Horizon**: `{horizon}` | **Spot Price**: `${curr_price:.2f}`
* **Algorithmic Bias**: **{bias_str}** (Buy Probability: `{b_prob}%` | Sell: `{s_prob}%`)

#### 1. Market Structure Breakdown
* **Structural State**: `{m_struct}`
* **Dynamic Resistance/Support**: EMA 8 (`${context['ema8']:.2f}`), EMA 21 (`${context['ema21']:.2f}`), EMA 50 (`${context['ema50']:.2f}`)

#### 2. Technical Momentum & Indicators
* **RSI (14)**: `{c_rsi:.1f}` — {"Strong upside momentum within healthy bounds." if 50<=c_rsi<=70 else ("Bearish pressure dominating." if c_rsi<50 else "Extreme overbought region.")}
* **MACD Histogram**: `{c_macd:.4f}` — {"Positive momentum histogram." if c_macd>0 else "Negative momentum histogram."}

#### 3. Fundamental Context
* Live Google RSS sentiment tracks **{bullish_news_count} Bullish** vs **{bearish_news_count} Bearish** catalysts.
"""

    elif any(k in q for k in ["history", "previous", "signals", "past", "saved"]):
        count = len(st.session_state.signal_history)
        return f"### 📜 Historical Signal Records\nCurrently storing **{count}** persistent execution signals in memory. You can view and expand the complete log in the side column list."

    else:
        return f"""### 🤖 MINION Quant AI
Currently tracking **{symbol}** on **{horizon}**.

* **Price**: `${curr_price:.2f}`
* **Model Probability**: **BUY {b_prob}%** | **SELL {s_prob}%**
* **Structure**: `{m_struct}`

Ask me for:
1. "Strategic market structure analysis"
2. "Technical momentum breakdown"
3. "Risk levels and targets"
"""

# ---------------------------------------------------------
# 10. TOP PROBABILITY & LATEST EXECUTION BAR (ABOVE CHART)
# ---------------------------------------------------------
badge_class = "prob-badge-buy" if buy_prob >= 58 else ("prob-badge-sell" if sell_prob >= 58 else "prob-badge-neutral")
bias_label = f"BUY BIAS ({buy_prob}%)" if buy_prob >= 58 else (f"SELL BIAS ({sell_prob}%)" if sell_prob >= 58 else "NEUTRAL / RANGE")

latest_sig_text = f"<b>{latest_sig['type']}</b> @ {latest_sig['price']} ({latest_sig['time']})" if latest_sig else "Scanning for confluence..."

st.markdown(f"""
<div class="top-prob-bar">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <span style="color:#6b778d; font-size:11px; font-weight:bold;">LIVE MODEL PROBABILITY:</span>
            <span class="{badge_class}" style="margin-left:8px;">{bias_label}</span>
        </div>
        <div style="font-family:monospace; font-size:12px; color:#d0d7de;">
            <span style="color:#6b778d;">LATEST SIGNAL:</span> <span style="color:#f5c518;">{latest_sig_text}</span>
        </div>
    </div>
    <div class="prob-meter-bg">
        <div class="prob-meter-buy" style="width: {buy_prob}%;"></div>
        <div class="prob-meter-sell" style="width: {sell_prob}%;"></div>
    </div>
    <div style="display:flex; justify-content:space-between; font-size:10px; color:#6b778d; font-family:monospace;">
        <span>▲ BUY CONFLUENCE: {buy_prob}%</span>
        <span>STRUCT: {market_struct}</span>
        <span>▼ SELL CONFLUENCE: {sell_prob}%</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 11. DASHBOARD LAYOUT GRID
# ---------------------------------------------------------
col_left, col_right = st.columns([2.6, 1.2])

# --- LEFT COLUMN: TRADINGVIEW CHART ---
with col_left:
    tv_html = f"""
    <div class="tradingview-widget-container" style="height:560px;width:100%">
      <div id="tv_minion_chart" style="height:560px;width:100%"></div>
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
    components.html(tv_html, height=565)
    st.markdown('<div class="scanning-footer">• SCANNING LIVE MARKET STRUCTURE & LIQUIDITY •</div>', unsafe_allow_html=True)

# --- RIGHT COLUMN: HISTORICAL SIGNALS, NEWS & AI CHAT ---
with col_right:
    # 1. SIGNAL HISTORY ACCORDION PANEL (PERSISTENT LOGS)
    st.markdown("<h4 style='color:#f5c518; margin-bottom:6px; font-size:13px;'>⚡ LIVE & SAVED SIGNAL HISTORY</h4>", unsafe_allow_html=True)
    
    if st.session_state.signal_history:
        for idx, sig in enumerate(st.session_state.signal_history[:3]):
            badge_cls = "sig-buy-badge" if sig["type"] == "BUY" else "sig-sell-badge"
            latest_html = '<span class="sig-latest-pill">LATEST</span>' if idx == 0 else ""
            
            card_html = f"""<div class="aurum-sig-card">
                <span class="{badge_cls}">{sig["type"]} ({sig["prob"]}%)</span>
                <span class="sig-price-center">{sig["price"]} {latest_html}</span>
                <span class="sig-time-right">{sig["time"]}</span>
            </div>"""
            st.markdown(card_html, unsafe_allow_html=True)
            
        if len(st.session_state.signal_history) > 3:
            with st.expander(f"📜 View All Saved Signals ({len(st.session_state.signal_history)})"):
                for sig in st.session_state.signal_history[3:]:
                    st.caption(f"**{sig['type']}** @ {sig['price']} | Prob: {sig['prob']}% | Time: {sig['time']} | {sig['horizon']}")
    else:
        st.info("Scanning live candles for strategy setup triggers...")

    st.divider()

    # 2. BREAKING NEWS PANEL
    st.markdown("<h4 style='color:#f5c518; margin-bottom:6px; font-size:13px;'>📰 BREAKING NEWS & SENTIMENT</h4>", unsafe_allow_html=True)
    
    if live_news:
        for article in live_news[:2]:
            sent_color = "#00ffaa" if article['sentiment'] == "BULLISH" else ("#ff4d4d" if article['sentiment'] == "BEARISH" else "#ffaa00")
            st.markdown(f"""
            <div style="background-color:#121722; border:1px solid #1f2838; padding:8px 10px; border-radius:6px; margin-bottom:6px;">
                <span style="color:{sent_color}; font-weight:bold; font-size:10px;">{article['badge']} {article['sentiment']}</span> 
                <span style="color:#6b778d; font-size:10px;">| {article['source']}</span>
                <a href="{article['link']}" target="_blank" style="color:#ffffff; font-weight:bold; font-size:11px; text-decoration:none; display:block; margin-top:2px;">
                    {article['title']}
                </a>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Fetching real-time RSS feeds...")

    st.divider()

    # 3. AI ASSISTANT CHAT
    st.markdown("<h4 style='color:#f5c518; margin-bottom:4px; font-size:13px;'>🤖 STRATEGIC QUANT CHAT</h4>", unsafe_allow_html=True)

    chat_container = st.container(height=180)
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    if user_input := st.chat_input("Ask about market structure..."):
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
            "buy_prob": buy_prob,
            "sell_prob": sell_prob,
            "structure": market_struct
        }
        
        ai_response = local_quant_ai_response(user_input, live_context)
        
        with chat_container:
            with st.chat_message("assistant"):
                st.markdown(ai_response)
        
        st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
        st.rerun()
