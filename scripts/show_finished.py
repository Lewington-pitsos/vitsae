import json
import boto3

with open('../vitsae/.credentials.json') as f:
    credentials = json.load(f)


s3 = boto3.client(
    's3',
    aws_access_key_id=credentials['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key=credentials['AWS_SECRET'],
    region_name='us-east-1'
)


bucket_name = 'sae-activations'
prefix = 'log/CLIP-ViT-L-14/'

# Function to list and filter files
def list_files_with_pattern(bucket, prefix, pattern):
    paginator = s3.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket=bucket, Prefix=prefix)
    
    # Iterate through the pages and objects
    for page in page_iterator:
        if 'Contents' in page:
            for obj in page['Contents']:
                key = obj['Key']
                # Check if the pattern is in the file name
                if pattern in key:
                    print(key)

# Call the function with the bucket name, prefix, and pattern
list_files_with_pattern(bucket_name, prefix, '600023040')


