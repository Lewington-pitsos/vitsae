# variables.tf

# General Settings
variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (e.g., dev, prod)"
  type        = string
  default     = "production"
}

# S3 Bucket Variables
variable "bucket_name" {
  description = "Name of the S3 bucket for model outputs (must be globally unique)"
  type        = string
}

# SQS Queue Variables
variable "queue_name" {
  description = "Name of the SQS queue (must be unique within the region)"
  type        = string
}

variable "visibility_timeout" {
  description = "Visibility timeout in seconds"
  type        = number
  default     = 30
}

variable "message_retention" {
  description = "Message retention period in seconds"
  type        = number
  default     = 345600  # 4 days
}

variable "receive_wait_time" {
  description = "Receive wait time in seconds"
  type        = number
  default     = 0
}

variable "delay_seconds" {
  description = "Delay in seconds for messages"
  type        = number
  default     = 0
}

variable "file_ecr_url" {
  description = "Name of the ECR repository for Docker images"
  type        = string
}

variable "file_ecr_arn" {
  description = "Name of the ECR repository for Docker images"
  type        = string
}

# ECS Cluster Variables
variable "cluster_name" {
  description = "Name of the ECS cluster"
  type        = string
  default     = "ml-ecs-cluster"
}

variable "container_memory" {
  description = "Container memory in MB"
  type        = number
  default     = 4096
}

variable "container_cpu" {
  description = "Container CPU units"
  type        = number
  default     = 1024
}

variable "service_desired_count" {
  description = "Desired count of ECS service tasks"
  type        = number
  default     = 2
}

variable "tar_ecs_service_name" {
  description = "Name of the ECS service"
  type        = string
  default     = "tar-ecs-service"
}

# Auto Scaling Group Variables
variable "max_size" {
  description = "Maximum size of the Auto Scaling Group"
  type        = number
  default     = 5
}

variable "my_ip_cidr_block" {
  description = "Your IP CIDR block for SSH access (e.g., '203.0.113.0/24')"
  type        = string
}

variable "dynamodb_table_name" {
  description = "The name of the DynamoDB table for image hashes."
  type        = string
  default     = "laion-batches"
}

#### secert related #####


variable "hf_token" {
  description = "HF_TOKEN for ECS tasks"
  type        = string
  sensitive   = true
}

variable "aws_access_key" {
  description = "AWS_ACCESS_KEY for ECS tasks"
  type        = string
  sensitive   = true
}

variable "aws_secret" {
  description = "AWS_SECRET for ECS tasks"
  type        = string
  sensitive   = true
}



variable "die_now" {
  default = false
}


variable "tar_queue_name" {
  description = "Name of the SQS queue containing uploaded batches"
  type        = string
  default     = "tar-queue"
}

variable "activations_ecr_url" {
  description = "Name of the activations repository"
  type        = string
}

variable "activations_ecr_arn" {
  description = "ARN of the activations repository"
  type        = string
}

variable "act_tasks" {
  description = "Number of activations instances"
  type        = number
  default     = 0
}


# variable "train_tasks" {
#   description = "Number of activations instances"
#   type        = number
#   default     = 0
# }