
from threading import Thread
import json
import boto3
import requests
import pandas as pd
from io import BytesIO
import os
import sys
import time
import tempfile
import asyncio
import aiohttp

from utils import load_credentials
from uploadwds import FileBundler

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

def process_parquet(parquet_id, base_dir, df, max_images_per_tar=30000, concurrency=1000):
    """
    Process the DataFrame asynchronously to download images concurrently and create tar files in WebDataset format.
    """
    temp_dir = tempfile.mkdtemp()
    loop = asyncio.get_event_loop()

    async def download_image(session, base_dir, prefix, index, row):
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

                    image_filename = os.path.join(base_dir, f"{prefix}-{parquet_id}-{index}.jpg")
                    with open(image_filename, 'wb') as f:
                        f.write(image_content)
                    with open(image_filename.replace('.jpg', '.json'), 'w') as f:
                        json.dump(metadata, f)
                    
                    return True  # Indicate that the image was successfully processed
        except Exception as e:
            return False
            pass
            # print(f"Exception while downloading {image_url}: {e}")
        
        return False  # Indicate that the image was not processed

    async def process_images(base_dir, batch_size):
        start_idx = 0
        next_idx = start_idx + batch_size
        prefix = f"{start_idx}-{next_idx}"
        semaphore = asyncio.Semaphore(concurrency)
        
        async with aiohttp.ClientSession() as session:
            start = time.time()
            tasks = set()
            for index, row in df.iterrows():
                if index >= next_idx:
                    start_idx = next_idx
                    next_idx = start_idx + batch_size
                    prefix = f"{start_idx}-{next_idx}"

                async with semaphore:
                    tasks.add(asyncio.create_task(download_image(session, base_dir, prefix, index, row)))

                # discard completed tasks to avoid memory leak
                if len(tasks) >= concurrency * 2:
                    _, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            if index / 200 == 0:
                print(f"Processed {200} images in {time.time() - start:.2f} seconds.")
                start = time.time()

            if tasks:
                await asyncio.gather(*tasks)

    loop.run_until_complete(process_images(base_dir, max_images_per_tar))

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

    
    base_dir = 'cruft/images'
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    
    uploader = FileBundler(base_dir, 1000, s3, s3_bucket_name, 'wds2', seconds_to_wait_before_upload=30)
    t = Thread(target=uploader.keep_monitoring)
    t.start()
    

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
                process_parquet(pq_id, base_dir, df, s3, s3_bucket_name)
                delete_message(sqs, sqs_queue_url, message['ReceiptHandle'])
                print(f"Deleted message from SQS: {message.get('MessageId')}")
            else:
                print(f"Failed to process parquet file from URL: {message_body}. Message not deleted for retry.")

    uploader.finalize()
    t.join()

if __name__ == "__main__":
    main()
