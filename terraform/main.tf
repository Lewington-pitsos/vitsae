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
# 3. ECR Repository for Docker Images
#######################################

resource "aws_ecr_repository" "ml_ecr" {
  name                 = var.ecr_repository_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "ML ECR Repository"
    Environment = var.environment
  }
}

#######################################
# 4. EC2 Key Pair for SSH Access
#######################################

resource "aws_key_pair" "ecs_key_pair" {
  key_name   = var.key_pair_name
  public_key = file(var.key_pair_public_key_path)

  tags = {
    Name        = "ECS Key Pair"
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
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "ecsTaskExecutionRole"

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

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy_attachment" {
  role       = aws_iam_role.ecs_task_execution_role.name
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
        Resource = aws_ecr_repository.ml_ecr.arn
      },
      {
        Action   = "ecr:GetAuthorizationToken"
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_policy_attachment" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.ecs_task_policy.arn
}

## IAM Role for ECS Instances
resource "aws_iam_role" "ecs_instance_role" {
  name = "ecsInstanceRole"

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

  key_name = aws_key_pair.ecs_key_pair.key_name

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

# ECS Task Definition
resource "aws_ecs_task_definition" "ml_task" {
  family                   = "ml_task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["EC2"]
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([
    {
      name      = "ml-container"
      image     = "${aws_ecr_repository.ml_ecr.repository_url}:latest"
      essential = true
      memory    = var.container_memory
      cpu       = var.container_cpu
      environment = [
        {
          name  = "SQS_QUEUE_URL"
          value = aws_sqs_queue.parquet_file_queue.url
        },
        {
          name  = "S3_BUCKET_NAME"
          value = aws_s3_bucket.model_outputs.bucket
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
    assign_public_ip = true
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

# ECR Repository Policy (Optional: To control access)
resource "aws_ecr_repository_policy" "ml_ecr_policy" {
  repository = aws_ecr_repository.ml_ecr.name

  policy = jsonencode({
    Version = "2008-10-17",
    Statement = [
      {
        Sid       = "AllowPushPull",
        Effect    = "Allow",
        Principal = "*",
        Action    = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
      }
    ]
  })
}
