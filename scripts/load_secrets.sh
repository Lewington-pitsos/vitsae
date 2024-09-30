# load_secrets.sh

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "This script must be sourced. Use 'source load_secrets.sh' or '. load_secrets.sh'"
    exit 1
fi

echo "Existing Environment Variables:"
echo "HF_TOKEN: $HF_TOKEN"
echo "AWS_ACCESS_KEY: $AWS_ACCESS_KEY"
echo "AWS_SECRET: $AWS_SECRET"
echo "SQS_QUEUE_URL: $SQS_QUEUE_URL"
echo "BUCKET_NAME: $S3_BUCKET_NAME"
echo "TABLE_NAME: $TABLE_NAME"

# Export environment variables by retrieving values from Parameter Store
export HF_TOKEN=$(aws ssm get-parameter --name production-hf-token --region us-east-1 --with-decryption --query 'Parameter.Value' --output text)
export AWS_ACCESS_KEY=$(aws ssm get-parameter --name production-aws-access-key --region us-east-1 --with-decryption --query 'Parameter.Value' --output text)
export AWS_SECRET=$(aws ssm get-parameter --name production-aws-secret --region us-east-1 --with-decryption --query 'Parameter.Value' --output text)
export SQS_QUEUE_URL=$(aws ssm get-parameter --name production-sqs-queue-url --region us-east-1 --query 'Parameter.Value' --output text)
export S3_BUCKET_NAME=$(aws ssm get-parameter --name production-s3-bucket-name --region us-east-1 --query 'Parameter.Value' --output text)
export TABLE_NAME=$(aws ssm get-parameter --name production-table-name --region us-east-1 --query 'Parameter.Value' --output text)

echo "Retrieved Environment Variables:"
echo "HF_TOKEN: $HF_TOKEN"
echo "AWS_ACCESS_KEY: $AWS_ACCESS_KEY"
echo "AWS_SECRET: $AWS_SECRET"
echo "SQS_QUEUE_URL: $SQS_QUEUE_URL"
echo "BUCKET_NAME: $S3_BUCKET_NAME"
echo "TABLE_NAME: $TABLE_NAME"
