from vitact.generate import generate_activations

if __name__ == '__main__':
    generate_activations(
        run_name="CLIP-ViT-L-14",
        n_samples=6_250_000,
        batch_size=1024,
        batches_per_cache=11,
        full_sequence=True,
        input_tensor_shape=(257,1024),
        log_every=25,
        num_cache_workers=5,
        num_data_workers=2
    )