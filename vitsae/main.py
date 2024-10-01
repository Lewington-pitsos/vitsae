import fire

from generatewds import generate_webdatasets

# poetry run python main.py --min_images_per_tar 150 --wait_after_last_change 5 --max_images_per_tar 300 --concurrency 300 --output_prefix test-wds --total_images_required 1200


if __name__ == "__main__": # with 2 workers, 2500 images per second roughly
    fire.Fire(generate_webdatasets)