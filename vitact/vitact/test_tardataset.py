import pytest
from torch.utils import data
from tardataset import StreamingDataset, StreamingTensorDataset
from PIL import Image
import io
import torch
import os
import shutil
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
    """
    Creates a valid WebDataset tar file containing random images.

    :param tar_path: Path where the tar file will be created.
    :param start_index: Starting index for naming the image files.
    :param num_samples: Number of image samples to include in the tar.
    """
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

@pytest.fixture(scope="session")
def source_tar_dir():
    """
    Fixture to provide the path to the source tar directory.
    Assumes that 'test/tars' exists and contains tar files.
    """
    return os.path.abspath('test/tars')

@pytest.fixture
def temporary_tar_dir(source_tar_dir, tmp_path):
    """
    Fixture to create a temporary directory and copy tar files from the source directory.
    Automatically cleans up after the test.
    
    :param source_tar_dir: Path to the source tar directory.
    :param tmp_path: Temporary path provided by pytest.
    :return: Path to the temporary tar directory.
    """
    dest_dir = tmp_path / "tars-tmp"
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Copy all tar files from source to destination
    for tar_file in os.listdir(source_tar_dir):
        tar_file_path = os.path.join(source_tar_dir, tar_file)
        if os.path.isfile(tar_file_path):
            shutil.copy(tar_file_path, dest_dir / tar_file)

    yield dest_dir

    # No need for explicit cleanup; tmp_path handles it

@pytest.fixture
def temporary_tar_dir_tensors(source_tar_dir, tmp_path):
    """
    Fixture similar to temporary_tar_dir but for tensor dataset tests.
    
    :param source_tar_dir: Path to the source tar directory.
    :param tmp_path: Temporary path provided by pytest.
    :return: Path to the temporary tar directory for tensor datasets.
    """
    dest_dir = tmp_path / "tars-tmp2"
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Copy all tar files from source to destination
    for tar_file in os.listdir(source_tar_dir):
        tar_file_path = os.path.join(source_tar_dir, tar_file)
        if os.path.isfile(tar_file_path):
            shutil.copy(tar_file_path, dest_dir / tar_file)

    yield dest_dir

    # No need for explicit cleanup; tmp_path handles it

@pytest.fixture
def multi_worker_tar_dir(tmp_path):
    """
    Fixture to create a temporary directory with multiple tar files for multi-worker tests.
    Automatically cleans up after the test.
    
    :param tmp_path: Temporary path provided by pytest.
    :return: Path to the temporary directory containing multiple tar files.
    """
    data_dir = tmp_path / "multi-worker-tars"
    data_dir.mkdir(parents=True, exist_ok=True)

    num_tar_files = 80
    samples_per_tar = 20

    # Create multiple valid WebDataset .tar files with unique samples
    for i in range(num_tar_files):
        # Calculate the starting index to ensure unique sample names across tar files
        start_index = i * samples_per_tar
        tar_path = data_dir / f'data_{i}.ready.tar'
        create_valid_webdataset_tar(tar_path, start_index=start_index, num_samples=samples_per_tar)

    yield data_dir

    # No need for explicit cleanup; tmp_path handles it

def test_loads_tar(temporary_tar_dir):
    """
    Test that tar files are loaded correctly by StreamingDataset.
    
    :param temporary_tar_dir: Temporary directory with copied tar files.
    """
    dataset = StreamingDataset(str(temporary_tar_dir))

    for i, sample in enumerate(dataset):
        assert 'jpg' in sample, "Sample does not contain 'jpg' key."

        image_data = sample['jpg']

        try:  # Check that we can load the jpg with PIL
            image = Image.open(io.BytesIO(image_data))
            image.verify()  # Verify that it's a valid image
        except Exception as e:
            pytest.fail(f"Failed to load image with PIL: {type(e)} {e}\n"
                        f"Image data type: {type(image_data)}\n"
                        f"Image data length: {len(image_data)}\n"
                        f"Image data snippet: {image_data[:10]}")

        if i >= 100:
            dataset._stop = True
            break

    # Assert that the temporary directory is empty after processing
    assert len(os.listdir(temporary_tar_dir)) == 1, "Temporary tar directory should still have 1 file after stopping"

def test_loads_tar_tensors(temporary_tar_dir_tensors):
    """
    Test that tar files are loaded correctly by StreamingTensorDataset.
    
    :param temporary_tar_dir_tensors: Temporary directory with copied tar files for tensor datasets.
    """
    # Assert test directory is not empty
    assert len(os.listdir(temporary_tar_dir_tensors)) > 0, "Temporary tar directory is empty."

    dataset = StreamingTensorDataset(str(temporary_tar_dir_tensors))

    for i, sample in enumerate(dataset):
        assert isinstance(sample, torch.Tensor), f"Sample {i} is not a torch.Tensor."

        if i >= 100:
            print('Stopping dataset iteration after 100 samples.')
            dataset._stop = True
            break

    # Assert that the temporary directory has exactly one tar file left
    assert len(os.listdir(temporary_tar_dir_tensors)) == 1, (
        f"Expected 1 tar file in temporary directory, but found {len(os.listdir(temporary_tar_dir_tensors))}."
    )

def test_multi_worker_loads_tar(multi_worker_tar_dir):
    """
    Test that multiple workers can load tar files without duplication or errors.
    
    :param multi_worker_tar_dir: Temporary directory containing multiple tar files for multi-worker tests.
    """
    dataset = StreamingDataset(str(multi_worker_tar_dir))

    num_workers = 2
    batch_size = 4

    # Initialize DataLoader with multiple workers
    dataloader = data.DataLoader(
        dataset,
        num_workers=num_workers,
        batch_size=batch_size,
        shuffle=False  # Shuffling is handled by WebDataset
    )

    num_tar_files = 80
    samples_per_tar = 20
    total_samples = num_tar_files * samples_per_tar - 150  # As per original test

    # Collect all sample hashes to check for duplicates
    collected_hashes = set()
    sample_count = 0

    try:
        for batch in dataloader:
            assert 'jpg' in batch, "Batch does not contain 'jpg' key."
            image_data_list = batch['jpg']
            for image_data in image_data_list:
                # Compute hash of the image data to ensure uniqueness
                img_hash = hashlib.md5(image_data).hexdigest()
                assert img_hash not in collected_hashes, "Duplicate sample detected."
                collected_hashes.add(img_hash)

                try:
                    image = Image.open(io.BytesIO(image_data))
                    image.verify()  # Verify that it's a valid image
                except Exception as e:
                    pytest.fail(f"Failed to load image with PIL: {type(e)} {e}")

                sample_count += 1

                if sample_count >= total_samples:
                    dataset._stop = True
                    break

            if sample_count >= total_samples:
                break
    except Exception as e:
        pytest.fail(f"Exception occurred during multi-worker loading: {type(e)} {e}")

    # Verify that all samples were loaded without duplication
    assert sample_count >= total_samples, (
        f"Expected at least {total_samples} samples, but got {sample_count}."
    )
    assert len(collected_hashes) >= total_samples, (
        "Number of unique samples does not match the expected total."
    )

    # No need for explicit cleanup; fixtures handle it

if __name__ == "__main__":
    # This allows the tests to be run directly without using the pytest command
    pytest.main([__file__])
