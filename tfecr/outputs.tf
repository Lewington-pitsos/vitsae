output "ecr_repository_url" {
  description = "The URL of the ECR repository."
  value       = aws_ecr_repository.file_ecr.repository_url
}

output "ecr_repository_arn" {
  description = "The ARN of the ECR repository."
  value       = aws_ecr_repository.file_ecr.arn
}


output "ecr_activations_repository_url" {
  description = "The URL of the activations ECR repository."
  value       = aws_ecr_repository.activations_ecr.repository_url
}

output "ecr_activations_repository_arn" {
  description = "The ARN of the activations ECR repository."
  value       = aws_ecr_repository.activations_ecr.arn
}



output "ecr_training_repository_url" {
  description = "The URL of the training ECR repository."
  value       = aws_ecr_repository.training_ecr.repository_url
}

output "ecr_training_repository_arn" {
  description = "The ARN of the training ECR repository."
  value       = aws_ecr_repository.training_ecr.arn
}