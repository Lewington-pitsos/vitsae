import os

from torch import log_
from generate import generate_activations

if __name__ == '__main__':
    run_name = 'CLIP-ViT-L-14'
    if os.environ.get("RUN_NAME"):
        run_name = os.environ.get("RUN_NAME")

    num_cache_workers = 4
    if os.environ.get("NUM_CACHE_WORKERS"):
        num_cache_workers = int(os.environ.get("NUM_CACHE_WORKERS"))

    num_data_workers = 2
    if os.environ.get("NUM_DATA_WORKERS"):
        num_data_workers = int(os.environ.get("NUM_DATA_WORKERS"))

    log_every = 5
    if os.environ.get("LOG_EVERY"):
        log_every = int(os.environ.get("LOG_EVERY"))
    
    batches_per_cache = 11
    if os.environ.get("BATCHES_PER_CACHE"):
        batches_per_cache = int(os.environ.get("BATCHES_PER_CACHE"))

    batch_size = 768
    if os.environ.get("BATCH_SIZE"):
        batch_size = int(os.environ.get("BATCH_SIZE"))

    print(f"Generating activations for {run_name}")

    generate_activations(
        run_name=run_name,
        n_samples=10_000_000,
        batch_size=batch_size,
        batches_per_cache=batches_per_cache,
        full_sequence=True,
        input_tensor_shape=(257,1024),
        log_every=log_every,
        num_cache_workers=num_cache_workers,
        num_data_workers=num_data_workers
    )