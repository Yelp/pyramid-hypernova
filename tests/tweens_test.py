from unittest import mock

import pytest

from pyramid_hypernova.rendering import RenderToken
from pyramid_hypernova.tweens import hypernova_tween_factory
from pyramid_hypernova.types import JobResult


class TestTweens:

    @pytest.fixture(autouse=True)
    def mock_setup(self):
        self.token = RenderToken('my-unique-id')

        mock_handler = mock.Mock()
        mock_handler.return_value = mock.Mock(
            text=str(self.token)
        )

        self.mock_get_job_group_url = mock.Mock(return_value='http://localhost:8888/batch')

        self.mock_json_encoder = mock.Mock()

        self.mock_batch_request_factory = mock.Mock()
        self.mock_batch_request_factory.return_value.submit.return_value = {
            'my-unique-id': JobResult(
                error=None,
                html='<div>REACT!</div>',
                job=None,
            )
        }

        self.mock_registry = mock.Mock()
        self.mock_registry.settings = {
            'pyramid_hypernova.get_job_group_url': self.mock_get_job_group_url,
            'pyramid_hypernova.batch_request_factory': self.mock_batch_request_factory,
            'pyramid_hypernova.json_encoder': self.mock_json_encoder,
        }

        self.tween = hypernova_tween_factory(mock_handler, self.mock_registry)

        self.mock_request = mock.Mock()

    def test_tween_replaces_tokens_when_disable_hypernova_tween_not_set(self):
        del self.mock_request.disable_hypernova_tween

        response = self.tween(self.mock_request)

        self.mock_batch_request_factory.assert_called_once_with(
            get_job_group_url=self.mock_get_job_group_url,
            plugin_controller=mock.ANY,
            json_encoder=self.mock_json_encoder,
            pyramid_request=self.mock_request,
        )
        assert self.mock_batch_request_factory.return_value.submit.called
        assert response.text == '<div>REACT!</div>'

    def test_tween_replaces_tokens_when_disable_hypernova_tween_set_false(self):
        self.mock_request.disable_hypernova_tween = False

        response = self.tween(self.mock_request)

        self.mock_batch_request_factory.assert_called_once_with(
            get_job_group_url=self.mock_get_job_group_url,
            plugin_controller=mock.ANY,
            json_encoder=self.mock_json_encoder,
            pyramid_request=self.mock_request,
        )
        assert self.mock_batch_request_factory.return_value.submit.called
        assert response.text == '<div>REACT!</div>'

    def test_tween_replaces_tokens_when_disable_hypernova_tween_set_true(self):
        self.mock_request.disable_hypernova_tween = True

        response = self.tween(self.mock_request)

        self.mock_batch_request_factory.assert_called_once_with(
            get_job_group_url=self.mock_get_job_group_url,
            plugin_controller=mock.ANY,
            json_encoder=self.mock_json_encoder,
            pyramid_request=self.mock_request,
        )
        assert not self.mock_batch_request_factory.return_value.submit.called
        assert response.text == str(self.token)

    def test_tween_returns_unmodified_response_if_no_jobs(self):
        mock_response = mock.Mock(
            body="I'm a binary file",
        )
        mock_handler = mock.Mock()
        mock_handler.return_value = mock_response

        tween = hypernova_tween_factory(mock_handler, self.mock_registry)

        mock_hypernova_batch = mock.Mock()
        mock_hypernova_batch.jobs = {}

        with mock.patch(
            'pyramid_hypernova.tweens.configure_hypernova_batch',
            return_value=mock_hypernova_batch,
        ):
            response = tween(self.mock_request)

        assert not self.mock_batch_request_factory.return_value.submit.called
        assert response == mock_response
