import os
import json
import uuid

import boto3

from vitact.utils import load_config

def build_configs(output_filename=None):
    baseline =        {
        "wandb_project": "CLIP-ViT-L-14-laion2B-s32B-b82K",
        "data_bucket": "sae-activations",
        "log_bucket": "sae-activations",
        "n_feats": 65536,
        "batch_size": 32896,
        "k": 32,
        "lr": 0.00009,
        "d_in": 1024,
        "seq_len": 257,
        "cache_buffer_size": 3,
        "n_cache_workers": 4,
        "batch_norm": True,
        'architecture': 'topk',
        "n_experts": None,

        "n_tokens": 1_000_000_000,
        "save_every": 33_000_000,

        "base_log_dir": "log",
    }

    all_configs = []
    locations = ['2_resid', '5_resid', '8_resid', '11_resid', '14_resid', '17_resid', '10_resid', '22_resid']
    for location in locations:
        clone = baseline.copy()
        clone['data_name'] = f"CLIP-ViT-L-14-laion2B-s32B-b82K/{location}"
        clone['id'] = location + '-' + str(uuid.uuid4())[:8]

        print()
        print('Config: ----------------------------------')
        print(json.dumps(clone, indent=2))

        all_configs.append(clone)

    if output_filename is not  None:
        print(f'Generated {len(all_configs)} configs at {output_filename}')

        if not os.path.exists(os.path.dirname(output_filename)):
            os.makedirs(os.path.dirname(output_filename))

        with open(output_filename, 'w') as f:
            json.dump(all_configs, f, indent=2)

    credentials = load_config()

    sqs = boto3.client(
        'sqs',
        aws_access_key_id=credentials['AWS_ACCESS_KEY'],
        aws_secret_access_key=credentials['AWS_SECRET'],
        region_name='us-east-1'
    )

    for config in all_configs:
        try:
            sqs.send_message(
                QueueUrl=credentials['SQS_TRAINING_CONFIG_QUEUE_URL'],
                MessageBody=json.dumps(config)
            )
        except Exception as e:
            print(f'Error sending config to SQS: {e}')

if __name__ == '__main__':
    build_configs('cruft/configs.json')