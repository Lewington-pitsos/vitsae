# main.tf

provider "aws" {
  region = var.region
}

#######################################
# 1. S3 Bucket for Model Outputs
#######################################

resource "aws_s3_bucket" "model_outputs" {
  bucket = var.bucket_name

  tags = {
    Name        = "Model Outputs Bucket"
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

#######################################
# 5. ECS Cluster with G6 Spot Instances
#######################################

# ECS Cluster
resource "aws_ecs_cluster" "ml_cluster" {
  name = var.cluster_name

  tags = {
    Name        = "ML ECS Cluster"
    Environment = var.environment
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

## Custom IAM Policy for S3, SQS, and ECR Access
resource "aws_iam_policy" "ecs_task_policy" {
  name        = "ecsTaskPolicy"
  description = "Policy for ECS tasks to access S3, SQS, and ECR"

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
        Action   = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ]
        Effect   = "Allow"
        Resource = var.file_ecr_arn
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
        Effect   = "Allow"
        Action   = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.hf_token.arn,
          aws_secretsmanager_secret.aws_access_key.arn,
          aws_secretsmanager_secret.aws_secret.arn,
        ]
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

# Security Group for ECS Instances
resource "aws_security_group" "ecs_security_group" {
  name        = "ecs_security_group"
  description = "Allow necessary traffic for ECS instances"
  vpc_id      = var.vpc_id

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
  instance_type = var.instance_type

  iam_instance_profile {
    name = aws_iam_instance_profile.ecs_instance_profile.name
  }

  instance_market_options {
    market_type = "spot"
    spot_options {
      spot_instance_type             = "one-time"
      instance_interruption_behavior = "terminate"
    }
  }

  network_interfaces {
    associate_public_ip_address = true
    delete_on_termination       = true
    security_groups             = [aws_security_group.ecs_security_group.id]
  }

  tag_specifications {
    resource_type = "instance"

    tags = {
      Name        = "ECS Instance"
      Environment = var.environment
    }
  }
}

# Auto Scaling Group for ECS Instances
resource "aws_autoscaling_group" "ecs_autoscaling_group" {
  name                      = "ecs-autoscaling-group"
  max_size                  = var.max_size
  min_size                  = var.min_size
  desired_capacity          = var.desired_capacity
  launch_template {
    id      = aws_launch_template.ecs_launch_template.id
    version = "$Latest"
  }

  vpc_zone_identifier = var.subnet_ids

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

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_ecs_task_definition" "ml_task" {
  family                   = "ml_task"
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
      secrets = [
        {
          name      = "HF_TOKEN"
          valueFrom = aws_secretsmanager_secret.hf_token.arn
        },
        {
          name      = "AWS_ACCESS_KEY"
          valueFrom = aws_secretsmanager_secret.aws_access_key.arn
        },
        {
          name      = "AWS_SECRET"
          valueFrom = aws_secretsmanager_secret.aws_secret.arn
        },
        {
          name      = "SQS_QUEUE_URL"
          valueFrom = aws_secretsmanager_secret.parquet_file_queue_url.arn
        },
        {
          name      = "S3_BUCKET_NAME"
          valueFrom = aws_secretsmanager_secret.model_outputs_bucket_name.arn
        },
        {
          name      = "TABLE_NAME"
          valueFrom = aws_secretsmanager_secret.table_name.arn
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

# ECS Service
resource "aws_ecs_service" "ml_service" {
  name            = "ml-service"
  cluster         = aws_ecs_cluster.ml_cluster.id
  task_definition = aws_ecs_task_definition.ml_task.arn
  desired_count   = var.service_desired_count
  launch_type     = "EC2"

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [aws_security_group.ecs_security_group.id]
  }

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 50

  tags = {
    Environment = var.environment
  }

  depends_on = [
    aws_cloudwatch_log_group.ecs_log_group
  ]
}

resource "aws_dynamodb_table" "laion_batches" {
  name           = var.dynamodb_table_name
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "parquet_id"
  range_key       = "batch_id"

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
# 6. Secrets Manager for Sensitive Env Vars
#######################################

resource "aws_secretsmanager_secret" "hf_token" {
  name        = "${var.environment}-hf-token"
  description = "HF_TOKEN for ECS tasks"
  
  tags = {
    Environment = var.environment
    Name        = "HF_TOKEN Secret"
  }
}

resource "aws_secretsmanager_secret_version" "hf_token_version" {
  secret_id     = aws_secretsmanager_secret.hf_token.id
  secret_string = jsonencode({ HF_TOKEN = var.hf_token })
}

resource "aws_secretsmanager_secret" "aws_access_key" {
  name        = "${var.environment}-aws-access-key"
  description = "AWS_ACCESS_KEY for ECS tasks"
  
  tags = {
    Environment = var.environment
    Name        = "AWS_ACCESS_KEY Secret"
  }
}

resource "aws_secretsmanager_secret_version" "aws_access_key_version" {
  secret_id     = aws_secretsmanager_secret.aws_access_key.id
  secret_string = jsonencode({ AWS_ACCESS_KEY = var.aws_access_key })
}

resource "aws_secretsmanager_secret" "aws_secret" {
  name        = "${var.environment}-aws-secret"
  description = "AWS_SECRET for ECS tasks"
  
  tags = {
    Environment = var.environment
    Name        = "AWS_SECRET Secret"
  }
}

resource "aws_secretsmanager_secret_version" "aws_secret_version" {
  secret_id     = aws_secretsmanager_secret.aws_secret.id
  secret_string = jsonencode({ AWS_SECRET = var.aws_secret })
}

# If storing non-sensitive variables as secrets
resource "aws_secretsmanager_secret" "parquet_file_queue_url" {
  name        = "${var.environment}-sqs-queue-url"
  description = "SQS_QUEUE_URL for ECS tasks"
  
  tags = {
    Environment = var.environment
    Name        = "SQS_QUEUE_URL Secret"
  }
}

resource "aws_secretsmanager_secret_version" "parquet_file_queue_url_version" {
  secret_id     = aws_secretsmanager_secret.parquet_file_queue_url.id
  secret_string = jsonencode({ SQS_QUEUE_URL = aws_sqs_queue.parquet_file_queue.url })
}

resource "aws_secretsmanager_secret" "model_outputs_bucket_name" {
  name        = "${var.environment}-s3-bucket-name"
  description = "S3_BUCKET_NAME for ECS tasks"
  
  tags = {
    Environment = var.environment
    Name        = "S3_BUCKET_NAME Secret"
  }
}

resource "aws_secretsmanager_secret_version" "model_outputs_bucket_name_version" {
  secret_id     = aws_secretsmanager_secret.model_outputs_bucket_name.id
  secret_string = jsonencode({ S3_BUCKET_NAME = aws_s3_bucket.model_outputs.bucket })
}

resource "aws_secretsmanager_secret" "table_name" {
  name        = "${var.environment}-table-name"
  description = "TABLE_NAME for ECS tasks"
  
  tags = {
    Environment = var.environment
    Name        = "TABLE_NAME Secret"
  }
}

resource "aws_secretsmanager_secret_version" "table_name_version" {
  secret_id     = aws_secretsmanager_secret.table_name.id
  secret_string = jsonencode({ TABLE_NAME = aws_dynamodb_table.laion_batches.name })
}
