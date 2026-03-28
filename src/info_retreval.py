import requests  # for making HTTP requests
import pandas as pd
from textblob import TextBlob  # for sentiment analysis
from datetime import datetime, timedelta  # for handling date and time
import os
from dotenv import load_dotenv 


# Load environment variables from .env file
load_dotenv()
news_api_key = os.getenv('NEWS_API_KEY')

keywords = {
    'AAPL': 'Apple Inc.',
    'MSFT': 'Microsoft Corporation',
    'GOOGL': 'Alphabet Inc.',
    'AMZN': 'Amazon.com, Inc.',
    'META': 'Meta Platforms, Inc.',
    'TSLA': 'Tesla, Inc.',
    'NVDA': 'NVIDIA Corporation',
    'AMD': 'Advanced Micro Devices, Inc.',
    'IBM': 'International Business Machines Corporation',
    'BTC-USD': 'Bitcoin',
    'ETH-USD': 'Ethereum'
}   # mapping of stock symbols to company names for news retrieval

def fetch_news_data(keyword, days=7):
    """Fetch news articles related to the specified keyword from NewsAPI."""
    url = f'https://newsapi.org/v2/everything?q={keyword}&from={(datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")}&sortBy=publishedAt&apiKey={news_api_key}' # construct the API URL with query parameters
    params = {
        'q': keyword,
        'from': (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d'),
        'sortBy': 'relevancy',
        'apiKey': news_api_key,
        'language': 'en',
        'pageSize': 100
    }   # set the parameters for the API request
    try:
        response = requests.get(url, params=params,timeout=20) # set a timeout for the request
        articles = response.json().get('articles', []) # parse the JSON response and extract articles
        return[article['title'] for article in articles if article.get('title')] # return a list of article titles
    except Exception as e:
        print(f"Error fetching news for {keyword}: {e}")
        return [] # return an empty list in case of an error
    
def analyze_sentiment(headlines):
    """Analyze the sentiment of the given text using TextBlob."""
    if not headlines:
        return 0.0 # return neutral sentiment if there are no headlines
    score = [TextBlob(text).sentiment.polarity for text in headlines] # calculate the sentiment polarity
    return round(sum(score) / len(score), 4) # return the average sentiment score rounded to 4 decimal places



def get_sentiment_scores():
    """Get sentiment scores for all keywords and save to a CSV file."""
    sentiment_data = []
    today = datetime.now().strftime('%Y-%m-%d')
    for symbol, keyword in keywords.items():
        print(f"Fetching news for {keyword}...")
        headlines = fetch_news_data(keyword) # fetch news headlines for the keyword
        sentiment_score = analyze_sentiment(headlines) # analyze the sentiment of the headlines
        print(f"Sentiment score for {keyword}: {sentiment_score}")
        sentiment_data.append({'symbol': symbol, 'keyword': keyword, 'sentiment_score': sentiment_score, 'date': today}) # append the results to the list
    df = pd.DataFrame(sentiment_data) # create a DataFrame from the sentiment data
    df.to_csv('data/sentiment_scores.csv', index=False) # save the DataFrame to a CSV file
    print("Sentiment scores saved to data/sentiment_scores.csv")
    return df


if __name__ == "__main__":
    get_sentiment_scores()
    print("Sentiment analysis completed and saved.")
    