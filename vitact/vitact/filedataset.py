import io
import os
import hashlib
import torch
from torch.utils.data import IterableDataset
from torchvision.io import read_image, ImageReadMode
from PIL import Image
import torchvision.transforms as transforms

class FileDataset(IterableDataset):
    def __init__(self, root_dir):
        self.root_dir = root_dir

    def _get_image_paths(self):
        for folder in os.listdir(self.root_dir):
            folder_path = os.path.join(self.root_dir, folder)
            if os.path.isdir(folder_path):
                for file_name in os.listdir(folder_path):
                    if file_name.endswith('.jpg'):
                        yield os.path.join(folder_path, file_name)

    def _get_image_data(self, image_path):
        return read_image(image_path, mode=ImageReadMode.RGB)

    def _worker_iter(self, worker_id, num_workers):
        for img_path in self._get_image_paths():
            hash_val = int(hashlib.sha1(img_path.encode('utf-8')).hexdigest(), 16)
            if hash_val % num_workers == worker_id:
                try:
                    yield self._get_image_data(img_path)
                except Exception as e:
                    print(f'Error reading image {img_path}: {e}')

    def __iter__(self):
        worker_info = torch.utils.data.get_worker_info()
        if worker_info is None:
            for img_path in self._get_image_paths():
                try:
                    yield self._get_image_data(img_path)
                except Exception as e:
                    print(f'Error reading image {img_path}: {e}')
                
        else:
            worker_id = worker_info.id
            num_workers = worker_info.num_workers
            yield from self._worker_iter(worker_id, num_workers)

class FilePathDataset(FileDataset):
    def _get_image_data(self, image_path):
        return image_path, read_image(image_path, mode=ImageReadMode.RGB)

class PILDataset(FileDataset):
    def _get_image_data(self, image_path):
        with Image.open(image_path) as pil_img:
            pil_img.load()
            return image_path, pil_img

class FloatFilePathDataset(FileDataset):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.transform = transforms.ToTensor()

    def _get_image_data(self, image_path):
        with open(image_path, 'rb') as f:
            image = Image.open(io.BytesIO(f.read())).convert('RGB')
            image = image.resize((224, 224))
            image_tensor = self.transform(image)

        return image_path, image_tensor

# if __name__ == '__main__':
#     from torch.utils.data import DataLoader
#     ds = PILDataset('../cruft/bench')
#     batch_size = 5
#     dataloader = DataLoader(ds, batch_size=batch_size, shuffle=False, num_workers=3, collate_fn=lambda x: [[y[0] for y in x], [y[1] for y in x]])

#     for x in dataloader:
#         print(x)
#         break