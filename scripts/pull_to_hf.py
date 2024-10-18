import os
import boto3
import torch
import json
import tempfile
from huggingface_hub import HfApi, Repository, create_repo
from botocore.exceptions import NoCredentialsError, ClientError

# Configuration
S3_BUCKET = 'sae-activations'  # Replace with your S3 bucket name
BASE_PREFIX = 'log/CLIP-ViT-L-14-laion2B-s32B-b82K/'  # Base prefix in the S3 bucket
HUGGINGFACE_REPO = 'lewington/CLIP-ViT-L-scope'  # Replace with your Hugging Face repo
HUGGINGFACE_TOKEN = os.getenv('HF_TOKEN')  # Ensure this environment variable is set

s3_client = boto3.client('s3')

hf_api = HfApi()

# Function to create the Hugging Face repo if it doesn't exist
def ensure_hf_repo(repo_id):
    try:
        hf_api.repo_info(repo_id)
        print(f"Hugging Face repository '{repo_id}' already exists.")
    except Exception:
        print(f"Creating Hugging Face repository '{repo_id}'.")
        create_repo(repo_id, private=False)

# Ensure the Hugging Face repository exists
ensure_hf_repo(HUGGINGFACE_REPO)

# Function to list all "resid" subdirectories
def list_resid_directories(bucket, prefix):
    paginator = s3_client.get_paginator('list_objects_v2')
    operation_parameters = {'Bucket': bucket, 'Prefix': prefix, 'Delimiter': '/'}
    page_iterator = paginator.paginate(**operation_parameters)
    
    resid_dirs = []
    for page in page_iterator:
        if 'CommonPrefixes' in page:
            for cp in page['CommonPrefixes']:
                dir_name = cp.get('Prefix').split('/')[-2]
                resid_dirs.append(dir_name)
    return resid_dirs

# Function to list subdirectories within a "resid" directory
def list_subdirectories(bucket, prefix):
    paginator = s3_client.get_paginator('list_objects_v2')
    operation_parameters = {'Bucket': bucket, 'Prefix': prefix, 'Delimiter': '/'}
    page_iterator = paginator.paginate(**operation_parameters)
    
    subdirs = []
    for page in page_iterator:
        if 'CommonPrefixes' in page:
            for cp in page['CommonPrefixes']:
                subdir_name = cp.get('Prefix').split('/')[-2]
                subdirs.append(subdir_name)
    return subdirs

# Function to list all .pt and .jsonl files in a subdirectory
def list_files(bucket, prefix):
    paginator = s3_client.get_paginator('list_objects_v2')
    operation_parameters = {'Bucket': bucket, 'Prefix': prefix}
    page_iterator = paginator.paginate(**operation_parameters)
    
    pt_files = []
    jsonl_files = []
    for page in page_iterator:
        for obj in page.get('Contents', []):
            key = obj['Key']
            if key.endswith('.pt'):
                pt_files.append(key)
            elif key.endswith('.jsonl'):
                jsonl_files.append(key)
    return pt_files, jsonl_files

# Function to filter .pt files based on token counts (selecting every ~1,000,000 tokens)
def filter_pt_files(pt_files):
    # Extract numeric part from filenames and sort them
    token_counts = []
    for file in pt_files:
        filename = os.path.basename(file)
        token_str = filename.replace('.pt', '')
        try:
            token = int(token_str)
            token_counts.append(token)
        except ValueError:
            continue  # Skip files that don't follow the naming convention
    
    token_counts = sorted(token_counts)
    
    # Select files where token count increases by at least 1,000,000
    step = 100_000_000
    selected_files = [f for f in pt_files if int(os.path.basename(f).replace('.pt', '')) % step < 300_000]
    return selected_files

# Function to download a file from S3 to a local path
def download_s3_file(bucket, key, local_path):
    try:
        s3_client.download_file(bucket, key, local_path)
        print(f"Downloaded {key} to {local_path}")
    except ClientError as e:
        print(f"Error downloading {key}: {e}")

# Function to upload a file to Hugging Face
def upload_to_hf(repo_id, local_path, hf_path):
    try:
        hf_api.upload_file(
            path_or_fileobj=local_path,
            path_in_repo=hf_path,
            repo_id=repo_id,
            repo_type="model",
            token=HUGGINGFACE_TOKEN,
            commit_message=f"Add {os.path.basename(local_path)}",
        )
        print(f"Uploaded {local_path} to Hugging Face at {hf_path}")
    except Exception as e:
        print(f"Error uploading {local_path} to Hugging Face: {e}")

