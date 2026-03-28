import os
import boto3
from dotenv import load_dotenv
import json

# load environment variables
load_dotenv()
s3 = boto3.client(
    's3',
    aws_access_key_id = os.getenv('AWS_Access_KEY') ,       # access key
    aws_secret_access_key = os.getenv('AWS_SECRET_KEY'),    # secret key
    region_name           = os.getenv('AWS_REGION', 'eu-north-1'), # region

)

bucket = os.getenv('S3_BUCKET')  

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
    local_dir = 'data/raw'
    for filename in os.listdir(local_dir):
        if filename.endswith('.csv'):
            upload_file_to_s3(f'data/raw/{filename}',f'raw/{filename}')  # upload each file to S3 under the 'raw/' prefix


def upload_featured_data():
    """Upload all featured data files from the local directory to the S3 bucket"""
    local_dir = 'data/featured'
    for filename in os.listdir(local_dir):
        if filename.endswith('.csv'):
            upload_file_to_s3(f'data/featured(f)',f'featured/{filename}')  # upload each file to S3 under the 'featured/' prefix

def upload_models():
    """ Upload all model files from the local directory to the S3 bucket"""
    for filename in ('decision_engine.pkl', 'scaler.pkl'):        
        if os.path.exists(f'models/(f)'):
            upload_file_to_s3(f'models/(f)',f'models/(f)')  # upload each file to S3 under the 'models/' prefix

def upload_plots():
    """ Upload all plot files from the local directory to the S3 bucket"""
    local_dir = 'data/plots'
    for filename in os.listdir(local_dir):
        if filename.endswith('.png'):
            upload_file_to_s3(f'data/plots(f)',f'plots/{filename}')  # upload each file to S3 under the 'plots/' prefix


def download_data_EC2():
    """Download all files from S3 to EC2"""
    objects = s3.list_v2(Bucket=bucket).get('contents',[])  # list all objects in the S3 bucket
    for obj in objects:
        key = obj['Key']  # get the key of each object
        local = key # set local path same as key
        download_file_from_s3(key, local)  # download each file from S3 to local path

if __name__ == "__main__":
    upload_raw_data()       # upload raw data files to S3
    print("Raw data files uploaded to S3 Bucket")