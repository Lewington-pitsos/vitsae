import json
import boto3

from python_terraform import Terraform

def generate_urls():
    base_url = "https://huggingface.co/datasets/laion/laion2B-multi-joined-translated-to-en/resolve/main/"
    urls = [
        f"{base_url}.part-{i:05d}-00478b7a-941e-4176-b569-25f4be656991-c000.snappy.parquet.crc"
        for i in range(0, 128)
    ]
    return urls

def push_to_sqs(urls, sqs_queue_url):
    with open('.credentials.json') as f:
        credentials = json.load(f)

    hf_token = credentials['HF_TOKEN']
    sqs = boto3.client('sqs', aws_access_key_id=credentials['AWS_ACCESS_KEY_ID'], aws_secret_access_key=credentials['AWS_SECRET'])

    for url in urls:
        try:
            response = sqs.send_message(
                QueueUrl=sqs_queue_url,
                MessageBody=url,
                MessageAttributes={
                    'Authorization': {
                        'StringValue': f'Bearer {hf_token}',
                        'DataType': 'String'
                    }
                }
            )
            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                print(f"Sent URL to SQS: {url}")
            else:
                print(f"Error sending URL to SQS: {url}. Status code: {response['ResponseMetadata']['HTTPStatusCode']}")
        except Exception as e:
            print(f"Error sending URL to SQS: {url}. Error: {str(e)}")

    response = sqs.get_queue_attributes(
        QueueUrl=sqs_queue_url,
        AttributeNames=['ApproximateNumberOfMessages']
    )
    num_messages = response['Attributes']['ApproximateNumberOfMessages']
    print(f'Approximate number of messages in the queue: {num_messages}')

if __name__ == "__main__":


    tf = Terraform(working_dir='../terraform')
    sqs_queue_url = tf.output()['sqs_queue_url']['value']

    print(f"SQS Queue URL: {sqs_queue_url}")

    urls = generate_urls()
    push_to_sqs(urls, sqs_queue_url)
