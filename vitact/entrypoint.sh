nvidia-smi

cat $(whereis -b cudnn_version.h | awk '{print $2}')

exec python vitact/main.py
