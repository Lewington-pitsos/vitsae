provider "aws" {
  region = var.region
}

resource "aws_sqs_queue" "parquet_file_queue" {
  name                        = var.queue_name
  visibility_timeout_seconds  = var.visibility_timeout
  message_retention_seconds   = var.message_retention
  receive_wait_time_seconds   = var.receive_wait_time
  delay_seconds               = var.delay_seconds

  tags = {
    Name        = "Parquet Files Queue"
    Environment = var.environment
  }
}
