import streamlit as st
import pandas as pd
import boto3
import json
import os
import io
import yfinance as yf
import plotly.graph_objects as go
from sqlalchemy import create_engine
from dotenv import load_dotenv
from datetime import datetime

# ==========================================
# 1. PAGE & CONFIG
# ==========================================
st.set_page_config(page_title="Agentic Trading Dashboard", layout="wide", initial_sidebar_state="collapsed")
load_dotenv()

ASSETS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'AMD', 'IBM', 'BTC-USD', 'ETH-USD']

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;700&display=swap');
    
    /* Global Resets */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; color: #c9d1d9; }
    .stApp { background-color: #0b1015 !important; }
    header { visibility: hidden; }
    
    /* Card Styling to match screenshots */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #121820 !important;
        border: 1px solid #1e293b !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: transparent; border-radius: 4px 4px 0px 0px; gap: 1px; padding-top: 10px; padding-bottom: 10px; color: #8b949e; font-weight: 600; font-size: 0.9rem; }
    .stTabs [aria-selected="true"] { color: #e6edf3; border-bottom: 2px solid #58a6ff; }
    
    /* Table Styling */
    [data-testid="stDataFrame"] { background-color: #121820; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. DATA CONNECTIONS (FULLY LIVE)
# ==========================================
@st.cache_resource
def get_r2_client():
    return boto3.client(
        's3',
        endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv('R2_ACCESS_KEY'),
        aws_secret_access_key=os.getenv('R2_SECRET_KEY'),
        region_name='auto',
    )
    return session.client('s3')
@st.cache_data(ttl=900)
def fetch_r2_csv(key):
    """Fetch a CSV file from R2 and return as a DataFrame."""
    try:
        s3 = get_r2_client()
        bucket = os.getenv('R2_BUCKET')
        obj = s3.get_object(Bucket=bucket, Key=key)
        return pd.read_csv(io.BytesIO(obj['Body'].read()))
    except Exception:
        return None
        
@st.cache_data(ttl=900)
def fetch_r2_json(key):
    """Fetch a JSON file from R2."""
    try:
        s3 = get_r2_client()
        bucket = os.getenv('R2_BUCKET')
        obj = s3.get_object(Bucket=bucket, Key=key)
        return json.loads(obj['Body'].read().decode('utf-8'))
    except Exception:
        return None

@st.cache_data(ttl=900)
def fetch_r2_image(key):
    """Fetch an image file from R2 and return it as raw bytes, or None if missing."""
    try:
        s3 = get_r2_client()
        bucket = os.getenv('R2_BUCKET')
        obj = s3.get_object(Bucket=bucket, Key=key)
        return obj['Body'].read()
    except Exception:
        return None
        
@st.cache_resource
def get_db_engine():
    return create_engine(os.getenv("SUPABASE_DB_URL"), pool_pre_ping=True, pool_recycle=3600)

@st.cache_data(ttl=900)
def fetch_kpi_metrics():
    """Fetches total trades and signal counts from RDS."""
    try:
        engine = get_db_engine()
        total = pd.read_sql("SELECT COUNT(*) AS total FROM trade_log", engine).iloc[0]['total']
        buys = pd.read_sql("SELECT COUNT(*) AS count FROM trade_log WHERE signal='BUY'", engine).iloc[0]['count']
        sells = pd.read_sql("SELECT COUNT(*) AS count FROM trade_log WHERE signal='SELL'", engine).iloc[0]['count']
        return total, buys, sells
    except Exception:
        return 0, 0, 0 

@st.cache_data(ttl=900)
def fetch_portfolio_performance():
    """Fetches portfolio metrics from the backtest summary."""
    try:
        df = pd.read_csv("data/backtest_summary.csv")
        annual_return = df['total_return'].median() * 100
        sharpe = df['sharpe_ratio'].median()
        max_dd = df['max_drawdown'].median() * 100
        volatility = df['total_return'].std() * 100
        return annual_return, sharpe, max_dd, volatility
    except Exception:
        return 0.0, 0.0, 0.0, 0.0

@st.cache_data(ttl=86400) 
def fetch_chart_data(ticker):
    """Fetches live pricing data from Yahoo Finance."""
    chart_json = fetch_r2_json('charts/chart_history_latest.json')
    if not chart_json or ticker not in chart_json or not chart_json[ticker]:
        return pd.DataFrame()
    df = pd.DataFrame(chart_json[ticker])
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    return df

@st.cache_data(ttl=300) 
def fetch_agent_decisions():
    """Fetches the latest agent decisions from S3."""
    try:
        s3 = get_r2_client()
        bucket = os.getenv('R2_BUCKET', 'goyum-trading-data')
        response = s3.list_objects_v2(Bucket=bucket, Prefix='signals/')
        if 'Contents' not in response: return []
        latest_file = sorted(response['Contents'], key=lambda x: x['LastModified'])[-1]['Key']
        obj = s3.get_object(Bucket=bucket, Key=latest_file)
        return json.loads(obj['Body'].read().decode('utf-8'))
    except Exception:
        return [] 

# ==========================================
# 3. DYNAMIC HTML GENERATOR
# ==========================================
def render_custom_metric(label, value, subtext, is_percent=False, invert_colors=False):
    """Dynamically generates HTML colors and arrows based on the value."""
    if value > 0:
        color = "#f85149" if invert_colors else "#3fb950" 
        arrow = "↗"
        sign = "+"
    elif value < 0:
        color = "#3fb950" if invert_colors else "#f85149" 
        arrow = "↘"
        sign = "-"
    else:
        color = "#58a6ff" 
        arrow = "−"
        sign = ""
        
    formatted_num = f"{abs(value):.2f}" if isinstance(value, float) else str(abs(value))
    if is_percent: formatted_num += "%"
        
    st.markdown(f"""
        <div style="padding: 5px;">
            <p style='color:#7d8590; font-size:0.75rem; font-weight:600; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:8px;'>{label}</p>
            <p style='color:{color}; font-family:"JetBrains Mono", monospace; font-size:1.9rem; font-weight:700; margin-bottom:8px;'>{sign}{formatted_num} <span style='font-size:1.2rem;'>{arrow}</span></p>
            <p style='color:#7d8590; font-size:0.8rem; margin-bottom:0px;'>{subtext}</p>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 4. MAIN DASHBOARD EXECUTION
# ==========================================
def main():
    # --- HEADER ---
    colA, colB = st.columns([3, 1])
    with colA:
        st.markdown("<h2 style='color:#e6edf3; margin-bottom:0px;'>📈 Agentic Trading <span style='font-size:1rem; color:#7d8590; font-weight:400;'>AI-Powered Dashboard</span></h2>", unsafe_allow_html=True)
    with colB:
        st.markdown(f"<p style='text-align:right; color:#7d8590; font-size: 0.85rem; margin-top:15px;'><span style='color:#3fb950; font-weight:700;'>● ONLINE</span> &nbsp;|&nbsp; Updated {datetime.now().strftime('%I:%M:%S %p')}</p>", unsafe_allow_html=True)
    st.write("")

    # --- LIVE DATA FETCHING ---
    total_trades, buying_count, selling_count = fetch_kpi_metrics()
    current_return, current_sharpe, current_drawdown, current_volatility = fetch_portfolio_performance()
    agent_data = fetch_agent_decisions()

    buy_count = sum(1 for item in agent_data if item.get('signal', '').upper() == 'BUY')
    sell_count = sum(1 for item in agent_data if item.get('signal', '').upper() == 'SELL')
    hold_count = sum(1 for item in agent_data if item.get('signal', '').upper() == 'HOLD')
    total_assets = len(agent_data) if agent_data else len(ASSETS)

    # --- ROW 1: METRICS ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        with st.container(border=True):
            render_custom_metric("Annual Return", current_return, "Equal-weight portfolio", is_percent=True)
    with col2:
        with st.container(border=True):
            render_custom_metric("Sharpe Ratio", current_sharpe, "Risk-adjusted return")
    with col3:
        with st.container(border=True):
            render_custom_metric("Max Drawdown", current_drawdown, "Peak-to-trough", is_percent=True, invert_colors=True) 
    with col4:
        with st.container(border=True):
            render_custom_metric("Volatility", current_volatility, "Annualised", is_percent=True)

    # --- ROW 2: SIGNALS ---
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        with st.container(border=True):
            render_custom_metric("Buy Signals", buy_count, f"of {total_assets} assets")
    with col6:
        with st.container(border=True):
            render_custom_metric("Sell Signals", -sell_count if sell_count > 0 else 0, f"of {total_assets} assets")
    with col7:
        with st.container(border=True):
            render_custom_metric("Hold Signals", hold_count, f"of {total_assets} assets")
    with col8:
        with st.container(border=True):
            render_custom_metric("Assets Tracked", len(ASSETS), "Stocks + Crypto")

    st.write("")

    # --- ROW 3: CHARTS & LIVE SIGNALS ---
    signal_col, chart_col = st.columns([1, 2.5])
    
    with signal_col:
        with st.container(border=True):
            st.markdown("<p style='font-size:0.85rem; font-weight:600; color:#e6edf3; margin-bottom:15px; letter-spacing:0.05em;'>LIVE SIGNALS</p>", unsafe_allow_html=True)
            
            # Dynamically map S3 JSON to the dataframe
            if agent_data:
                table_data = []
                for item in agent_data:
                    sig = item.get('signal', 'HOLD').upper()
                    icon = "🟢 BUY" if sig == "BUY" else ("🔴 SELL" if sig == "SELL" else "⚪ HOLD")
                    price_val = item.get('price')
                    formatted_price = f"${price_val:.2f}" if isinstance(price_val, (int, float)) else "Live"
                    
                    table_data.append({"Symbol": item.get('ticker', 'N/A'), "Price": formatted_price, "Signal": icon})
                df_live = pd.DataFrame(table_data)
            else:
                df_live = pd.DataFrame({"Symbol": ["Awaiting S3 Sync"], "Price": [""], "Signal": [""]})
                
            st.dataframe(df_live, width="stretch", hide_index=True)
        with st.container(border=True):
            st.markdown("<p style='font-size:0.85rem; font-weight:600; color:#e6edf3; margin-bottom:15px;'>NEWS SENTIMENT</p>", unsafe_allow_html=True)
            sentiment_df = fetch_r2_csv('data/sentiment_scores.csv')
            if sentiment_df is not None and not sentiment_df.empty:
                fig_sent = go.Figure(go.Bar(
                    x=sentiment_df['sentiment_score'],
                    y=sentiment_df['symbol'],
                    orientation='h',
                    marker_color=['#3fb950' if v >= 0 else '#f85149' for v in sentiment_df['sentiment_score']]
                ))
                fig_sent.update_layout(
                    template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=0, r=0, t=10, b=0), height=280,
                    xaxis=dict(gridcolor='#1e293b', title=None), yaxis=dict(gridcolor='#1e293b', title=None)
                )
                st.plotly_chart(fig_sent, use_container_width=True)
            else:
                st.caption("Sentiment data not yet synced.")

    with chart_col:
        with st.container(border=True):
            selected_asset = st.selectbox("Market Chart Asset", ASSETS, label_visibility="collapsed")
            df_chart = fetch_chart_data(selected_asset)
            if df_chart.empty:
                st.warning(f"No chart data synced yet for {selected_asset}. This updates daily via the pipeline.")
            else:
                fig = go.Figure(data=[go.Candlestick(
                    x=df_chart.index, open=df_chart['Open'], high=df_chart['High'],
                    low=df_chart['Low'], close=df_chart['Close'],
                    increasing_line_color='#3fb950', decreasing_line_color='#f85149'
                )])
                fig.update_layout(
                    template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False, height=400,
                    yaxis=dict(gridcolor='#1e293b'), xaxis=dict(gridcolor='#1e293b')
                )
                st.plotly_chart(fig, use_container_width=True)

    st.write("")

    # --- ROW 4: TABS ---
    tab1, tab2, tab3 = st.tabs(["⚙️ Agent Decision Engine", "📊 Backtesting", "📰 Market News", "🧠 Model Insights"])
    
    with tab1:
        with st.container(border=True):
            st.markdown("<p style='font-size:0.8rem; font-weight:600; color:#fff; margin-bottom:15px;'>AGENT DECISION ENGINE LOGIC</p>", unsafe_allow_html=True)
            
            if not agent_data:
                st.info("Awaiting daily Agentic Workflow sync from AWS S3.")
            else:
                for item in agent_data:
                    ticker = item.get('ticker', 'UNKNOWN')
                    signal = item.get('signal', 'HOLD').upper()
                    conf = float(item.get('confidence', 0.5))
                    reasoning = item.get('reasoning', 'Rule-based decision applied.')
                    
                    if signal == "BUY":
                        bg_color, text_color, icon = "#3fb95033", "#3fb950", "🟢"
                    elif signal == "SELL":
                        bg_color, text_color, icon = "#f8514933", "#f85149", "🔴"
                    else:
                        bg_color, text_color, icon = "#1e293b", "#c9d1d9", "⚪"

                    col_a, col_b, col_c = st.columns([1.5, 3, 1.5])
                    with col_a: 
                        st.markdown(f"<span style='font-weight:700; font-size:1.1rem; color:#e6edf3;'>{ticker}</span> &nbsp;&nbsp; <span style='background-color:{bg_color}; padding:3px 10px; border-radius:4px; font-weight:600; font-size:0.75rem; color:{text_color};'>{icon} {signal}</span>", unsafe_allow_html=True)
                    with col_b: 
                        st.progress(conf, text=f"Agent Confidence: {int(conf * 100)}%")
                    with col_c: 
                        st.markdown(f"<p style='text-align:right; font-size:0.8rem; color:#7d8590; margin-top:5px;'>RSI: {item.get('rsi', 'N/A')} | Vol: {item.get('volume', 'N/A')}</p>", unsafe_allow_html=True)
                    
                    st.caption(f"*Agent Rationale:* {reasoning}")
                    st.divider()

    with tab2:
        with st.container(border=True):
            try:
                df_backtest = pd.read_csv("data/backtest_summary.csv")
                def style_dataframe(val):
                    try:
                        num = float(str(val).replace('%', ''))
                        if num > 0: return 'color: #3fb950;'
                        elif num < 0: return 'color: #f85149;'
                    except: pass
                    return 'color: #8b949e;'
                st.dataframe(df_backtest.style.map(style_dataframe), width="stretch", hide_index=True)
            except Exception:
                st.info("Upload backtest_summary.csv to data/ to view this section.")
        st.write("")
        with st.container(border=True):
            st.markdown("<p style='font-size:0.8rem; font-weight:600; color:#fff; margin-bottom:15px;'>RECENT TRADE LOG</p>", unsafe_allow_html=True)
            try:
                engine = get_db_engine()
                recent_trades = pd.read_sql(
                    "SELECT ticker, signal_date, signal, quantity, price, confidence, reason FROM trade_log ORDER BY inserted_at DESC LIMIT 20",
                    engine
                )
                st.dataframe(recent_trades, width="stretch", hide_index=True)
            except Exception:
                st.info("Trade log not available yet.")
        

    with tab3:
        with st.container(border=True):
            try:
                news_df = fetch_r2_csv('data/sentiment_scores.csv')
                if news_df is not None and 'headline' in news_df.columns:
                    for _, row in news_df.iterrows():
                        st.markdown(f"**{row['headline']}**")
                        st.caption(f"{row['keyword']} • {row['date']}")
                        st.divider()
                else:
                    st.info("News headlines not yet synced. Re-run the pipeline to populate this.")
            except Exception:
                st.info("News data not yet available.")
    with tab4:
        with st.container(border=True):
            st.markdown("<p style='font-size:0.8rem; font-weight:600; color:#fff; margin-bottom:15px;'>MODEL PERFORMANCE</p>", unsafe_allow_html=True)

            metrics = fetch_r2_json('models/metrics.json')
            if metrics:
                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    render_custom_metric("Accuracy", metrics['accuracy'] * 100, "Test set", is_percent=True)
                with m2:
                    render_custom_metric("Buy Precision", metrics['precision_buy'] * 100, "Of predicted buys", is_percent=True)
                with m3:
                    render_custom_metric("Buy Recall", metrics['recall_buy'] * 100, "Of actual buys caught", is_percent=True)
                with m4:
                    st.markdown(f"<p style='color:#7d8590; font-size:0.75rem; margin-top:20px;'>Last trained</p><p style='color:#e6edf3; font-size:1rem;'>{metrics['trained_at']}</p>", unsafe_allow_html=True)
            else:
                st.info("Model metrics not yet synced from R2.")

            st.divider()

            img_col1, img_col2 = st.columns(2)
            with img_col1:
                st.markdown("<p style='color:#8b949e; font-size:0.8rem;'>Confusion Matrix</p>", unsafe_allow_html=True)
                cm_bytes = fetch_r2_image('plots/confusion_matrix.png')
                if cm_bytes:
                    st.image(cm_bytes, use_container_width=True)
                else:
                    st.caption("Not available yet.")
            with img_col2:
                st.markdown("<p style='color:#8b949e; font-size:0.8rem;'>Feature Importance</p>", unsafe_allow_html=True)
                fi_bytes = fetch_r2_image('plots/feature_importance.png')
                if fi_bytes:
                    st.image(fi_bytes, use_container_width=True)
                else:
                    st.caption("Not available yet.")

            st.divider()
            st.markdown("<p style='font-size:0.8rem; font-weight:600; color:#fff; margin-bottom:15px;'>PER-ASSET BACKTEST CURVE</p>", unsafe_allow_html=True)
            asset_choice = st.selectbox("Select asset", ASSETS, key="backtest_asset_picker")
            safe_name = asset_choice.replace('-', '_')
            curve_bytes = fetch_r2_image(f'plots/{safe_name}_backtest.png')
            if curve_bytes:
                st.image(curve_bytes, use_container_width=True)
            else:
                st.caption(f"No backtest plot found for {asset_choice} yet.")
if __name__ == "__main__":
    main()
