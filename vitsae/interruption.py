import time
import threading
import requests

def check_for_interruption():
    try:
        response = requests.get("http://169.254.169.254/latest/meta-data/spot/instance-action", timeout=1)
        if response.status_code == 200:
            return True
    except requests.exceptions.RequestException:
        pass
    return False

class InterruptionHandler():
    def __init__(self, message, sqs_client, interrupt_fn=None) -> None:
        self._stop = False
        self.message = message
        self.sqs_client = sqs_client

        if interrupt_fn is None:
            interrupt_fn = check_for_interruption

        self.interrupt_fn = interrupt_fn

    def listen(self):
        while not self._stop:
            if self.interrupt_fn():
                self._add_pq_back()
                break
            time.sleep(5)

    def _add_pq_back(self):
        if isinstance(self.message, dict):
            self.sqs_client.send_message(**self.message)
        else:
            raise ValueError("Message must be a dictionary with 'QueueUrl' and 'MessageBody'")


    def start_listening(self):
        self.listener_thread = threading.Thread(target=self.listen, daemon=True)
        self.listener_thread.start()

    def stop_listening(self):
        self.stop()
        if self.listener_thread.is_alive():
            self.listener_thread.join()

    def stop(self):
        self._stop = True