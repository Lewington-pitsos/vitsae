from boto3.dynamodb.conditions import Key
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
import pyarrow.parquet as pq
import pyarrow as pa

from utils import load_config
from uploadwds import FileBundler
from interruption import InterruptionHandler

def initialize_boto3_clients(credentials):
    """
    Initialize AWS SQS and S3 clients using provided credentials.
    """
    sqs = boto3.client(
        'sqs',
        aws_access_key_id=credentials['AWS_ACCESS_KEY'],
        aws_secret_access_key=credentials['AWS_SECRET'],
        region_name=credentials.get('AWS_REGION', 'us-east-1')
    )
    s3 = boto3.client(
        's3',
        aws_access_key_id=credentials['AWS_ACCESS_KEY'],
        aws_secret_access_key=credentials['AWS_SECRET'],
        region_name=credentials.get('AWS_REGION', 'us-east-1')
    )
    ddb = boto3.resource(
        'dynamodb',
        aws_access_key_id=credentials['AWS_ACCESS_KEY'],
        aws_secret_access_key=credentials['AWS_SECRET'],
        region_name=credentials.get('AWS_REGION', 'us-east-1')
    )
    ddb_table = ddb.Table(credentials.get('TABLE_NAME'))

    return sqs, s3, ddb_table

def receive_message(sqs, queue_url, wait_time=30, max_messages=1):
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

# def download_parquet(url, hf_token):
#     """
#     Download a parquet file from the given URL using the Hugging Face token.
#     """
#     headers = {
#         'Authorization': f'Bearer {hf_token}'
#     }
#     try:
#         response = requests.get(url, headers=headers, timeout=60)
#         response.raise_for_status()
#         # Read parquet file into pandas DataFrame
#         pq_id = os.path.basename(url).split('part-')[1].split('-')[0]
#         df = pd.read_parquet(BytesIO(response.content))
#         return pq_id, df
#     except Exception as e:
#         print(f"Error downloading or parsing parquet file from {url}: {e}")
#         return None

def download_parquet(base_dir, url, hf_token):
    """
    Download a parquet file from the given URL using the Hugging Face token and save it to disk.

    Parameters:
    - url (str): The URL of the parquet file.
    - hf_token (str): The Hugging Face token for authorization.
    - output_dir (str): The directory where the parquet file will be saved.

    Returns:
    - tuple: A tuple containing the parquet file ID and the saved file path.
    """
    headers = {
        'Authorization': f'Bearer {hf_token}'
    }
    try:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        
        # Generate the file name from the URL and save to the specified directory
        pq_id = os.path.basename(url).split('part-')[1].split('-')[0]
        file_path = os.path.join(base_dir, f'{pq_id}.parquet')
        
        # Save the parquet content to disk
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        return pq_id, file_path
    except Exception as e:
        print(f"Error downloading or saving parquet file from {url}: {e}")
        return None



def download_image(image_url):
    try:
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Error downloading image from {image_url}: {e}")
        return None






def iterate_parquet_rows(file_path, chunk_size=30000):
    try:
        pf = pq.ParquetFile(file_path)
        batch_iter = pf.iter_batches(batch_size=chunk_size)
        
        total_rows_processed = 0  # Initialize the total rows counter
        
        for batch in batch_iter:
            # Convert the PyArrow Table batch to a pandas DataFrame
            df_chunk = batch.to_pandas()
            
            if df_chunk.empty:
                break

            # Adjust the index to keep it incrementing
            df_chunk.index = range(total_rows_processed, total_rows_processed + len(df_chunk))
            total_rows_processed += len(df_chunk)  # Update the counter
            
            yield df_chunk

    except Exception as e:
        print(f"Error reading parquet file in chunks from {file_path}: {e}")
        return



