# outputs.tf

# S3 Bucket Output
output "s3_bucket_name" {
  description = "Name of the S3 bucket for model outputs"
  value       = aws_s3_bucket.model_outputs.bucket
}

# SQS Queue Outputs
output "sqs_queue_url" {
  description = "URL of the SQS queue"
  value       = aws_sqs_queue.parquet_file_queue.url
}

output "sqs_queue_arn" {
  description = "ARN of the SQS queue"
  value       = aws_sqs_queue.parquet_file_queue.arn
}

# ECS Cluster Outputs
output "ecs_cluster_id" {
  description = "ID of the ECS cluster"
  value       = aws_ecs_cluster.activation_cluster.id
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.tar_service.name
}

output "ecs_task_definition" {
  description = "ARN of the ECS task definition"
  value       = aws_ecs_task_definition.tar_create_task.arn
}

output "ecs_autoscaling_group_name" {
  description = "Name of the ECS Auto Scaling Group"
  value       = aws_autoscaling_group.ecs_autoscaling_group.name
}