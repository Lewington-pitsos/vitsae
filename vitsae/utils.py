import os

def load_config():
    hf_token = os.getenv('HF_TOKEN')
    aws_access_key = os.getenv('AWS_ACCESS_KEY')
    aws_secret = os.getenv('AWS_SECRET')
    sqs_queue_url = os.getenv('SQS_QUEUE_URL')
    s3_bucket_name = os.getenv('S3_BUCKET_NAME')
    table_name = os.getenv('TABLE_NAME')

    return {
        'HF_TOKEN': hf_token,
        'AWS_ACCESS_KEY': aws_access_key,
        'AWS_SECRET': aws_secret,
        'SQS_QUEUE_URL': sqs_queue_url,
        'S3_BUCKET_NAME': s3_bucket_name,
        'TABLE_NAME': table_name
    }
