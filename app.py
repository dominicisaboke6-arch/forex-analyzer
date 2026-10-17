import streamlit as st
import feedparser
import pandas as pd
import torch
from transformers import BertTokenizer, BertForSequenceClassification

# Page configuration
st.set_page_config(
    page_title="XAU/USD News & Sentiment Intelligence",
    page_icon="📈",
    layout="wide"
)

# Title & Description
st.title("📈 XAU/USD Macro News & Sentiment Engine")
st.markdown("Automated news aggregator and local NLP sentiment engine built without third-party APIs.")

# 1. Load Local Sentiment Model (Cached so it downloads only once)
@st.cache_resource
def load_sentiment_model():
    model_name = "ProsusAI/finbert"
    tokenizer = BertTokenizer.from_pretrained(model_name)
    model = BertForSequenceClassification.from_pretrained(model_name)
    return tokenizer, model

with st.spinner("Loading local FinBERT model into memory..."):
    tokenizer, model = load_sentiment_model()

# Function to analyze text sentiment
def analyze_sentiment(text):
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    outputs = model(**inputs)
    predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
    
    labels = ["Positive", "Negative", "Neutral"]
    scores = predictions.detach().numpy()[0]
    return dict(zip(labels, scores))

# 2. Free RSS News Ingestion
RSS_FEEDS = {
    "Investing.com - Forex/Commodities": "https://www.investing.com/rss/news_25.rss",
    "Wall Street Journal - Markets": "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml"
}

st.sidebar.header("Data Sources")
selected_feed = st.sidebar.selectbox("Select RSS Feed", list(RSS_FEEDS.keys()))

@st.cache_data(ttl=300)  # Refresh every 5 minutes
def fetch_news(feed_url):
    feed = feedparser.parse(feed_url)
    news_items = []
    for entry in feed.entries[:10]:
        news_items.append({
            "Title": entry.title,
            "Published": getattr(entry, 'published', 'N/A'),
            "Link": entry.link
        })
    return news_items

# Main App Layout
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📰 Live Financial Headlines")
    news_data = fetch_news(RSS_FEEDS[selected_feed])
    
    if news_data:
        processed_news = []
        for item in news_data:
            sentiment = analyze_sentiment(item["Title"])
            
            # Simple rule-based directional inference for Gold based on financial sentiment
            pos_score = sentiment["Positive"]
            neg_score = sentiment["Negative"]
            
            if pos_score > 0.6:
                gold_bias = "🔴 Bearish USD Gain"
            elif neg_score > 0.6:
                gold_bias = "🟢 Bullish Safe Haven"
            else:
                gold_bias = "⚪ Neutral / Mixed"

            processed_news.append({
                "Headline": item["Title"],
                "Positive": f"{pos_score:.2f}",
                "Negative": f"{neg_score:.2f}",
                "Neutral": f"{sentiment['Neutral']:.2f}",
                "Gold Bias": gold_bias
            })
            
        df = pd.DataFrame(processed_news)
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No news items retrieved from the selected RSS feed.")

with col2:
    st.subheader("⚡ Manual Release Predictor")
    st.markdown("Test hypothetical economic figures against consensus forecasts:")
    
    event_type = st.selectbox("Economic Release", ["CPI (Inflation)", "NFP (Employment)", "PPI", "FOMC Rate Signal"])
    forecast_val = st.number_input("Consensus Forecast / Previous", value=3.6)
    actual_val = st.number_input("Actual Printed / Expected Figure", value=3.7)
    
    if st.button("Predict XAU/USD Direction"):
        diff = actual_val - forecast_val
        st.markdown("---")
        if diff > 0:
            st.error(f"**Result:** Actual figure came in **HIGHER** than expected by +{diff:.2f}.")
            st.markdown("👉 **Impact on Gold:** Hawkish signal for Fed rates → **Bearish XAU/USD Short-Term**.")
        elif diff < 0:
            st.success(f"**Result:** Actual figure came in **LOWER** than expected by {diff:.2f}.")
            st.markdown("👉 **Impact on Gold:** Dovish signal for Fed rates → **Bullish XAU/USD Short-Term**.")
        else:
            st.info("**Result:** Actual figure matched consensus forecast exactly.")
            st.markdown("👉 **Impact on Gold:** Low volatility expected / **Neutral**.")
