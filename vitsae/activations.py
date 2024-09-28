from email.mime import image
import json
from re import T
import boto3
import requests
import pandas as pd
from io import BytesIO
import os
import sys
import time
import tarfile
import tempfile
import asyncio
import aiohttp
import aiofiles


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
        pq_id = os.path.basename(url).split('.')[0]
        df = pd.read_parquet(BytesIO(response.content))
        return pq_id, df
    except Exception as e:
        print(f"Error downloading or parsing parquet file from {url}: {e}")
        return None

def download_image(image_url):
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


def process_parquet(parquet_id, df, s3, bucket_name, max_images_per_tar=30000, tar_file_index=0, concurrency=1000):
    """
    Process the DataFrame asynchronously to download images concurrently and create tar files in WebDataset format.
    """
    temp_dir = tempfile.mkdtemp()

    loop = asyncio.get_event_loop()

    async def create_tar_file(tar_file_index):
        tar_filename = f"{temp_dir}/{parquet_id}-{tar_file_index * max_images_per_tar}-{(tar_file_index + 1) * max_images_per_tar}.tar"
        tar_file = tarfile.open(tar_filename, "w")
        return tar_file, tar_filename, tar_file_index + 1

    async def close_and_upload_tar(tar_file, tar_filename):
        if tar_file:
            tar_file.close()
            s3_key = os.path.basename(tar_filename)
            try:
                with open(tar_filename, 'rb') as f:
                    s3.upload_fileobj(f, bucket_name, f"webdataset/{s3_key}")
                print(f"Uploaded {s3_key} to S3.")
            except Exception as e:
                print(f"Error uploading {s3_key} to S3: {e}")
            os.remove(tar_filename)

    async def fetch_and_process_image(session, index, row, tar_file):
        image_url = row.get('URL')
        if not image_url:
            print(f"No URL found in row {index}. Skipping.")
            return False  # Indicate that this image was not processed

        try:
            async with session.get(image_url, timeout=30) as response:
                if response.status == 200:
                    image_content = await response.read()
                    metadata = {
                        "URL": image_url,
                        "hash": row.get('hash'),
                        "TEXT": row.get('TEXT'),
                        "WIDTH": row.get('WIDTH'),
                        "HEIGHT": row.get('HEIGHT'),
                        "similarity": row.get('similarity'),
                        "LANGUAGE": row.get('LANGUAGE'),
                        "pwatermark": row.get('pwatermark'),
                        "punsafe": row.get('punsafe'),
                        "ENG TEXT": row.get('ENG TEXT'),
                        "__index_level_0__": row.get('__index_level_0__'),
                        "prediction": row.get('prediction')
                    }

                    image_filename = f"{parquet_id}-{index}.jpg"
                    await add_image_to_tar(tar_file, image_content, image_filename, metadata)
                    return True  # Indicate that the image was successfully processed
        except Exception as e:
            print(f"Exception while downloading {image_url}: {e}")
        
        return False  # Indicate that the image was not processed

    async def add_image_to_tar(tar_file, image_content, image_filename, metadata):
        # Save image content to a temporary file asynchronously
        image_path = os.path.join(temp_dir, image_filename)
        async with aiofiles.open(image_path, 'wb') as img_file:
            await img_file.write(image_content)

        # Add image to tar file
        tar_file.add(image_path, arcname=image_filename)

        # Save metadata to a temporary file asynchronously
        metadata_content = json.dumps(metadata).encode('utf-8')
        metadata_filename = f"{os.path.splitext(image_filename)[0]}.json"
        metadata_path = os.path.join(temp_dir, metadata_filename)
        async with aiofiles.open(metadata_path, 'wb') as meta_file:
            await meta_file.write(metadata_content)
        tar_file.add(metadata_path, arcname=metadata_filename)

    async def process_images(tar_file_index):
        tar_file, tar_filename, tar_file_index = await create_tar_file(tar_file_index)
        url_count = 0
        async with aiohttp.ClientSession() as session:
            tasks = []
            for index, row in df.iterrows():
                tasks.append(fetch_and_process_image(session, index, row, tar_file))

                if len(tasks) >= concurrency:  # Adjust concurrency limit as needed
                    results = await asyncio.gather(*tasks)
                    url_count += sum(results)  # Count the number of successfully processed images
                    tasks = []

                if url_count >= max_images_per_tar:
                    await asyncio.gather(*tasks)  # Ensure all tasks are completed
                    tasks = []
                    print('Uploading tar file to S3...')
                    await close_and_upload_tar(tar_file, tar_filename)
                    tar_file, tar_filename, tar_file_index = await create_tar_file(tar_file_index)
                    url_count = 0

            if tasks:
                results = await asyncio.gather(*tasks)
                url_count += sum(results)

            if url_count > 0:
                await close_and_upload_tar(tar_file, tar_filename)

    loop.run_until_complete(process_images(tar_file_index))

    # Clean up the temporary directory and its contents
    try:
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            os.remove(file_path)
        os.rmdir(temp_dir)
    except OSError as e:
        print(f"Error removing temporary directory: {e}")

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

            pq_id, df = download_parquet(message_body, hf_token)

            if df is not None:
                process_parquet(pq_id, df, s3, s3_bucket_name)
                delete_message(sqs, sqs_queue_url, message['ReceiptHandle'])
                print(f"Deleted message from SQS: {message.get('MessageId')}")
            else:
                print(f"Failed to process parquet file from URL: {message_body}. Message not deleted for retry.")

if __name__ == "__main__":
    main()
