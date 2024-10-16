provider "aws" {
  region = var.region
}


#######################################
# 0. VPC and Subnet Configuration
#######################################

# Create VPC
resource "aws_vpc" "ml_vpc" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "${var.environment}-vpc"
  }
}

# Create Subnets
resource "aws_subnet" "public_subnet" {
  vpc_id     = aws_vpc.ml_vpc.id
  cidr_block = "10.0.1.0/24"
  availability_zone = "${var.region}a"

  map_public_ip_on_launch = true

  tags = {
    Name = "${var.environment}-public-subnet"
  }
}

resource "aws_subnet" "private_subnet" {
  vpc_id     = aws_vpc.ml_vpc.id
  cidr_block = "10.0.2.0/24"
  availability_zone = "${var.region}a"

  tags = {
    Name = "${var.environment}-private-subnet"
  }
}

resource "aws_subnet" "private_subnet_b" {
  vpc_id     = aws_vpc.ml_vpc.id
  cidr_block = "10.0.3.0/24"
  availability_zone = "${var.region}b"

  tags = {
    Name = "${var.environment}-private-subnet"
  }
}

resource "aws_subnet" "private_subnet_c" {
  vpc_id     = aws_vpc.ml_vpc.id
  cidr_block = "10.0.4.0/24"
  availability_zone = "${var.region}c"

  tags = {
    Name = "${var.environment}-private-subnet"
  }
}

# Create Internet Gateway for the public subnet
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.ml_vpc.id

  tags = {
    Name = "${var.environment}-igw"
  }
}

resource "aws_vpc_endpoint" "s3_endpoint" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"

  route_table_ids = [
    aws_route_table.private_rt.id,
    aws_route_table.private_rt_b.id,
    aws_route_table.private_rt_c.id,
  ]

  tags = {
    Name = "${var.environment}-s3-endpoint"
  }
}


resource "aws_eip" "nat_eip" {
  domain = "vpc"
}

resource "aws_nat_gateway" "nat_gw" {
  allocation_id = aws_eip.nat_eip.id
  subnet_id     = aws_subnet.public_subnet.id

  tags = {
    Name = "${var.environment}-nat-gw"
  }
}

# Create Public Route Table
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.ml_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "${var.environment}-public-rt"
  }
}

# Associate Public Subnet with Public Route Table
resource "aws_route_table_association" "public_rt_assoc" {
  subnet_id      = aws_subnet.public_subnet.id
  route_table_id = aws_route_table.public_rt.id
}

# Create Private Route Table
resource "aws_route_table" "private_rt" {
  vpc_id = aws_vpc.ml_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat_gw.id
  }

  tags = {
    Name = "${var.environment}-private-rt"
  }
}

# Associate Private Subnet with Private Route Table
resource "aws_route_table_association" "private_rt_assoc" {
  subnet_id      = aws_subnet.private_subnet.id
  route_table_id = aws_route_table.private_rt.id
}

resource "aws_route_table_association" "private_rt_assoc_b" {
  subnet_id      = aws_subnet.private_subnet_b.id
  route_table_id = aws_route_table.private_rt.id
}

resource "aws_route_table_association" "private_rt_assoc_c" {
  subnet_id      = aws_subnet.private_subnet_c.id
  route_table_id = aws_route_table.private_rt.id
}

#######################################
# 1. S3 Bucket for Model Outputs
#######################################

resource "aws_s3_bucket" "model_outputs" {
  bucket = var.bucket_name

  tags = {
    Name        = "Tar Files Bucket"
    Environment = var.environment
  }

  force_destroy = true
}

#######################################
# 2. SQS Queue for Parquet File URLs
#######################################

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

