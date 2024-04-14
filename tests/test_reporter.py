import pytest
from unittest.mock import patch, MagicMock
from app.reporter import send_slack_message


@pytest.fixture
def mock_requests_post():
    with patch("app.reporter.requests.post") as mock:
        yield mock


@pytest.fixture
def mock_flask_logger_error():
    with patch("app.reporter.FLASK_APP.logger.error") as mock:
        yield mock


@pytest.mark.slack_report
def test_send_slack_message_success(mock_requests_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_requests_post.return_value = mock_response
    send_slack_message("Test message", "http://fakeurl.com")
    mock_requests_post.assert_called_once_with(
        "http://fakeurl.com",
        data='{"text": "test message"}',
        headers={"Content-Type": "application/json"},
    )


@pytest.mark.slack_report
def test_send_slack_message_failure(mock_requests_post, mock_flask_logger_error):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"
    mock_requests_post.return_value = mock_response
    send_slack_message("test message", "http://fakeurl.com")
    mock_requests_post.assert_called_once_with(
        "http://fakeurl.com",
        data='{"text": "test message"}',
        headers={"Content-Type": "application/json"},
    )
    mock_flask_logger_error.assert_called_once_with(
        f"Request to slack returned an error {mock_response.status_code} with the following message: {mock_response.text}"
    )
