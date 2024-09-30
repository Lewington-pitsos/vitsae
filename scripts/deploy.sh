if [ -z "$1" ]
  then
    echo "Supply an account id"
    exit 1
fi

AWS_ACCOUNT_ID=$1

aws sqs purge-queue --queue-url https://sqs.us-east-1.amazonaws.com/$AWS_ACCOUNT_ID/parquet-files-queue
aws sqs get-queue-attributes --queue-url https://sqs.us-east-1.amazonaws.com/$AWS_ACCOUNT_ID/parquet-files-queue --attribute-names ApproximateNumberOfMessages

cd vitsae
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

docker build -t $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/file-ecr:latest . 
docker push $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/file-ecr:latest
cd ../ 

terraform -chdir=terraform apply -auto-approve
source ./scripts/load_secrets.sh

cd vitsae
poetry run python add_to_queue.py


