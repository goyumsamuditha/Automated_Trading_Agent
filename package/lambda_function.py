import json, boto3, os, joblib
import pandas as pd
import yfinance as yf
import ta
from io import BytesIO
from datetime import datetime


BUCKET  = os.getenv('S3_BUCKET', 'trading-project-data')
ASSETS  = ['AAPL', 'TSLA', 'MSFT', 'BTC-USD', 'ETH-USD']
FEATURES = [
    'RSI_14','MACD','MACD_Signal','MACD_Hist',
    'SMA_20','SMA_50','BB_Width','Volatility_20',
    'Daily_Return','RSI_Signal','MA_Cross',
    'MACD_Cross','Sentiment',
]                                                     



def load_model_from_s3():   
    s3  = boto3.client('s3')
    buf = BytesIO()
    s3.download_fileobj(BUCKET, 'models/decision_engine.pkl', buf)
    buf.seek(0)
    return joblib.load(buf)



def add_features(df):
    close = df['Close'].squeeze()
    df['SMA_20']       = ta.trend.sma_indicator(close, 20)
    df['SMA_50']       = ta.trend.sma_indicator(close, 50)
    df['RSI_14']       = ta.momentum.rsi(close, 14)
    macd_obj           = ta.trend.MACD(close)
    df['MACD']         = macd_obj.macd()
    df['MACD_Signal']  = macd_obj.macd_signal()
    df['MACD_Hist']    = macd_obj.macd_diff()
    bb                 = ta.volatility.BollingerBands(close, 20)
    df['BB_Width']     = bb.bollinger_wband()
    df['Daily_Return'] = close.pct_change()
    df['Volatility_20']= df['Daily_Return'].rolling(20).std()
    df['RSI_Signal']   = ((df['RSI_14']<30).astype(int)
                         -(df['RSI_14']>70).astype(int))
    df['MA_Cross']     = (df['SMA_20']>df['SMA_50']).astype(int)*2-1
    df['MACD_Cross']   = (df['MACD']>df['MACD_Signal']).astype(int)*2-1
    df['Sentiment']    = 0.0
    return df.dropna()


def lambda_handler(event, context):
    model   = load_model_from_s3()
    today   = datetime.today().strftime('%Y-%m-%d')
    results = []
    for ticker in ASSETS:
        try:
            df     = yf.download(ticker, period='60d', progress=False)
            df     = add_features(df)
            latest = df[FEATURES].iloc[-1:]
            pred   = model.predict(latest)[0]
            proba  = model.predict_proba(latest)[0].max()
            label  = {0:'SELL', 1:'HOLD', 2:'BUY'}[pred]
            results.append({'ticker':ticker,'date':today,
                            'signal':label,
                            'confidence':round(float(proba),3)})
        except Exception as e:
            results.append({'ticker':ticker,'error':str(e)})


    s3  = boto3.client('s3')
    key = f'signals/signals_{today}.json'
    s3.put_object(Bucket=BUCKET, Key=key,
                  Body=json.dumps(results, indent=2),
                  ContentType='application/json')
    return {'statusCode': 200, 'body': json.dumps(results)}
