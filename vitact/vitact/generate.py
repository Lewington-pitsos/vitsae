from sache import vit_generate
import fire
import sys
import time
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import randomname
from tardataset import StreamingDataset, StreamingTensorDataset
from utils import load_config
from pull import keep_pulling
from threading import Thread, Event

def main(
        run_name=None, 
        n_samples=None,
        transformer_name='laion/CLIP-ViT-L-14-laion2B-s32B-b82K', # 24 layers in total
        batch_size=1024,
        log_every=10,
        batches_per_cache=50,
        full_sequence=False,
        n_hooks=None,
        input_tensor_shape=None,
        num_cache_workers=4,
        num_data_workers=3
    ):


    # start the pulling in another thread

    tar_dir = 'cruft/tars'
    stop_event = Event()
    t = Thread(target=keep_pulling, args=(tar_dir, stop_event))
    t.start()

    if run_name is None:
        run_name = randomname.generate('adj/', 'n/')
    print('run_name:', run_name)

    dataset = StreamingTensorDataset(tar_dir)

    hook_locations = [
        (2, 'resid'),
        (5, 'resid'),
        (8, 'resid'),
        (11, 'resid'),
        (14, 'resid'),
        (17, 'resid'),
        (20, 'resid'),
        (22, 'resid'),
    ]

    if n_hooks:
        hook_locations = hook_locations[:n_hooks]

    print('number of hooks:', len(hook_locations))
    config = load_config()
    config['AWS_ACCESS_KEY_ID'] = config['AWS_ACCESS_KEY']
    
    try:
        vit_generate(
            config,
            run_name,
            batches_per_cache=batches_per_cache,
            dataset=dataset, 
            transformer_name=transformer_name, 
            batch_size=batch_size, 
            device='cuda',
            hook_locations=hook_locations,
            cache_type='s3_multilayer',
            n_samples=n_samples,
            log_every=None if log_every < 1 else log_every,
            bucket_name=config['S3_ACTIVATIONS_BUCKET_NAME'],
            full_sequence=full_sequence,
            input_tensor_shape=(batch_size, *input_tensor_shape) if input_tensor_shape else None,
            num_cache_workers=num_cache_workers,
            num_data_workers=num_data_workers
        )
    except Exception as e:
        stop_event.set()
        t.join()
        raise e
    

if __name__ == '__main__':
    fire.Fire(main)
    
# 641.3362 MB/s @ 8 processes
# 471.1610 MB/s @ 6 processes
# 548.0496 MB/s @ 6 processes memshare