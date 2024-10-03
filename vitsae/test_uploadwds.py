import os
import tarfile
from uploadwds import make_tarfile
from PIL import Image
import pytest

def create_test_files(directory, prefix, num_files):
    os.makedirs(directory, exist_ok=True)
    for i in range(num_files // 2):
        with open(os.path.join(directory, f'{prefix}_{i}.json'), 'w') as f:
            f.write('{}')
        with open(os.path.join(directory, f'{prefix}_{i}.jpg'), 'wb') as f:
            img = Image.new('RGB', (100, 100), color='white')
            img.save(f, 'JPEG')
    with open(os.path.join(directory, f'{prefix}_invalid.jpg'), 'w') as f:
        f.write('Not a valid image')
    with open(os.path.join(directory, f'{prefix}_badpair.json'), 'w') as f:
        f.write('{}')
    with open(os.path.join(directory, f'{prefix}_badpair.jpg'), 'w') as f:
        f.write('Corrupted image data')

@pytest.fixture
def setup_test_directory(tmp_path):
    test_dir = tmp_path / 'laion_files'
    prefix = 'test_prefix'
    create_test_files(test_dir, prefix, 36)
    yield str(test_dir), prefix
    for item in test_dir.iterdir():
        item.unlink()
    test_dir.rmdir()

def test_make_tarfile_correct_files(setup_test_directory):
    test_dir, prefix = setup_test_directory
    tar_filename, files_to_bundle = make_tarfile(test_dir, prefix)
    assert os.path.exists(tar_filename)
    with tarfile.open(tar_filename, 'r') as tar:
        tar_contents = tar.getnames()
        assert len(tar_contents) == 36
        json_files = [f for f in tar_contents if f.endswith('.json')]
        jpg_files = [f for f in tar_contents if f.endswith('.jpg')]
        assert len(json_files) == len(jpg_files)
    os.remove(tar_filename)

def test_make_tarfile_invalid_jpg(setup_test_directory):
    test_dir, prefix = setup_test_directory
    invalid_jpg_path = os.path.join(test_dir, f'{prefix}_invalid.jpg')
    with open(invalid_jpg_path, 'w') as f:
        f.write('invalid image data')

    tar_filename, files_to_bundle = make_tarfile(test_dir, prefix)
    assert os.path.exists(tar_filename)
    with tarfile.open(tar_filename, 'r') as tar:
        tar_contents = tar.getnames()
        assert f'{prefix}_invalid.jpg' not in tar_contents
        assert len(tar_contents) == 36
    os.remove(tar_filename)

def test_make_tarfile_no_files(tmp_path):
    test_dir = tmp_path / 'empty_dir'
    test_dir.mkdir()
    prefix = 'test_prefix'
    tar_filename, _ = make_tarfile(str(test_dir), prefix)
    assert tar_filename is None

def test_make_tarfile_partial_files(tmp_path):
    test_dir = tmp_path / 'partial_files'
    test_dir.mkdir()
    prefix = 'test_prefix'
    for i in range(5):
        with open(os.path.join(test_dir, f'{prefix}_{i}.json'), 'w') as f:
            f.write('{}')

    tar_filename, files_to_bundle = make_tarfile(str(test_dir), prefix)
    assert os.path.exists(tar_filename)
    with tarfile.open(tar_filename, 'r') as tar:
        tar_contents = tar.getnames()
        assert len(tar_contents) == 5
    os.remove(tar_filename)

def test_make_tarfile_bad_pair(setup_test_directory):
    test_dir, prefix = setup_test_directory
    tar_filename, files_to_bundle = make_tarfile(test_dir, prefix)
    assert os.path.exists(tar_filename)
    with tarfile.open(tar_filename, 'r') as tar:
        tar_contents = tar.getnames()
        assert f'{prefix}_badpair.json' not in tar_contents
        assert f'{prefix}_badpair.jpg' not in tar_contents
    os.remove(tar_filename)
