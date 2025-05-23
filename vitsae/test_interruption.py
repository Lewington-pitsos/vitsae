import pytest
from unittest.mock import MagicMock, patch
import threading
import time
import requests

from interruption import InterruptionHandler, check_for_interruption

@pytest.fixture
def mock_sqs_client():
    return MagicMock()

def test_check_for_interruption_success():
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        assert check_for_interruption() is True
        mock_get.assert_called_once_with("http://169.254.169.254/latest/meta-data/spot/instance-action", timeout=1)

def test_check_for_interruption_non_200():
    with patch('requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        assert check_for_interruption() is False
        mock_get.assert_called_once_with("http://169.254.169.254/latest/meta-data/spot/instance-action", timeout=1)

def test_check_for_interruption_exception():
    with patch('requests.get', side_effect=requests.exceptions.RequestException):
        assert check_for_interruption() is False

def test_interruption_handler_init_default_interrupt_fn(mock_sqs_client):
    url = "test_body"
    queue_url = "test_url"
    handler = InterruptionHandler(url, queue_url, mock_sqs_client)

    assert handler.message == url
    assert handler.queue_url == queue_url
    assert handler.sqs_client == mock_sqs_client
    assert handler.interrupt_fn == check_for_interruption
    assert not handler._stop

def test_interruption_handler_init_custom_interrupt_fn(mock_sqs_client):
    url = "test_body"
    queue_url = "test_url"
    custom_fn = MagicMock(return_value=False)
    handler = InterruptionHandler(url, queue_url, mock_sqs_client, interrupt_fn=custom_fn)

    assert handler.interrupt_fn == custom_fn

def test_add_pq_back_with_valid_message(mock_sqs_client):
    url = "test_body"
    queue_url = "test_url"
    handler = InterruptionHandler(url, queue_url, mock_sqs_client)
    handler.add_pq_back()
    mock_sqs_client.send_message.assert_called_once_with(QueueUrl=queue_url, MessageBody=url)

@patch('time.sleep', return_value=None)
def test_listen_interrupt_triggered(mock_sleep, mock_sqs_client):
    interrupt_fn = MagicMock(return_value=True)
    url = "test_body"
    queue_url = "test_url"
    handler = InterruptionHandler(url, queue_url, mock_sqs_client, interrupt_fn=interrupt_fn)

    with patch.object(handler, 'add_pq_back') as mock_add_pq_back:
        handler.listen()
        mock_add_pq_back.assert_called_once()
        interrupt_fn.assert_called_once()
        mock_sleep.assert_not_called()

@patch('time.sleep', return_value=None)
def test_listen_no_interrupt(mock_sleep, mock_sqs_client):
    interrupt_fn = MagicMock(side_effect=[False, False, True])
    url = "test_body"
    queue_url = "test_url"
    handler = InterruptionHandler(url, queue_url, mock_sqs_client, interrupt_fn=interrupt_fn)

    with patch.object(handler, 'add_pq_back') as mock_add_pq_back:
        listen_thread = threading.Thread(target=handler.listen)
        listen_thread.start()
        time.sleep(0.1)
        handler.stop()
        listen_thread.join()

        assert interrupt_fn.call_count == 3
        assert mock_add_pq_back.call_count == 1

def test_start_listening_creates_thread(mock_sqs_client):
    handler = InterruptionHandler("body", "url", mock_sqs_client)
    with patch('threading.Thread') as mock_thread_class:
        mock_thread_instance = MagicMock()
        mock_thread_class.return_value = mock_thread_instance
        handler.start_listening()
        mock_thread_class.assert_called_once_with(target=handler.listen, daemon=True)
        mock_thread_instance.start.assert_called_once()

def test_stop_listening_stops_thread(mock_sqs_client):
    handler = InterruptionHandler("body", "url", mock_sqs_client)
    mock_thread = MagicMock()
    mock_thread.is_alive.return_value = True
    handler.listener_thread = mock_thread

    with patch.object(handler, 'stop') as mock_stop:
        handler.stop_listening()
        mock_stop.assert_called_once()
        mock_thread.join.assert_called_once()

def test_stop_sets_stop_flag(mock_sqs_client):
    handler = InterruptionHandler("body", "url", mock_sqs_client)
    assert not handler._stop
    handler.stop()
    assert handler._stop
