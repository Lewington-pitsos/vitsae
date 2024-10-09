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

    def _get_tar_files(self):
        """Retrieve the list of .ready.tar files in the data directory."""
        tar_files = glob.glob(os.path.join(self.data_dir, '*.ready.tar'))
        tar_files.sort()
        return tar_files

    def stop(self):
        self._stop = True

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
                print(f'Worker {worker_id}: Waiting for tar files...')
                time.sleep(5)
                continue

            for tar_file in tar_files:
                processing_tar_file = tar_file + '.processing'
                try:
                    # Attempt to atomically rename the tar file to mark it as being processed
                    os.rename(tar_file, processing_tar_file)
                    print(f'Worker {worker_id}: Processing {processing_tar_file}')
                except OSError:
                    # If renaming fails, another worker is processing this tar file
                    continue

                try:
                    with tarfile.open(processing_tar_file, 'r') as tar:
                        for member in tar:
                            if member.isfile() and member.name.lower().endswith('.jpg'):
                                try:
                                    file_obj = tar.extractfile(member)
                                    if file_obj is not None:
                                        img_bytes = file_obj.read()
                                        sample = {'jpg': img_bytes}
                                        yield sample
                                except Exception as img_e:
                                    print(f'Worker {worker_id}: Error reading {member.name} in {processing_tar_file}: {img_e}')

                    # After processing, remove the tar file to prevent re-processing
                    os.remove(processing_tar_file)
                    print(f'Worker {worker_id}: Removed {processing_tar_file}')
                except Exception as e:
                    print(f'Worker {worker_id}: Error processing {processing_tar_file}: {e}')
                    # Optionally, you can rename the file back or move it to a failed directory
                    continue

            # Brief pause before checking for new tar files
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
                    print(f'Error processing image: {e}')
