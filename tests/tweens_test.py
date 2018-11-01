# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import mock

from pyramid_hypernova.rendering import RenderToken
from pyramid_hypernova.tweens import hypernova_tween_factory
from pyramid_hypernova.types import JobResult


def test_tween_replaces_tokens():
    token = RenderToken('my-unique-id')

    mock_handler = mock.Mock()
    mock_handler.return_value = mock.Mock(
        text=str(token)
    )

    mock_batch_request_factory = mock.Mock()
    mock_get_batch_url = mock.Mock(return_value='http://localhost:8888/batch')

    mock_json_encoder = mock.Mock()

    mock_registry = mock.Mock()
    mock_registry.settings = {
        'pyramid_hypernova.get_batch_url': mock_get_batch_url,
        'pyramid_hypernova.batch_request_factory': mock_batch_request_factory,
        'pyramid_hypernova.json_encoder': mock_json_encoder,
    }

    tween = hypernova_tween_factory(mock_handler, mock_registry)

    mock_request = mock.Mock()

    mock_batch_request_factory.return_value.submit.return_value = {
        'my-unique-id': JobResult(
            error=None,
            html='<div>REACT!</div>',
            job=None,
        )
    }

    response = tween(mock_request)

    mock_batch_request_factory.assert_called_once_with(
        batch_url='http://localhost:8888/batch',
        plugin_controller=mock.ANY,
        json_encoder=mock_json_encoder,
    )
    assert mock_batch_request_factory.return_value.submit.called
    assert response.text == '<div>REACT!</div>'
