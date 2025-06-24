from json import JSONEncoder
from unittest import mock

import pytest
from fido.exceptions import NetworkError
from requests.exceptions import ConnectionError
from requests.exceptions import HTTPError
from requests.exceptions import JSONDecodeError

from pyramid_hypernova.request import create_jobs_payload
from pyramid_hypernova.request import ErrorData
from pyramid_hypernova.request import format_response_error_data
from pyramid_hypernova.request import HypernovaQuery
from pyramid_hypernova.request import HypernovaQueryError
from pyramid_hypernova.types import Job

TEST_JOB_GROUP = {
    'yellow keycard': Job('open the exit door', 'behind the cacodemon', {}),
    'red skull key': Job('get the bfg9k', 'rocket jump from the platform', {'foo': 'bar'}),
}


@pytest.fixture
def mock_fido_fetch():
    with mock.patch('pyramid_hypernova.request.fido.fetch') as mock_fido_fetch:
        yield mock_fido_fetch


@pytest.fixture
def mock_requests_post():
    with mock.patch('pyramid_hypernova.request.requests.post') as mock_requests_post:
        yield mock_requests_post


@pytest.fixture
def mock_requests_failed_post():
    # simulates when there's no healthy SSR host to send a request to
    with mock.patch('pyramid_hypernova.request.requests.post', side_effect=ConnectionError()) as mock_requests_post:
        yield mock_requests_post


def test_create_jobs_payload():
    result = create_jobs_payload(TEST_JOB_GROUP)

    assert result == {
        'yellow keycard': {
            'name': 'open the exit door',
            'data': 'behind the cacodemon',
            'context': {},
        },
        'red skull key': {
            'name': 'get the bfg9k',
            'data': 'rocket jump from the platform',
            'context': {'foo': 'bar'},
        }
    }


@pytest.mark.parametrize(
    'response_error_data,expected_result',
    [
        (
            {'name': 'error', 'message': 'message', 'stack': 'stack'},
            ErrorData('error', 'message', 'stack')
        ),
        ({'name': None, 'message': None, 'stack': None}, None),
        ('some string', None)
    ]
)
def test_format_response_error_data(response_error_data, expected_result):
    result = format_response_error_data(response_error_data)

    assert result == expected_result


class TestHypernovaQuery:

    def test_successful_send_synchronous(self, mock_fido_fetch, mock_requests_post):
        mock_requests_post.return_value.json.return_value = 'ayy lmao'

        query = HypernovaQuery(TEST_JOB_GROUP, 'google.com', JSONEncoder(), True, {'header1': 'value1'})
        query.send()

        mock_fido_fetch.assert_not_called()
        mock_requests_post.assert_not_called()

        assert query.json() == 'ayy lmao'

        mock_requests_post.assert_called_once_with(
            url='google.com',
            headers={'header1': 'value1', 'Content-Type': 'application/json'},
            data=mock.ANY,
        )

    def test_erroneous_send_synchronous(self, mock_fido_fetch, mock_requests_post):
        mock_requests_post.return_value.raise_for_status.side_effect = HTTPError('ayy lmao')

        query = HypernovaQuery(TEST_JOB_GROUP, 'google.com', JSONEncoder(), True, {})
        query.send()

        mock_fido_fetch.assert_not_called()
        mock_requests_post.assert_not_called()

        with pytest.raises(HypernovaQueryError) as exc_info:
            query.json()
        assert str(exc_info.value) == str(HypernovaQueryError(HTTPError('ayy lmao')))

    def test_json_error_fallbacks_to_text(self, mock_fido_fetch, mock_requests_post):
        mock_requests_post.return_value.raise_for_status.side_effect = HTTPError('ayy lmao')
        mock_resp = mock_requests_post.return_value
        mock_resp.json.side_effect = JSONDecodeError('Expecting value', 'body', 0)
        mock_resp.text = 'Non-JSON Error Body'

        query = HypernovaQuery(TEST_JOB_GROUP, 'google.com', JSONEncoder(), True, {})
        query.send()

        mock_fido_fetch.assert_not_called()
        mock_requests_post.assert_not_called()

        with pytest.raises(HypernovaQueryError) as exc_info:
            query.json()

        mock_requests_post.assert_called_once_with(
            url='google.com',
            headers={'Content-Type': 'application/json'},
            data=mock.ANY,
        )
        assert str(exc_info.value) == str(HypernovaQueryError(HTTPError('ayy lmao')))
        assert exc_info.value.error_data == 'Non-JSON Error Body'

    def test_successful_send_asynchronous(self, mock_fido_fetch, mock_requests_post):
        mock_fido_fetch.return_value.wait.return_value.code = 200
        mock_fido_fetch.return_value.wait.return_value.json.return_value = 'ayy lmao'

        query = HypernovaQuery(TEST_JOB_GROUP, 'google.com', JSONEncoder(), False, {'header1': 'value1'})
        query.send()

        mock_fido_fetch.assert_called_once_with(
            url='google.com',
            method='POST',
            headers={'header1': ['value1'], 'Content-Type': ['application/json']},
            body=mock.ANY,
        )
        mock_requests_post.assert_not_called()

        assert query.json() == 'ayy lmao'

    def test_erroneous_send_asynchronous(self, mock_fido_fetch, mock_requests_post):
        mock_fido_fetch.return_value.wait.side_effect = NetworkError('ayy lmao')

        query = HypernovaQuery(TEST_JOB_GROUP, 'google.com', JSONEncoder(), False, {})
        query.send()

        mock_fido_fetch.assert_called_once()
        mock_requests_post.assert_not_called()

        with pytest.raises(HypernovaQueryError) as exc_info:
            query.json()
        assert str(exc_info.value) == str(HypernovaQueryError(NetworkError('ayy lmao')))

    def test_error_status_code_send_asynchronous(self, mock_fido_fetch, mock_requests_post):
        mock_fido_fetch.return_value.wait.return_value.code = 504
        mock_fido_fetch.return_value.wait.return_value.body = b'<h1>504 Bad Gateway</h1>'
        mock_fido_fetch.return_value.wait.return_value.json.side_effect = AssertionError()

        query = HypernovaQuery(TEST_JOB_GROUP, 'google.com', JSONEncoder(), False, {})
        query.send()

        mock_fido_fetch.assert_called_once()
        mock_requests_post.assert_not_called()

        with pytest.raises(HypernovaQueryError) as exc_info:
            query.json()
        assert str(exc_info.value) == (
            'Received response with status code 504 from Hypernova. Response body:\n'
            '<h1>504 Bad Gateway</h1>'
        )

    def test_does_not_throw_httperror_when_no_ssr_shard_available(self, mock_requests_failed_post):
        # WEBCORE-10219: throwing an error during query.send() returns an http error instead of a fallback response
        # instead, we should throw a HypernovaQueryError during query.json().
        query = HypernovaQuery(TEST_JOB_GROUP, 'google.com', JSONEncoder(), True, {})
        query.send()
        with pytest.raises(HypernovaQueryError):
            query.json()
