aws ec2 describe-vpcs --region us-east-1 

aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=xxxxxx" \
    --query "Subnets[*].{ID:SubnetId, CIDR:CidrBlock, AZ:AvailabilityZone, State:State}" \
    --output table

aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <aws_account_id>.dkr.ecr.us-east-1.amazonaws.com


aws sts get-caller-identity --query "Account" --output text
