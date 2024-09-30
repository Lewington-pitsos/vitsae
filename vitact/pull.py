import boto3
import os
import time
import logging
import os

def load_config():
    hf_token = os.getenv('HF_TOKEN')
    aws_access_key = os.getenv('AWS_ACCESS_KEY')
    aws_secret = os.getenv('AWS_SECRET')
    sqs_queue_url = os.getenv('SQS_QUEUE_URL')
    s3_bucket_name = os.getenv('S3_bucket_name')
    table_name = os.getenv('TABLE_NAME')

    return {
        'HF_TOKEN': hf_token,
        'AWS_ACCESS_KEY': aws_access_key,
        'AWS_SECRET': aws_secret,
        'SQS_QUEUE_URL': sqs_queue_url,
        'S3_bucket_name': s3_bucket_name,
        'TABLE_NAME': table_name
    }


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


config = load_config()

# Initialize S3 client
s3 = boto3.client('s3')

def get_local_tar_count(local_dir):
    """Counts the number of .tar files in the local directory."""
    return len([f for f in os.listdir(local_dir) if f.endswith('.tar')])

def list_s3_tar_files(bucket_name, prefix):
    """Lists all .tar files under the specified prefix in the S3 bucket."""
    paginator = s3.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
    tar_files = []

    for page in page_iterator:
        if 'Contents' in page:
            for obj in page['Contents']:
                key = obj['Key']
                if key.endswith('.tar'):
                    tar_files.append(key)
    return tar_files

def download_and_delete_from_s3(local_dir, bucket_name, key):
    """Downloads a file from S3 and deletes it from the bucket."""
    local_filename = os.path.join(local_dir, os.path.basename(key))
    # Download the file
    s3.download_file(bucket_name, key, local_filename)
    logging.info(f'Downloaded {key} to {local_filename}')
    # Delete the file from S3
    s3.delete_object(Bucket=bucket_name, Key=key)
    logging.info(f'Deleted {key} from S3')

    # rename the file to .ready.tar
    os.rename(local_filename, local_filename.replace('.tar', '.ready.tar'))

def main():
    config = load_config()
    local_dir = 'data'
    bucket_name = config['S3_BUCKET_NAME']
    prefix = 'data/'

    # Ensure the local directory exists
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)
        logging.info(f'Created local directory {local_dir}')

    while True:
        local_tar_count = get_local_tar_count(local_dir)
        logging.info(f'Number of local .tar files: {local_tar_count}')

        if local_tar_count >= 3:
            logging.info('Local .tar files count >= 3, waiting...')
            time.sleep(3)  # Wait before checking again
            continue

        # List .tar files in S3
        tar_files_in_s3 = list_s3_tar_files(bucket_name, prefix)
        if not tar_files_in_s3:
            logging.info('No .tar files found in S3.')
            time.sleep(20)
            continue

        # Download files until we have 3 locally
        for key in tar_files_in_s3:
            if get_local_tar_count(local_dir) >= 3:
                break
            try:
                download_and_delete_from_s3(local_dir, bucket_name, key)
            except Exception as e:
                logging.error(f'Error downloading or deleting {key}: {e}')
                continue

        # Sleep before the next iteration
        time.sleep(5)

if __name__ == '__main__':
    main()
