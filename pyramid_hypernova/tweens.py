# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from json import JSONEncoder

from pyramid_hypernova.batch import BatchRequest
from pyramid_hypernova.plugins import PluginController
from pyramid_hypernova.token_replacement import hypernova_token_replacement


def hypernova_tween_factory(handler, registry):
    registry = registry

    def hypernova_tween(request):
        request.hypernova_batch = configure_hypernova_batch(registry, request)

        response = handler(request)

        if not request.hypernova_batch.jobs:
            return response

        try:
            # Skip token replacement logic if explicitly flagged to
            if request.disable_hypernova_tween:
                return response
        except AttributeError:
            pass

        with hypernova_token_replacement(request.hypernova_batch) as body:
            body['content'] = response.text

        response.text = body['content']

        return response

    return hypernova_tween


def configure_hypernova_batch(registry, request):
    get_job_group_url = registry.settings['pyramid_hypernova.get_job_group_url']

    plugins = registry.settings.get('pyramid_hypernova.plugins', [])
    plugin_controller = PluginController(plugins)

    batch_request_factory = registry.settings.get(
        'pyramid_hypernova.batch_request_factory',
        BatchRequest,
    )

    json_encoder = registry.settings.get('pyramid_hypernova.json_encoder', JSONEncoder())

    return batch_request_factory(
        get_job_group_url=get_job_group_url,
        plugin_controller=plugin_controller,
        json_encoder=json_encoder,
        pyramid_request=request,
    )
