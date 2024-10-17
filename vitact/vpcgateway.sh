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

traceroute -T -p 80 "$S3_ACTIVATIONS_BUCKET_NAME.s3.amazonaws.com" > /tmp/traceroute_output.txt

FILE=/tmp/traceroute_output.txt
cat "$FILE"

vpc_gateway() {
    local file="$1"
    local total_lines
    total_lines=$(wc -l < "$file")

    # Ensure there are enough lines to perform the check
    if [ "$total_lines" -le 2 ]; then
        return 1
    fi

    # Check all intermediate hops (excluding the first and last) for '* * *'
    awk -v total="$total_lines" '
    NR > 2 && NR < total {
        if ($2 != "*" || $3 != "*" || $4 != "*") {
            exit 1
        }
    }
    ' "$file"

    if tail -n 1 "$file" | grep -q "amazonaws.com"; then
        return 0
    else
        return 1
    fi
}

# Check the traceroute output
# A valid VPC Gateway Endpoint result should only show stars (*) for the intermediate hops
if vpc_gateway /tmp/traceroute_output.txt; then
    echo "Confirmed: S3 connection is going through a VPC Gateway Endpoint."
    exit 0
else
    echo "Error: S3 connection appears to be going through a public internet gateway."
    exit 1
fi