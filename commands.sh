aws ec2 describe-vpcs --region us-east-1 

aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=xxxxxx" \
    --query "Subnets[*].{ID:SubnetId, CIDR:CidrBlock, AZ:AvailabilityZone, State:State}" \
    --output table

aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com

aws sts get-caller-identity --query "Account" --output text

for i in {00000..00127}; do wget --header="Authorization: Bearer $HF_TOKEN" https://huggingface.co/datasets/laion/laion2B-multi-joined-translated-to-en/resolve/main/.part-$i-00478b7a-941e-4176-b569-25f4be656991-c000.snappy.parquet.crc; done

terraform output ecr_repository_arn
terraform output ecr_repository_url

aws ecr list-images --repository-name file-ecr --region us-east-1

docker build -t file-ecr-localtest .
docker build -t file-ecr-localtest . && docker run -e HF_TOKEN=$HF_TOKEN -e AWS_ACCESS_KEY=$AWS_ACCESS_KEY -e AWS_SECRET=$AWS_SECRET -e SQS_QUEUE_URL=$SQS_QUEUE_URL -e S3_BUCKET_NAME=$S3_BUCKET_NAME -e TABLE_NAME=$TABLE_NAME -e ECS_CLUSTER_NAME=$ECS_CLUSTER_NAME -e ECS_SERVICE_NAME=$ECS_SERVICE_NAME -e S3_ACTIVATIONS_BUCKET_NAME=$S3_ACTIVATIONS_BUCKET_NAME -e SQS_TAR_QUEUE_URL=$SQS_TAR_QUEUE_URL -e S3_ACTIVATIONS_BUCKET_NAME=$S3_ACTIVATIONS_BUCKET_NAME file-ecr-localtest

aws autoscaling describe-auto-scaling-groups --query "AutoScalingGroups[?contains(AutoScalingGroupName, 'ecs-autoscaling-group')]"



# die_now stops the capacity provider being in charge of desired instances in the autoscaling group, which makes the desired capacity deafult to 0
# this will cause all the instances to be terminated, which means the subsiquent destroy will now succeed.
# if you run this immediately after creation it will still fail because the tasks can't be delted for some reason :(
terraform apply -var="die_now=true" --auto-approve && terraform destroy -var="die_now=true" --auto-approve

source ../scripts/load_secrets.sh && poetry run python add_to_queue.py --test

for file in *.tar; do mv "$file" "${file%.tar}.ready.tar"; done


docker build -t file-vitact-localtest .
docker run -e HF_TOKEN=$HF_TOKEN -e AWS_ACCESS_KEY=$AWS_ACCESS_KEY -e AWS_SECRET=$AWS_SECRET -e SQS_QUEUE_URL=$SQS_QUEUE_URL  -e SQS_TAR_QUEUE_URL=$SQS_TAR_QUEUE_URL -e S3_BUCKET_NAME=$S3_BUCKET_NAME -e TABLE_NAME=$TABLE_NAME -e ECS_CLUSTER_NAME=$ECS_CLUSTER_NAME -e ECS_SERVICE_NAME=$ECS_SERVICE_NAME -e S3_ACTIVATIONS_BUCKET_NAME=$S3_ACTIVATIONS_BUCKET_NAME -e RUN_NAME=test file-vitact-localtest
