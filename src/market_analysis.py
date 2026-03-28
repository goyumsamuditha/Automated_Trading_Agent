import pandas as pd
import numpy as np

assets = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META','TSLA', 'NVDA','AMD','IBM','BTC-USD','ETH-USD']
threshold = 0.05 # 5% movement threshold
horizon = 5 # look ahead 5 days


def market_signal(asset,horizon=horizon,threshold=threshold):
    """Generate market signals based on future returns for a given asset."""
    df = df.copy()
    df['Future_Close'] = df['Close'].shift(-horizon)/ df['Close'] - 1 # calculate future return
    
    def assign_signal(x):
        if x >= threshold:
            return 2  # Buy signal
        elif x < -threshold:
            return 0 # Sell signal
        else:
            return 1  # Hold signal
    df['signal'] = df['Future_Close'].apply(assign_signal) # assign signal based on future return
    return df


def generate_signals():
    df = df.copy()
    df['RSI_Signal'] = np.where(df['RSI'] < 30, 1, np.where(df['RSI'] > 70, -1, 0)) # generate RSI signal
    df['MACD_Signal'] = np.where(df['MACD'] > df['Signal_Line'], 1, np.where(df['MACD'] < df['Signal_Line'], -1, 0)) # generate MACD signal
    df['MA_Cross'] = np.where(df['SMA_20'] > df['SMA_50'], 1, -1) # generate moving average crossover signal
    df['MACD_Crossover'] = np.where(df['MACD'] > df['MACD_Signal'], 1, -1) # generate MACD crossover signal
    df['Combined_Signal'] = df['RSI_Signal'] + df['MACD_Signal'] + df['MA_Cross'] # combine signals
    return df

if __name__ == "__main__":
    for asset in assets:
        df = pd.read_csv(f"data/featured/{asset.replace('-', '_')}.csv", index_col='Date',parse_dates=True ) # read featured data
        df = market_signal(df) # generate market signals
        df = generate_signals(df) # generate technical signals
        print(f'\n{asset} - Signal Distribution:\n{df["signal"].value_counts()}') # print signal distribution
        counts = df['Label'].value_counts() # count the number of each signal type
        total = len(df) # total number of rows
        print(f'Sell: {counts.get(0, 0)} ({counts.get(0, 0)/total:.1%})') # print sell signal count and percentage
        print(f'Hold: {counts.get(1, 0)} ({counts.get(1, 0)/total:.1%})') # print hold signal count and percentage
        print(f'Buy: {counts.get(2, 0)} ({counts.get(2, 0)/total:.1%})') # print buy signal count and percentage
        df.to_csv(f"data/featured/{asset.replace('-', '_')}_featured.csv") # save updated data back to CSV
print("Signal generation completed for all assets.")
