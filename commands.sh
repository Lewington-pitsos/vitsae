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
