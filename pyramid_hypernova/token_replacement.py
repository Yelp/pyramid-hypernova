# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from contextlib import contextmanager

from pyramid_hypernova.rendering import RenderToken


@contextmanager
def hypernova_token_replacement(hypernova_batch):
    """A context manager that performs hypernova token replacement in a batch.
    Write the content you wish to modify in body['content'] where body is the
    yielded dict. Written content must be of unicode type in py2 and str in py3.

    Example usage:
        with hypernova_token_replacement(hypernova_batch) as body:
            body['content'] = do_rendering_stuff(...)

        response.body = body['content']

    :rtype: NoneType
    """
    body = {'content': ''}

    yield body

    hypernova_response = hypernova_batch.submit()

    for identifier, job_result in hypernova_response.items():
        token = RenderToken(identifier)
        body['content'] = body['content'].replace(str(token), job_result.html)
