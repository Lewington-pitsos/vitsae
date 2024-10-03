from tardataset import StreamingDataset
from PIL import Image
import io
import webdataset as wds

def test_loads_tar():
    dataset = StreamingDataset('test/tars')

    for sample in dataset:
        image_data = sample['jpg']
        print(sample.keys())
        assert 'jpg' in sample

        try:        # check that we can load the jpg with pil
            image = Image.open(io.BytesIO(image_data))
        except Exception as e:
            print(type(e), e)
            print(type(image_data))  # Should be 'bytes'
            print(len(image_data))   # Should be greater than 0

            # Check the first few bytes to inspect the file signature (magic number)
            print(image_data[:10])  # This gives a hint about the file format