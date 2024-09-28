from activations import process_parquet
import pandas as pd
import json
import boto3

def test_process_parquet():
    parquet_id = 'part-00000-00478b7a-941e-4176-b569-25f4be656991-c000'
    df = pd.read_csv('cruft/df.csv', nrows=3000)

    with open('.credentials.json') as f:
        credentials = json.load(f)

    s3_client = boto3.client(
        's3',
        aws_access_key_id=credentials['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=credentials['AWS_SECRET'],
        region_name=credentials.get('AWS_REGION', 'us-east-1')
    )
    
    process_parquet(parquet_id, df, s3_client, 'vit-sae-activations', max_images_per_tar=50, concurrency=50)