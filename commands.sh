mkdir -p terraform/modules/{s3_bucket,sqs_queue,ecs_cluster}
touch terraform/main.tf
touch terraform/variables.tf
touch terraform/modules/s3_bucket/main.tf
touch terraform/modules/sqs_queue/main.tf
touch terraform/modules/ecs_cluster/main.tf
touch terraform/modules/s3_bucket/variables.tf
touch terraform/modules/sqs_queue/variables.tf
touch terraform/modules/ecs_cluster/variables.tf
touch terraform/modules/s3_bucket/outputs.tf
touch terraform/modules/sqs_queue/outputs.tf
touch terraform/modules/ecs_cluster/outputs.tf
touch terraform/modules/s3_bucket/terraform.tfvars
touch terraform/modules/sqs_queue/terraform.tfvars
touch terraform/modules/ecs_cluster/terraform.tfvars

