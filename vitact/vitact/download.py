import requests
from img2dataset import download
import shutil
import os

from utils import load_config

if __name__ == "__main__":
    config = load_config()

    os.environ['HF_TOKEN'] = config['HF_TOKEN']

# for i in {00000..00127}; do wget --header="Authorization: Bearer $HF_TOKEN" https://huggingface.co/datasets/laion/laion2B-multi-joined-translated-to-en/resolve/main/.part-$i-00478b7a-941e-4176-b569-25f4be656991-c000.snappy.parquet.crc; done
    # pq_url = 

    headers = {
        
    }

    response = requests.get(
        "https://huggingface.co/datasets/laion/laion2B-multi-joined-translated-to-en/resolve/main/part-00000-00478b7a-941e-4176-b569-25f4be656991-c000.snappy.parquet"
    )



    output_dir = os.path.abspath("bench")

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    download(
        processes_count=16,
        thread_count=32,
        url_list="test_10000.parquet",
        image_size=256,
        output_folder=output_dir,
        output_format="files",
        input_format="parquet",
        url_col="URL",
        caption_col="TEXT",
        enable_wandb=True,
        number_sample_per_shard=1000,
        distributor="multiprocessing",
    )
