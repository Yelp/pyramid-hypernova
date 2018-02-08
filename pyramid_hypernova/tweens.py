# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from pyramid_hypernova.batch import BatchRequest
from pyramid_hypernova.plugins import PluginController
from pyramid_hypernova.rendering import RenderToken


def hypernova_tween_factory(handler, registry):
    get_batch_url = registry.settings['pyramid_hypernova.get_batch_url']

    plugins = registry.settings.get('pyramid_hypernova.plugins', [])
    plugin_controller = PluginController(plugins)

    batch_request_factory = registry.settings.get(
        'pyramid_hypernova.batch_request_factory',
        BatchRequest,
    )

    def hypernova_tween(request):
        request.hypernova_batch = batch_request_factory(get_batch_url(), plugin_controller)
        response = handler(request)

        hypernova_response = request.hypernova_batch.submit()

        for identifier, job_result in hypernova_response.items():
            token = RenderToken(identifier)
            response.text = response.text.replace(str(token), job_result.html)

        return response

    return hypernova_tween
