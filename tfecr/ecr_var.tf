variable "aws_region" {
  description = "The AWS region where resources will be created."
  type        = string
  default     = "us-east-1"
}

variable "ecr_training_repository_name" {
  description = "The name of the training ECR repository."
  type        = string
  default     = "training-ecr"
}

variable "ecr_activations_repository_name" {
  description = "The name of the activations ECR repository."
  type        = string
  default     = "activations-ecr"
}

variable "ecr_repository_name" {
  description = "The name of the ECR repository."
  type        = string
  default     = "file-ecr"
}

variable "image_tag_mutability" {
  description = "Whether image tags can be overwritten."
  type        = string
  default     = "MUTABLE" # Options: MUTABLE or IMMUTABLE
}

variable "scan_on_push" {
  description = "Enable image scanning on push."
  type        = bool
  default     = true
}
