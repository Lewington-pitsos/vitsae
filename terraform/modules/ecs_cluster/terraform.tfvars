# AWS Region
region = "us-east-1"

# Name of the ECS cluster
cluster_name = "vit-sae-ecs-cluster"

# Environment (e.g., dev, prod)
environment = "production"

# Docker image for the ML task (e.g., "123456789012.dkr.ecr.us-east-1.amazonaws.com/my-ml-image:latest")
docker_image = "your-docker-image-uri"

# Container memory in MB
container_memory = 4096

# Container CPU units
container_cpu = 1024

# URL of the SQS queue
sqs_queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/parquet-files-queue"

# ARN of the SQS queue
sqs_queue_arn = "arn:aws:sqs:us-east-1:123456789012:parquet-files-queue"

# Name of the S3 bucket
s3_bucket_name = "vit-sae-activations"

# EC2 instance type (e.g., "g4dn.xlarge" for GPU instances)
instance_type = "g4dn.xlarge"

# Key pair name for SSH access
key_name = "my-ec2-keypair"

# Auto Scaling Group settings
max_size = 5
min_size = 1
desired_capacity = 2

# List of subnet IDs for the Auto Scaling Group (ensure these are in the same VPC)
subnet_ids = [
  "subnet-0123456789abcdef0",
  "subnet-0fedcba9876543210"
]

# VPC ID where the ECS cluster will be deployed
vpc_id = "vpc-0123456789abcdef0"

# Your IP CIDR block for SSH access (e.g., "203.0.113.0/24")
my_ip_cidr_block = "your-ip-cidr-block"

# Desired count of ECS service tasks
service_desired_count = 2