def process_parquet(base_dir, pq_path, pq_id, already_processed, max_images_per_tar=30000, concurrency=1000):
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

                    image_filename = os.path.join(base_dir, f"{prefix}--{index}.jpg")
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

    async def process_images(base_dir, pq_path, pq_id, batch_size, already_processed):
        start_idx = 0
        next_idx = start_idx + batch_size
        prefix = f"{pq_id}-{start_idx}-{next_idx}"
        
        time_every = 500
        async with aiohttp.ClientSession() as session:
            start = time.time()
            tasks = set()
            for df in iterate_parquet_rows(pq_path):
                for index, row in df.iterrows():
                    if index >= next_idx:
                        start_idx = next_idx
                        next_idx = start_idx + batch_size
                        prefix = f"{pq_id}-{start_idx}-{next_idx}"

                    if prefix in already_processed:
                        print('Skipping already processed batch:', prefix)
                        continue

                    # discard completed tasks to avoid memory leak
                    if len(tasks) >= concurrency * 2:
                        while len(tasks) >= concurrency:
                            print('Waiting for tasks to complete...', len(tasks))
                            _, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                            time.sleep(0.5)

                    tasks.add(asyncio.create_task(download_image(session, base_dir, prefix, index, row)))
                    
                    if index % time_every == 0:
                        print(f"Processed {time_every} images in {time.time() - start:.2f} seconds.")
                        start = time.time()

            if tasks:
                await asyncio.gather(*tasks)

    loop.run_until_complete(process_images(base_dir, pq_path, pq_id, max_images_per_tar, already_processed))

    # Clean up the temporary directory and its contents
    try:
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            os.remove(file_path)
        os.rmdir(temp_dir)
    except OSError as e:
        print(f"Error removing temporary directory: {e}")

def get_already_processed_batches(ddb_table, pq_id):
    try:
        response = ddb_table.query(
            KeyConditionExpression=Key('parquet_id').eq(pq_id)
        )
        return set([f"{pq_id}-{item.get('batch_id')}" for item in response.get('Items', [])])
    except Exception as e:
        print(f"Error retrieving already processed batches from DynamoDB: {e}")
        return []

def generate_webdatasets():
    """
    Main function to continuously process messages from SQS.
    """
    config = load_config()
    sqs, s3, ddb_table = initialize_boto3_clients(config)

    # Retrieve SQS queue URL and S3 bucket name from credentials
    sqs_queue_url = config.get('SQS_QUEUE_URL')
    s3_bucket_name = config.get('S3_BUCKET_NAME')

    hf_token = config.get('HF_TOKEN')

    if not sqs_queue_url or not s3_bucket_name:
        print("Error: 'SQS_QUEUE_URL' and 'S3_BUCKET_NAME' must be set in the credentials file.")
        sys.exit(1)

    
    base_dir = 'cruft/images'
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    
    uploader = FileBundler(base_dir, 230, s3, s3_bucket_name, 'wds2', ddb_table, seconds_to_wait_before_upload=10)
    t = Thread(target=uploader.keep_monitoring)
    t.start()
    
    print(f"Starting to process messages from SQS queue: {sqs_queue_url}")
    total_wait_time = 0
    max_wait_time = 500
    while True:
        messages = receive_message(sqs, sqs_queue_url, wait_time=20)
        if not messages:
            total_wait_time += 20
            print(f"No messages available yet. Total wait time: {total_wait_time} seconds.")

            if total_wait_time > max_wait_time:
                print(f"No messages available for {max_wait_time} seconds terminating")
                break

            continue

        for message in messages:
            parquet_url = message['Body']
            ih = InterruptionHandler(parquet_url, sqs_queue_url, sqs) # adds the pq message back into the queue if the spot instance is interrupted
            try:
                ih.start_listening()

                print(f"Processing parquet file URL: {parquet_url}")
                download_start = time.time()

                pq_id, pq_path = download_parquet(base_dir, parquet_url, hf_token)

                print(f"Processing parquet with ID: {pq_id} downloaded in {time.time() - download_start:.2f} seconds.")

                already_processed = get_already_processed_batches(ddb_table, pq_id)        

                if pq_path is not None:
                    process_parquet(base_dir=base_dir, pq_path=pq_path, pq_id=pq_id, already_processed=already_processed, max_images_per_tar=500, concurrency=500)
                    delete_message(sqs, sqs_queue_url, message['ReceiptHandle'])
                    ih.stop_listening() # the parquet time_everyhas been completed, we never want to add it back to the queue now.
                    print(f"Deleted message from SQS: {message.get('MessageId')}")
                else:
                    print(f"Failed to process parquet file from URL: {parquet_url}. Message not deleted for retry.")
            except Exception as e:
                print(f"Error processing message: {e}")
                ih.stop_listening()
                ih.add_pq_back()
                continue

    uploader.finalize()
    t.join()

if __name__ == "__main__":
    generate_webdatasets()
