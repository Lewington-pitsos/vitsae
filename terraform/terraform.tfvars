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
# instance_type   = "g4dn.xlarge"
instance_type   = "t3.micro"

# Auto Scaling Group Variables
max_size         = 0
min_size         = 0
desired_capacity = 0

# Networking Variables
vpc_id = "vpc-02bea51ed45afd15c"

subnet_ids = [
  "subnet-0d9bd4ef7047caea2",
]

my_ip_cidr_block = "172.31.80.0/20"