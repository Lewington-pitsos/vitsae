import boto3
import os
import time
import logging

from utils import load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
config = load_config()

s3 = boto3.client('s3')
sqs = boto3.client('sqs')

def get_local_tar_count(local_dir):
    """Counts the number of .tar files in the local directory."""
    return len([f for f in os.listdir(local_dir) if f.endswith('.tar')])

def download_from_s3(local_dir, bucket_name, key):
    local_filename = os.path.join(local_dir, os.path.basename(key))
    s3.download_file(bucket_name, key, local_filename)
    logging.info(f'Downloaded {key} to {local_filename}')
    os.rename(local_filename, local_filename.replace('.tar', '.ready.tar'))

def get_next_s3_key_from_sqs(queue_url):
    """Fetches the next S3 key from the SQS queue."""
    try:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5
        )
        
        messages = response.get('Messages', [])
        if not messages:
            logging.info('No messages in SQS queue.')
            return None, None

        # Get the message and its receipt handle for deletion
        message = messages[0]
        receipt_handle = message['ReceiptHandle']
        s3_key = message['Body']

        return s3_key, receipt_handle
    except Exception as e:
        logging.error(f'Error fetching S3 key from SQS: {e}')
        return None, None

def delete_message_from_sqs(queue_url, receipt_handle):
    """Deletes a message from the SQS queue."""
    try:
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
        logging.info('Deleted message from SQS queue.')
    except Exception as e:
        logging.error(f'Error deleting message from SQS: {e}')

def keep_pulling(local_dir, stop_event=None):
    config = load_config()
    bucket_name = config['S3_BUCKET_NAME']
    queue_url = config['SQS_TAR_QUEUE_URL']

    # Ensure the local directory exists
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)
        logging.info(f'Created local directory {local_dir}')

    while stop_event is None or not stop_event.is_set():
        local_tar_count = get_local_tar_count(local_dir)
        logging.info(f'Number of local .tar files: {local_tar_count}')

        if local_tar_count >= 9:
            time.sleep(3)  # Wait before checking again
            continue

        # Get the next S3 key from the SQS queue
        s3_key, receipt_handle = get_next_s3_key_from_sqs(queue_url)
        if not s3_key:
            logging.info('No .tar files found in SQS queue.')
            time.sleep(20)
            continue

        try:
            response = s3.list_objects_v2(Bucket=bucket_name, Prefix=s3_key)

            if 'Contents' not in response:
                logging.error(f'Error processing {s3_key}: File not found on S3')
                delete_message_from_sqs(queue_url, receipt_handle)
            else:
                download_from_s3(local_dir, bucket_name, s3_key)
                delete_message_from_sqs(queue_url, receipt_handle)
        except Exception as e:
            logging.error(f'Error processing {s3_key}: {e}')
            continue

if __name__ == '__main__':
    keep_pulling(local_dir='cruft/tars')
