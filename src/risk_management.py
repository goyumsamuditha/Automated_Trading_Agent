import joblib
import pandas as pd
import numpy as np
from src.cloud.rds_database import log_trade


risk = {
    'min_confidence': 0.55,        # Minimum confidence level for executing a trade
    'max_position_pct': 0.20,  # Maximum percentage of total capital to allocate to a single position
    'stop_loss_pct': 0.05,      # Stop loss percentage
    'max_daily_trades': 5,         # Maximum number of trades per day
    'max_cash_pct': 0.50,          # Maximum percentage of total capital to use in cash for trading
}

portfolio = {
    'total_value': 100000,           # Total portfolio value
    'cash': 100000,                  # Available cash for trading
    'positions': {
        'AAPL': {'shares': 50, 'avg_price': 150.00},
        'MSFT': {'shares': 30, 'avg_price': 200.00},
        'GOOGL': {'shares': 10, 'avg_price': 120.00},
    },  # Current positions in the portfolio
    'trades_today': 0                     # Counter for trades executed today
}



def get_predictions(model, features):
    """ Get predictions and probabilities from the model for the given features. """
    scaled = scaler.transform([features])  # Scale the features using the same scaler used during training
    probability = model.predict_proba(scaled)[0]  # Get the predicted probabilities for each class
    predictions = model.predict(scaled)[0]  # Get the predicted class
    return predictions, probability

def check_stop_loss(position, current_price):
    """ Check if the stop loss threshold is breached for a given position. """
    if position not in portfolio['positions']:
        return False  # No position, no stop loss
    entry_price = portfolio['positions'][position]['entry_price']  # Get the entry price of the position
    stop_loss = (current_price - entry_price) / entry_price  # Calculate the percentage change from the entry price
    if stop_loss <= -risk['stop_loss_pct']:  # Check if the stop loss threshold is breached
        return True, f'Stop loss triggered for {position}: current price {current_price} is {stop_loss:.2%} below entry price {entry_price}'  # Return True and a message if stop loss is triggered
    return False  # Stop loss not triggered


def check_positon_size(symbol, price):
    """ Check if the position size for a given symbol is within the defined risk limits. """
    exposure = 0
    if symbol in portfolio['positions']:
        shares = portfolio['positions'][symbol] # Get the number of shares currently held for the symbol
        exposure = shares['shares'] * shares['entry_price'] # Calculate the current exposure for the symbol
    new_percentage = (exposure + price) / portfolio['total_value'] # Calculate the new percentage of total capital that would be allocated to the position after the trade
    if new_percentage > risk['max_position_pct']: # Check if the new percentage exceeds the maximum allowed position size
        return False, f'Position size for {symbol} would exceed max limit: {new_percentage:.2%} > {risk["max_position_pct"]:.2%}' # Return False and a message if position size would be exceeded
    return True, f'Position size for {symbol} is within limits: {new_percentage:.2%} <= {risk["max_position_pct"]:.2%}' # Return True and a message if position size is within limits


def risk_check(symbol, signal, confidence, current_price,trade_value,signal_time):
    if confidence < risk['min_confidence']:
        reason = f'Confidence {confidence:.2%} is below minimum threshold of {risk["min_confidence"]:.2%}' # Return False and a message if confidence is below threshold
        log_trade(symbol, signal_time, trade_value, confidence, current_price, False, reason, {0: 'Sell', 1: 'Hold', 2: 'Buy'}[signal]) # Log the trade attempt with the reason for rejection
        return False, reason
    if portfolio['trades_today'] >= risk['max_daily_trades']:
        reason = f'Max daily trades limit reached: {portfolio["trades_today"]} >= {risk["max_daily_trades"]}' # Return False and a message if maximum daily trades limit is reached
        log_trade(symbol, signal_time, trade_value, confidence, current_price, False, reason, {0: 'Sell', 1: 'Hold', 2: 'Buy'}[signal]) # Log the trade attempt with the reason for rejection
        return False, reason
    if signal == 2:  # Buy signal
        cash_pct = portfolio['cash'] / portfolio['total_value'] # Calculate the percentage of total capital currently available in cash
        if cash_pct < risk['max_cash_pct']: # Check if the available cash percentage is below the maximum allowed cash percentage
            reason = f'Not enough cash available: {cash_pct:.2%} < {risk["max_cash_pct"]:.2%}' # Return False and a message if not enough cash is available
            log_trade(symbol, signal_time, trade_value, confidence, current_price, False, reason, 'Buy') # Log the trade attempt with the reason for rejection
            return False, reason
    triggered, msg = check_stop_loss(symbol, current_price) # Check if the stop loss threshold is breached for the symbol
    if triggered:
        log_trade(symbol, signal_time, 'Sell (stop loss)', 1.0, current_price, True, msg) # Log the stop loss trade
        return False, msg
    if signal == 2:  # Buy signal
        ok, msg = check_positon_size(symbol, current_price) # Check if the position size for the symbol is within the defined risk limits
        if not ok:
            log_trade(symbol, signal_time, 'Buy', confidence, current_price, False, msg) # Log the trade attempt with the reason for rejection
            return False, msg
        reason = 'All risk checks passed' # Return True and a message if all risk checks are passed
        log_trade(symbol, signal_time, {0: 'Sell', 1: 'Hold', 2: 'Buy'}[signal], confidence, current_price, True, reason) # Log the successful trade attempt
        return True, reason
    