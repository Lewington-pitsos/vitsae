import json
import time
import traceback
import boto3
import threading

from sache import train_sae

from vitact.utils import load_config

VISIBILITY_TIMEOUT = 600 # 10 mins

def get_next_config_from_sqs(sqs, queue_url):
    try:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=15,
            VisibilityTimeout=VISIBILITY_TIMEOUT
        )
        
        messages = response.get('Messages', [])
        if not messages:
            print('No messages in SQS queue.')
            return None, None

        message = messages[0]
        receipt_handle = message['ReceiptHandle']
        config =  json.loads(message['Body'])

        return config, receipt_handle
    except Exception as e:
        print(f'Error fetching S3 key from SQS: {e}')
        return None, None

def delete_message_from_sqs(sqs, queue_url, receipt_handle):
    try:
        sqs.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
    except Exception as e:
        print(f'Error deleting message from SQS: {e}')

def keep_extending_invisibility(sqs, queue_url, receipt_handle, stop_event):
    while not stop_event.is_set():
        sqs.change_message_visibility(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle,
            VisibilityTimeout=VISIBILITY_TIMEOUT
        )
        print(f'Extended visibility timeout')
        time.sleep(60)

def get_checkpoint_from_s3(s3, bucket, prefix):
    all_existing_checkpoints = []
    try:
        paginator = s3.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)

        for page in page_iterator:
            if 'Contents' in page:
                all_existing_checkpoints.extend([obj['Key'] for obj in page['Contents']])
            else:
                # If there are no contents in the current page, continue to the next
                continue

        if not all_existing_checkpoints:
            return None, 0

    except Exception as e:
        print(f'Error fetching checkpoint from S3: {e}')
        return None, 0

    max_checkpoint = None
    max_n_tokens = 0
    for checkpoint in all_existing_checkpoints:
        print(f'Existing checkpoint: {checkpoint}')

        # Extract the number of tokens from the checkpoint filename
        try:
            n_tokens = int(checkpoint.split('/')[-1].split('.')[0])
        except ValueError:
            print(f"Could not extract n_tokens from checkpoint: {checkpoint}")
            continue

        if n_tokens > max_n_tokens:
            max_n_tokens = n_tokens
            max_checkpoint = checkpoint


    max_checkpoint = f"s3://{bucket}/{max_checkpoint}" if max_checkpoint is not None else None
    return max_checkpoint, max_n_tokens



def keep_training():
    credentials = load_config()

    sqs = boto3.client(
        'sqs',
        aws_access_key_id=credentials['AWS_ACCESS_KEY'],
        aws_secret_access_key=credentials['AWS_SECRET'],
        region_name='us-east-1'
    )

    while True:
        config, receipt_handle = get_next_config_from_sqs(sqs, credentials['SQS_TRAINING_CONFIG_QUEUE_URL'])
        if config is None:
            print('No more configs to process. Exiting...')
            break

        stop_event = threading.Event()
        t = threading.Thread(target=keep_extending_invisibility, args=(sqs, credentials['SQS_TRAINING_CONFIG_QUEUE_URL'], receipt_handle, stop_event))
        t.start()

        try:
            print(f'Running with config: {config}')

            checkpoint, n_tokens = get_checkpoint_from_s3(
                boto3.client(
                    's3',
                    aws_access_key_id=credentials['AWS_ACCESS_KEY'],
                    aws_secret_access_key=credentials['AWS_SECRET'],
                    region_name='us-east-1'
                ),
                config['log_bucket'],
                f"{config['base_log_dir']}.{config['data_name']}"
            )

            if checkpoint is not None and n_tokens >= config['n_tokens']:
                print(f'Config {config} already trained up to {n_tokens} tokens. Skipping...')
                delete_message_from_sqs(sqs, credentials['SQS_TRAINING_CONFIG_QUEUE_URL'], receipt_handle)
            else:
                train_sae(credentials=credentials, load_checkpoint=checkpoint, start_from=n_tokens, **config)
                delete_message_from_sqs(sqs, credentials['SQS_TRAINING_CONFIG_QUEUE_URL'], receipt_handle)
        except Exception as e:
            print(f'Error running config {config}: {e}')
            traceback.print_exc()
        finally:
            stop_event.set()
            t.join()


        print('\nProceeding to the next config ----->\n')


if __name__ == '__main__':
    keep_training()