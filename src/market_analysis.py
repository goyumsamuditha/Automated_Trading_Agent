import os

import pandas as pd
import numpy as np

assets = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META','TSLA', 'NVDA','AMD','IBM','BTC-USD','ETH-USD']
threshold = 0.05 # 5% movement threshold
horizon = 5 # look ahead 5 days


def market_signal(df,horizon=horizon,threshold=threshold):
    """Generate market signals based on future returns for a given asset."""
    df = df.copy()
    df['Future_Close'] = df['Close'].shift(-horizon)/ df['Close'] - 1 # calculate future return
    
    def assign_signal(x):
        if pd.isna(x):
            return 1  # Hold signal for NaN values (e.g., last few rows where future return cannot be calculated)
        if x >= threshold:
            return 2  # Buy signal
        elif x < -threshold:
            return 0 # Sell signal
        else:
            return 1  # Hold signal
    df['signal'] = df['Future_Close'].apply(assign_signal) # assign signal based on future return
    return df


def generate_signals(df):
    """Generate technical signals based on indicators."""
    df = df.copy()
    df['RSI_Signal'] = np.where(df['RSI_14'] < 30, 1, np.where(df['RSI_14'] > 70, -1, 0)) # generate RSI signal
    df['MACD_Signal'] = np.where(df['MACD'] > 0,1,-1) # generate MACD signal
    df['MA_Cross'] = np.where(df['SMA_20'] > df['SMA_50'], 1, -1) # generate moving average crossover signal
    df['MACD_Crossover'] = np.where(df['MACD'] > df['MACD_Signal'], 1, -1) # generate MACD crossover signal
    df['Combined_Signal'] = df['RSI_Signal'] + df['MACD_Signal'] + df['MA_Cross'] # combine signals
    return df

if __name__ == "__main__":
    for asset in assets:
        safe= asset.replace('-', '_') # create a safe version of the asset name for file paths
        file_path = f"data/featured/{safe}_featured.csv" # construct the file path to the CSV file containing the featured data for the given asset
        
        if os.path.exists(file_path):
            print(f"Processing {asset}...") # print the name of the asset being processed
            df = pd.read_csv(file_path) # read featured data
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']) # convert date column to datetime if it exists
                df.set_index('date', inplace=True) # set date as index if it's a column
            elif 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date']) # convert Date column to datetime if it exists
                df.set_index('Date', inplace=True) # set Date as index if it's a column
            else:
                print(f'Error:Unable to find date column in {asset} data. Columns found: {df.columns.tolist()}') # print an error message if no date column is found
                continue
        
        
            df = market_signal(df) # generate market signals
        
            df = generate_signals(df) # generate technical signals
            print(f'\n{asset} - Signal Distribution:\n{df["signal"].value_counts()}') # print signal distribution
            counts = df['signal'].value_counts() # count the number of each signal type
            total = len(df) # total number of rows
            print(f'Sell: {counts.get(0, 0)} ({counts.get(0, 0)/total:.1%})') # print sell signal count and percentage
            print(f'Hold: {counts.get(1, 0)} ({counts.get(1, 0)/total:.1%})') # print hold signal count and percentage
            print(f'Buy: {counts.get(2, 0)} ({counts.get(2, 0)/total:.1%})') # print buy signal count and percentage
            df.to_csv(f"data/featured/{safe}_featured.csv") # save updated data back to CSV
        else:
            print(f"File for {asset} not found at {file_path}. ") # print a warning message if the file is not found
print("Signal generation completed for all assets.")
