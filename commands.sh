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


docker build -t vitact-localtest .
docker run -e HF_TOKEN=$HF_TOKEN -e AWS_ACCESS_KEY=$AWS_ACCESS_KEY -e AWS_SECRET=$AWS_SECRET -e SQS_QUEUE_URL=$SQS_QUEUE_URL  -e SQS_TAR_QUEUE_URL=$SQS_TAR_QUEUE_URL -e S3_BUCKET_NAME=$S3_BUCKET_NAME -e TABLE_NAME=$TABLE_NAME -e ECS_CLUSTER_NAME=$ECS_CLUSTER_NAME -e ECS_SERVICE_NAME=$ECS_SERVICE_NAME -e S3_ACTIVATIONS_BUCKET_NAME=$S3_ACTIVATIONS_BUCKET_NAME -e RUN_NAME=test -e WANDB_API_KEY=$WANDB_API_KEY -e SQS_TRAINING_CONFIG_QUEUE_URL=$SQS_TRAINING_CONFIG_QUEUE_URL vitact-localtest

docker inspect --format='{{.Os}}/{{.Architecture}}' vitact-localtest  

aws ec2 describe-instances --query 'Reservations[*].Instances[*].[InstanceId,State.Name,InstanceType,PublicIpAddress]' --output table

aws logs filter-log-events --log-group-name /ecs/activations-service --limit 10 --query 'events[].message' 

aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names activations-autoscaling-group --region us-east-1    --query "AutoScalingGroups[].{Min:MinSize, Max:MaxSize, Desired:DesiredCapacity}" 


aws ecs describe-services \
    --cluster vit-sae-ecs-cluster \
    --services activations-service \
    --query "services[].desiredCount" \
    --output table


aws ecs describe-tasks \
    --cluster vit-sae-ecs-cluster \
    --tasks $(aws ecs list-tasks \
        --cluster vit-sae-ecs-cluster \
        --service-name activations-service \
        --query "taskArns" \
        --output text) \
    --query "tasks[].{TaskArn:taskArn, Status:lastStatus, DesiredStatus:desiredStatus}" \
    --output table


aws ecs describe-tasks \
    --cluster vit-sae-ecs-cluster \
    --tasks $(aws ecs list-tasks \
        --cluster vit-sae-ecs-cluster \
        --service-name training-service \
        --query "taskArns" \
        --output text) \
    --query "tasks[].{TaskArn:taskArn, Status:lastStatus, DesiredStatus:desiredStatus}" \
    --output table


aws logs filter-log-events --log-group-name /ecs/activations-service --limit 10 --query 'events[].message' --start-time $(( $(date +%s) - 300 ))000 --filter-pattern "CUDA"


docker build -f Dockerfile.training -t train-localtest .


docker run -e HF_TOKEN=$HF_TOKEN -e AWS_ACCESS_KEY=$AWS_ACCESS_KEY -e AWS_SECRET=$AWS_SECRET -e SQS_QUEUE_URL=$SQS_QUEUE_URL  -e SQS_TAR_QUEUE_URL=$SQS_TAR_QUEUE_URL -e S3_BUCKET_NAME=$S3_BUCKET_NAME -e TABLE_NAME=$TABLE_NAME -e ECS_CLUSTER_NAME=$ECS_CLUSTER_NAME -e ECS_SERVICE_NAME=$ECS_SERVICE_NAME -e S3_ACTIVATIONS_BUCKET_NAME=$S3_ACTIVATIONS_BUCKET_NAME -e RUN_NAME=test -e WANDB_API_KEY=$WANDB_API_KEY -e SQS_TRAINING_CONFIG_QUEUE_URL=$SQS_TRAINING_CONFIG_QUEUE_URL --gpus all --shm-size=15gb train-localtest


aws ecs describe-tasks --cluster vit-sae-ecs-cluster --tasks $(aws ecs list-tasks --cluster vit-sae-ecs-cluster --service-name training-service --query "taskArns" --output text) --query "tasks[].{TaskArn:taskArn, Status:lastStatus, DesiredStatus:desiredStatus}" --output table
aws logs filter-log-events --log-group-name /ecs/training-service --limit 40 --query 'events[].message' --start-time $(( $(date +%s) - 300 ))000 

