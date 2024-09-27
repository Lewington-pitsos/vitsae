# AWS Region
region = "us-east-1"

# Name of the SQS queue (must be unique within the region)
queue_name = "laion-parquet-queue"

# Visibility timeout in seconds (e.g., 30)
visibility_timeout = 30

# Message retention period in seconds (default is 4 days)
message_retention = 345600

# Receive wait time in seconds (default is 0)
receive_wait_time = 0

# Delay in seconds for messages (default is 0)
delay_seconds = 0

# Environment (e.g., dev, prod)
environment = "production"
