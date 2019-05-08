# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from contextlib import contextmanager

from pyramid_hypernova.rendering import RenderToken
from pyramid_hypernova.tweens import configure_hypernova_batch


@contextmanager
def hypernova_batch(request, registry):
    """A context manager that performs hypernova token replacement in a batch.
    Write the content you wish to modify in body['content'] where body is the
    yielded object.

    :param request: a Pyramid request object
    :type request: pyramid.util.Request
    :param registry: a Pyramid application registry object
    :type registry: pyramid.registry.Registry

    :rtype: NoneType
    """
    if not request.hypernova_batch:
        request.hypernova_batch = configure_hypernova_batch(registry)

    body = {'content': None}

    yield body

    hypernova_response = request.hypernova_batch.submit()

    for identifier, job_result in hypernova_response.items():
        token = RenderToken(identifier)
        body['content'] = body['content'].replace(str(token), job_result.html)
