from json import JSONEncoder

from pyramid_hypernova.batch import BatchRequest
from pyramid_hypernova.plugins import PluginController
from pyramid_hypernova.token_replacement import hypernova_token_replacement


class _ClosingMap(map):
    """Preserve the original WSGI iterable's close hook when mapping chunks.

    Like ``werkzeug.wsgi.ClosingIterator``, but without adding a Werkzeug dependency.
    https://github.com/pallets/werkzeug/blob/3.1.3/src/werkzeug/wsgi.py#L192-L238
    """

    def __init__(self, mapper, app_iter):
        close = getattr(app_iter, 'close', None)
        if close is not None:
            self.close = close


def hypernova_tween_factory(handler, registry):
    registry = registry

    def hypernova_mapper(request, chunk):
        if not request.hypernova_batch.jobs:
            return chunk

        try:
            # Skip token replacement logic if explicitly flagged to
            if request.disable_hypernova_tween:
                return chunk
        except AttributeError:
            pass

        transformed_chunk = chunk.decode('utf-8')
        with hypernova_token_replacement(request.hypernova_batch) as body:
            body['content'] = transformed_chunk

        transformed_chunk = body['content']
        return transformed_chunk.encode('utf-8')

    def hypernova_tween(request):
        request.hypernova_batch = configure_hypernova_batch(registry, request)
        response = handler(request)
        # Loop over all chunks in response.app_iter. Unlike accessing response.body
        # or response.text directly, this avoids buffering and is important
        # if our app_iter is a generator
        #
        # In cases where app_iter is a list (the default), this should work
        # equivalently
        response.app_iter = _ClosingMap(lambda chunk: hypernova_mapper(request, chunk), response.app_iter)
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
    should_display_error_stack = registry.settings.get(
        'pyramid_hypernova.should_display_error_stack', lambda request: False
    )

    return batch_request_factory(
        get_job_group_url=get_job_group_url,
        plugin_controller=plugin_controller,
        json_encoder=json_encoder,
        pyramid_request=request,
        display_error_stack=should_display_error_stack(request),
    )
