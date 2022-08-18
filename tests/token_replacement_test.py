from unittest import mock

from pyramid_hypernova.rendering import RenderToken
from pyramid_hypernova.token_replacement import hypernova_token_replacement
from pyramid_hypernova.types import JobResult


def test_hypernova_token_replacement():
    token = RenderToken('my-unique-id')

    mock_hypernova_batch = mock.Mock()
    mock_hypernova_batch.submit.return_value = {
        'my-unique-id': JobResult(
            error=None,
            html='<div>REACT!</div>',
            job=None,
        )
    }

    with hypernova_token_replacement(mock_hypernova_batch) as body:
        body['content'] = str(token)

    assert mock_hypernova_batch.submit.called
    assert body['content'] == '<div>REACT!</div>'


def test_hypernova_token_replacement_with_no_token():
    content = '<div>hello world</div>'
    mock_hypernova_batch = mock.Mock()
    mock_hypernova_batch.submit.return_value = {}

    with hypernova_token_replacement(mock_hypernova_batch) as body:
        body['content'] = content

    assert mock_hypernova_batch.submit.called
    assert body['content'] == content


def test_hypernova_token_replacement_no_content_written_to_body():
    mock_hypernova_batch = mock.Mock()
    mock_hypernova_batch.submit.return_value = {}

    with hypernova_token_replacement(mock_hypernova_batch) as body:
        pass

    assert mock_hypernova_batch.submit.called
    assert body['content'] == ''
