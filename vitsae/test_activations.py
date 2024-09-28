from uploadwds import FileBundler
from activations import process_parquet
import pandas as pd
import json
import boto3
from threading import Thread

def test_process_parquet():
    parquet_id = 'part-00000-00478b7a-941e-4176-b569-25f4be656991-c000'
    df = pd.read_csv('cruft/df.csv', nrows=40_000)

    with open('.credentials.json') as f:
        credentials = json.load(f)

    s3_client = boto3.client(
        's3',
        aws_access_key_id=credentials['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=credentials['AWS_SECRET'],
        region_name=credentials.get('AWS_REGION', 'us-east-1')
    )
    
    base_dir = 'cruft/images/'
    uploader = FileBundler(base_dir, 700, s3_client, credentials['S3_BUCKET_NAME'], 'wds2', seconds_to_wait_before_upload=35)
    t = Thread(target=uploader.keep_monitoring)
    t.start()


    process_parquet(parquet_id, base_dir, df, max_images_per_tar=1300, concurrency=200)

    uploader.finalize()
    t.join()