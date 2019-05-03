# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from json import JSONEncoder
import json

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

    json_encoder = registry.settings.get('pyramid_hypernova.json_encoder', JSONEncoder())

    def hypernova_tween(request):
        request.hypernova_batch = batch_request_factory(
            batch_url=get_batch_url(),
            plugin_controller=plugin_controller,
            json_encoder=json_encoder,
        )
        response = handler(request)

        hypernova_response = request.hypernova_batch.submit()

        if request.response.content_type == 'application/json':
            # For a JSON-encoded response, load the JSON into a dict and iteratively
            # perform token replacement. At the end, we re-encode the modified dict
            # back into the reponse.
            response_dict = json.loads(response.text)

            # To modify the dict properly, we need to keep a reference to the parent dict
            stack = [(key, value, response_dict) for key, value in response_dict.items()]

            while stack:
                key, value, parent_dict = stack.pop()
                if isinstance(value, dict):
                    stack.extend([(new_key, new_value, value) for new_key, new_value in value.items()])
                elif isinstance(value, unicode):
                    for identifier, job_result in hypernova_response.items():
                        token = RenderToken(identifier)
                        value = value.replace(str(token), job_result.html)
                    parent_dict[key] = value

            response_text = json.dumps(response_dict)
            try:
                # In python 2, decode str to unicode before writing to response.text
                response_text = response_text.decode('utf-8')
            except:
                # If '.decode' failed, we're in python 3 and response_text is already in unicode
                pass
            response.text = response_text
            return response

        for identifier, job_result in hypernova_response.items():
            token = RenderToken(identifier)
            response.text = response.text.replace(str(token), job_result.html)

        return response

    return hypernova_tween
