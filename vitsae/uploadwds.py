import os
import tarfile
import boto3
from collections import defaultdict
import time
from utils import load_credentials

class FileBundler:
    def __init__(self, watch_dir, upload_threshold, s3_client, s3_bucket, s3_prefix, seconds_to_wait_before_upload=300):
        self.file_counts = defaultdict(int)
        self.previous_file_counts = {}
        self.watch_dir = watch_dir
        self.upload_threshold = upload_threshold
        self.s3_client = s3_client
        self.s3_bucket = s3_bucket
        self.s3_prefix = s3_prefix
        
        self.seconds_since_change = {}
        self.seconds_to_wait_before_upload = seconds_to_wait_before_upload

    def check_directory(self):
        print(f'Checking directory {self.watch_dir} for files...')
        # Scan the directory for files and update the counts
        for file_name in os.listdir(self.watch_dir):
            if not os.path.isfile(os.path.join(self.watch_dir, file_name)):
                continue  # Skip directories

            prefix = file_name.split('-part-')[0]
            self.file_counts[prefix] += 1

        for prefix, count in self.file_counts.items():
            if count == self.previous_file_counts.get(prefix, 0):
                if prefix in self.seconds_since_change:
                    if count > self.upload_threshold and time.time() - self.seconds_since_change.get(prefix, 0) > self.seconds_to_wait_before_upload:
                        self.bundle_and_upload_files(prefix)
                else:
                    self.seconds_since_change[prefix] = time.time()
            else:
                self.seconds_since_change[prefix] = time.time()

        # Update previous counts for the next iteration
        self.previous_file_counts = self.file_counts.copy()
        # Reset the file_counts for the next check
        self.file_counts.clear()

    def bundle_and_upload_files(self, prefix):
        files_to_bundle = [f for f in os.listdir(self.watch_dir) if f.startswith(prefix)]
        tar_filename = os.path.join(self.watch_dir, f'{prefix}.tar')

        with tarfile.open(tar_filename, 'w') as tar:
            for file_name in files_to_bundle:
                file_path = os.path.join(self.watch_dir, file_name)
                tar.add(file_path, arcname=file_name)
        
        self.upload_to_s3(tar_filename, prefix)

        os.remove(tar_filename)
        for file_name in files_to_bundle:
            os.remove(os.path.join(self.watch_dir, file_name))

        # Reset the count for this prefix
        self.previous_file_counts[prefix] = 0

    def upload_to_s3(self, tar_filename, prefix):
        try:
            s3_key = os.path.join(self.s3_prefix, f'{prefix}.tar')
            self.s3_client.upload_file(tar_filename, self.s3_bucket, s3_key)
            print(f'Successfully uploaded {tar_filename} to s3://{self.s3_bucket}/{s3_key}')
        except Exception as e:
            print(f'Failed to upload {tar_filename} to S3: {e}')

if __name__ == "__main__":
    s3_prefix = 'wds/'

    # Monitor directory and threshold
    watch_dir = 'cruft/images/'
    file_count_threshold = 50

    credentials = load_credentials()
    s3 = boto3.client('s3', 
                      aws_access_key_id=credentials['AWS_ACCESS_KEY_ID'],
                      aws_secret_access_key=credentials['AWS_SECRET'],
                      region_name='us-east-1')

    file_bundler = FileBundler(watch_dir, file_count_threshold, s3, credentials['S3_BUCKET_NAME'], s3_prefix)
    
    try:
        while True:
            file_bundler.check_directory()
            time.sleep(5)  # Wait for 5 seconds before checking again
    except KeyboardInterrupt:
        print("Stopping the directory monitoring.")
