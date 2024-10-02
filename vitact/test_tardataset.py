import pytest
import os
import tarfile
from torch.utils.data import DataLoader
from tardataset import StreamingDataset

# Helper function to create a mock .tar file for testing
def create_mock_tar(data_dir, tar_name, num_samples=5):
    os.makedirs(data_dir, exist_ok=True)
    tar_path = os.path.join(data_dir, tar_name)
    with tarfile.open(tar_path, "w") as tar:
        for i in range(num_samples):
            sample_data = f"sample_{i}".encode("utf-8")
            sample_file = f"sample_{i}.txt"
            with open(sample_file, "wb") as f:
                f.write(sample_data)
            tar.add(sample_file)
            os.remove(sample_file)
    os.rename(tar_path, tar_path.replace('.tar', '.ready.tar'))

@pytest.fixture
def setup_mock_data(tmp_path):
    # Create mock tar files for testing
    data_dir = tmp_path / "data"
    create_mock_tar(data_dir, "mock_data_1.tar", num_samples=10)
    create_mock_tar(data_dir, "mock_data_2.tar", num_samples=10)
    return str(data_dir)

def test_no_repeated_samples(setup_mock_data):
    data_dir = setup_mock_data
    dataset = StreamingDataset(data_dir)
    
    # Use DataLoader with multiple workers
    data_loader = DataLoader(dataset, num_workers=4, batch_size=None)

    # Collect all samples
    collected_samples = set()
    sample_count = 0

    # Iterate through the DataLoader to collect samples
    for sample in data_loader:
        # Assuming sample is a dictionary containing data with a 'txt' key
        sample_key = sample['__key__'] if '__key__' in sample else str(sample)
        assert sample_key not in collected_samples, f"Duplicate sample found: {sample_key}"
        collected_samples.add(sample_key)
        sample_count += 1

        # Limit iterations to avoid infinite loop during the test
        if sample_count >= 20:
            break

    # Ensure we collected the expected number of unique samples
    assert len(collected_samples) == sample_count

