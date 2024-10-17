#!/bin/bash

if [ -z "$S3_ACTIVATIONS_BUCKET_NAME" ]; then
    echo "Error: BUCKET_NAME is not set."
    exit 1
fi
if ! command -v traceroute &> /dev/null
then
    echo "Error: traceroute could not be found"
    exit 1
fi



which traceroute
traceroute --version

traceroute "$S3_ACTIVATIONS_BUCKET_NAME.s3.amazonaws.com" > /tmp/traceroute_output.txt

FILE=/tmp/traceroute_output.txt
cat "$FILE"

vpc_gateway() {
    awk 'NR > 3 { 
        # Check if the second, third, or fourth fields are not '*'
        if ($2 != "*" || $3 != "*" || $4 != "*") { 
            exit 1 
        } 
    }' "$FILE"
}

if vpc_gateway; then
    echo "Confirmed that S3 connection is going through a VPC Gateway Endpoint."
    exit 0
else
    echo "Error: S3 connection appears to be going through a public internet gateway."
    exit 1
fi

# Check the traceroute output
# A valid VPC Gateway Endpoint result should only show stars (*) for the intermediate hops
if echo "$output" | grep -qE "^[1-9]+ \* \* \*"; then
    echo "Traffic is reaching s3 through a VPC Gateway Endpoint."
    exit 0
else
    echo "Fatal Error: Traffic is not going through the VPC Gateway Endpoint."
    exit 1
fi