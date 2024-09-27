# terraform.tfvars

# General Settings
region      = "us-east-1"
environment = "production"

# S3 Bucket Variables
bucket_name = "vit-sae-activations"

# SQS Queue Variables
queue_name           = "parquet-files-queue"
visibility_timeout   = 30
message_retention    = 345600
receive_wait_time    = 0
delay_seconds        = 0

# ECR Variables
ecr_repository_name  = "vit-sae-ecr-repo"

# ECS Cluster Variables
cluster_name          = "vit-sae-ecs-cluster"
docker_image          = "" # Will be set dynamically
container_memory      = 4096
container_cpu         = 1024
service_desired_count = 2

# EC2 Instance Variables
instance_type   = "g4dn.xlarge"
key_pair_name   = "my-ssh-key"
key_pair_public_key_path = "~/.ssh/id_sache.pub"# Path to your existing public key

# Auto Scaling Group Variables
max_size         = 5
min_size         = 1
desired_capacity = 2

# Networking Variables
vpc_id = "vpc-0123456789abcdef0"

subnet_ids = [
  "subnet-0123456789abcdef0",
  "subnet-0fedcba9876543210"
]

my_ip_cidr_block = "203.0.113.0/24"
