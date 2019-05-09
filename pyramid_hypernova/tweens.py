# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from json import JSONEncoder

from pyramid_hypernova.batch import BatchRequest
from pyramid_hypernova.context_manager import hypernova_batch
from pyramid_hypernova.plugins import PluginController


def hypernova_tween_factory(handler, registry):
    registry = registry

    def hypernova_tween(request):
        request.hypernova_batch = configure_hypernova_batch(registry)

        response = handler(request)

        try:
            # If hypernova_batch context manager (pyramid_hypernova/context_manager.py)
            # was used, this flag will be set to True.
            if request.disable_hypernova_tween:
                return response
        except AttributeError:
            pass

        with hypernova_batch(request, request.hypernova_batch) as body:
            body['content'] = response.text

        response.text = body['content']

        return response

    return hypernova_tween


def configure_hypernova_batch(registry):
    get_batch_url = registry.settings['pyramid_hypernova.get_batch_url']

    plugins = registry.settings.get('pyramid_hypernova.plugins', [])
    plugin_controller = PluginController(plugins)

    batch_request_factory = registry.settings.get(
        'pyramid_hypernova.batch_request_factory',
        BatchRequest,
    )

    json_encoder = registry.settings.get('pyramid_hypernova.json_encoder', JSONEncoder())

    return batch_request_factory(
        batch_url=get_batch_url(),
        plugin_controller=plugin_controller,
        json_encoder=json_encoder,
    )