resource "aws_sqs_queue" "tar_file_queue" {
  name                        = var.tar_queue_name
  visibility_timeout_seconds  = var.visibility_timeout
  message_retention_seconds   = var.message_retention
  receive_wait_time_seconds   = var.receive_wait_time
  delay_seconds               = var.delay_seconds

  tags = {
    Name        = "Tar File Queue"
    Environment = var.environment
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "activation_cluster" {
  name = var.cluster_name

  tags = {
    Name        = "ML ECS Cluster"
    Environment = var.environment
  }
}


resource "aws_ecs_cluster_capacity_providers" "activation_cluster_capacity_providers" {
  cluster_name = aws_ecs_cluster.activation_cluster.name

  capacity_providers = [
    aws_ecs_capacity_provider.ecs_capacity_provider.name,
    aws_ecs_capacity_provider.activations_capacity_provider.name
  ]

  default_capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.ecs_capacity_provider.name
    weight            = 1
    base              = 0
  }
}

# IAM Roles and Policies

## IAM Role for ECS Task Execution
resource "aws_iam_role" "ecs_interface_role" {
  name = "ecsInterfaceRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "ecs_interface_role_policy_attachment" {
  role       = aws_iam_role.ecs_interface_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

## Custom IAM Policy for S3, SQS, ECR, and Parameter Store Access
resource "aws_iam_policy" "ecs_task_policy" {
  name        = "ecsTaskPolicy"
  description = "Policy for ECS tasks to access S3, SQS, ECR, and Parameter Store"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = ["s3:GetObject", "s3:PutObject"]
        Effect   = "Allow"
        Resource = [
          aws_s3_bucket.model_outputs.arn,
          "${aws_s3_bucket.model_outputs.arn}/*"
        ]
      },
      {
        Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
        Effect   = "Allow"
        Resource = aws_sqs_queue.parquet_file_queue.arn
      },
      {
        Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
        Effect   = "Allow"
        Resource = aws_sqs_queue.tar_file_queue.arn
      },
      {
        Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
        Effect   = "Allow"
        Resource = aws_sqs_queue.training_config_queue.arn
      },
      {
        Action   = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ]
        Effect   = "Allow"
        Resource = var.file_ecr_arn
      },
      {
        Action   = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ]
        Effect   = "Allow"
        Resource = var.activations_ecr_arn
      },
      {
        Action   = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ]
        Effect   = "Allow"
        Resource = var.training_ecr_arn
      },
      {
        Action   = "ecr:GetAuthorizationToken"
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Action   = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem"
        ]
        Effect   = "Allow"
        Resource = aws_dynamodb_table.laion_batches.arn
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameters",
          "ssm:GetParameter",
          "ssm:GetParameterHistory",
          "kms:Decrypt"
        ]
        Resource = [
          aws_ssm_parameter.hf_token.arn,
          aws_ssm_parameter.aws_access_key.arn,
          aws_ssm_parameter.aws_secret.arn,
          aws_ssm_parameter.parquet_file_queue_url.arn,
          aws_ssm_parameter.tar_file_queue_url.arn,
          aws_ssm_parameter.tarfiles_bucket_name.arn,
          aws_ssm_parameter.activations_bucket_name.arn,
          aws_ssm_parameter.table_name.arn,
          aws_ssm_parameter.ecs_cluster_name.arn,    
          aws_ssm_parameter.ecs_service_name.arn,        
          aws_ssm_parameter.wandb_api_key.arn,
          aws_ssm_parameter.training_config_queue_url.arn
        ]
      },
      {
        Effect   = "Allow"
        Action   = [
          "kms:Decrypt"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_policy_attachment" {
  role       = aws_iam_role.ecs_interface_role.name
  policy_arn = aws_iam_policy.ecs_task_policy.arn
}

## IAM Role for ECS Instances
resource "aws_iam_role" "ecs_instance_role" {
  name = "ecsInstanceRole2"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Environment = var.environment
  }
}

resource "aws_iam_role_policy_attachment" "ecs_instance_role_policy_attachment" {
  role       = aws_iam_role.ecs_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
}

resource "aws_iam_instance_profile" "ecs_instance_profile" {
  name = "ecsInstanceProfile"
  role = aws_iam_role.ecs_instance_role.name
}


