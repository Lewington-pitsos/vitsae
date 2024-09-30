import time
import boto3

from python_terraform import Terraform
from utils import load_config
import fire

def generate_urls(small=False):
    if small:
        base_url = "https://huggingface.co/datasets/lewington/laion2B-multi-joined-translated-to-en-smol/resolve/main/"

        # part-00001-00478b7a-941e-4176-b569-25f4be656991-c000.snappy_part_01.parquet
        urls = [
            f"{base_url}part-00001-00478b7a-941e-4176-b569-25f4be656991-c000.snappy_part_{i:02d}.parquet"
            for i in range(1, 31)
        ]

        return urls


    base_url = "https://huggingface.co/datasets/laion/laion2B-multi-joined-translated-to-en/resolve/main/"
    urls = [
        f"{base_url}part-{i:05d}-00478b7a-941e-4176-b569-25f4be656991-c000.snappy.parquet"
        for i in range(0, 128)
    ]
    return urls

def push_to_sqs(urls, sqs_queue_url):
    config = load_config()

    sqs = boto3.client('sqs', aws_access_key_id=config['AWS_ACCESS_KEY'], aws_secret_access_key=config['AWS_SECRET'])

    for url in urls:
        try:
            response = sqs.send_message(QueueUrl=sqs_queue_url, MessageBody=url)
            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                print(f"Sent URL to SQS: {url}")
            else:
                print(f"Error sending URL to SQS: {url}. Status code: {response['ResponseMetadata']['HTTPStatusCode']}")
        except Exception as e:
            print(f"Error sending URL to SQS: {url}. Error: {str(e)}")

    time.sleep(15)
    response = sqs.get_queue_attributes(
        QueueUrl=sqs_queue_url,
        AttributeNames=['ApproximateNumberOfMessages']
    )
    num_messages = response['Attributes']['ApproximateNumberOfMessages']
    print(f'Approximate number of messages in the queue: {num_messages}')

def main(test=False):
    tf = Terraform(working_dir='../terraform')
    sqs_queue_url = tf.output()['sqs_queue_url']['value']

    print(f"SQS Queue URL: {sqs_queue_url}")

    urls = generate_urls(small=test)
    push_to_sqs(urls, sqs_queue_url)


if __name__ == "__main__":
    fire.Fire(main)

