import streamlit as st
import pandas as pd
import boto3
import json
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()


# Page configuration
st.set_page_config(
    page_title="Trading  Dashboard",
    layout="wide",
)

# Global CSS
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');
    
    html, body {
        font-family: 'IBM Plex Sans', sans-serif;
        background-color: #0f1117;
        color: #e0e0e0;
    }
    #MainMenu,footer, header { visibility: hidden; }
    
    /* Sidebar */
    [data-testid="stSidebar"]{
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    
    /* Section headers */
    h2, h3 {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.9rem !important;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #8b949e !important;
    }
    
    /* Metric Cards */
    [data-testid="stMetricValue"] {
        background: #ffffff;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.6rem ;
    }
    
    [data-testid="stMetricLabel"] {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.7rem ;
        letter-spacing: 0.08em;
        color: #a0aab4;
    }
 
    [data-testid="stDataFrame"] {
        border: 1px solid #30363d;
        border-radius: 8px;
    }
    [data-testid="stSidebar"] * { 
    color: #c9d1d9; 
    }
    p { color: #c9d1d9 !important; }
    .block-container { background-color: #0f1117; }
    </style>
    """,
    unsafe_allow_html=True
)
assets = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META','TSLA', 'NVDA','AMD','IBM','BTC-USD','ETH-USD']


session = boto3.Session(
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('AWS_SECRET_KEY'),
    region_name=os.getenv('AWS_REGION', 'eu-north-1')
)
s3 = session.client('s3')
bucket = os.getenv('S3_BUCKET', 'goyum-trading-data')


DB_URL = f'mysql+pymysql://{os.getenv("RDS_USER")}:{os.getenv("RDS_PASSWORD")}'f'@{os.getenv("RDS_HOST")}:3306/{os.getenv("RDS_DB","database-1")}'
engine = create_engine(DB_URL)



st.sidebar.markdown("### 📡 Live Trading Signals")
try:
    response = s3.list_objects_v2(Bucket=bucket, Prefix='signals/')
    latest_file = sorted(response['Contents'], key=lambda x: x['LastModified'])[-1]['Key']
    
    obj = s3.get_object(Bucket=bucket, Key=latest_file)
    signal_data = json.loads(obj['Body'].read().decode('utf-8'))
    
    for item in signal_data:
        signal = item.get('signal', '-')
        confidence = item.get('confidence', 0)
        
        if signal == "BUY":
           icon, color = "🟢", "#3fb950"
        elif signal == "SELL":
            icon, color = "🔴", "#f85149"
        else:
            icon, color = "🟡", "#d29922"
            
        col1, col2 = st.sidebar.columns([1, 1])
        col1.markdown(f"**{icon} {item['ticker']}**")
        col2.markdown(f"<p style='color:{color}; font-weight:700; margin:0'>{signal}</p>", unsafe_allow_html=True)
        st.sidebar.caption(f"Confidence: {confidence:.2f}")
        st.sidebar.divider()
        
except Exception as e:
    st.sidebar.error(f"Could not load latest signals.{e}")


# Header
st.markdown("<h1 style='color:#ffffff; font-size:2rem;'>📈 Automated Trading Agent Dashboard</h1>", unsafe_allow_html=True)
st.markdown(f"<p style='color:#8b949e'>Last updated: {datetime.now().strftime('%d %b %Y  %H:%M:%S')}</p>", unsafe_allow_html=True)
st.divider()

# KPI Metrics
st.markdown("### 📊 Portfolio Overview")
try:
    total_trades = pd.read_sql("SELECT COUNT(*) AS total FROM trade_log", engine).iloc[0]['total']
    top_df = pd.read_sql("SELECT ticker, COUNT(*) AS count FROM trade_log GROUP BY ticker ORDER BY count DESC LIMIT 1", engine)
    top_ticker = top_df.iloc[0]['ticker'] if not top_df.empty else 'N/A'
    buying_count = pd.read_sql("SELECT COUNT(*) AS count FROM trade_log WHERE `signal`='BUY'", engine).iloc[0]['count']
    selling_count = pd.read_sql("SELECT COUNT(*) AS count FROM trade_log WHERE `signal`='SELL'", engine).iloc[0]['count']

except Exception:
    total_trades = 0
    top_ticker = 'N/A'
    buying_count = 0
    selling_count = 0
    
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Trades", total_trades)
col2.metric("Top Asset", top_ticker)
col3.metric("Buy Signals", buying_count)
col4.metric("Sell Signals", selling_count)
col5.metric("Live Assets", len(assets))

st.divider()

# Trade Log
st.markdown("### 📊 Recent Trade Log")

try:
    df = pd.read_sql("SELECT * FROM trade_log ORDER BY signal_date DESC LIMIT 10", engine)
    
    if df.empty:
        st.markdown("No trade data available yet.")
    else:
        def colour_signal(val):
            if val == 'BUY':
                return 'color: #3fb950; font-weight: 600'
            elif val == 'SELL':
                return 'color: #f85149; font-weight: 600'
            else:
                return 'color: #8b949e'
        
        def colour_conf(val):
            try:
                if float(val) >= 0.65:
                    return 'color: #3fb950'
                elif float(val) >= 0.45:
                    return 'color: #d29922'
                return 'color: #f85149'
            except:
                return ''
        styled = df.style
        if 'signal' in df.columns:
            styled = styled.applymap(colour_signal, subset=['signal'])
        if 'confidence' in df.columns:
            styled = styled.applymap(colour_conf, subset=['confidence'])
        
        st.dataframe(styled, use_container_width=True, hide_index=True)
except Exception as e:
    st.error(f"Could not load trade log. {e}")
    
st.divider()


# Performance Summary

st.markdown("### 📈 Performance Summary")

try:
    df_perf = pd.read_sql("SELECT `signal`, COUNT(*) AS count, ROUND(AVG(confidence),3) AS avg_confidence,Round(AVG(price),2) AS avg_price FROM trade_log GROUP BY `signal`", engine)
    
    if not df_perf.empty:
        st.dataframe(df_perf, use_container_width=True, hide_index=True)
    else:
        st.markdown("No performance data available yet.")
except Exception as e:
    st.error(f"Could not load performance summary. {e}")
            