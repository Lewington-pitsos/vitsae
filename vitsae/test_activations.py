import os
from uploadwds import FileBundler
from utils import load_config
from generatewds import process_parquet, initialize_boto3_clients
import pandas as pd
from threading import Thread

def test_process_parquet():
    parquet_id = '00001'
    df = pd.read_csv('cruft/df.csv', nrows=1000)

    config = load_config()
    _, s3_client, ddb_table = initialize_boto3_clients(config)

    base_dir = 'cruft/images/'

    if not os.path.exists(base_dir):
        os.makedirs(base_dir)

    uploader = FileBundler(base_dir, 70, s3_client, config['S3_BUCKET_NAME'], 'wds2', ddb_table, seconds_to_wait_before_upload=5)
    t = Thread(target=uploader.keep_monitoring)
    t.start()

    process_parquet(base_dir, df, parquet_id, set(), max_images_per_tar=130, concurrency=50)

    uploader.finalize()
    t.join()