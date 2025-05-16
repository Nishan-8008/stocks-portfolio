import streamlit as st
import requests
import time
import pandas as pd

# --- CONFIG ---
API_KEY = st.secrets["api"]["finnhub_key"]
BASE_URL = "https://finnhub.io/api/v1"
st.set_page_config(page_title="Stocks Portfolio", layout="wide")

# --- THEME + SIGNATURE ---
st.markdown("""
    <style>
        h1 { color: #90ee90; font-size: 24px; }
        h4 { color: white; font-size: 16px; font-weight: bold; margin-top: 16px; margin-bottom: 8px; }
        .styled-table th {
            color: #aaaaaa;
            font-size: 14px;
            text-align: left;
            padding: 4px;
        }
        .styled-table td {
            color: #7df9ff;
            font-size: 14px;
            padding: 4px;
        }
        a { color: #1de9b6; }
        .corner-label {
            position: fixed;
            right: 10px;
            bottom: 8px;
            font-size: 12px;
            font-weight: bold;
            color: white;
        }
        @media print {
            html, body {
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }
            .stApp {
                zoom: 80%;
                margin: 0;
                padding: 0;
            }
            button, input, .corner-label {
                display: none;
            }
        }
    </style>
    <div class="corner-label">N.P</div>
""", unsafe_allow_html=True)

st.markdown("<h1>Stocks Portfolio</h1>", unsafe_allow_html=True)

# --- UTILITIES ---
def styled_table(data_dict, col1="Label", col2="Value"):
    df = pd.DataFrame(data_dict.items(), columns=[col1, col2])
    df[col2] = df[col2].apply(lambda x: x if str(x).startswith("<") else f"<span style='color:#7df9ff; font-size:14px;'>{x}</span>")
    return df.to_html(escape=False, index=False, classes="styled-table")

def styled_df_table(df):
    return df.to_html(escape=False, index=False, classes="styled-table")

def safe_api_call(url, delay=0.7):
    try:
        time.sleep(delay)
        res = requests.get(url)
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return None

def generate_insights(metrics, quote, rec, sentiment):
    insights = []
    pe = metrics.get("peTTM") if metrics else None
    dividend = metrics.get("dividendYieldIndicatedAnnual", 0) if metrics else 0
    buy = rec[0].get("buy") if rec and isinstance(rec, list) and len(rec) > 0 else 0
    sell = rec[0].get("sell") if rec and isinstance(rec, list) and len(rec) > 0 else 0
    c = quote.get("c", 0) if quote else 0
    h = quote.get("h", 0) if quote else 0
    l = quote.get("l", 0) if quote else 0

    if pe is not None:
        if pe < 15:
            insights.append(("📉 Appears undervalued with a low PE ratio.", "green"))
        elif pe > 30:
            insights.append(("⚠️ High PE ratio suggests overvaluation.", "red"))
    if dividend and dividend > 0.03:
        insights.append(("💰 Strong dividend yield — suitable for income investors.", "green"))
    if buy > 20 and sell == 0:
        insights.append(("🧠 Strong Buy consensus from analysts.", "green"))
    if (h - l) / h > 0.05:
        insights.append(("⚠️ High intraday volatility observed.", "red"))
    if sentiment:
        reddit = len(sentiment.get("reddit", []))
        twitter = len(sentiment.get("twitter", []))
        if reddit + twitter > 20:
            insights.append(("🔥 Stock is trending on social platforms.", "green"))
    return insights

@st.cache_data(ttl=3600)
def get_nasdaq_symbols():
    url = f"{BASE_URL}/stock/symbol?exchange=US&token={API_KEY}"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        nasdaq = [d for d in data if d.get("mic") == "XNAS"]
        return {f"{d['symbol']} - {d['description']}": d["symbol"] for d in nasdaq if d.get("symbol") and d.get("description")}
    return {}

