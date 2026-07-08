import os
import boto3 # AWS SDK for Python  
from dotenv import load_dotenv
import json

from pathlib import Path

# load environment variables
load_dotenv()
s3 = boto3.client(
    's3',
    endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
    aws_access_key_id=os.getenv('R2_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('R2_SECRET_KEY'),
    region_name='auto',
)

bucket = os.getenv('R2_BUCKET')  
base = Path(__file__).resolve().parent.parent.parent  # base directory of the project

def upload_file_to_s3(file_path, s3_key):   
    """upload data files to S3 bucket """
    s3.upload_file(file_path, bucket, s3_key)   # upload file to S3
    print(f"File {file_path} uploaded to S3 bucket {bucket} with key {s3_key}") # print confirmation


def download_file_from_s3(s3_key, local_path):
    """Download file from S3"""
    os.makedirs(os.path.dirname(local_path), exist_ok=True)  # ensure local directory exists
    s3.download_file(bucket, s3_key, local_path)   # download file from S3
    print(f"File with key {s3_key} downloaded from S3 bucket {bucket} to {local_path}") # print confirmation

def upload_raw_data():
    """Upload all raw data files from the local directory to the S3 bucket."""
    local_dir = base / 'data' / 'raw'
    for filename in os.listdir(local_dir):
        if filename.endswith('.csv'):
            upload_file_to_s3(str(local_dir / filename), f'raw/{filename}')  # upload each file to S3 under the 'raw/' prefix


def upload_featured_data():
    """Upload all featured data files from the local directory to the S3 bucket"""
    local_dir = base / 'data' / 'featured'
    for filename in os.listdir(local_dir):
        if filename.endswith('.csv'):
            upload_file_to_s3(str(local_dir / filename), f'featured/{filename}')  # upload each file to S3 under the 'featured/' prefix

def upload_models():
    """ Upload all model files from the local directory to the S3 bucket"""
    local_dir = base / 'models'
    for filename in ['decision_engine.pkl', 'scaler.pkl']:
        filepath = local_dir / filename # construct full file path  
        if filepath.exists():  # check if file exists
            upload_file_to_s3(filepath, f'models/{filename}')  # upload each file to S3 under the 'models/' prefix

def upload_plots():
    """ Upload all plot files from the local directory to the S3 bucket"""
    local_dir = base / 'data' / 'plots'
    for filename in os.listdir(local_dir):
        if filename.endswith('.png'):
            upload_file_to_s3(str(local_dir / filename), f'plots/{filename}')  # upload each file to S3 under the 'plots/' prefix

def upload_data_files():
    """Upload sentiment scores and backtest summary CSVs to R2."""
    files_to_upload = [
        (base / 'data' / 'sentiment_scores.csv', 'data/sentiment_scores.csv'),
        (base / 'data' / 'backtest_summary.csv', 'data/backtest_summary.csv'),
    ]
    for filepath, s3_key in files_to_upload:
        if filepath.exists():
            upload_file_to_s3(str(filepath), s3_key)
def download_data_EC2():
    """Download all files from S3 to EC2"""
    objects = s3.list_objects_v2(Bucket=bucket).get('Contents',[])  # list all objects in the S3 bucket
    for obj in objects:
        key = obj['Key']  # get the key of each object
        local = key # set local path same as key
        download_file_from_s3(key, local)  # download each file from S3 to local path

if __name__ == "__main__":
    upload_raw_data()       # upload raw data files to S3
    print("Raw data files uploaded to S3 Bucket")
