import os
import tarfile
import boto3
from collections import defaultdict
import time

from utils import load_config
from PIL import Image
import PIL


from constants import COUNTER_BATCH_ID, COUNTER_PQ_ID

def non_extension_part(file_path):
    return os.path.splitext(os.path.basename(file_path))[0]

def make_tarfile(watch_dir, prefix):
    all_files = sorted([os.path.join(watch_dir, f)  for f in os.listdir(watch_dir) if f.startswith(prefix)])
    tar_filename = os.path.join(watch_dir, f'{prefix}.tar')

    exclude = set()
    for file_path in all_files:
        if file_path.split('.')[-1] == 'jpg':
            try:
                _ = Image.open(file_path)
            except PIL.UnidentifiedImageError:
                exclude.add(non_extension_part(file_path))

    files_to_bundle = [f for f in all_files if non_extension_part(f) not in exclude]

    if len(files_to_bundle) == 0:
        return None, []

    with tarfile.open(tar_filename, 'w') as tar:
        for file_path in files_to_bundle:
            tar.add(file_path, arcname=file_path.split('/')[-1])
    
    return tar_filename, all_files


class TarMaker:
    def __init__(self, 
                 watch_dir, 
                 min_images_per_tar, 
                 s3_client, 
                 s3_bucket_name, 
                 s3_prefix, 
                 ddb_table,
                 sqs_client,
                 tar_queue_url,
                 wait_after_last_change=300
        ):
        self.file_counts = defaultdict(int)
        self.previous_file_counts = {}
        self.watch_dir = watch_dir
        self.min_images_per_tar = min_images_per_tar
        self.s3_client = s3_client
        self.s3_bucket = s3_bucket_name
        self.s3_prefix = s3_prefix
        self.dd_table = ddb_table

        self.sqs_client = sqs_client
        self.tar_queue_url = tar_queue_url

        self.seconds_since_change = {}
        self.wait_after_last_change = wait_after_last_change

        self.stop = False

    def _get_ids_from_file(self, file_name):
        pq_id = file_name.split('-')[0]
        batch_id = "-".join(file_name.split('-')[1:])
        return pq_id, batch_id

    def check_directory(self):
        print(f'Checking directory {self.watch_dir} for files...')
        self.update_file_counts()

        for prefix, count in self.file_counts.items():
            if count == self.previous_file_counts.get(prefix, 0):
                if prefix in self.seconds_since_change:
                    if count > self.min_images_per_tar and time.time() - self.seconds_since_change.get(prefix, 0) > self.wait_after_last_change:
                        pq_id, batch_id = self._get_ids_from_file(prefix)
                        self.bundle_and_upload_files(pq_id, batch_id)
                else:
                    self.seconds_since_change[prefix] = time.time()
            else:
                self.seconds_since_change[prefix] = time.time()

        self.previous_file_counts = self.file_counts.copy()
        self.file_counts.clear()

    def mark_as_uploaded(self, pq_id, batch_id):
        try:
            response = self.dd_table.put_item(
                Item={
                    'parquet_id': pq_id,
                    'batch_id': batch_id,
                    'uploaded': True,
                }
            )
            print(f'Marked {pq_id}, {batch_id} as uploaded.', response)

            counter_response = self.dd_table.update_item(
                Key={
                    'parquet_id': COUNTER_PQ_ID,
                    'batch_id': COUNTER_BATCH_ID
                },
                UpdateExpression="ADD upload_count :increment",
                ExpressionAttributeValues={
                    ':increment': 1
                },
                ReturnValues="UPDATED_NEW"
            )
        
            print(f'Upload counter incremented. Current count: {counter_response["Attributes"]["upload_count"]}')

        except Exception as e:
            print(f'Failed to mark {pq_id}, {batch_id} as uploaded: {e}')


    def bundle_and_upload_files(self, pq_id, batch_id):
        prefix = f'{pq_id}-{batch_id}'

        tar_filename, all_files = make_tarfile(self.watch_dir, prefix)
        if not tar_filename:
            print(f'No valid files found for {prefix}. Skipping bundling and uploading.')
            return

        s3_path = self.upload_to_s3(tar_filename, prefix)
        if s3_path:
            self.mark_as_uploaded(pq_id, batch_id)
            self.sqs_client.send_message(QueueUrl=self.tar_queue_url, MessageBody=s3_path)

            if os.path.exists(tar_filename):
                os.remove(tar_filename)
            for file_path in all_files:
                if os.path.exists(file_path):
                    os.remove(file_path)

            self.previous_file_counts[prefix] = 0

    def upload_to_s3(self, tar_filename, prefix):
        try:
            s3_key = os.path.join(self.s3_prefix, f'{prefix}.tar')
            self.s3_client.upload_file(tar_filename, self.s3_bucket, s3_key)
            print(f'Successfully uploaded {tar_filename} to s3://{self.s3_bucket}/{s3_key}')

            return f's3://{self.s3_bucket}/{s3_key}'
        except Exception as e:
            print(f'Failed to upload {tar_filename} to S3: {e}')
            return None

    def update_file_counts(self):
        for file_name in os.listdir(self.watch_dir):
            if not os.path.isfile(os.path.join(self.watch_dir, file_name)):
                continue  # Skip directories

            prefix = file_name.split('--')[0]
            self.file_counts[prefix] += 1

    def finalize(self):
        self.stop = True

    def keep_monitoring(self, sleep_time=5):
        try:
            while not self.stop:
                self.check_directory()
                time.sleep(sleep_time)  # Wait for 5 seconds before checking again

            self.update_file_counts()
            for prefix, count in self.file_counts.items():
                if count > self.min_images_per_tar:
                    pq_id, batch_id = self._get_ids_from_file(prefix)
                    self.bundle_and_upload_files(pq_id, batch_id)

        except KeyboardInterrupt:
            print("Stopping the directory monitoring.")

if __name__ == "__main__":
    s3_prefix = 'wds/'

    # Monitor directory and threshold
    watch_dir = 'cruft/images/'
    file_count_threshold = 50

    config = load_config()
    s3 = boto3.client('s3', 
                      aws_access_key_id=config['AWS_ACCESS_KEY'],
                      aws_secret_access_key=config['AWS_SECRET'],
                      region_name='us-east-1')

    file_bundler = TarMaker(watch_dir, file_count_threshold, s3, config['S3_BUCKET_NAME'], s3_prefix, seconds_to_wait_before_upload=10)
    
    file_bundler.keep_monitoring()