variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Name of the ECS cluster"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "docker_image" {
  description = "Docker image for the ML task"
  type        = string
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

variable "sqs_queue_url" {
  description = "URL of the SQS queue"
  type        = string
}

variable "sqs_queue_arn" {
  description = "ARN of the SQS queue"
  type        = string
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "g4dn.xlarge"
}

variable "key_name" {
  description = "Key pair name for SSH access"
  type        = string
}

variable "max_size" {
  description = "Max size of Auto Scaling Group"
  type        = number
  default     = 5
}

variable "min_size" {
  description = "Min size of Auto Scaling Group"
  type        = number
  default     = 1
}

variable "desired_capacity" {
  description = "Desired capacity of Auto Scaling Group"
  type        = number
  default     = 2
}

variable "subnet_ids" {
  description = "List of subnet IDs for the Auto Scaling Group"
  type        = list(string)
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "my_ip_cidr_block" {
  description = "Your IP CIDR block for SSH access"
  type        = string
}

variable "service_desired_count" {
  description = "Desired count of ECS service tasks"
  type        = number
  default     = 2
}
