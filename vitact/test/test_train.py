import boto3
import pytest
from moto import mock_aws
from vitact.train import get_checkpoint_from_s3

# Mock data for the S3 setup
mock_bucket = 'sae-activations'
mock_prefix = 'log/CLIP-ViT-L-14/17_resid/'

@pytest.fixture
def s3_setup():
    # Setup mock S3 using moto
    with mock_aws():
        s3 = boto3.client('s3')
        s3.create_bucket(Bucket=mock_bucket)
        
        yield s3

def test_get_highest_checkpoint(s3_setup):
    # Add mock checkpoints to the S3 bucket
    s3_setup.put_object(Bucket=mock_bucket, Key='log/CLIP-ViT-L-14/17_resid/a/100.pth', Body=b'')
    s3_setup.put_object(Bucket=mock_bucket, Key='log/CLIP-ViT-L-14/17_resid/a/200.pth', Body=b'')
    s3_setup.put_object(Bucket=mock_bucket, Key='log/CLIP-ViT-L-14/17_resid/b/150.pth', Body=b'')

    # Test that the function returns the highest checkpoint based on n_tokens.
    checkpoint, n_tokens = get_checkpoint_from_s3(s3_setup, mock_bucket, mock_prefix)
    assert checkpoint == 'log/CLIP-ViT-L-14/17_resid/a/200.pth'
    assert n_tokens == 200

def test_reads_files_correctly(s3_setup):
    # Add a mock checkpoint to the S3 bucket
    s3_setup.put_object(Bucket=mock_bucket, Key='log/CLIP-ViT-L-14/17_resid/a/100.pth', Body=b'')

    # Test that the function reads files correctly from the S3 bucket.
    checkpoint, n_tokens = get_checkpoint_from_s3(s3_setup, mock_bucket, mock_prefix)
    assert checkpoint == 'log/CLIP-ViT-L-14/17_resid/a/100.pth'
    assert isinstance(n_tokens, int)
    assert n_tokens == 100

def test_no_checkpoints(s3_setup):
    # Test the case when there are no checkpoints in the S3 bucket.
    checkpoint, n_tokens = get_checkpoint_from_s3(s3_setup, mock_bucket, mock_prefix)
    assert checkpoint is None
    assert n_tokens == 0
