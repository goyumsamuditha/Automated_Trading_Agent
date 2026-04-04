import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # add the parent directory to the system path to allow imports from src
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import joblib
from src.cloud.RDS_Database import log_trade
from src.cloud.S3_bucket  import upload_plots

features = ['Open', 'High', 'Low', 'Close', 'Volume','RSI_14',
            'SMA_20','SMA_50','MACD','MACD_Signal','sentiment_score','RSI_Signal','MACD_Crossover'
            ]# List of features used for prediction

model = joblib.load('models/decision_engine.pkl') # Load the trained model from a file
scaler = joblib.load('models/scaler.pkl') # Load the scaler used for feature scaling during training

sentiment_df = pd.read_csv('data/sentiment_scores.csv') # Load sentiment scores from a CSV file
symbols = sentiment_df.iloc[:, 0]
scores = sentiment_df.iloc[:, 2]
sentiment_map = dict(zip(symbols, scores)) # Create a mapping of symbols to sentiment scores for easy lookup

def backtest_asset(data, initial_capital=100000):
    safe = data.replace('-','_') # Replace any dashes in the asset name with underscores for file naming
    df = pd.read_csv(f'data/featured/{safe}_featured.csv') # Load the feature data for the asset from a CSV file
    df.columns = df.columns.str.strip() # Strip any leading or trailing whitespace from the column names to ensure they match the expected feature names
    df['Date'] = pd.to_datetime(df['Date']) # Convert the 'Date' column to datetime format
    df['sentiment_score'] = sentiment_map.get(data, 0.1) # Add the sentiment score to the DataFrame based on the asset symbol, defaulting to 0.1 if not found
    df.dropna(subset=features, inplace=True) # Drop any rows with missing values in the feature columns
    
    split = int(len(df) * 0.8) # Define the split point for training and testing data (80% training, 20% testing)
    test = df.iloc[split:].copy() # Create a copy of the test data for backtesting
    
    X_test = scaler.transform(test[features]) # Scale the test features using the same scaler used during training
    test['predicted_signal'] = model.predict(X_test) # Get the predicted trading signals from the model
    test['Confidence'] = model.predict_proba(X_test).max(axis=1) # Get the confidence of the predictions
    
    cash = float(initial_capital) # Initialize cash with the initial capital
    shares = 0 # Initialize shares to zero
    portfolio_values = [] # List to store the portfolio value over time
    
    for index, row in test.iterrows():
        date = row['Date'] # Get the date for the current row
        price = float(row['Close']) # Get the closing price for the current date    
        conf = float(row['Confidence']) # Get the confidence of the prediction for the current date
        
        if row['predicted_signal'] == 2 and conf >= 0.45 and cash > price: # If the predicted signal is 'Buy', confidence is above threshold, and there is enough cash to buy
            spend = min(cash*0.10,cash) # Calculate the amount to spend on buying shares (10% of cash or remaining cash)
            shares_to_buy = int(spend // price) # Calculate the number of shares to buy based on the spend amount and current price
            if shares_to_buy > 0: # If there are shares to buy
                shares += shares_to_buy # Update the total shares held
                cash -= shares_to_buy * price # Deduct the cost of buying shares from cash
                log_trade(str(date.date()), 'BUY', safe, shares_to_buy, price, conf, 'Backtest Buy') # Log the trade in the database
            
        elif row['predicted_signal'] == 0 and conf >= 0.45 and shares > 0: # If the predicted signal is 'Sell', confidence is above threshold, and there are shares to sell
            cash += shares * price # Add the proceeds from selling shares to cash
            log_trade(str(date.date()), 'SELL', safe, shares, price, conf, 'Backtest Sell') # Log the trade in the database
            shares = 0 # Reset shares to zero after selling
            
        portfolio_values.append(cash + shares * price) # Calculate and store the current portfolio value (cash + value of held shares)
        
    results = pd.Series(portfolio_values, index=test.index, name='Portfolio Value') # Create a pandas Series to store the portfolio values over time
    final = results.iloc[-1] # Get the final portfolio value at the end of the backtest
    ret = (final - initial_capital) / initial_capital # Calculate the return on investment
    daily = results.pct_change().dropna() # Calculate daily returns from the portfolio values
    sharpe = (daily.mean() / daily.std()) * np.sqrt(252) # Calculate the Sharpe ratio using daily returns (assuming 252 trading days in a year
    rolling_max = results.cummax() # Calculate the cumulative maximum of the portfolio values to determine drawdown
    drawdown = (results - rolling_max) / rolling_max # Calculate the drawdown as the percentage drop from the cumulative maximum
    max_drawdown = drawdown.min() # Get the maximum drawdown from the drawdown series
    
    print(f'\n Backtest Results for {safe}:') # Print the backtest results for the asset
    print(f'Starting Capital: ${initial_capital:.2f}') # Print the starting capital
    print(f'Final Portfolio Value: ${final:.2f}') # Print the final portfolio value
    print(f'Total Return: {ret:.2%}') # Print the total return on investment
    print(f'Sharpe Ratio: {sharpe:.2f}') # Print the Sharpe ratio
    print(f'Max Drawdown: {max_drawdown:.2%}') # Print the maximum drawdown
    
    # plot the strategy vs buy and hold
    buy_and_hold = (test['Close'] / test['Close'].iloc[0])* initial_capital # Calculate the buy and hold strategy values for comparison
    fig, ax = plt.subplots(figsize=(12, 6)) # Create a new figure and axis for plotting
    ax.plot(results, label='Strategy', color='blue') # Plot the strategy portfolio values over time
    ax.plot(buy_and_hold, label='Buy and Hold', color='orange') # Plot the buy and hold strategy values over time
    ax.set_title(f'Backtest Results for {safe}') # Set the title of the plot
    ax.set_xlabel('Date') # Set the x-axis label
    ax.set_ylabel('Portfolio Value ($)') # Set the y-axis label
    ax.legend() # Add a legend to the plot
    plt.tight_layout() # Adjust the layout of the plot
    plt.savefig(f'data/plots/{safe}_backtest.png') # Save the plot to a file
    plt.close() # Close the plot to free up memory
    
    
    return {
        'final_value': final, # Return the final portfolio value
        'total_return': ret, # Return the total return on investment
        'sharpe_ratio': sharpe, # Return the Sharpe ratio
        'max_drawdown': max_drawdown, # Return the maximum drawdown
    }
    
    
if __name__ == "__main__":
    assets = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META','TSLA', 'NVDA','AMD','IBM','BTC-USD','ETH-USD'] # List of assets to backtest
    summary = [backtest_asset(asset) for asset in assets] # Run backtesting for each asset and store the results in a summary list
    summary_df = pd.DataFrame(summary, index=assets) # Create a DataFrame from the summary results
    print("\nBacktest Summary:") # Print the backtest summary
    print(summary_df) # Print the summary DataFrame with backtest results for all assets
    summary_df.to_csv('data/backtest_summary.csv') # Save the backtest summary to a CSV file
    upload_plots() # Upload the generated plots to the S3 bucket
    print("Backtest completed and results saved.") # Print a message indicating that the backtest is completed and results are saved