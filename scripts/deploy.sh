if [ -z "$1" ]
  then
    echo "Supply an account id"
    exit 1
fi

AWS_ACCOUNT_ID=$1

cd vitsae
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

docker build  --platform linux/amd64 -t $AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/file-ecr:latest --push . 
cd ../ 

terraform -chdir=terraform apply -auto-approve
source ./scripts/load_secrets.sh

cd vitsae
poetry run python add_to_queue.py


