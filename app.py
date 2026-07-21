import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import datetime

# ---------------------------------------------------------
# 1. PAGE CONFIGURATION & STYLING
# ---------------------------------------------------------
st.set_page_config(
    page_title="Forex & Gold Pro Terminal",
    page_icon="📈",
    layout="wide"
)

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e222d; padding: 10px; border-radius: 8px; border: 1px solid #2a2e39; }
    div[data-testid="stSidebar"] { background-color: #131722; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. REAL-TIME CLOCK (JavaScript Ticker)
# ---------------------------------------------------------
clock_html = """
<div style="background-color: #1e222d; border: 1px solid #2a2e39; padding: 10px 15px; border-radius: 8px; text-align: center; margin-bottom: 15px;">
    <span style="color: #888888; font-size: 13px; font-weight: bold; font-family: monospace;">REAL-TIME MARKET CLOCK:</span>
    <span id="live_clock" style="color: #00e676; font-size: 16px; font-weight: bold; font-family: monospace; margin-left: 10px;">--:--:--</span>
</div>
<script>
function updateClock() {
    const now = new Date();
    const utcStr = now.toUTCString().split(' ')[4] + " UTC";
    const localStr = now.toLocaleTimeString();
    document.getElementById("live_clock").innerText = localStr + " (Local)  |  " + utcStr;
}
setInterval(updateClock, 1000);
updateClock();
</script>
"""
components.html(clock_html, height=55)

# ---------------------------------------------------------
# 3. HEADER & SIDEBAR CONTROLS
# ---------------------------------------------------------
st.title("⚡ Forex & Gold Live Analyzer")

symbol_map = {
    "Gold Spot (XAU/USD)": {"yf": "GC=F", "tv": "OANDA:XAUUSD"},
    "EUR/USD": {"yf": "EURUSD=X", "tv": "FX:EURUSD"},
    "GBP/USD": {"yf": "GBPUSD=X", "tv": "FX:GBPUSD"},
    "USD/JPY": {"yf": "JPY=X", "tv": "FX:USDJPY"},
    "AUD/USD": {"yf": "AUDUSD=X", "tv": "FX:AUDUSD"},
    "USD/CAD": {"yf": "CAD=X", "tv": "FX:USDCAD"},
    "USD/CHF": {"yf": "CHF=X", "tv": "FX:USDCHF"}
}

st.sidebar.header("⚙️ Market Parameters")
selected_asset = st.sidebar.selectbox("Select Asset / Currency Pair", list(symbol_map.keys()))
interval = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h"], index=1)

curr_info = symbol_map[selected_asset]

# ---------------------------------------------------------
# 4. LIVE METRICS SUMMARY
# ---------------------------------------------------------
try:
    ticker = yf.Ticker(curr_info["yf"])
    data = ticker.history(period="1d", interval="1m")
    if not data.empty:
        latest_price = data['Close'].iloc[-1]
        prev_price = data['Close'].iloc[0]
        change = latest_price - prev_price
        pct_change = (change / prev_price) * 100

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Current Price", f"{latest_price:,.2f}", f"{change:+.2f} ({pct_change:+.2f}%)")
        col2.metric("Session High", f"{data['High'].max():,.2f}")
        col3.metric("Session Low", f"{data['Low'].min():,.2f}")
        col4.metric("Volume", f"{int(data['Volume'].iloc[-1]):,}")
except Exception as e:
    st.warning("Fetching live header metrics from Yahoo Finance... (TradingView Chart below active)")

# ---------------------------------------------------------
# 5. TRADINGVIEW INTERACTIVE CHART (FIXED)
# ---------------------------------------------------------
st.subheader(f"📊 {selected_asset} Interactive Chart")

# Map timeframe for TradingView
tv_interval_map = {"1m": "1", "5m": "5", "15m": "15", "1h": "60"}
tv_interval = tv_interval_map.get(interval, "5")

tv_html = f"""
<div class="tradingview-widget-container" style="height:550px;width:100%">
  <div id="tv_chart" style="height:550px;width:100%"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <script type="text/javascript">
  new TradingView.widget({{
    "autosize": true,
    "symbol": "{curr_info['tv']}",
    "interval": "{tv_interval}",
    "timezone": "Etc/UTC",
    "theme": "dark",
    "style": "1",
    "locale": "en",
    "toolbar_bg": "#f1f3f6",
    "enable_publishing": false,
    "allow_symbol_change": true,
    "container_id": "tv_chart"
  }});
  </script>
</div>
"""
components.html(tv_html, height=560)

# ---------------------------------------------------------
# 6. LIVE FOREX & MARKET NEWS SECTION
# ---------------------------------------------------------
st.markdown("---")
st.subheader("📰 Live Market News (ForexLive, Investing.com, FXStreet & Reuters)")

# Embedded TradingView Market News & Calendar Widget
news_html = """
<div class="tradingview-widget-container" style="width:100%; height:450px;">
  <div class="tradingview-widget-container__widget"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-timeline.js" async>
  {
  "feedMode": "all_symbols",
  "isTransparent": false,
  "displayMode": "regular",
  "width": "100%",
  "height": "450",
  "colorTheme": "dark",
  "locale": "en"
}
  </script>
</div>
"""
components.html(news_html, height=460)
