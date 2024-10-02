import torch
from torch.utils.data import IterableDataset
import os
import time
import glob
import webdataset as wds

class StreamingDataset(IterableDataset):
    def __init__(self, data_dir):
        self.data_dir = data_dir

    def _get_tar_files(self):
        """Retrieve the list of .ready.tar files in the data directory."""
        tar_files = glob.glob(os.path.join(self.data_dir, '*.ready.tar'))
        tar_files.sort()
        return tar_files

    def __iter__(self):
        worker_info = torch.utils.data.get_worker_info()
        if worker_info is None:
            worker_id = 0
            num_workers = 1
        else:
            worker_id = worker_info.id
            num_workers = worker_info.num_workers

        while True:
            tar_files = self._get_tar_files()
            if not tar_files:
                time.sleep(5)
                continue

            # Create a WebDataset pipeline for each tar file
            for tar_file in tar_files:
                dataset = wds.WebDataset(tar_file).with_worker(worker_id, num_workers)
                for sample in dataset:
                    yield sample

