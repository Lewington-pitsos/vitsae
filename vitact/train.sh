set -e
./vpcgateway.sh

nvidia-smi


echo "Starting Training"

exec python3.11 train.py
