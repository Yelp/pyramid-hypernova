# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from json import JSONEncoder

import mock
import pytest
from fido.exceptions import NetworkError
from requests.exceptions import HTTPError

from pyramid_hypernova.request import create_jobs_payload
from pyramid_hypernova.request import HypernovaQuery
from pyramid_hypernova.request import HypernovaQueryError
from pyramid_hypernova.types import Job

TEST_JOB_GROUP = {
    'yellow keycard': Job('open the exit door', 'behind the cacodemon'),
    'red skull key': Job('get the bfg9k', 'rocket jump from the platform'),
}


@pytest.fixture
def mock_fido_fetch():
    with mock.patch('pyramid_hypernova.request.fido.fetch') as mock_fido_fetch:
        yield mock_fido_fetch


@pytest.fixture
def mock_requests_post():
    with mock.patch('pyramid_hypernova.request.requests.post') as mock_requests_post:
        yield mock_requests_post


def test_create_jobs_payload():
    result = create_jobs_payload(TEST_JOB_GROUP)

    assert result == {
        'yellow keycard': {
            'name': 'open the exit door',
            'data': 'behind the cacodemon',
        },
        'red skull key': {
            'name': 'get the bfg9k',
            'data': 'rocket jump from the platform',
        }
    }


class TestHypernovaQuery(object):

    def test_successful_send_synchronous(self, mock_fido_fetch, mock_requests_post):
        mock_requests_post.return_value.json.return_value = 'ayy lmao'

        query = HypernovaQuery(TEST_JOB_GROUP, 'google.com', JSONEncoder(), True)
        query.send()

        mock_fido_fetch.assert_not_called()
        mock_requests_post.assert_called_once()

        assert query.json() == 'ayy lmao'

    def test_erroneous_send_synchronous(self, mock_fido_fetch, mock_requests_post):
        mock_requests_post.return_value.raise_for_status.side_effect = HTTPError('ayy lmao')

        query = HypernovaQuery(TEST_JOB_GROUP, 'google.com', JSONEncoder(), True)
        query.send()

        mock_fido_fetch.assert_not_called()
        mock_requests_post.assert_called_once()

        with pytest.raises(HypernovaQueryError) as exc_info:
            query.json()
        assert str(exc_info.value) == str(HypernovaQueryError(NetworkError('ayy lmao')))

    def test_successful_send_asynchronous(self, mock_fido_fetch, mock_requests_post):
        mock_fido_fetch.return_value.wait.return_value.code = 200
        mock_fido_fetch.return_value.wait.return_value.json.return_value = 'ayy lmao'

        query = HypernovaQuery(TEST_JOB_GROUP, 'google.com', JSONEncoder(), False)
        query.send()

        mock_fido_fetch.assert_called_once()
        mock_requests_post.assert_not_called()

        assert query.json() == 'ayy lmao'

    def test_erroneous_send_asynchronous(self, mock_fido_fetch, mock_requests_post):
        mock_fido_fetch.return_value.wait.side_effect = NetworkError('ayy lmao')

        query = HypernovaQuery(TEST_JOB_GROUP, 'google.com', JSONEncoder(), False)
        query.send()

        mock_fido_fetch.assert_called_once()
        mock_requests_post.assert_not_called()

        with pytest.raises(HypernovaQueryError) as exc_info:
            query.json()
        assert str(exc_info.value) == str(HypernovaQueryError(NetworkError('ayy lmao')))

    def test_error_status_code_send_asynchronous(self, mock_fido_fetch, mock_requests_post):
        mock_fido_fetch.return_value.wait.return_value.code = 504
        mock_fido_fetch.return_value.wait.return_value.json.side_effect = AssertionError()

        query = HypernovaQuery(TEST_JOB_GROUP, 'google.com', JSONEncoder(), False)
        query.send()

        mock_fido_fetch.assert_called_once()
        mock_requests_post.assert_not_called()

        with pytest.raises(HypernovaQueryError) as exc_info:
            query.json()
        assert str(exc_info.value) == 'Received response with status code 504 from Hypernova.'
