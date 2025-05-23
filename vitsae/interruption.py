import time
import threading
import requests
import signal

def check_for_interruption():
    try:
        response = requests.get("http://169.254.169.254/latest/meta-data/spot/instance-action", timeout=1)
        if response.status_code == 200:
            print("Instance is scheduled for interruption")
            return True
    except requests.exceptions.RequestException:
        pass
    return False

class InterruptionHandler():
    def __init__(self, message, queue_url, sqs_client, interrupt_fn=None) -> None:
        self._stop = False
        self.message = message
        self.queue_url = queue_url
        self.sqs_client = sqs_client

        if interrupt_fn is None:
            interrupt_fn = check_for_interruption

        self.interrupt_fn = interrupt_fn

        signal.signal(signal.SIGTERM, self.handle_sigterm)

    def listen(self):
        while not self._stop:
            if self.interrupt_fn():
                self.add_pq_back()
                break
            time.sleep(5)

    def add_pq_back(self):
        if self.message is not None:
            url = self.message
            self.message = None

            self.sqs_client.send_message(QueueUrl=self.queue_url, MessageBody=url)
        else:
            print("Message has already been added back to the queue")

    def start_listening(self):
        self.listener_thread = threading.Thread(target=self.listen, daemon=True)
        self.listener_thread.start()

    def stop_listening(self):
        self.stop()
        if self.listener_thread.is_alive():
            self.listener_thread.join()

    def stop(self):
        self._stop = True

    def handle_sigterm(self, signum, frame):
        print("Received SIGTERM signal. Performing cleanup...")
        self.add_pq_back()
        self.stop()
