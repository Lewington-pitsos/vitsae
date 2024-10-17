set -e

nvidia-smi

./vpcgateway.sh

echo "Starting Training"

exec python3.11 train.py
