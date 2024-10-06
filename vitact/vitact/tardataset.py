import torch
from torch.utils.data import IterableDataset
import os
import time
import glob
import webdataset as wds
from PIL import Image
import io

from torchvision.io import decode_jpeg, ImageReadMode
import torchvision.transforms as transforms

class StreamingDataset(IterableDataset):
    def __init__(self, data_dir, destructive=False):
        self.data_dir = data_dir
        self.stop = False
        self.exclude = set()
        self.destructive = destructive

    def _get_tar_files(self):
        """Retrieve the list of .ready.tar files in the data directory."""
        tar_files = glob.glob(os.path.join(self.data_dir, '*.ready.tar'))
        tar_files.sort()
        return tar_files

    def __iter__(self):
        worker_info = torch.utils.data.get_worker_info()
        if worker_info is not None:
            raise ValueError("This dataset is not compatible with multi-process loading.")

        while not self.stop:
            tar_files = self._get_tar_files()
            if not tar_files:
                print('waiting for tar files...')
                time.sleep(5)
                continue

            # Create a WebDataset pipeline for each tar file
            for tar_file in tar_files:
                dataset = wds.WebDataset(tar_file, shardshuffle=False)
                for sample in dataset:
                    yield sample
                
                if self.destructive:
                    os.remove(tar_file)

class StreamingTensorDataset(StreamingDataset):
    def __init__(self, data_dir, destructive=False, device='cuda'):
        super().__init__(data_dir, destructive)

        self.transform = transforms.ToTensor()
        self.device = device

    def __iter__(self):
        for sample in super().__iter__():
            if self.stop:
                break

            if 'jpg' in sample:
                try:
                    image = Image.open(io.BytesIO(sample['jpg'])).convert('RGB')
                    image = image.resize((224, 224))

                    image_tensor = self.transform(image).to(self.device)
                    yield image_tensor
                except Exception as e:
                    print(type(e), e)


