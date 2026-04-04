import json, boto3, os, joblib, io   
import pandas as pd
import yfinance as yf
import ta
from datetime import datetime


BUCKET  = os.getenv('S3_BUCKET', 'goyum-trading-data')
ASSETS  =['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META','TSLA', 'NVDA','AMD','IBM','BTC-USD','ETH-USD']

FEATURES = [
    'Open', 'High', 'Low', 'Close', 'Volume', 
    'RSI_14', 'SMA_20', 'SMA_50', 'MACD', 'MACD_Signal', 
    'RSI_Signal', 'MACD_Crossover', 'sentiment_score'
]                                                     

s3  = boto3.client('s3')

def load_model_from_s3(key): 
    '''Load the trained model from S3 and return it as a joblib object.'''
    buf = io.BytesIO()
    s3.download_fileobj(BUCKET, key, buf)
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
    df['RSI_Signal'] = ((df['RSI_14'] < 30).astype(int) - (df['RSI_14'] > 70).astype(int))
    df['MACD_Crossover'] = (df['MACD'] > df['MACD_Signal']).astype(int) * 2 - 1
    df['sentiment_score']    = 0.1
    return df.dropna()


def lambda_handler(event, context):
    try:
        model   = load_model_from_s3('models/decision_engine.pkl')
        scaler  = load_model_from_s3('models/scaler.pkl')
        today   = datetime.today().strftime('%Y-%m-%d')
        results = []
        for ticker in ASSETS:
            try:
                df     = yf.download(ticker, period='100d', progress=False)
                if df.empty:
                    continue
                df     = add_features(df)
                latest_raw = df[FEATURES].iloc[-1:]
                latest_scaled = scaler.transform(latest_raw)
                pred   = model.predict(latest_scaled)[0]
                proba  = model.predict_proba(latest_scaled)[0].max()
                label  = {0:'SELL', 1:'HOLD', 2:'BUY'}[pred]
                results.append({'ticker':ticker,
                            'date':today,
                            'signal':label,
                            'confidence':round(float(proba),3)})
            except Exception as e:
                results.append({'ticker':ticker,'error':str(e)})
    
        output_key = f'signals/signals_{today}.json'
        s3.put_object(Bucket=BUCKET, Key=output_key,
                  Body=json.dumps(results, indent=2),
                  ContentType='application/json')
        return {'statusCode': 200, 'body': results}
    
    except Exception as e:
        return {'statusCode': 500, 'body': str(e)}

