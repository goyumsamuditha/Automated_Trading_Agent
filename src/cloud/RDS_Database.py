import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
DB_URL = os.getenv("SUPABASE_DB_URL")
engine = create_engine(DB_URL, echo=False)

def create_table():
    with engine.connect() as conn:
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS asset_features (
                id          SERIAL PRIMARY KEY,
                ticker      VARCHAR(20),
                date        DATE,
                close       FLOAT,
                rsi_14      FLOAT,
                macd        FLOAT,
                sma_20      FLOAT,
                sma_50      FLOAT,
                bb_width    FLOAT,
                volatility  FLOAT,
                label       INT,
                inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS trade_log (
                id          SERIAL PRIMARY KEY,
                ticker      VARCHAR(20),
                signal_date DATE,
                signal      VARCHAR(10),
                quantity    FLOAT,
                confidence  FLOAT,
                price       FLOAT,
                reason      VARCHAR(255),
                inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''))
        conn.commit()
    print("Tables created successfully.")


def push_asset_features(ticker):
    safe = ticker.replace('-', '_')
    base = Path(__file__).resolve().parent.parent.parent
    file_path = base / 'data' / 'featured' / f'{safe}_featured.csv'

    df = pd.read_csv(file_path, skiprows=2, header=None, index_col=0, parse_dates=True)
    df.index.name = 'date'
    df['ticker'] = ticker
    df.reset_index(inplace=True)
    df.rename(columns={
        'Close': 'close', 'RSI_14': 'rsi_14', 'MACD': 'macd',
        'SMA_20': 'sma_20', 'SMA_50': 'sma_50',
        'BB_Width': 'bb_width', 'Volatility_20': 'volatility', 'Label': 'label',
    }, inplace=True)
    cols = ['ticker', 'date', 'close', 'rsi_14', 'macd', 'sma_20', 'sma_50', 'bb_width', 'volatility', 'label']
    existing = [c for c in cols if c in df.columns]
    df[existing].to_sql('asset_features', engine, if_exists='append', index=False)
    print(f'Pushed {len(df)} rows for {ticker} to Supabase.')


def log_trade(ticker, signal_date, signal, confidence, price, quantity, reason):
    with engine.connect() as conn:
        query = text('''
            INSERT INTO trade_log
            (signal_date, signal, ticker, quantity, price, confidence, reason)
            VALUES (:d, :s, :t, :q, :p, :c, :r)
        ''')
        conn.execute(query, {
            'd': signal_date, 's': signal, 't': ticker,
            'q': quantity, 'p': price,
            'c': round(float(confidence), 4), 'r': reason
        })
        conn.commit()


def query_trade_log():
    return pd.read_sql('SELECT * FROM trade_log ORDER BY signal_date DESC', engine)


if __name__ == '__main__':
    create_table()
