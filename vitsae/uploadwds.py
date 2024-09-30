import os
import tarfile
import boto3
from collections import defaultdict
import time
from utils import load_config

class FileBundler:
    def __init__(self, 
                 watch_dir, 
                 upload_threshold, 
                 s3_client, 
                 s3_bucket, 
                 s3_prefix, 
                 table,
                 seconds_to_wait_before_upload=300
        ):
        self.file_counts = defaultdict(int)
        self.previous_file_counts = {}
        self.watch_dir = watch_dir
        self.upload_threshold = upload_threshold
        self.s3_client = s3_client
        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix
        self.dd_table = table

        self.seconds_since_change = {}
        self.seconds_to_wait_before_upload = seconds_to_wait_before_upload

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
                    if count > self.upload_threshold and time.time() - self.seconds_since_change.get(prefix, 0) > self.seconds_to_wait_before_upload:
                        pq_id, batch_id = self._get_ids_from_file(prefix)
                        self.bundle_and_upload_files(pq_id, batch_id)
                else:
                    self.seconds_since_change[prefix] = time.time()
            else:
                self.seconds_since_change[prefix] = time.time()

        # Update previous counts for the next iteration
        self.previous_file_counts = self.file_counts.copy()
        # Reset the file_counts for the next check
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
        except Exception as e:
            print(f'Failed to mark {pq_id}, {batch_id} as uploaded: {e}')

    def bundle_and_upload_files(self, pq_id, batch_id):
        prefix = f'{pq_id}-{batch_id}'

        files_to_bundle = [f for f in os.listdir(self.watch_dir) if f.startswith(prefix)]
        tar_filename = os.path.join(self.watch_dir, f'{prefix}.tar')

        with tarfile.open(tar_filename, 'w') as tar:
            for file_name in files_to_bundle:
                file_path = os.path.join(self.watch_dir, file_name)
                tar.add(file_path, arcname=file_name)
        
        self.upload_to_s3(tar_filename, prefix)
        self.mark_as_uploaded(pq_id, batch_id)

        os.remove(tar_filename)
        for file_name in files_to_bundle:
            os.remove(os.path.join(self.watch_dir, file_name))

        self.previous_file_counts[prefix] = 0

    def upload_to_s3(self, tar_filename, prefix):
        try:
            s3_key = os.path.join(self.s3_prefix, f'{prefix}.tar')
            self.s3_client.upload_file(tar_filename, self.s3_bucket, s3_key)
            print(f'Successfully uploaded {tar_filename} to s3://{self.s3_bucket}/{s3_key}')
        except Exception as e:
            print(f'Failed to upload {tar_filename} to S3: {e}')

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
                if count > self.upload_threshold:
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

    file_bundler = FileBundler(watch_dir, file_count_threshold, s3, config['S3_BUCKET_NAME'], s3_prefix, seconds_to_wait_before_upload=10)
    
    file_bundler.keep_monitoring()