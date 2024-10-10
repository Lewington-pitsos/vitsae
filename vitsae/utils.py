import os

def load_config():
    config = {}
    for k in [
        'HF_TOKEN',
        'AWS_ACCESS_KEY',
        'AWS_SECRET',
        'SQS_QUEUE_URL',
        'SQS_TAR_QUEUE_URL',
        'SQS_TRAINING_CONFIG_QUEUE_URL',
        'S3_BUCKET_NAME',
        'S3_ACTIVATIONS_BUCKET_NAME',
        'TABLE_NAME',
        'ECS_CLUSTER_NAME',
        'ECS_SERVICE_NAME',
        'WANDB_API_KEY',
    ]:
        config[k] = os.environ.get(k)

    config['AWS_ACCESS_KEY_ID'] = config['AWS_ACCESS_KEY']

    return config