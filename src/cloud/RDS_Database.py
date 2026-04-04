import pandas as pd
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()
DB_URL=(f'mysql+pymysql://{os.getenv("RDS_USER")}:{os.getenv("RDS_PASSWORD")}'f'@{os.getenv("RDS_HOST")}:3306/{os.getenv("RDS_DB",'database-1')}')  # construct the database URL
engine = create_engine(DB_URL, echo=False)  # create SQLAlchemy engine


def create_table():
    """Create the asset_features and trade_log tables in the database if they do not exist."""
    ADMIN_DB_URL = f'mysql+pymysql://{os.getenv("RDS_USER")}:{os.getenv("RDS_PASSWORD")}@{os.getenv("RDS_HOST")}:3306/'
    temp_engine = create_engine(ADMIN_DB_URL)
    
    with temp_engine.connect() as conn:
        db_name = os.getenv("RDS_DB", "database-1")
        # Use backticks for database names to avoid syntax errors
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}`"))
        conn.commit()
    temp_engine.dispose()
    print(f"Database '{db_name}' verified/created.")
    
    with engine.connect() as conn:
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS asset_features (
                id          INT AUTO_INCREMENT PRIMARY KEY,
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
        '''))                     # execute the SQL command to create the asset_features table if it does not exist
        conn.execute(text("DROP TABLE IF EXISTS trade_log")) # drop the trade_log table if it already exists to ensure a clean slate for logging trades
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS trade_log (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                ticker      VARCHAR(20),
                signal_date DATE,
                `signal`      VARCHAR(10),
                quantity    FLOAT,
                confidence  FLOAT,
                price       FLOAT,
                reason      VARCHAR(255),
                inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''))                    # execute the SQL command to create the trade_log table if it does not exist
        conn.commit()           # commit the transaction to save the changes to the database
    print("Tables created successfully.")



def push_asset_features(ticker):                         
    """Push the asset features DataFrame to the asset_features table in the database."""
    safe = ticker.replace('-','_')         # replace any hyphens in the DataFrame with underscores to ensure compatibility with SQL column names
    
    base = Path(__file__).resolve().parent.parent.parent  # base directory of the project
    file_path = base / 'data' / 'featured' / f'{safe}_featured.csv'  # construct the file path to the CSV file containing the asset features for the given ticker
    
    
    df = pd.read_csv(file_path, skiprows=2,header=None,index_col=0,parse_dates=True)  # read the CSV file into a DataFrame, skipping the first two rows which contain metadata, and setting the first column as the index while parsing it as dates
    df.index.name = 'date'  # rename the index to 'date' to match the column name in the database
    df['ticker'] = ticker  # assign the DataFrame to a variable named 'ticker' for easier reference
    df.reset_index(inplace=True)    # reset the index of the DataFrame to convert the 'Date' index back into a regular column, allowing it to be renamed and inserted into the database
    df.rename(columns={
        'Close':'close',
        'RSI_14':'rsi_14',
        'MACD':'macd',
        'SMA_20':'sma_20',
        'SMA_50':'sma_50',
        'BB_Width':'bb_width',
        'Volatility_20':'volatility',
        'Label':'label',
        }, inplace=True)  # rename the columns of the DataFrame to match the column names in the asset_features table in the database
    cols = ['ticker','date','close','rsi_14','macd','sma_20','sma_50','bb_width','volatility','label'] # create a list of the column names in the DataFrame that correspond to the columns in the asset_features table in the database, ensuring that only the relevant columns are inserted into the database
    
    existing = [c for c in cols if c in df.columns]  # check which of the expected columns are actually present in the DataFrame, creating a list of the existing columns to avoid errors when inserting into the database
    df[existing].to_sql('asset_features', engine,
                    if_exists='append', index=False)  # use the to_sql method to insert the data from the DataFrame into the asset_features table in the database, appending the data if the table already exists and not including the index as a column in the database
    
    print(f'Pushed {len(df)} rows for {ticker} to RDS database.')


def log_trade(ticker, signal_date, signal, confidence, price, quantity, reason):
    with engine.connect() as conn:                
        query = text('''
            INSERT INTO trade_log
            (signal_date, `signal`, ticker, quantity, price, confidence, reason)
            VALUES (:d, :s, :t, :q, :p, :c, :r)                     
        ''')
        conn.execute(query,{
            'd': signal_date,
            's': signal,
            't': ticker,
            'q': quantity,
            'p': price,
            'c': round(float(confidence), 4),
            'r': reason
        })
        conn.commit()


def query_trade_log():
    return pd.read_sql('SELECT * FROM trade_log ORDER BY signal_date DESC', engine)





if __name__ == '__main__':
    create_table()