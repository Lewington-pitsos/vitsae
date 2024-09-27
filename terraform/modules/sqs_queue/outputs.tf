output "queue_url" {
  description = "URL of the SQS queue"
  value       = aws_sqs_queue.parquet_file_queue.url
}

output "queue_arn" {
  description = "ARN of the SQS queue"
  value       = aws_sqs_queue.parquet_file_queue.arn
}
