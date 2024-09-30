if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "This script must be sourced. Use 'source load_secrets.sh' or '. load_secrets.sh'"
    exit 1
fi

echo HF_TOKEN: $HF_TOKEN
echo AWS_ACCESS_KEY: $AWS_ACCESS_KEY
echo AWS_SECRET: $AWS_SECRET
echo SQS_QUEUE_URL: $SQS_QUEUE_URL
echo BUCKET_NAME: $S3_BUCKET_NAME
echo TABLE_NAME: $TABLE_NAME

export HF_TOKEN=$(aws secretsmanager get-secret-value --secret-id production-hf-token --region us-east-1 --query SecretString --output text | jq -r .HF_TOKEN)
export AWS_ACCESS_KEY=$(aws secretsmanager get-secret-value --secret-id production-aws-access-key --region us-east-1 --query SecretString --output text | jq -r .AWS_ACCESS_KEY)
export AWS_SECRET=$(aws secretsmanager get-secret-value --secret-id production-aws-secret --region us-east-1 --query SecretString --output text | jq -r .AWS_SECRET)
export SQS_QUEUE_URL=$(aws secretsmanager get-secret-value --secret-id production-sqs-queue-url --region us-east-1 --query SecretString --output text | jq -r .SQS_QUEUE_URL)
export S3_BUCKET_NAME=$(aws secretsmanager get-secret-value --secret-id production-s3-bucket-name --region us-east-1 --query SecretString --output text | jq -r .S3_BUCKET_NAME)
export TABLE_NAME=$(aws secretsmanager get-secret-value --secret-id production-table-name --region us-east-1 --query SecretString --output text | jq -r .TABLE_NAME)

echo HF_TOKEN: $HF_TOKEN
echo AWS_ACCESS_KEY: $AWS_ACCESS_KEY
echo AWS_SECRET: $AWS_SECRET
echo SQS_QUEUE_URL: $SQS_QUEUE_URL
echo BUCKET_NAME: $S3_BUCKET_NAME
echo TABLE_NAME: $TABLE_NAME
