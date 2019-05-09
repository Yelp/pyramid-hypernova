# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import mock
import pytest

from pyramid_hypernova.rendering import RenderToken
from pyramid_hypernova.tweens import hypernova_tween_factory
from pyramid_hypernova.types import JobResult


class TestTweens(object):

    @pytest.fixture(autouse=True)
    def mock_setup(self):
        self.token = RenderToken('my-unique-id')

        mock_handler = mock.Mock()
        mock_handler.return_value = mock.Mock(
            text=str(self.token)
        )

        mock_get_batch_url = mock.Mock(return_value='http://localhost:8888/batch')

        self.mock_json_encoder = mock.Mock()

        self.mock_batch_request_factory = mock.Mock()
        self.mock_batch_request_factory.return_value.submit.return_value = {
            'my-unique-id': JobResult(
                error=None,
                html='<div>REACT!</div>',
                job=None,
            )
        }

        mock_registry = mock.Mock()
        mock_registry.settings = {
            'pyramid_hypernova.get_batch_url': mock_get_batch_url,
            'pyramid_hypernova.batch_request_factory': self.mock_batch_request_factory,
            'pyramid_hypernova.json_encoder': self.mock_json_encoder,
        }

        self.tween = hypernova_tween_factory(mock_handler, mock_registry)

        self.mock_request = mock.Mock()

    def test_tween_replaces_tokens_when_disable_hypernova_tween_not_set(self):
        del self.mock_request.disable_hypernova_tween

        response = self.tween(self.mock_request)

        self.mock_batch_request_factory.assert_called_once_with(
            batch_url='http://localhost:8888/batch',
            plugin_controller=mock.ANY,
            json_encoder=self.mock_json_encoder,
        )
        assert self.mock_batch_request_factory.return_value.submit.called
        assert response.text == '<div>REACT!</div>'

    def test_tween_replaces_tokens_when_disable_hypernova_tween_set_false(self):
        self.mock_request.disable_hypernova_tween = False

        response = self.tween(self.mock_request)

        self.mock_batch_request_factory.assert_called_once_with(
            batch_url='http://localhost:8888/batch',
            plugin_controller=mock.ANY,
            json_encoder=self.mock_json_encoder,
        )
        assert self.mock_batch_request_factory.return_value.submit.called
        assert response.text == '<div>REACT!</div>'

    def test_tween_replaces_tokens_when_disable_hypernova_tween_set_true(self):
        self.mock_request.disable_hypernova_tween = True

        response = self.tween(self.mock_request)

        self.mock_batch_request_factory.assert_called_once_with(
            batch_url='http://localhost:8888/batch',
            plugin_controller=mock.ANY,
            json_encoder=self.mock_json_encoder,
        )
        assert not self.mock_batch_request_factory.return_value.submit.called
        assert response.text == str(self.token)
