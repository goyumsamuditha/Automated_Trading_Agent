# import required libraries
import yfinance as yf # Yahoo Finance API for data collection
import os
import datetime

# assets to collect data for
# AAPL : Apple
# MSFT : Microsoft Corporation
# GOOGL : Alphabet
# AMZN : Amazon
# META : Meta Platforms
# TSLA : Tesla
# NVDA : NVIDIA
# AMD : Advanced Micro Devices
# IBM : International Business Machines Corporation
# BTC-USD : Bitcoin
# ETH-USD : Ethereum
assets = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META','TSLA', 'NVDA','AMD','IBM','BTC-USD','ETH-USD']
# Set the start and end dates for data collection
start_date = '2010-01-01'
end_date = datetime.datetime.now().strftime('%Y-%m-%d')
# Create a directory to store the data if it doesn't exist
data_dir = 'data/raw'

# ensure the directory exists
os.makedirs(data_dir, exist_ok=True)

def collect_data(asset):
    """Collect historical data for the specified assets and save to CSV files."""
    
    # download data from Yahoo Finance
    print(f'Collecting data for {asset}...')
    df = yf.download(asset, start=start_date, end=end_date)

    # if empty
    if df.empty:
        print(f'No data found for {asset}. Skipping.')
        return

    # enhance the file name
    clean_name = asset.replace('-', '_')
    file_path = f"{data_dir}/{clean_name}.csv"

    # save to CSV
    df.to_csv(file_path)
    print(f'Data for {asset} saved to {file_path}.')



if __name__ == "__main__":
    for asset in assets:
        collect_data(asset)

    print("All data saved.....")
