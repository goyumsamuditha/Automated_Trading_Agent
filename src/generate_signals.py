import json
import os
import sys
from datetime import datetime
 
import joblib
import pandas as pd
import yfinance as yf
import ta
 
sys.path.append(os.getcwd())  # allow imports from src when run as a script
from src.cloud.S3_bucket import upload_file_to_s3  # reuses your existing R2-configured client
 
ASSETS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'AMD', 'IBM', 'BTC-USD', 'ETH-USD']
 
FEATURES = ['Open', 'High', 'Low', 'Close', 'Volume', 'RSI_14', 'SMA_20', 'SMA_50', 'MACD', 'MACD_Signal', 'sentiment_score', 'RSI_Signal', 'MACD_Crossover']

 
 
def add_features(df):
    close = df['Close'].squeeze()
    df['SMA_20'] = ta.trend.sma_indicator(close, 20)
    df['SMA_50'] = ta.trend.sma_indicator(close, 50)
    df['RSI_14'] = ta.momentum.rsi(close, 14)
    macd_obj = ta.trend.MACD(close)
    df['MACD'] = macd_obj.macd()
    df['MACD_Signal'] = macd_obj.macd_signal()
    df['RSI_Signal'] = ((df['RSI_14'] < 30).astype(int) - (df['RSI_14'] > 70).astype(int))
    df['MACD_Crossover'] = (df['MACD'] > df['MACD_Signal']).astype(int) * 2 - 1
    df['sentiment_score'] = 0.1  # placeholder; wire in real sentiment_scores.csv lookup if desired
    return df.dropna()
 
 
def main():
    model = joblib.load('models/decision_engine.pkl')
    scaler = joblib.load('models/scaler.pkl')
    today = datetime.today().strftime('%Y-%m-%d')
    results = []

    for ticker in ASSETS:
        try:
            df = yf.download(ticker, period='100d', progress=False)
            if df.empty:
             rsi_val = float(latest_raw['RSI_14'].values[0])
             macd_cross = float(latest_raw['MACD_Crossover'].values[0])
             reasons = []
            if rsi_val < 30:
                reasons.append("RSI signals oversold")
            elif rsi_val > 70:
                reasons.append("RSI signals overbought")
            reasons.append("MACD bullish crossover" if macd_cross == 1 else "MACD bearish crossover")
            reasoning = "; ".join(reasons)
            
                results.append({
                'ticker': ticker,
                'date': today,
                'signal': label,
                'confidence': round(float(proba), 3),
                'price': round(float(df['Close'].iloc[-1]), 2),
                'rsi': round(float(df['RSI_14'].iloc[-1]), 1),
                'volume': int(df['Volume'].iloc[-1]),
                'reasoning': reasoning,
            })
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df = add_features(df)
            latest_raw = df[FEATURES].iloc[-1:]
            latest_scaled = scaler.transform(latest_raw)
            pred = model.predict(latest_scaled)[0]
            proba = model.predict_proba(latest_scaled)[0].max()
            label = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}[pred]
            results.append({
                'ticker': ticker,
                'date': today,
                'signal': label,
                'confidence': round(float(proba), 3),
                'price': round(float(df['Close'].iloc[-1]), 2),
                'rsi': round(float(df['RSI_14'].iloc[-1]), 1),
                'volume': int(df['Volume'].iloc[-1]),
            })
        except Exception as e:
            results.append({'ticker': ticker, 'error': str(e)})

    os.makedirs('data/signals', exist_ok=True)
    local_path = f'data/signals/signals_{today}.json'
    with open(local_path, 'w') as f:
        json.dump(results, f, indent=2)

    upload_file_to_s3(local_path, f'signals/signals_{today}.json')
    print(f'Signals generated and uploaded for {today}.')

    # Also save recent price history for each asset, so the dashboard never needs live yfinance calls
    chart_data = {}
    for ticker in ASSETS:
        try:
            df_hist = yf.download(ticker, period="6mo", interval="1d", progress=False)
            if isinstance(df_hist.columns, pd.MultiIndex):
                df_hist.columns = df_hist.columns.get_level_values(0)
            df_hist = df_hist.reset_index()
            df_hist['Date'] = df_hist['Date'].astype(str)
            chart_data[ticker] = df_hist[['Date', 'Open', 'High', 'Low', 'Close']].to_dict('records')
        except Exception:
            chart_data[ticker] = []

    chart_path = 'data/signals/chart_history_latest.json'
    with open(chart_path, 'w') as f:
        json.dump(chart_data, f)
    upload_file_to_s3(chart_path, 'charts/chart_history_latest.json')
    print('Chart history uploaded.')


if __name__ == '__main__':
    main()