resource "aws_security_group" "ecs_security_group" {
  name        = "${var.environment}-ecs-sg"
  description = "Allow necessary traffic for ECS instances"
  vpc_id      = aws_vpc.ml_vpc.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr_block]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Environment = var.environment
  }
}
# Data Source for ECS Optimized AMI
data "aws_ami" "ecs_optimized" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-ecs-hvm-*-x86_64-ebs"]
  }
}

# Launch Template for EC2 Instances with Spot Market Options
resource "aws_launch_template" "ecs_launch_template" {
  name_prefix   = "ecs-launch-template-"
  image_id      = data.aws_ami.ecs_optimized.id

  iam_instance_profile {
    name = aws_iam_instance_profile.ecs_instance_profile.name
  }

  instance_market_options {
    market_type = "spot"
  }

  network_interfaces {
    associate_public_ip_address = true
    delete_on_termination       = true
    security_groups             = [aws_security_group.ecs_security_group.id]
  }

  user_data = base64encode(<<EOF
#!/bin/bash
echo ECS_CLUSTER=${aws_ecs_cluster.activation_cluster.name} >> /etc/ecs/ecs.config
EOF
)

  block_device_mappings {
    device_name = data.aws_ami.ecs_optimized.root_device_name

    ebs {
      volume_size           = 150
      delete_on_termination = true
    }
  }

  tag_specifications {
    resource_type = "instance"

    tags = {
      Name        = "ECS Instance"
      Environment = var.environment
    }
  }
}

resource "aws_autoscaling_group" "ecs_autoscaling_group" {
  name             = "ecs-autoscaling-group"
  max_size         = var.max_size          # Set as appropriate
  min_size         = 0                     # Allow scaling down to zero
  desired_capacity = 0
  protect_from_scale_in = false

  mixed_instances_policy {
    launch_template {
      launch_template_specification {
        launch_template_id = aws_launch_template.ecs_launch_template.id
        version            = "$Latest"
      }

      override {
        instance_type = "m4.large"
      }
      override {
        instance_type = "m4.xlarge"
      }

      override {
        instance_type = "t3.medium"
      }

      override {
        instance_type = "t3.large"
      }
    }

    instances_distribution {
      on_demand_percentage_above_base_capacity = 0
      spot_allocation_strategy                 = "lowest-price"
      spot_instance_pools                      = 3
    }

  }

  vpc_zone_identifier = [
    aws_subnet.private_subnet.id, # a
    aws_subnet.private_subnet_b.id,
    aws_subnet.private_subnet_c.id,
  ]

  initial_lifecycle_hook {
    name                 = "ecs-managed-draining-termination-hook"
    default_result       = "CONTINUE"
    heartbeat_timeout    = 120
    lifecycle_transition = "autoscaling:EC2_INSTANCE_TERMINATING"
  }

  tag {
    key                 = "Name"
    value               = "ECS Instance"
    propagate_at_launch = true
  }

  tag {
    key                 = "Environment"
    value               = var.environment
    propagate_at_launch = true
  }

  tag {
    key                 = "AmazonECSManaged"
    value               = true
    propagate_at_launch = true
  }

}


resource "aws_ecs_capacity_provider" "ecs_capacity_provider" {
  name = "${var.environment}-capacity-provider"

  auto_scaling_group_provider {
    auto_scaling_group_arn         = aws_autoscaling_group.ecs_autoscaling_group.arn
    managed_draining = "DISABLED"
    managed_termination_protection = "DISABLED" 

    managed_scaling {
      status = var.die_now ? "DISABLED" : "ENABLED"
      target_capacity           = 100
      minimum_scaling_step_size = 1
      maximum_scaling_step_size = 1000
    }
  }

  tags = {
    Environment = var.environment
  }
}

