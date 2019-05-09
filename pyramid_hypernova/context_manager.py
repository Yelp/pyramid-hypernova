# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from contextlib import contextmanager

from pyramid_hypernova.rendering import RenderToken


@contextmanager
def hypernova_batch(request, batch):
    """A context manager that performs hypernova token replacement in a batch.
    Write the content you wish to modify in body['content'] where body is the
    yielded object.

    :param request: a Pyramid request object
    :type request: pyramid.util.Request
    :param registry: a Pyramid application registry object
    :type registry: pyramid.registry.Registry

    :rtype: NoneType
    """
    body = {'content': None}

    yield body

    hypernova_response = batch.submit()

    for identifier, job_result in hypernova_response.items():
        token = RenderToken(identifier)
        body['content'] = body['content'].replace(str(token), job_result.html)

    # If this context manager was used, we can skip token replacement in hypernova tween
    request.disable_hypernova_tween = True
