import json
import boto3
import requests
import pandas as pd
from io import BytesIO
import os
import sys
import time

def load_credentials(credentials_path='.credentials.json'):
    """
    Load credentials and configuration from a JSON file.
    """
    try:
        with open(credentials_path) as f:
            credentials = json.load(f)
        return credentials
    except Exception as e:
        print(f"Error loading credentials from {credentials_path}: {e}")
        sys.exit(1)

def initialize_boto3_clients(credentials):
    """
    Initialize AWS SQS and S3 clients using provided credentials.
    """
    sqs = boto3.client(
        'sqs',
        aws_access_key_id=credentials['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=credentials['AWS_SECRET'],
        region_name=credentials.get('AWS_REGION', 'us-east-1')
    )
    s3 = boto3.client(
        's3',
        aws_access_key_id=credentials['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=credentials['AWS_SECRET'],
        region_name=credentials.get('AWS_REGION', 'us-east-1')
    )
    return sqs, s3

def receive_message(sqs, queue_url, wait_time=20, max_messages=1):
    """
    Receive messages from the specified SQS queue.
    """
    response = sqs.receive_message(
        QueueUrl=queue_url,
        AttributeNames=['All'],
        MessageAttributeNames=['All'],
        MaxNumberOfMessages=max_messages,
        WaitTimeSeconds=wait_time
    )
    messages = response.get('Messages', [])
    return messages

def delete_message(sqs, queue_url, receipt_handle):
    """
    Delete a message from the SQS queue after processing.
    """
    sqs.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=receipt_handle
    )

def download_parquet(url, hf_token):
    """
    Download a parquet file from the given URL using the Hugging Face token.
    """
    headers = {
        'Authorization': f'Bearer {hf_token}'
    }
    try:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        # Read parquet file into pandas DataFrame
        df = pd.read_parquet(BytesIO(response.content))
        return df
    except Exception as e:
        print(f"Error downloading or parsing parquet file from {url}: {e}")
        return None

def download_image(image_url):
    """
    Download an image from the given URL.
    """
    try:
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Error downloading image from {image_url}: {e}")
        return None

def upload_to_s3(s3, bucket_name, image_content, s3_key):
    """
    Upload image content to the specified S3 bucket with the given key.
    """
    try:
        s3.put_object(Bucket=bucket_name, Key=s3_key, Body=image_content)
        print(f"Uploaded image to S3: {s3_key}")
    except Exception as e:
        print(f"Error uploading image to S3: {s3_key}. Error: {e}")

def process_parquet(df, s3, bucket_name):
    """
    Process each row in the parquet DataFrame: download and upload images.
    """
    for index, row in df.iterrows():
        image_url = row.get('URL')
        if not image_url:
            print(f"No URL found in row {index}. Skipping.")
            continue
        image_content = download_image(image_url)
        if image_content:
            # Generate a unique S3 key, e.g., based on image URL or other metadata
            # For example, use the last part of the URL path
            image_filename = os.path.basename(image_url)
            # Optionally, include subdirectories based on metadata
            s3_key = f"images/{image_filename}"
            upload_to_s3(s3, bucket_name, image_content, s3_key)
        else:
            print(f"Failed to download image from {image_url}. Skipping to next.")

def main():
    """
    Main function to continuously process messages from SQS.
    """
    credentials = load_credentials()
    sqs, s3 = initialize_boto3_clients(credentials)

    # Retrieve SQS queue URL and S3 bucket name from credentials
    sqs_queue_url = credentials.get('SQS_QUEUE_URL')
    s3_bucket_name = credentials.get('S3_BUCKET_NAME')

    hf_token = credentials.get('HF_TOKEN')

    if not sqs_queue_url or not s3_bucket_name:
        print("Error: 'SQS_QUEUE_URL' and 'S3_BUCKET_NAME' must be set in the credentials file.")
        sys.exit(1)

    print(f"Starting to process messages from SQS queue: {sqs_queue_url}")
    while True:
        messages = receive_message(sqs, sqs_queue_url)
        if not messages:
            print("No messages available. Waiting...")
            time.sleep(10)  # Wait before checking for new messages
            continue

        for message in messages:
            message_body = message['Body']

            print(f"Processing parquet file URL: {message_body}")

            df = download_parquet(message_body, hf_token)
            if df is not None:
                process_parquet(df, s3, s3_bucket_name)
                # After successful processing, delete the message
                delete_message(sqs, sqs_queue_url, message['ReceiptHandle'])
                print(f"Deleted message from SQS: {message.get('MessageId')}")
            else:
                print(f"Failed to process parquet file from URL: {message_body}. Message not deleted for retry.")

if __name__ == "__main__":
    main()
