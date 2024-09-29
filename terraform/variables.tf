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

variable "docker_image" {
  description = "Docker image URI for the ML task (e.g., ECR or Docker Hub)"
  type        = string
  default     = "" # Will be set dynamically
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

# EC2 Instance Variables
variable "instance_type" {
  description = "EC2 instance type (e.g., g4dn.xlarge for GPU instances)"
  type        = string
  default     = "g4dn.xlarge"
}

# Auto Scaling Group Variables
variable "max_size" {
  description = "Maximum size of the Auto Scaling Group"
  type        = number
  default     = 5
}

variable "min_size" {
  description = "Minimum size of the Auto Scaling Group"
  type        = number
  default     = 1
}

variable "desired_capacity" {
  description = "Desired capacity of the Auto Scaling Group"
  type        = number
  default     = 2
}

# Networking Variables
variable "vpc_id" {
  description = "VPC ID where resources will be deployed"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for the Auto Scaling Group and ECS service"
  type        = list(string)
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