from json import JSONEncoder
from textwrap import dedent

import pytest

from pyramid_hypernova.rendering import encode
from pyramid_hypernova.rendering import render_blank_markup
from pyramid_hypernova.rendering import RenderToken
from pyramid_hypernova.types import HypernovaError
from pyramid_hypernova.types import Job
from testing.json_encoder import ComplexJSONEncoder


def test_rendering_token():
    identifier = 'this-is-a-unique-token'
    token = RenderToken(identifier)
    markup = '<!--hypernova-render-token-this-is-a-unique-token-->'

    assert str(token) == markup
    assert token.__html__() == markup


def test_encode():
    data = {
        'foo': '<script>alert(0);</script>',
    }
    assert encode(data, JSONEncoder()) == '{"foo": "<script&gt;alert(0);</script&gt;"}'


def test_encode_with_custom_json_encoder():
    data = {
        'foo': 1.2 + 3.4j,
    }
    assert encode(data, ComplexJSONEncoder()) == '{"foo": [1.2, 3.4]}'


def test_render_blank_markup():
    job = Job('MyCoolComponent.js', data={'title': 'sup'}, context={})
    markup = render_blank_markup('my-unique-token', job, False, JSONEncoder())

    assert markup == dedent('''
        <div data-hypernova-key="MyCoolComponentjs" data-hypernova-id="my-unique-token"></div>
        <script
          type="application/json"
          data-hypernova-key="MyCoolComponentjs"
          data-hypernova-id="my-unique-token"
        ><!--{"title": "sup"}--></script>
    ''')


def test_render_blank_markup_with_custom_json_encoder():
    job = Job('MyCoolComponent.js', data={'a complex subject': 4.3 + 2.1j}, context={})
    markup = render_blank_markup('my-unique-token', job, False, ComplexJSONEncoder())

    assert markup == dedent('''
        <div data-hypernova-key="MyCoolComponentjs" data-hypernova-id="my-unique-token"></div>
        <script
          type="application/json"
          data-hypernova-key="MyCoolComponentjs"
          data-hypernova-id="my-unique-token"
        ><!--{"a complex subject": [4.3, 2.1]}--></script>
    ''')


@pytest.mark.parametrize('error, error_markup', [
    (
        HypernovaError('Error', 'Error msg', ['1: Error', '2: stack']),
        '["Error", "Error msg", ["1: Error", "2: stack"]]'
    ),
    (None, 'undefined'),
])
def test_render_blank_markup_when_throw_client_error_true(error, error_markup):
    job = Job('MyCoolComponent.js', data={'title': 'sup'}, context={})
    markup = render_blank_markup('my-unique-token', job, True, JSONEncoder(), error)

    expected_markup = dedent('''
        <div data-hypernova-key="MyCoolComponentjs" data-hypernova-id="my-unique-token"></div>
        <script
          type="application/json"
          data-hypernova-key="MyCoolComponentjs"
          data-hypernova-id="my-unique-token"
        ><!--{"title": "sup"}--></script>
    ''')

    expected_markup += dedent('''
        <script type="text/javascript">
            (function () {{
                function ServerSideRenderingError(component, error) {{
                    this.name = 'ServerSideRenderingError';
                    this.component = component;
                    this.cause = error;
                }}

                ServerSideRenderingError.prototype = Object.create(ServerSideRenderingError.prototype);
                ServerSideRenderingError.prototype.constructor = ServerSideRenderingError;

                throw new ServerSideRenderingError('MyCoolComponentjs failed to render server-side, and fell back to client-side rendering.', {error_markup});
            }}());
        </script>
    ''').format(error_markup=error_markup)  # noqa: ignore=E501

    assert markup == expected_markup
