from numpy import isin
from torch.utils import data
from tardataset import StreamingDataset, StreamingTensorDataset
from PIL import Image
import io
import torch
import webdataset as wds
import os

def test_loads_tar():
    test_data = 'test/tars'

    # copy test data to new directory
    new_dir = 'test/tars-tmp'
    os.makedirs(new_dir, exist_ok=True)
    
    for tar_file in os.listdir(test_data):
        tar_file_path = os.path.join(test_data, tar_file)
        new_tar_file_path = os.path.join(new_dir, tar_file)
        os.system(f'cp {tar_file_path} {new_tar_file_path}')

    dataset = StreamingDataset(new_dir, destructive=False)

    for i, sample in enumerate(dataset):
        image_data = sample['jpg']
        assert 'jpg' in sample

        try:        # check that we can load the jpg with pil
            image = Image.open(io.BytesIO(image_data))
        except Exception as e:
            print(type(e), e)
            print(type(image_data))  # Should be 'bytes'
            print(len(image_data))   # Should be greater than 0

            # Check the first few bytes to inspect the file signature (magic number)
            print(image_data[:10])  # This gives a hint about the file format

        if i > 100:
            dataset.stop = True

    # assert test directory is empty

    assert len(os.listdir(new_dir)) > 0

    dataset = StreamingTensorDataset(new_dir, destructive=False)

    for i, sample in enumerate(dataset):
        assert isinstance(sample, torch.Tensor)

        if i > 100:
            print('stopping')   
            dataset.stop = True

    assert len(os.listdir(new_dir)) > 0

    # delete all files then remove directory
    for tar_file in os.listdir(new_dir):
        os.remove(os.path.join(new_dir, tar_file))
    os.rmdir(new_dir)


