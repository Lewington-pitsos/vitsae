import requests
from img2dataset import download
import shutil
import os
import sys

from utils import load_config

def download_parquet(part_number, headers, save_path):
    """
    Downloads a specific parquet file from Hugging Face.
    
    Args:
        part_number (str): The part number of the parquet file (e.g., '00000').
        headers (dict): The HTTP headers including authorization.
        save_path (str): The local path where the parquet file will be saved.
    """
    pq_url = (
        f"https://huggingface.co/datasets/laion/laion2B-multi-joined-translated-to-en/"
        f"resolve/main/part-{part_number}-00478b7a-941e-4176-b569-25f4be656991-c000.snappy.parquet"
    )
    
    print(f"Starting download of {pq_url}...")
    
    try:
        with requests.get(pq_url, headers=headers, stream=True) as response:
            response.raise_for_status()  # Check for HTTP errors
            with open(save_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
        print(f"Successfully downloaded parquet file to {save_path}")
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred while downloading parquet file: {http_err}")
        sys.exit(1)
    except Exception as err:
        print(f"An error occurred while downloading parquet file: {err}")
        sys.exit(1)

def main():
    # Load configuration
    config = load_config()
    hf_token = config.get('HF_TOKEN')
    
    if not hf_token:
        print("Error: HF_TOKEN not found in configuration.")
        sys.exit(1)
    
    # Set the Hugging Face token as an environment variable
    os.environ['HF_TOKEN'] = hf_token
    
    # Define headers for authentication
    headers = {
        "Authorization": f"Bearer {hf_token}"
    }
    
    # Specify which part to download (e.g., '00000' to '00127')
    part_number = '00000'  # Change this as needed
    
    # Define the local filename and path for the parquet file
    parquet_filename = f"part-{part_number}.snappy.parquet"
    parquet_path = os.path.abspath(parquet_filename)
    
    # Download the specified parquet file
    download_parquet(part_number, headers, parquet_path)
    
    # Define the output directory for img2dataset
    output_dir = os.path.abspath("bench")
    
    # Clear the output directory if it already exists
    if os.path.exists(output_dir):
        try:
            shutil.rmtree(output_dir)
            print(f"Removed existing output directory: {output_dir}")
        except Exception as err:
            print(f"Error removing output directory: {err}")
            sys.exit(1)
    
    # Initiate img2dataset download process
    try:
        download(
            processes_count=16,
            thread_count=32,
            url_list=parquet_path,          # Path to the downloaded parquet file
            image_size=256,
            output_folder=output_dir,
            output_format="files",
            input_format="parquet",
            url_col="URL",
            caption_col="TEXT",
            enable_wandb=True,              # Change to False if you don't use Weights & Biases
            number_sample_per_shard=1000,
            distributor="multiprocessing",
        )
        print(f"Started img2dataset download. Images will be saved to {output_dir}")
    except Exception as err:
        print(f"Error during img2dataset download: {err}")
        sys.exit(1)

if __name__ == "__main__":
    main()