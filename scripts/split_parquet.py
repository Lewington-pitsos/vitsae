import os
import requests
from tqdm import tqdm
import pyarrow.parquet as pq
from math import ceil

def download_file(session, url, headers, dest_path):
    """Download a file from a URL with headers and save it to dest_path."""
    with session.get(url, headers=headers, stream=True) as response:
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024  # 1 Kibibyte
        with open(dest_path, 'wb') as file, tqdm(
            total=total_size, unit='iB', unit_scale=True, desc=os.path.basename(dest_path)
        ) as progress:
            for data in response.iter_content(block_size):
                progress.update(len(data))
                file.write(data)

def split_parquet_file(file_path, num_splits, output_dir):
    """Split a parquet file into num_splits smaller parquet files."""
    table = pq.read_table(file_path)
    total_rows = table.num_rows
    rows_per_split = ceil(total_rows / num_splits)
    
    for i in range(num_splits):
        start = i * rows_per_split
        end = min((i + 1) * rows_per_split, total_rows)
        if start >= end:
            break  # No more data to split
        
        split_table = table.slice(start, end - start)
        split_file_name = f"{os.path.splitext(os.path.basename(file_path))[0]}_part_{i+1:02d}.parquet"
        split_file_path = os.path.join(output_dir, split_file_name)
        pq.write_table(split_table, split_file_path)
        print(f"Saved split file: {split_file_path}")

def main():
    # Configuration
    HF_TOKEN = os.getenv('HF_TOKEN')
    if not HF_TOKEN:
        raise EnvironmentError("Please set the HF_TOKEN environment variable.")

    base_url = "https://huggingface.co/datasets/laion/laion2B-multi-joined-translated-to-en/resolve/main"
    file_pattern = "part-{i:05d}-00478b7a-941e-4176-b569-25f4be656991-c000.snappy.parquet"
    total_files = 128  # From 00000 to 00127
    num_splits = 30

    download_dir = "cruft/downloaded_parquets"
    split_dir = "cruft/split_parquets"

    os.makedirs(download_dir, exist_ok=True)
    os.makedirs(split_dir, exist_ok=True)

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}"
    }

    session = requests.Session()

    for i in tqdm(range(total_files), desc="Downloading files"):
        file_suffix = file_pattern.format(i=i)
        url = f"{base_url}/{file_suffix}"
        dest_path = os.path.join(download_dir, file_suffix)

        # Check if file already exists to avoid re-downloading
        if os.path.exists(dest_path):
            print(f"File already exists, skipping download: {dest_path}")
        else:
            try:
                download_file(session, url, headers, dest_path)
            except requests.HTTPError as e:
                print(f"Failed to download {url}: {e}")
                continue  # Skip to the next file

        # Split the downloaded parquet file
        try:
            split_parquet_file(dest_path, num_splits, split_dir)
        except Exception as e:
            print(f"Failed to split {dest_path}: {e}")
            continue  # Skip to the next file

    print("All files downloaded and split successfully.")

if __name__ == "__main__":
    main()
