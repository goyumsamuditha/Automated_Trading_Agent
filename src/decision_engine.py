import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import seaborn as sns
import joblib,os
import sys
import os
sys.path.append(os.getcwd()) # add the current working directory to the system path to allow imports from src


asset = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'AMD', 'IBM', 'BTC-USD', 'ETH-USD'] # list of assets to analyze
features = ['Open', 'High', 'Low', 'Close', 'Volume','RSI_14','SMA_20','SMA_50','MACD','MACD_Signal','sentiment_score','RSI_Signal','MACD_Crossover'] # list of features to use for the model


# load and comined labelled data for all assets
frames = []
sentiment_data = pd.read_csv('data/sentiment_scores.csv') # load sentiment scores from CSV file
sentiment_map = dict(zip(sentiment_data['symbol'], sentiment_data['sentiment_score'])) # create a mapping of symbols to sentiment scores

for symbol in asset:
    safe = symbol.replace('-','_') # replace '-' with '_' for file naming
    df = pd.read_csv(f'data/featured/{safe}_featured.csv',index_col='Date',parse_dates=True) # load the featured data for the asset
    df['sentiment_score'] = sentiment_map.get(symbol, 0.0) # add the sentiment score to the DataFrame
    df['symbol'] = symbol # add the symbol to the DataFrame
    frames.append(df) # append the DataFrame to the list
    
combined_df = pd.concat(frames).sort_index() # combine all DataFrames into one and sort by index (date)
print(f"Combined dataset shape: {combined_df.shape}") # print the shape of the combined dataset
print(combined_df['symbol'].value_counts()) # print the count of each symbol in the combined dataset

# featue and labeling
cols_to_keep = features + ['signal'] # specify the columns to keep for modeling
tempp_df = combined_df[cols_to_keep].dropna() # create a temporary DataFrame with only the specified columns

X = tempp_df[features] # features for modeling
y = tempp_df['signal'] # target variable for modeling

print(f"Aligned X shape: {X.shape}") # print the shape of the final dataset after dropping NA values
print(f'Aligned y shape: {y.shape}') # print the shape of the target variable to confirm it matches the features

# split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42) # split the data into training and testing sets

# scale the features
scaler = StandardScaler() # initialize the StandardScaler
X_train_scaled = scaler.fit_transform(X_train) # fit the scaler to the training data and transform it
X_test_scaled = scaler.transform(X_test) # transform the testing data using the fitted scaler


# train the Random Forest Classifier
model = RandomForestClassifier(n_estimators=100,random_state=42, max_depth=10,min_samples_split=2,class_weight='balanced',n_jobs=-1) # initialize the Random Forest Classifier with specified parameters
model.fit(X_train_scaled, y_train) # fit the model to the training data
print("Model training completed.") # print a message indicating that model training is completed

# evaluate the model
y_pred = model.predict(X_test_scaled) # make predictions on the testing data
print("Classification Report:") # print the classification report
print(classification_report(y_test, y_pred, target_names=['Sell', 'Hold', 'Buy'])) # print the classification report
print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}") # print the accuracy of the model

#confusion matrix
cm = confusion_matrix(y_test, y_pred) # compute the confusion matrix
plt.figure(figsize=(8,6)) # set the figure size
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['Sell', 'Hold', 'Buy'], yticklabels=['Sell', 'Hold', 'Buy']) # create a heatmap of the confusion matrix
plt.xlabel('Predicted') # set the x-axis label
plt.ylabel('Actual') # set the y-axis label
plt.title('Confusion Matrix') # set the title of the plot
plt.tight_layout() # adjust the layout of the plot
plt.savefig('data/plots/confusion_matrix.png') # save the plot to a file
plt.show() # display the plot


# Feature importance
importances = model.feature_importances_ # get the feature importances from the model
feature_importance_df = pd.DataFrame({'feature': features, 'importance': importances}).sort_values(by='importance', ascending=False) # create a DataFrame of feature importances and sort it
plt.figure(figsize=(10,6)) # set the figure size
sns.barplot(x='importance', y='feature', data=feature_importance_df) # create a bar plot of feature importances
plt.title('Feature Importance') # set the title of the plot
plt.tight_layout() # adjust the layout of the plot
plt.savefig('data/plots/feature_importance.png') # save the plot to a file
plt.show() # display the plot

# save the model and scaler for future use
os.makedirs('models', exist_ok=True) # create the directory for saving models if it doesn't exist
joblib.dump(model, 'models/decision_engine.pkl') # save the trained model to a file
joblib.dump(scaler, 'models/scaler.pkl') # save the scaler to a file
print("Model and scaler saved to 'models/' directory.") # print a message indicating that the model and scaler have been saved


# Upload the model and scaler to S3
from src.cloud.S3_bucket import upload_models, upload_plots
upload_models() # upload the model and scaler to S3
upload_plots() # upload the plots to S3
print("Model, scaler, and plots uploaded to S3.") # print a message indicating that the model, scaler, and plots have been uploaded to S3