resource "aws_ecs_task_definition" "tar_create_task" {
  family                   = "tar_create"
  network_mode             = "awsvpc"
  requires_compatibilities = ["EC2"]
  execution_role_arn       = aws_iam_role.ecs_interface_role.arn
  task_role_arn            = aws_iam_role.ecs_interface_role.arn

  container_definitions = jsonencode([
    {
      name      = "ml-container"
      image     = "${var.file_ecr_url}:latest"
      essential = true
      memory    = var.container_memory
      cpu       = var.container_cpu
      stop_timeout = 60
      secrets = [
        {
          name      = "HF_TOKEN"
          valueFrom = aws_ssm_parameter.hf_token.arn
        },
        {
          name      = "AWS_ACCESS_KEY"
          valueFrom = aws_ssm_parameter.aws_access_key.arn
        },
        {
          name      = "AWS_SECRET"
          valueFrom = aws_ssm_parameter.aws_secret.arn
        },
        {
          name      = "SQS_QUEUE_URL"
          valueFrom = aws_ssm_parameter.parquet_file_queue_url.arn
        },
        {
          name      = "SQS_TAR_QUEUE_URL"
          valueFrom = aws_ssm_parameter.tar_file_queue_url.arn
        },
        {
          name      = "S3_BUCKET_NAME"
          valueFrom = aws_ssm_parameter.tarfiles_bucket_name.arn
        },
        {
          name      = "S3_ACTIVATIONS_BUCKET_NAME"
          valueFrom = aws_ssm_parameter.activations_bucket_name.arn
        },
        {
          name      = "TABLE_NAME"
          valueFrom = aws_ssm_parameter.table_name.arn
        },
        {
          name      = "ECS_CLUSTER_NAME"
          valueFrom = aws_ssm_parameter.ecs_cluster_name.arn
        },
        {
          name      = "ECS_SERVICE_NAME"
          valueFrom = aws_ssm_parameter.ecs_service_name.arn
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/ml-task"
          awslogs-region        = var.region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = {
    Name        = "ML Task Definition"
    Environment = var.environment
  }
}

# CloudWatch Log Group for ECS Tasks
resource "aws_cloudwatch_log_group" "ecs_log_group" {
  name              = "/ecs/ml-task"
  retention_in_days = 7

  tags = {
    Environment = var.environment
  }
}


# Update ECS Service Configuration to Use New Subnets
resource "aws_ecs_service" "tar_service" {
  name            = var.tar_ecs_service_name
  cluster         = aws_ecs_cluster.activation_cluster.id
  task_definition = aws_ecs_task_definition.tar_create_task.arn
  desired_count   = var.die_now ? 0 : var.service_desired_count

  capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.ecs_capacity_provider.name
    weight            = 1
    base              = 0
  }

  network_configuration {
    subnets         = [aws_subnet.private_subnet.id]
    security_groups = [aws_security_group.ecs_security_group.id]
  }

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 85

  tags = {
    Environment = var.environment
  }

  depends_on = [
    aws_cloudwatch_log_group.ecs_log_group,
    aws_iam_role.ecs_instance_role,
    aws_iam_role.ecs_interface_role,
    aws_iam_role_policy_attachment.ecs_instance_role_policy_attachment,
    aws_iam_role_policy_attachment.ecs_interface_role_policy_attachment,
    aws_iam_instance_profile.ecs_instance_profile,
    aws_iam_policy.ecs_task_policy,
  ]
}

resource "aws_dynamodb_table" "laion_batches" {
  name           = var.dynamodb_table_name
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "parquet_id"
  range_key      = "batch_id"

  attribute {
    name = "batch_id"
    type = "S"
  }

  attribute {
    name = "parquet_id"
    type = "S"
  }

  tags = {
    Name        = "ImageHashesTable"
    Environment = var.environment
  }
}

#######################################
# 6. Parameter Store for Sensitive Env Vars
#######################################

resource "aws_ssm_parameter" "hf_token" {
  name        = "${var.environment}-hf-token"
  description = "HF_TOKEN for ECS tasks"
  type        = "SecureString"
  value       = var.hf_token

  tags = {
    Environment = var.environment
    Name        = "HF_TOKEN Secret"
  }
}

resource "aws_ssm_parameter" "aws_access_key" {
  name        = "${var.environment}-aws-access-key"
  description = "AWS_ACCESS_KEY for ECS tasks"
  type        = "SecureString"
  value       = var.aws_access_key

  tags = {
    Environment = var.environment
    Name        = "AWS_ACCESS_KEY Secret"
  }
}

resource "aws_ssm_parameter" "aws_secret" {
  name        = "${var.environment}-aws-secret"
  description = "AWS_SECRET for ECS tasks"
  type        = "SecureString"
  value       = var.aws_secret

  tags = {
    Environment = var.environment
    Name        = "AWS_SECRET Secret"
  }
}

# If storing non-sensitive variables as parameters
resource "aws_ssm_parameter" "parquet_file_queue_url" {
  name        = "${var.environment}-sqs-queue-url"
  description = "SQS_QUEUE_URL for ECS tasks"
  type        = "String"
  value       = aws_sqs_queue.parquet_file_queue.url

  tags = {
    Environment = var.environment
    Name        = "SQS_QUEUE_URL Parameter"
  }
}


resource "aws_ssm_parameter" "tar_file_queue_url" {
  name        = "${var.environment}-sqs-tar-queue-url"
  description = "SQS_TAR_QUEUE_URL for ECS tasks"
  type        = "String"
  value       = aws_sqs_queue.tar_file_queue.url

  tags = {
    Environment = var.environment
    Name        = "SQS_TAR_QUEUE_URL Parameter"
  }
}

resource "aws_ssm_parameter" "tarfiles_bucket_name" {
  name        = "${var.environment}-s3-bucket-name"
  description = "S3_BUCKET_NAME for ECS tasks"
  type        = "String"
  value       = aws_s3_bucket.model_outputs.bucket

  tags = {
    Environment = var.environment
    Name        = "S3_BUCKET_NAME Parameter"
  }
}

resource "aws_ssm_parameter" "activations_bucket_name" {
  name        = "${var.environment}-s3-activation-bucket-name"
  description = "S3_BUCKET_NAME for storing output activations"
  type        = "String"
  value       = "sae-activations"

  tags = {
    Environment = var.environment
    Name        = "S3_ACTIVATIONS_BUCKET_NAME Parameter"
  }
}

resource "aws_ssm_parameter" "table_name" {
  name        = "${var.environment}-table-name"
  description = "TABLE_NAME for ECS tasks"
  type        = "String"
  value       = aws_dynamodb_table.laion_batches.name

  tags = {
    Environment = var.environment
    Name        = "TABLE_NAME Parameter"
  }
}

resource "aws_ssm_parameter" "ecs_cluster_name" {
  name        = "${var.environment}-ecs-cluster-name"
  description = "ECS_CLUSTER_NAME for ECS tasks"
  type        = "String"
  value       = aws_ecs_cluster.activation_cluster.name

  tags = {
    Environment = var.environment
    Name        = "ECS_CLUSTER_NAME Parameter"
  }
}

resource "aws_ssm_parameter" "ecs_service_name" {
  name        = "${var.environment}-ecs-service-name"
  description = "ECS_SERVICE_NAME for ECS tasks"
  type        = "String"
  value       = var.tar_ecs_service_name

  tags = {
    Environment = var.environment
    Name        = "ECS_SERVICE_NAME Parameter"
  }
}










# ------------------------- ACTIVATION GENERATION ---------------------------


resource "aws_ecs_task_definition" "activations_service_task" {
  family                   = "activations-service"
  network_mode             = "awsvpc"
  requires_compatibilities = ["EC2"]
  execution_role_arn       = aws_iam_role.ecs_interface_role.arn
  task_role_arn            = aws_iam_role.ecs_interface_role.arn

  container_definitions = jsonencode([
    {
      name      = "activations-container"
      image     = "${var.activations_ecr_url}:latest"
      essential = true
      memory    = 31500  # Adjust as needed
      cpu       = 4096  # Adjust as needed
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/activations-service"
          awslogs-region        = var.region
          awslogs-stream-prefix = "ecs"
        }
      },
      secrets = [
        {
          name      = "HF_TOKEN"
          valueFrom = aws_ssm_parameter.hf_token.arn
        },
        {
          name      = "AWS_ACCESS_KEY"
          valueFrom = aws_ssm_parameter.aws_access_key.arn
        },
        {
          name      = "AWS_SECRET"
          valueFrom = aws_ssm_parameter.aws_secret.arn
        },
        {
          name      = "SQS_QUEUE_URL"
          valueFrom = aws_ssm_parameter.parquet_file_queue_url.arn
        },
        {
          name      = "SQS_TAR_QUEUE_URL"
          valueFrom = aws_ssm_parameter.tar_file_queue_url.arn
        },
        {
          name      = "S3_BUCKET_NAME"
          valueFrom = aws_ssm_parameter.tarfiles_bucket_name.arn
        },
        {
          name      = "S3_ACTIVATIONS_BUCKET_NAME"
          valueFrom = aws_ssm_parameter.activations_bucket_name.arn
        },
        {
          name      = "TABLE_NAME"
          valueFrom = aws_ssm_parameter.table_name.arn
        },
        {
          name      = "ECS_CLUSTER_NAME"
          valueFrom = aws_ssm_parameter.ecs_cluster_name.arn
        },
        {
          name      = "ECS_SERVICE_NAME"
          valueFrom = aws_ssm_parameter.ecs_service_name.arn
        }
      ],
      linuxParameters = {
        sharedMemorySize = 15500
      }
      resourceRequirements = [
        {
          type  = "GPU"
          value = "1"  # Adjust the number of GPUs as needed
        }
      ]
    }
  ])

  tags = {
    Name        = "Activations Generation Service Task Definition"
    Environment = var.environment
  }
}


resource "aws_cloudwatch_log_group" "activations_service_log_group" {
  name              = "/ecs/activations-service"
  retention_in_days = 7

  tags = {
    Environment = var.environment
  }
}


resource "aws_ecs_service" "activations_service" {
  name            = "activations-service"
  cluster         = aws_ecs_cluster.activation_cluster.id
  task_definition = aws_ecs_task_definition.activations_service_task.arn
  desired_count   = var.act_tasks

  capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.activations_capacity_provider.name
    weight            = 1
    base              = 0
  }

  network_configuration {
    subnets         = [
      aws_subnet.private_subnet.id,
      aws_subnet.private_subnet_b.id,
      aws_subnet.private_subnet_c.id,
    ]
    security_groups = [aws_security_group.ecs_security_group.id]
  }

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100

  tags = {
    Environment = var.environment
  }

  depends_on = [
    aws_cloudwatch_log_group.activations_service_log_group,
    aws_iam_role.ecs_instance_role,
    aws_iam_role.ecs_interface_role,
    aws_iam_role_policy_attachment.ecs_instance_role_policy_attachment,
    aws_iam_role_policy_attachment.ecs_interface_role_policy_attachment,
    aws_iam_instance_profile.ecs_instance_profile,
    aws_iam_policy.ecs_task_policy,
  ]
}


resource "aws_launch_template" "activations_launch_template" {
  name_prefix   = "activations-launch-template"
  image_id      = "ami-0757fc38223742869"
  # https://aws.amazon.com/releasenotes/aws-deep-learning-base-ami-amazon-linux-2/
  # CUDA version 12.4
  # Nvidia driver version  550.90.12 

  instance_type = "g6e.xlarge"  
  iam_instance_profile {
    name = aws_iam_instance_profile.ecs_instance_profile.name
  }

  instance_market_options {
    market_type = "spot"
  }

  network_interfaces {
    associate_public_ip_address = true
    delete_on_termination       = true
    security_groups             = [aws_security_group.ecs_security_group.id]
  }

  user_data = base64encode(<<EOF
#!/bin/bash
echo ECS_CLUSTER=${aws_ecs_cluster.activation_cluster.name} >> /etc/ecs/ecs.config
EOF
)

   block_device_mappings {
    device_name = "/dev/xvda"

    ebs {
      volume_size           = 250
      delete_on_termination = true
    }
  }

  tag_specifications {
    resource_type = "instance"

    tags = {
      Name        = "Activations Service Instance"
      Environment = var.environment
    }
  }
}

resource "aws_ecs_capacity_provider" "activations_capacity_provider" {
  name = "${var.environment}-activatons-capacity-provider"

  auto_scaling_group_provider {
    auto_scaling_group_arn         = aws_autoscaling_group.activations_autoscaling_group.arn
    managed_scaling {
      status                      = "ENABLED"
      target_capacity             = 100
      minimum_scaling_step_size   = 1
      maximum_scaling_step_size   = 1000
    }
  }

  tags = {
    Environment = var.environment
  }
}



resource "aws_autoscaling_group" "activations_autoscaling_group" {
  name             = "activations-autoscaling-group"
  max_size         = 4          # Set as appropriate
  min_size         = 0                     # Allow scaling down to zero
  desired_capacity = max(var.act_tasks, var.train_tasks)
  protect_from_scale_in = false

  wait_for_capacity_timeout  = "0"


  launch_template {
    id      = aws_launch_template.activations_launch_template.id
    version = "$Latest"
  }
  

  vpc_zone_identifier = [
        aws_subnet.private_subnet.id, # a
        aws_subnet.private_subnet_b.id,
        aws_subnet.private_subnet_c.id,
  ]

  initial_lifecycle_hook {
    name                 = "ecs-managed-draining-termination-hook"
    default_result       = "CONTINUE"
    heartbeat_timeout    = 120
    lifecycle_transition = "autoscaling:EC2_INSTANCE_TERMINATING"
  }

  tag {
    key                 = "Name"
    value               = "ECS Instance"
    propagate_at_launch = true
  }

  tag {
    key                 = "Environment"
    value               = var.environment
    propagate_at_launch = true
  }

  tag {
    key                 = "AmazonECSManaged"
    value               = true
    propagate_at_launch = true
  }

}







# ------------------------ TRAINING ----------------------------


resource "aws_ssm_parameter" "training_config_queue_url" {
  name        = "${var.environment}-sqs-training-config-queue-url"
  description = "training config queue url"
  type        = "String"
  value       = aws_sqs_queue.training_config_queue.url

  tags = {
    Environment = var.environment
    Name        = "training config queue url Parameter"
  }
}


resource "aws_ssm_parameter" "wandb_api_key" {
  name        = "${var.environment}-wandb-api-key"
  description = "wanb api key"
  type        = "SecureString"
  value       = var.wandb_api_key

  tags = {
    Environment = var.environment
    Name        = "ECS_SERVICE_NAME Parameter"
  }
}


resource "aws_sqs_queue" "training_config_queue" {
  name                        = "training-config-queue"
  visibility_timeout_seconds  = var.visibility_timeout
  message_retention_seconds   = var.message_retention
  receive_wait_time_seconds   = var.receive_wait_time
  delay_seconds               = var.delay_seconds

  tags = {
    Name        = "Training Config Queue"
    Environment = var.environment
  }
}


resource "aws_ecs_task_definition" "training_service_task" {
  family                   = "training-service"
  network_mode             = "awsvpc"
  requires_compatibilities = ["EC2"]
  execution_role_arn       = aws_iam_role.ecs_interface_role.arn
  task_role_arn            = aws_iam_role.ecs_interface_role.arn

  container_definitions = jsonencode([
    {
      name      = "activations-container"
      image     = "${var.training_ecr_url}:latest"
      essential = true
      memory    = 31500  # Adjust as needed
      cpu       = 4096  # Adjust as needed
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/training-service"
          awslogs-region        = var.region
          awslogs-stream-prefix = "ecs"
        }
      },
      secrets = [
        {
          name      = "HF_TOKEN"
          valueFrom = aws_ssm_parameter.hf_token.arn
        },
        {
          name      = "AWS_ACCESS_KEY"
          valueFrom = aws_ssm_parameter.aws_access_key.arn
        },
        {
          name      = "AWS_SECRET"
          valueFrom = aws_ssm_parameter.aws_secret.arn
        },
        {
          name      = "SQS_QUEUE_URL"
          valueFrom = aws_ssm_parameter.parquet_file_queue_url.arn
        },
        {
          name      = "SQS_TAR_QUEUE_URL"
          valueFrom = aws_ssm_parameter.tar_file_queue_url.arn
        },
        {
          name      = "SQS_TRAINING_CONFIG_QUEUE_URL"
          valueFrom = aws_ssm_parameter.training_config_queue_url.arn
        },
        {
          name      = "S3_BUCKET_NAME"
          valueFrom = aws_ssm_parameter.tarfiles_bucket_name.arn
        },
        {
          name      = "S3_ACTIVATIONS_BUCKET_NAME"
          valueFrom = aws_ssm_parameter.activations_bucket_name.arn
        },
        {
          name      = "TABLE_NAME"
          valueFrom = aws_ssm_parameter.table_name.arn
        },
        {
          name      = "WANDB_API_KEY"
          valueFrom = aws_ssm_parameter.wandb_api_key.arn
        },
        {
          name      = "ECS_CLUSTER_NAME"
          valueFrom = aws_ssm_parameter.ecs_cluster_name.arn
        },
        {
          name      = "ECS_SERVICE_NAME"
          valueFrom = aws_ssm_parameter.ecs_service_name.arn
        }
      ],
      linuxParameters = {
        sharedMemorySize = 15500
      }
      resourceRequirements = [
        {
          type  = "GPU"
          value = "1"  # Adjust the number of GPUs as needed
        }
      ]
    }
  ])

  tags = {
    Name        = "Training Service Task Definition"
    Environment = var.environment
  }
}