def main():
    # Create a temporary directory to store downloaded and processed files
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Using temporary directory {tmpdir}")
        
        # List all "resid" directories
        resid_dirs = list_resid_directories(S3_BUCKET, BASE_PREFIX)
        print(f"Found {len(resid_dirs)} 'resid' directories.")
        
        for resid_dir in resid_dirs:
            resid_prefix = os.path.join(BASE_PREFIX, resid_dir)  # e.g., log/.../11_resid/
            print(f"\nProcessing '{resid_dir}'...")
            
            # List all subdirectories within the "resid" directory
            subdirs = list_subdirectories(S3_BUCKET, resid_prefix)
            print(f"  Found {len(subdirs)} subdirectories in '{resid_dir}'.")
            
            for subdir in subdirs:
                subdir_prefix = os.path.join(resid_prefix, subdir)  # e.g., log/.../11_resid/11_resid-a3ff8172/
                print(f"  Processing subdirectory '{subdir}'...")
                
                # List .pt and .jsonl files
                pt_files, jsonl_files = list_files(S3_BUCKET, subdir_prefix)
                print(f"    Found {len(pt_files)} .pt files and {len(jsonl_files)} .jsonl files.")
                
                if not jsonl_files:
                    print(f"    No .jsonl file found in '{subdir}'. Skipping.")
                    continue
                
                # Assume there's only one .jsonl file per subdirectory
                jsonl_key = jsonl_files[0]
                jsonl_filename = os.path.basename(jsonl_key)
                local_jsonl_path = os.path.join(tmpdir, jsonl_filename)
                download_s3_file(S3_BUCKET, jsonl_key, local_jsonl_path)
                
                # Filter .pt files based on token counts
                selected_pt_files = filter_pt_files(pt_files)
                print(f"    Selected {len(selected_pt_files)} .pt files based on token counts.")
                for pt_file in selected_pt_files:
                    print(f"      {os.path.basename(pt_file)}")
                
                for pt_key in selected_pt_files:
                    pt_filename = os.path.basename(pt_key)
                    local_pt_path = os.path.join(tmpdir, pt_filename)
                    download_s3_file(S3_BUCKET, pt_key, local_pt_path)
                    
                    # Load the .pt file
                    try:
                        checkpoint = torch.load(local_pt_path, map_location='cpu')
                        print(f"      Loaded checkpoint from {pt_filename}")
                    except Exception as e:
                        print(f"      Error loading {pt_filename}: {e}")
                        continue
                    
                    # Modify the checkpoint dictionary
                    if 'optimizer_state_dict' in checkpoint:
                        del checkpoint['optimizer_state_dict']
                        print(f"        Removed 'optimizer_state_dict' from {pt_filename}")
                    
                    # Add new keys
                    checkpoint['d_in'] = 1024
                    checkpoint['n_features'] = 65536
                    checkpoint['k'] = 32
                    print(f"        Added new keys to {pt_filename}")
                    
                    
                    # Save the modified checkpoint
                    modified_pt_filename = f"modified_{pt_filename}"
                    modified_pt_path = os.path.join(tmpdir, modified_pt_filename)
                    try:
                        torch.save(checkpoint, modified_pt_path)
                        print(f"        Saved modified checkpoint to {modified_pt_filename}")
                    except Exception as e:
                        print(f"        Error saving modified checkpoint {modified_pt_filename}: {e}")
                        continue
                    
                    # Define the Hugging Face path
                    resid_prefix_hf = resid_dir  # e.g., '11_resid'
                    hf_pt_path = os.path.join(resid_prefix_hf, pt_filename)  # e.g., '11_resid/800162304.pt'
                    
                    # Upload the modified .pt file to Hugging Face
                    upload_to_hf(HUGGINGFACE_REPO, modified_pt_path, hf_pt_path)
                    
                    # Optionally, remove the downloaded and modified .pt files to save space
                    os.remove(local_pt_path)
                    os.remove(modified_pt_path)
                    print(f"        Cleaned up local files for {pt_filename}")
                
                # Upload the .jsonl file to Hugging Face
                hf_jsonl_path = os.path.join(resid_prefix_hf, jsonl_filename)  # e.g., '11_resid/11_resid-a3ff8172.jsonl'
                upload_to_hf(HUGGINGFACE_REPO, local_jsonl_path, hf_jsonl_path)
                
                # Clean up the downloaded .jsonl file
                os.remove(local_jsonl_path)
                print(f"    Cleaned up local file {jsonl_filename}")
        
        print("\nAll processing and uploads completed successfully.")

if __name__ == "__main__":
    import sys
    main()
