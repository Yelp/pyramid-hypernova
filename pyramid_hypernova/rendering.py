# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import re
from textwrap import dedent


BLANK_MARKUP_TEMPLATE = dedent('''
    <div data-hypernova-key="{key}" data-hypernova-id="{identifier}"></div>
    <script
      type="application/json"
      data-hypernova-key="{key}"
      data-hypernova-id="{identifier}"
    ><!--{encoded_data}--></script>
''')


# https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Error#Custom_Error_Types
# Only show for unintended client side fallbacks
FALLBACK_ERROR = dedent('''
    <script type="text/javascript">
        (function () {{
            function ServerSideRenderingError(component) {{
                this.name = 'ServerSideRenderingError';
                this.component = component;
            }}

            ServerSideRenderingError.prototype = Object.create(ServerSideRenderingError.prototype);
            ServerSideRenderingError.prototype.constructor = ServerSideRenderingError;

            throw new ServerSideRenderingError('{component} failed to render server-side, and fell back to client-side rendering.');
        }}());
    </script>
''')  # noqa: ignore=E501


def encode(data, json_encoder):
    text = json_encoder.encode(data)
    # NOTE: we don't escape all html characters, because hypernova.decode will
    # only resolve &amp; and &gt;. This should be safe though, because the
    # encoded JSON always appears within an HTML comment.
    return text.replace('&', '&amp;').replace('>', '&gt;')


def render_blank_markup(identifier, job, throw_client_error, json_encoder):
    """This will be called as a fallback when server-side rendering fails."""
    # Hypernova server strips out non-word characters from the name
    key = re.sub(r'\W', '', job.name)
    encoded_data = encode(job.data, json_encoder)
    blank_markup = BLANK_MARKUP_TEMPLATE.format(
        key=key,
        identifier=identifier,
        encoded_data=encoded_data,
    )

    if throw_client_error:
        blank_markup += FALLBACK_ERROR.format(
            component=key,
        )

    return blank_markup


class RenderToken(object):
    """A placeholder for a Hypernova job that can later be replaced by the
    rendered component.

    The token is an HTML comment so we can be sure that it won't appear
    in user-generated content (if it does, you're already vulnerable to
    XSS).
    """

    def __init__(self, identifier):
        self.identifier = identifier

    def __html__(self):
        """Custom HTML markup for templating languages that use markupsafe."""
        return '<!--hypernova-render-token-{}-->'.format(self.identifier)

    def __str__(self):
        return self.__html__()