# --- INIT SESSION STATE ---
symbol_options = get_nasdaq_symbols()
for i in range(1, 5):
    for key in ["symbol", "profile", "quote", "metrics", "rec", "news", "sentiment"]:
        st.session_state.setdefault(f"{key}{i}", None)

# --- MAIN SELECTION ---
cols = st.columns(4)
for idx, col in enumerate(cols, start=1):
    with col:
        selection = st.selectbox(f"Select NASDAQ Stock {idx}", list(symbol_options.keys()), key=f"select_{idx}")
        selected_symbol = symbol_options.get(selection)
        if st.button("Load Data", key=f"load_{idx}"):
            st.session_state[f"symbol{idx}"] = selected_symbol
            st.session_state[f"profile{idx}"] = safe_api_call(f"{BASE_URL}/stock/profile2?symbol={selected_symbol}&token={API_KEY}")
            st.session_state[f"quote{idx}"] = safe_api_call(f"{BASE_URL}/quote?symbol={selected_symbol}&token={API_KEY}")
            st.session_state[f"metrics{idx}"] = safe_api_call(f"{BASE_URL}/stock/metric?symbol={selected_symbol}&metric=all&token={API_KEY}")
            st.session_state[f"rec{idx}"] = safe_api_call(f"{BASE_URL}/stock/recommendation?symbol={selected_symbol}&token={API_KEY}")
            st.session_state[f"news{idx}"] = safe_api_call(f"{BASE_URL}/company-news?symbol={selected_symbol}&from=2024-12-01&to=2025-05-14&token={API_KEY}")
            st.session_state[f"sentiment{idx}"] = safe_api_call(f"{BASE_URL}/stock/social-sentiment?symbol={selected_symbol}&token={API_KEY}")

        profile = st.session_state.get(f"profile{idx}")
        quote = st.session_state.get(f"quote{idx}")
        metrics_data = st.session_state.get(f"metrics{idx}")
        rec = st.session_state.get(f"rec{idx}")
        news = st.session_state.get(f"news{idx}")
        sentiment = st.session_state.get(f"sentiment{idx}")
        m = metrics_data.get("metric", {}) if metrics_data else {}

        if profile:
            st.markdown("<h4>Company Profile</h4>", unsafe_allow_html=True)
            if profile.get("logo"):
                st.image(profile["logo"], width=50)
            st.markdown(styled_table({
                "Company Name": profile.get("name", "N/A"),
                "Exchange": profile.get("exchange", "N/A"),
                "Industry": profile.get("finnhubIndustry", "N/A"),
                "IPO Date": profile.get("ipo", "N/A")
            }), unsafe_allow_html=True)

            st.markdown("<h4>Stock Details</h4>", unsafe_allow_html=True)
            curr = quote.get("c", 0) if quote else 0
            prev = quote.get("pc", 0) if quote else 0
            try:
                ret = ((curr - prev) / prev) * 100 if prev else 0
            except:
                ret = 0
            price_color = "lightgreen" if curr > prev else "red" if curr < prev else "gray"
            st.markdown(styled_table({
                "Current Price": f"<span style='color:{price_color}; font-size:14px;'>${curr:.2f}</span>",
                "Previous Close": f"${prev}",
                "Return Since Close": f"{ret:.2f}%",
                "High Today": f"${quote.get('h', 'N/A') if quote else 'N/A'}",
                "Low Today": f"${quote.get('l', 'N/A') if quote else 'N/A'}",
                "Market Cap (in Billion USD)": m.get("marketCapitalization", "N/A"),
                "PE Ratio": m.get("peTTM", "N/A"),
                "Dividend Yield": m.get("dividendYieldIndicatedAnnual", "N/A")
            }), unsafe_allow_html=True)

            st.markdown("<h4>News & Social Sentiment</h4>", unsafe_allow_html=True)
            if news:
                for article in news[:2]:
                    st.markdown(f"<span style='color:#1de9b6; font-size:14px;'>- <a href='{article['url']}' target='_blank'>{article['headline']}</a></span>", unsafe_allow_html=True)
            if sentiment:
                reddit = sentiment.get("reddit", [])
                twitter = sentiment.get("twitter", [])
                st.markdown(styled_table({
                    "Reddit mentions": len(reddit),
                    "Twitter mentions": len(twitter)
                }, "Source", "Mentions"), unsafe_allow_html=True)

            st.markdown("<h4>💡 Smart Insights</h4>", unsafe_allow_html=True)
            insights = generate_insights(m, quote, rec, sentiment)
            for tip, color in insights:
                st.markdown(f"<span style='color:{'lightgreen' if color == 'green' else 'red'}; font-size:14px;'>• {tip}</span>", unsafe_allow_html=True)

