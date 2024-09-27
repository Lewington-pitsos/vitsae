output "bucket_name" {
  description = "The name of the S3 bucket"
  value       = aws_s3_bucket.vit-sae-activations.id
}
