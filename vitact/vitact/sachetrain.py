import json
import time
import traceback
import boto3
import threading

from sache import train_sae, find_s3_checkpoint

from vitact.utils import load_config

VISIBILITY_TIMEOUT = 60 * 4 # 4 minutes 

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

            checkpoint = find_s3_checkpoint(
                boto3.client(
                    's3',
                    aws_access_key_id=credentials['AWS_ACCESS_KEY'],
                    aws_secret_access_key=credentials['AWS_SECRET'],
                    region_name='us-east-1'
                ),
                config['log_bucket'],
                f"{config['base_log_dir']}/{config['data_name']}"
            )

            if checkpoint is not None:
                print(f'Found checkpoint {checkpoint}')

            train_sae(credentials=credentials, load_checkpoint=checkpoint, **config)
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