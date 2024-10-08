# load_secrets.sh

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "This script must be sourced. Use 'source load_secrets.sh' or '. load_secrets.sh'"
    exit 1
fi

echo "Existing Environment Variables: ---------------------------------------"
echo "HF_TOKEN: $HF_TOKEN"
echo "AWS_ACCESS_KEY: $AWS_ACCESS_KEY"
echo "AWS_SECRET: $AWS_SECRET"
echo "SQS_QUEUE_URL: $SQS_QUEUE_URL"
echo "SQS_TAR_QUEUE_URL: $SQS_TAR_QUEUE_URL"
echo "SQS_TRAINING_CONFIG_QUEUE_URL: $SQS_TRAINING_CONFIG_QUEUE_URL"
echo "BUCKET_NAME: $S3_BUCKET_NAME"
echo "ACTIVATIONS_BUCKET_NAME: $S3_ACTIVATIONS_BUCKET_NAME"
echo "TABLE_NAME: $TABLE_NAME"
echo "ECS_CLUSTER_NAME: $ECS_CLUSTER_NAME"
echo "ECS_SERVICE_NAME: $ECS_SERVICE_NAME"
echo "WANDB_API_KEY: $WANDB_API_KEY"


# Export environment variables by retrieving values from Parameter Store
export HF_TOKEN=$(aws ssm get-parameter --name production-hf-token --region us-east-1 --with-decryption --query 'Parameter.Value' --output text)
export WANDB_API_KEY=$(aws ssm get-parameter --name production-wandb-api-key --region us-east-1 --with-decryption --query 'Parameter.Value' --output text)

export AWS_ACCESS_KEY=$(aws ssm get-parameter --name production-aws-access-key --region us-east-1 --with-decryption --query 'Parameter.Value' --output text)
export AWS_SECRET=$(aws ssm get-parameter --name production-aws-secret --region us-east-1 --with-decryption --query 'Parameter.Value' --output text)
export SQS_QUEUE_URL=$(aws ssm get-parameter --name production-sqs-queue-url --region us-east-1 --query 'Parameter.Value' --output text)
export SQS_TAR_QUEUE_URL=$(aws ssm get-parameter --name production-sqs-tar-queue-url --region us-east-1 --query 'Parameter.Value' --output text)
export SQS_TRAINING_CONFIG_QUEUE_URL=$(aws ssm get-parameter --name production-sqs-training-config-queue-url --region us-east-1 --query 'Parameter.Value' --output text)

export S3_BUCKET_NAME=$(aws ssm get-parameter --name production-s3-bucket-name --region us-east-1 --query 'Parameter.Value' --output text)
export S3_ACTIVATIONS_BUCKET_NAME=$(aws ssm get-parameter --name production-s3-activation-bucket-name --region us-east-1 --query 'Parameter.Value' --output text)

export TABLE_NAME=$(aws ssm get-parameter --name production-table-name --region us-east-1 --query 'Parameter.Value' --output text)
export ECS_CLUSTER_NAME=$(aws ssm get-parameter --name production-ecs-cluster-name --region us-east-1 --query 'Parameter.Value' --output text)
export ECS_SERVICE_NAME=$(aws ssm get-parameter --name production-ecs-service-name --region us-east-1 --query 'Parameter.Value' --output text)


echo ""
echo "Retrieved Environment Variables: ---------------------------------------"
echo "HF_TOKEN: $HF_TOKEN"
echo "AWS_ACCESS_KEY: $AWS_ACCESS_KEY"
echo "AWS_SECRET: $AWS_SECRET"
echo "SQS_QUEUE_URL: $SQS_QUEUE_URL"
echo "SQS_TAR_QUEUE_URL: $SQS_TAR_QUEUE_URL"
echo "SQS_TRAINING_CONFIG_QUEUE_URL: $SQS_TRAINING_CONFIG_QUEUE_URL"
echo "BUCKET_NAME: $S3_BUCKET_NAME"
echo "ACTIVATIONS_BUCKET_NAME: $S3_ACTIVATIONS_BUCKET_NAME"
echo "TABLE_NAME: $TABLE_NAME"
echo "ECS_CLUSTER_NAME: $ECS_CLUSTER_NAME"
echo "ECS_SERVICE_NAME: $ECS_SERVICE_NAME"
echo "WANDB_API_KEY: $WANDB_API_KEY"
