# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import mock

from pyramid_hypernova.context_manager import hypernova_batch
from pyramid_hypernova.rendering import RenderToken
from pyramid_hypernova.types import JobResult


def test_hypernova_batch_context_manager():
    token = RenderToken('my-unique-id')

    mock_request = mock.Mock()
    mock_request.hypernova_batch = None
    mock_hypernova_batch = mock.Mock()
    mock_hypernova_batch.submit.return_value = {
        'my-unique-id': JobResult(
            error=None,
            html='<div>REACT!</div>',
            job=None,
        )
    }

    mock_registry = mock.Mock()

    with mock.patch(
        'pyramid_hypernova.context_manager.configure_hypernova_batch',
        return_value=mock_hypernova_batch,
    ) as mock_configure_hypernova_batch, hypernova_batch(
        mock_request,
        mock_registry,
    ) as body:
        body['content'] = str(token)

    mock_configure_hypernova_batch.assert_called_once_with(mock_registry)
    assert mock_hypernova_batch.submit.called
    assert body['content'] == '<div>REACT!</div>'


def test_hypernova_batch_context_manager_request_already_has_batch():
    token = RenderToken('my-unique-id')

    mock_request = mock.Mock()
    mock_registry = mock.Mock()
    mock_request.hypernova_batch.submit.return_value = {
        'my-unique-id': JobResult(
            error=None,
            html='<div>REACT!</div>',
            job=None,
        )
    }

    with hypernova_batch(mock_request, mock_registry) as body:
        body['content'] = str(token)

    assert mock_request.hypernova_batch.submit.called
    assert body['content'] == '<div>REACT!</div>'
