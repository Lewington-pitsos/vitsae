import requests
from img2dataset import download
import shutil
import os
import sys
import pandas as pd  # Added pandas for parquet manipulation

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

def create_subset_parquet(original_path, subset_path, max_urls=100000):
    """
    Creates a subset of the original parquet file containing only the first `max_urls` URLs.

    Args:
        original_path (str): Path to the original parquet file.
        subset_path (str): Path where the subset parquet file will be saved.
        max_urls (int): Maximum number of URLs to include in the subset.
    """
    print(f"Creating a subset parquet file with the first {max_urls} URLs...")
    
    try:
        # Load the original parquet file
        df = pd.read_parquet(original_path)
        original_count = len(df)
        print(f"Original parquet file contains {original_count:,} URLs.")
        
        # Select the first `max_urls` rows
        subset_df = df.head(max_urls)
        subset_count = len(subset_df)
        print(f"Subset parquet file will contain {subset_count:,} URLs.")
        
        # Save the subset to a new parquet file
        subset_df.to_parquet(subset_path, compression='snappy', index=False)
        print(f"Successfully created subset parquet file at {subset_path}")
    except Exception as err:
        print(f"An error occurred while creating subset parquet file: {err}")
        sys.exit(1)

def download_laion(
    n_urls: int = 100_000,
    processes_count: int = 16,
    thread_count: int = 32,
    image_size: int = 224,
    base_dir='cruft',
    output_dir='cruft/bench',
):
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
    parquet_filename = f"{base_dir}/part-{part_number}.snappy.parquet"
    parquet_path = os.path.abspath(parquet_filename)
    
    # Download the specified parquet file
    download_parquet(part_number, headers, parquet_path)
    
    # Create a subset parquet file with only the first 100,000 URLs
    subset_parquet_filename = f"{base_dir}/part-{part_number}_subset.snappy.parquet"
    subset_parquet_path = os.path.abspath(subset_parquet_filename)
    create_subset_parquet(parquet_path, subset_parquet_path, max_urls=n_urls)
    
    # Clear the output directory if it already exists
    if os.path.exists(output_dir):
        try:
            shutil.rmtree(output_dir)
            print(f"Removed existing output directory: {output_dir}")
        except Exception as err:
            print(f"Error removing output directory: {err}")
            sys.exit(1)
    
    # Initiate img2dataset download process using the subset parquet file
    try:
        download(
            processes_count=processes_count,
            thread_count=thread_count,
            url_list=subset_parquet_path,          # Use the subset parquet file
            image_size=image_size,
            output_folder=output_dir,
            output_format="files",
            input_format="parquet",
            url_col="URL",                         # Ensure this matches your parquet schema
            caption_col="TEXT",
            enable_wandb=False,                     # Change to False if you don't use Weights & Biases
            number_sample_per_shard=10000,
            distributor="multiprocessing",
        )
        print(f"Started img2dataset download. Images will be saved to {output_dir}")
    except Exception as err:
        print(f"Error during img2dataset download: {err}")
        sys.exit(1)

    return output_dir

if __name__ == "__main__":
    download_laion()