resource "aws_cloudwatch_log_group" "training_service_log_group" {
  name              = "/ecs/training-service"
  retention_in_days = 7

  tags = {
    Environment = var.environment
  }
}


resource "aws_ecs_service" "training_service" {
  name            = "training-service"
  cluster         = aws_ecs_cluster.activation_cluster.id
  task_definition = aws_ecs_task_definition.training_service_task.arn
  desired_count   = var.train_tasks

  capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.activations_capacity_provider.name
    weight            = 1
    base              = 0
  }

  network_configuration {
    subnets         = [
      aws_subnet.private_subnet.id,
      aws_subnet.private_subnet_b.id,
      aws_subnet.private_subnet_c.id,
    ]
    security_groups = [aws_security_group.ecs_security_group.id]
  }

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100

  tags = {
    Environment = var.environment
  }

  depends_on = [
    aws_cloudwatch_log_group.activations_service_log_group,
    aws_iam_role.ecs_instance_role,
    aws_iam_role.ecs_interface_role,
    aws_iam_role_policy_attachment.ecs_instance_role_policy_attachment,
    aws_iam_role_policy_attachment.ecs_interface_role_policy_attachment,
    aws_iam_instance_profile.ecs_instance_profile,
    aws_iam_policy.ecs_task_policy,
  ]
}


resource "aws_launch_template" "training_launch_template" {
  name_prefix   = "training-launch-template"
  image_id      = "ami-0757fc38223742869"
  # https://aws.amazon.com/releasenotes/aws-deep-learning-base-ami-amazon-linux-2/
  # CUDA version 12.4
  # Nvidia driver version  550.90.12 

  instance_type = "g6e.xlarge"  
  iam_instance_profile {
    name = aws_iam_instance_profile.ecs_instance_profile.name
  }

  instance_market_options {
    market_type = "spot"
  }

  network_interfaces {
    associate_public_ip_address = true
    delete_on_termination       = true
    security_groups             = [aws_security_group.ecs_security_group.id]
  }

  user_data = base64encode(<<EOF
#!/bin/bash
echo ECS_CLUSTER=${aws_ecs_cluster.activation_cluster.name} >> /etc/ecs/ecs.config
EOF
)

   block_device_mappings {
    device_name = "/dev/xvda"

    ebs {
      volume_size           = 1000
      delete_on_termination = true
    }
  }

  tag_specifications {
    resource_type = "instance"

    tags = {
      Name        = "Training Service Instance"
      Environment = var.environment
    }
  }
}