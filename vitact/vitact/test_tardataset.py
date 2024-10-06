from torch.utils import data
from tardataset import StreamingDataset, StreamingTensorDataset
from PIL import Image
import io
import torch
import os
import hashlib
import tarfile
import numpy as np


def create_random_image(width, height, mode='RGB'):
    """
    Creates a new PIL Image with random pixels.

    :param width: Width of the image in pixels.
    :param height: Height of the image in pixels.
    :param mode: Color mode of the image. Common modes include 'RGB', 'RGBA', 'L' (grayscale).
    :return: PIL Image object with random pixels.
    """
    if mode == 'RGB':
        # For RGB, we need three channels
        array = np.random.randint(0, 256, (height, width, 3), dtype='uint8')
    elif mode == 'RGBA':
        # For RGBA, we need four channels
        array = np.random.randint(0, 256, (height, width, 4), dtype='uint8')
    elif mode == 'L':
        # For grayscale, we need one channel
        array = np.random.randint(0, 256, (height, width), dtype='uint8')
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    # Create the image from the array
    image = Image.fromarray(array, mode)
    return image


def create_valid_webdataset_tar(tar_path, start_index=0, num_samples=10):
    with tarfile.open(tar_path, "w") as tar:
        for i in range(num_samples):
            # Calculate the global index to ensure unique sample names across multiple tar files
            global_index = start_index + i
            # Zero-pad the index to 5 digits (e.g., '00000.jpg')
            filename = f"{global_index:05d}.jpg"
            
            # Create a unique color based on the sample index
            # This ensures each image has distinct data

            img = create_random_image(64, 64, mode='RGB')


            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG')
            img_data = img_bytes.getvalue()
            
            # Create a tarinfo object with the correct filename and size
            tarinfo = tarfile.TarInfo(name=filename)
            tarinfo.size = len(img_data)
            
            # Add the image to the tar file
            tar.addfile(tarinfo, io.BytesIO(img_data))

def test_loads_tar():
    test_data = 'test/tars'

    # Copy test data to new directory
    new_dir = 'test/tars-tmp'
    os.makedirs(new_dir, exist_ok=True)
    
    for tar_file in os.listdir(test_data):
        tar_file_path = os.path.join(test_data, tar_file)
        new_tar_file_path = os.path.join(new_dir, tar_file)
        if os.path.isfile(tar_file_path):
            os.system(f'cp {tar_file_path} {new_tar_file_path}')


    dataset = StreamingDataset(new_dir)

    for i, sample in enumerate(dataset):
        image_data = sample['jpg']
        assert 'jpg' in sample

        try:        # check that we can load the jpg with pil
            image = Image.open(io.BytesIO(image_data))
        except Exception as e:
            print(type(e), e)
            print(type(image_data))  # Should be 'bytes'
            print(len(image_data))   # Should be greater than 0

            print(image_data[:10])  # This gives a hint about the file format

        if i > 100:
            dataset.stop = True

    assert len(os.listdir(new_dir)) == 0

    for tar_file in os.listdir(new_dir):
        tar_file_path = os.path.join(new_dir, tar_file)
        os.remove(tar_file_path)
    os.rmdir(new_dir)

def test_loads_tar_tensors():
    test_data = 'test/tars'

    # Copy test data to new directory
    new_dir = 'test/tars-tmp2'
    os.makedirs(new_dir, exist_ok=True)
    
    for tar_file in os.listdir(test_data):
        tar_file_path = os.path.join(test_data, tar_file)
        new_tar_file_path = os.path.join(new_dir, tar_file)
        if os.path.isfile(tar_file_path):
            os.system(f'cp {tar_file_path} {new_tar_file_path}')

    # assert test directory is not empty
    assert len(os.listdir(new_dir)) > 0

    dataset = StreamingTensorDataset(new_dir)

    for i, sample in enumerate(dataset):
        assert isinstance(sample, torch.Tensor)

        if i > 100:
            print('stopping')   
            dataset.stop = True

    assert len(os.listdir(new_dir)) == 1

    for tar_file in os.listdir(new_dir):
        tar_file_path = os.path.join(new_dir, tar_file)
        os.remove(tar_file_path)
    os.rmdir(new_dir)


def test_multi_worker_loads_tar():
    tmp_dir = 'test/tars'
    
    data_dir = os.path.join(tmp_dir, 'test')
    os.makedirs(data_dir, exist_ok=True)
    
    num_tar_files = 80
    samples_per_tar = 20
    total_samples = num_tar_files * samples_per_tar - 150
    
    # Create multiple valid WebDataset .tar files with unique samples
    for i in range(num_tar_files):
        # Calculate the starting index to ensure unique sample names across tar files
        start_index = i * samples_per_tar
        tar_path = os.path.join(data_dir, f'data_{i}.ready.tar')
        create_valid_webdataset_tar(tar_path, start_index=start_index, num_samples=samples_per_tar)
    
    # Initialize the StreamingDataset
    dataset = StreamingDataset(data_dir)
    
    num_workers = 2
    batch_size = 4
    
    # Initialize DataLoader with multiple workers
    dataloader = data.DataLoader(
        dataset,
        num_workers=num_workers,
        batch_size=batch_size,
        shuffle=False  # Shuffling is handled by WebDataset
    )
    
    # Collect all sample hashes to check for duplicates
    collected_hashes = set()
    sample_count = 0
    
    try:
        for sample in dataloader:
            assert 'jpg' in sample, "Sample does not contain 'jpg' key."
            image_data_list = sample['jpg']
            for image_data in image_data_list:
                # Compute hash of the image data to ensure uniqueness
                img_hash = hashlib.md5(image_data).hexdigest()
                assert img_hash not in collected_hashes, "Duplicate sample detected."
                collected_hashes.add(img_hash)
                
                try:
                    image = Image.open(io.BytesIO(image_data))
                    image.verify()  # Verify that it's a valid image
                except Exception as e:
                    assert False, f"Failed to load image with PIL: {e}"
                
                sample_count += 1
            if sample_count >= total_samples:
                dataset.stop = True
                break
            if sample_count >= total_samples:
                break
    except Exception as e:
        assert False, f"Exception occurred during multi-worker loading: {e}"
    
    # Verify that all samples were loaded without duplication
    assert sample_count >= total_samples, (
        f"Expected {total_samples} samples, but got {sample_count}."
    )
    assert len(collected_hashes) >= total_samples, (
        "Number of unique samples does not match the expected total."
    )

    # Clean up the temporary directory

    for tar_file in os.listdir(data_dir):
        tar_file_path = os.path.join(data_dir, tar_file)
        os.remove(tar_file_path)
    os.rmdir(data_dir)

if __name__ == "__main__":
    test_multi_worker_loads_tar()