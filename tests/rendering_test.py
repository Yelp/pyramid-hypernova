# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from textwrap import dedent

from pyramid_hypernova.rendering import encode
from pyramid_hypernova.rendering import render_blank_markup
from pyramid_hypernova.rendering import RenderToken
from pyramid_hypernova.types import Job


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
    assert encode(data) == '{"foo": "<script&gt;alert(0);</script&gt;"}'


def test_render_blank_markup():
    job = Job('MyCoolComponent.js', data={'title': 'sup'})
    markup = render_blank_markup('my-unique-token', job, False)

    assert markup == dedent('''
        <div data-hypernova-key="MyCoolComponentjs" data-hypernova-id="my-unique-token"></div>
        <script
          type="application/json"
          data-hypernova-key="MyCoolComponentjs"
          data-hypernova-id="my-unique-token"
        ><!--{"title": "sup"}--></script>
    ''')


def test_render_blank_markup_with_error():
    job = Job('MyCoolComponent.js', data={'title': 'sup'})
    markup = render_blank_markup('my-unique-token', job, True)

    assert markup == dedent('''
        <div data-hypernova-key="MyCoolComponentjs" data-hypernova-id="my-unique-token"></div>
        <script
          type="application/json"
          data-hypernova-key="MyCoolComponentjs"
          data-hypernova-id="my-unique-token"
        ><!--{"title": "sup"}--></script>

        <script type="text/javascript">
            (function () {
                function ServerSideRenderingError(component) {
                    this.name = 'ServerSideRenderingError';
                    this.component = component;
                }

                ServerSideRenderingError.prototype = Object.create(ServerSideRenderingError.prototype);
                ServerSideRenderingError.prototype.constructor = ServerSideRenderingError;

                throw new ServerSideRenderingError('MyCoolComponentjs failed to render server-side, and fell back to client-side rendering.');
            }());
        </script>
    ''')  # noqa: ignore=E501
