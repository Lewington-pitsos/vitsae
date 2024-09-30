if [ -z "$1" ]
  then
    echo "Supply an account id"
    exit 1
fi

AWS_ACCOUNT_ID=$1

terraform -chdir=terraform destroy -auto-approve

./scripts/deploy.sh $AWS_ACCOUNT_ID