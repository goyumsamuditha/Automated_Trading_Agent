# Agentic AI Automated Trading System

### Project Overview
MSC Finance Project — An end-to-end agentic AI pipeline for automated trading signal generation across 11 financial assets using machine learning, technical analysis, and AWS cloud infrastructure.

The entire pipeline is deployed on **AWS**, operating daily via serverless triggers, with a real-time monitoring dashboard hosted on an EC2 instance.

### System Architecture & Workflow

The system is divided into six distinct layers, separating the heavy data science processing from the lightweight daily execution and user interface.

* **Agent 1 (Market Analysis):** Calculates technical indicators (RSI, MACD, SMA crossovers) and labels data based on 5-day forward returns.
* **Agent 2 (Information Retrieval):** Fetches daily global news headlines and extracts multi-class sentiment scores using NLP.
* **Agent 3 (Decision Engine):** A Random Forest Classifier (100 Trees, 13 Features) that outputs BUY/SELL/HOLD signals with confidence probabilities.
* **Agent 4 (Risk Management):** The "Gatekeeper." Enforces a 55% minimum confidence threshold, stop-loss limits, and portfolio sizing rules before approving a trade.

  <img width="721" height="781" alt="Duagram 1 drawio" src="https://github.com/user-attachments/assets/65e2d238-11a3-4115-b84d-a7290f549ddb" />

<img width="451" height="701" alt="Diagram 2 drawio" src="https://github.com/user-attachments/assets/17960bf6-5d8e-42bd-b744-2ea950428959" />

<img width="621" height="541" alt="diagram 3 drawio" src="https://github.com/user-attachments/assets/daea52e5-55c5-4f44-bbe5-7e7ffff3e850" />

### Technology Stack
* **Cloud Infrastructure (AWS):** * **EventBridge:** Daily cron schedule trigger (8:00 AM Local).
  * **Lambda:** Executes the daily trading pipeline.
  * **S3:** Stores historical raw data, trained `.pkl` models, and daily `signals.json` outputs.
  * **RDS (MySQL 8.4):** Maintains an immutable audit trail (`trade_log`) of all AI decisions.
  * **EC2:** Hosts the persistent 24/7 web dashboard.
* **Machine Learning:** `scikit-learn` (Random Forest, StandardScaler)
* **Data Pipelines:** `yfinance` (OHLCV data), `NewsAPI` (Sentiment), `pandas`
* **Frontend UI:** `Streamlit`


### Project Structure

├── data/

│     ├── featured/              # Processed data with technical indicators

│     ├── plots/                 # Generated EDA and performance charts

│     ├── raw/                   # Raw OHLCV market data

│     ├── backtest_summary.csv   # Historical backtesting results

│     └── sentiment_scores.csv   # NLP sentiment analysis outputs

├── notebooks/                 # Jupyter notebooks for experimentation

├── package/                   # AWS Lambda deployment packages

├── src/                       # Python scripts for the 4 ML Agents

├── .gitignore                 # Hidden files and keys

├── app.py                     # Streamlit Dashboard UI

├── requirements.txt           # Project dependencies

└── README.md                  # Project documentation

  
