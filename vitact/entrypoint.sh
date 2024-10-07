nvidia-smi

cat $(whereis -b cudnn_version.h | awk '{print $2}')

exec python3.11 vitact/main.py
