# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import json

import mock
import pytest

from pyramid_hypernova.rendering import RenderToken
from pyramid_hypernova.tweens import hypernova_tween_factory
from pyramid_hypernova.types import JobResult


class TestTweens(object):

    @pytest.fixture(autouse=True)
    def mock_setup(self):
        self.token = RenderToken('my-unique-id')
        self.mock_batch_request_factory = mock.Mock()
        self.mock_json_encoder = mock.Mock()

        mock_get_batch_url = mock.Mock(return_value='http://localhost:8888/batch')
        self.mock_registry = mock.Mock()
        self.mock_registry.settings = {
            'pyramid_hypernova.get_batch_url': mock_get_batch_url,
            'pyramid_hypernova.batch_request_factory': self.mock_batch_request_factory,
            'pyramid_hypernova.json_encoder': self.mock_json_encoder,
        }

        self.mock_batch_request_factory.return_value.submit.return_value = {
            'my-unique-id': JobResult(
                error=None,
                html='<div>REACT!</div>',
                job=None,
            )
        }

        self.mock_request = mock.Mock()
        self.mock_handler = mock.Mock()

    def test_tween_replaces_tokens(self):
        self.mock_handler.return_value = mock.Mock(
            text=str(self.token)
        )
        tween = hypernova_tween_factory(self.mock_handler, self.mock_registry)
        mock_request = mock.Mock()

        response = tween(mock_request)

        self.mock_batch_request_factory.assert_called_once_with(
            batch_url='http://localhost:8888/batch',
            plugin_controller=mock.ANY,
            json_encoder=self.mock_json_encoder,
        )
        assert self.mock_batch_request_factory.return_value.submit.called
        assert response.text == '<div>REACT!</div>'

    # TODO: Add a test with response text that escapes markup tags
    def test_tween_replaces_tokens_in_json(self):
        text = json.dumps({
            'js_display': {},
            'body': str(self.token),
            'number': 3,
        })

        self.mock_handler.return_value = mock.Mock(
            text=text,
            content_type='application/json',
        )

        tween = hypernova_tween_factory(self.mock_handler, self.mock_registry)
        mock_request = mock.Mock()

        response = tween(mock_request)

        self.mock_batch_request_factory.assert_called_once_with(
            batch_url='http://localhost:8888/batch',
            plugin_controller=mock.ANY,
            json_encoder=self.mock_json_encoder,
        )
        assert self.mock_batch_request_factory.return_value.submit.called
        assert json.loads(response.text) == {
            'js_display': {},
            'body': '<div>REACT!</div>',
            'number': 3,
        }

    def test_tween_replaces_tokens_in_json_nested(self):
        text = json.dumps({
            'js_display': {},
            'content': {
                'body': str(self.token),
                'is_cool': True,
            },
            'number': 3,
        })

        self.mock_handler.return_value = mock.Mock(
            text=text,
            content_type='application/json',
        )

        tween = hypernova_tween_factory(self.mock_handler, self.mock_registry)
        mock_request = mock.Mock()

        response = tween(mock_request)

        self.mock_batch_request_factory.assert_called_once_with(
            batch_url='http://localhost:8888/batch',
            plugin_controller=mock.ANY,
            json_encoder=self.mock_json_encoder,
        )
        assert self.mock_batch_request_factory.return_value.submit.called
        assert json.loads(response.text) == {
            'js_display': {},
            'content': {
                'body': '<div>REACT!</div>',
                'is_cool': True,
            },
            'number': 3,
        }
