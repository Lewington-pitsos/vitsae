import torch
from torch.utils.data import IterableDataset
import os
import time
import glob
import tarfile
from PIL import Image
import io
import hashlib  # For deterministic hashing

from torchvision.io import decode_jpeg, ImageReadMode
import torchvision.transforms as transforms

class StreamingDataset(IterableDataset):
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self._stop = False
        self.exclude = set()

    def _get_tar_files(self):
        """Retrieve the list of .ready.tar files in the data directory."""
        tar_files = glob.glob(os.path.join(self.data_dir, '*.ready.tar'))
        tar_files.sort()
        return tar_files

    def stop(self):
        self._stop = True

    def _hash_file_path(self, tar_path):
        hash_digest = hashlib.md5(tar_path.encode('utf-8')).hexdigest()
        return int(hash_digest, 16)

    def __iter__(self):
        worker_info = torch.utils.data.get_worker_info()
        
        if worker_info is None:
            worker_id = 0
            num_workers = 1
        else:
            worker_id = worker_info.id
            num_workers = worker_info.num_workers

        while not self._stop:
            tar_files = self._get_tar_files()
            if not tar_files:
                print('Waiting for tar files...')
                time.sleep(5)
                continue

            assigned_tar_files = [
                tar for tar in tar_files
                if self._hash_file_path(tar) % num_workers == worker_id
            ]

            if not assigned_tar_files:
                print(f'Worker {worker_id}: No assigned tar files. Waiting...')
                time.sleep(5)
                continue
            
            try:
                for tar_file in assigned_tar_files:
                    with tarfile.open(tar_file, 'r') as tar:
                        for member in tar:
                            if member.isfile() and member.name.lower().endswith('.jpg'):
                                try:
                                    file_obj = tar.extractfile(member)
                                    if file_obj is not None:
                                        img_bytes = file_obj.read()
                                        sample = {'jpg': img_bytes}
                                        yield sample
                                except Exception as img_e:
                                    print(f'Worker {worker_id}: Error reading {member.name} in {tar_file}: {img_e}')

                    try:
                        os.remove(tar_file)
                        print(f'Worker {worker_id}: Removed {tar_file}')
                    except OSError as e:
                        print(f'Worker {worker_id}: Error removing {tar_file}: {e}')

            except Exception as e:
                print(f'Worker {worker_id}: Error processing {tar_file}: {e}')
  
            time.sleep(0.3)

class StreamingTensorDataset(StreamingDataset):
    def __init__(self, data_dir):
        super().__init__(data_dir)

        self.transform = transforms.ToTensor()

    def __iter__(self):
        for sample in super().__iter__():
            if self._stop:
                break

            if 'jpg' in sample:
                try:
                    image = Image.open(io.BytesIO(sample['jpg'])).convert('RGB')
                    image = image.resize((224, 224))

                    image_tensor = self.transform(image)
                    yield image_tensor
                except Exception as e:
                    print(type(e), e)
