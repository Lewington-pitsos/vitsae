import os

def load_config():
    config = {}
    for k in [
        'HF_TOKEN',
        'AWS_ACCESS_KEY',
        'AWS_SECRET',
        'SQS_QUEUE_URL',
        'SQS_TAR_QUEUE_URL',
        'S3_BUCKET_NAME',
        'S3_ACTIVATIONS_BUCKET_NAME',
        'TABLE_NAME',
        'ECS_CLUSTER_NAME',
        'ECS_SERVICE_NAME',
    ]:
        config[k] = os.environ.get(k)

    return config