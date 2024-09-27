variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "queue_name" {
  description = "Name of the SQS queue"
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
  description = "Delay in seconds"
  type        = number
  default     = 0
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}
