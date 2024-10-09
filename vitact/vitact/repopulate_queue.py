import boto3
import logging
import sys
from botocore.exceptions import ClientError

from utils import load_config

def initialize_boto3_clients(config):
    """
    Initialize boto3 S3 and SQS clients using provided configuration.
    """
    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=config['AWS_ACCESS_KEY'],
            aws_secret_access_key=config['AWS_SECRET']
        )
        sqs = boto3.client(
            'sqs',
            aws_access_key_id=config['AWS_ACCESS_KEY'],
            aws_secret_access_key=config['AWS_SECRET']
        )
        return s3, sqs
    except Exception as e:
        logging.error(f"Failed to initialize boto3 clients: {e}")
        sys.exit(1)

def purge_sqs_queue(sqs, queue_url):
    """
    Purge all messages from the specified SQS queue.
    """
    try:
        logging.info(f"Purge initiated for SQS queue: {queue_url}")
        sqs.purge_queue(QueueUrl=queue_url)
        logging.info("SQS queue purged successfully.")
    except ClientError as e:
        if e.response['Error']['Code'] == 'QueueAlreadyExists':
            logging.error("The specified queue does not exist.")
        elif e.response['Error']['Code'] == 'PurgeQueueInProgress':
            logging.error("Purge already in progress for this queue.")
        else:
            logging.error(f"Failed to purge SQS queue: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error during SQS purge: {e}")
        sys.exit(1)

def list_s3_objects(s3, bucket_name, prefix):
    """
    List all object keys in the specified S3 bucket under the given prefix.
    Handles pagination to retrieve all objects.
    """
    keys = []
    try:
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    keys.append(obj['Key'])
        logging.info(f"Total objects found in S3 with prefix '{prefix}': {len(keys)}")
    except ClientError as e:
        logging.error(f"Failed to list objects in S3 bucket: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error during S3 listing: {e}")
        sys.exit(1)

    return keys

def enqueue_messages(sqs, queue_url, messages):
    """
    Send messages to the specified SQS queue
    """
    BATCH_SIZE = 25
    total = len(messages)
    sent = 0

    for i in range(0, total, BATCH_SIZE):
        batch = messages[i:i+BATCH_SIZE]
        entries = [{'Id': str(j), 'MessageBody': msg} for j, msg in enumerate(batch)]
        try:
            response = sqs.send_message_batch(
                QueueUrl=queue_url,
                Entries=entries
            )
            if 'Failed' in response and response['Failed']:
                for failure in response['Failed']:
                    logging.error(f"Failed to send message ID {failure['Id']}: {failure['Message']}")
            sent += len(batch) - len(response.get('Failed', []))
            logging.info(f"Batch {i//BATCH_SIZE + 1}: Sent {len(batch) - len(response.get('Failed', []))} messages.")
        except ClientError as e:
            logging.error(f"Failed to send message batch: {e}")
        except Exception as e:
            logging.error(f"Unexpected error during sending messages: {e}")

    logging.info(f"Enqueued {sent} out of {total} messages to SQS queue.")

def main():
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Load configuration
    config = load_config()

    # Initialize boto3 clients
    s3, sqs = initialize_boto3_clients(config)

    # Purge the SQS queue
    purge_sqs_queue(sqs, config['SQS_TAR_QUEUE_URL'])

    # List all S3 object keys under the specified prefix
    s3_keys = list_s3_objects(s3, config['S3_BUCKET_NAME'], 'webdataset')

    if not s3_keys:
        logging.info("No objects found in S3 to enqueue.")
        sys.exit(0)

    # Enqueue all S3 keys to the SQS queue
    enqueue_messages(sqs, config['SQS_TAR_QUEUE_URL'], s3_keys)

    logging.info("All messages have been enqueued successfully.")

if __name__ == '__main__':
    main()
