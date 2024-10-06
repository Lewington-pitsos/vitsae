import os
from generate import generate_activations

if __name__ == '__main__':
    # check if the RUN_NAME environment variable is set

    run_name = 'CLIP-ViT-L-14'
    if os.environ.get("RUN_NAME"):
        run_name = os.environ.get("RUN_NAME")

    print(f"Generating activations for {run_name}")

    generate_activations(
        run_name=run_name,
        n_samples=6_500_000,
        batch_size=1024,
        batches_per_cache=11,
        full_sequence=True,
        input_tensor_shape=(257,1024),
        log_every=25,
        num_cache_workers=5,
        num_data_workers=2
    )