# --- SUMMARY + WEIGHTS + GUIDE TABLE ---
if st.button("🔍 Show Summary & Portfolio Suggestion"):
    summary = []
    for idx in range(1, 5):
        symbol = st.session_state.get(f"symbol{idx}")
        metrics_data = st.session_state.get(f"metrics{idx}")
        quote = st.session_state.get(f"quote{idx}")
        rec = st.session_state.get(f"rec{idx}")
        rec_data = rec[0] if rec and isinstance(rec, list) and len(rec) > 0 else {}
        m = metrics_data.get("metric", {}) if metrics_data else {}

        if not symbol or not m or not quote:
            continue

        score = 0
        pe = m.get("peTTM")
        dy = m.get("dividendYieldIndicatedAnnual", 0)
        vol = m.get("volatility", 0)
        curr = quote.get("c", 0)
        prev = quote.get("pc", 0)
        try:
            ret = (curr - prev) / prev
        except:
            ret = 0
        if pe: score += 2 if pe < 15 else 1 if pe < 25 else 0
        if dy: score += 2 if dy > 0.03 else 1 if dy > 0.01 else 0
        if ret: score += 2 if ret > 0.01 else 1 if ret > 0 else 0
        if rec_data.get("buy"): score += 2 if rec_data["buy"] > 20 else 1 if rec_data["buy"] > 10 else 0
        if vol: score += 1 if vol < 3 else 0
        summary.append((symbol, score, pe, dy, ret))

    if not summary:
        st.warning("⚠️ No Stocks Selected")
    else:
        summary.sort(key=lambda x: x[1], reverse=True)
        best = summary[0]
        reason = "lower PE" if best[2] and best[2] < 25 else "higher dividend" if best[3] > 0.01 else "positive return"

        col_left, col_right = st.columns([2, 1])
        with col_left:
            st.markdown("<h4>Summary</h4>", unsafe_allow_html=True)
            st.success(f"✅ Best Pick: {best[0]} — due to its {reason} vs others.")
            st.markdown("<h4>Portfolio Weights Suggestion</h4>", unsafe_allow_html=True)
            total_score = sum(s[1] for s in summary)
            for symbol, score, *_ in summary:
                weight = (score / total_score) * 100 if total_score > 0 else 0
                st.markdown(f"- **{symbol}** → {weight:.1f}%")

        with col_right:
            guide_data = {
                "Metric": ["PE Ratio", "PE Ratio", "PE Ratio", "Dividend Yield", "Dividend Yield", "Dividend Yield"],
                "Category": ["Good", "Average", "High", "Strong", "Moderate", "Low / None"],
                "Interpretation": [
                    "< 15 (Undervalued)",
                    "15 – 30",
                    "> 30 (Overvalued)",
                    "> 3%",
                    "1% – 3%",
                    "< 1% or missing"
                ]
            }
            guide_df = pd.DataFrame(guide_data)
            st.markdown("<h4>PE & Dividend Yield Guide</h4>", unsafe_allow_html=True)
            st.markdown(styled_df_table(guide_df), unsafe_allow_html=True)


