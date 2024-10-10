import json

import boto3

from vitact.utils import load_config

def build_configs(output_filename=None):
    baseline =        {
        "wandb_project": "test-vit-sae-multilayer",
        "data_bucket": "sae-activations",
        "log_bucket": "sae-activations",
        "n_feats": 65536,
        "batch_size": 16448 * 2,
        "k": 32,
        "lr": 0.002,
        "d_in": 1024,
        "seq_len": 257,
        "cache_buffer_size": 3,
        "n_cache_workers": 4,
        "batch_norm": False,
        'architecture': 'topk',
        "n_experts": None,

        "n_tokens": 1_000_000_000,
        "save_every": 100_000_000,
        
        "save_checkpoints_to_s3": True,
    }

    all_configs = []
    for layer in ['11_resid', '14_resid', '17_resid', '20_resid', '22_resid', '2_resid', '5_resid', '8_resid']:
        clone = baseline.copy()
        clone['data_name'] = f"CLIP-ViT-L-14/{layer}"
        clone['name'] = 'test-' + layer

        print()
        print('Config: ----------------------------------')
        print(json.dumps(clone, indent=2))

        all_configs.append(clone)

    if output_filename is not  None:
        print(f'Generated {len(all_configs)} configs at {output_filename}')
        with open(output_filename, 'w') as f:
            json.dump(all_configs, f, indent=2)

    credentials = load_config()

    sqs = boto3.client(
        'sqs',
        aws_access_key_id=credentials['AWS_ACCESS_KEY'],
        aws_secret_access_key=credentials['AWS_SECRET']
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