provider "aws" {
  region = var.region
}

resource "aws_s3_bucket" "vit-sae-activations" {
  bucket = var.bucket_name
  acl    = "private"

  versioning {
    enabled = true
  }

  tags = {
    Name        = "Model Outputs Bucket"
    Environment = var.environment
  }
}
