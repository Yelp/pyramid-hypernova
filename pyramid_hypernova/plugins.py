# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals


class PluginController(object):
    """A controller that coordinates calling hook methods of any registered
    plugins.

    See https://github.com/airbnb/hypernova/blob/master/docs/client-spec.md
    """

    def __init__(self, plugins):
        self.plugins = plugins

    def get_view_data(self, view_name, data, request):
        """Allows you to alter the data that a "view" will receive

        :param view_name: the name of the component
        :type view_name: string
        :param data: the props that will be passed into the component
        :type data: any
        :type request: a Pyramid request object
        :returns: the new data
        :rtype: any
        """
        for plugin in self.plugins:
            data = plugin.get_view_data(view_name, data, request)
        return data

    def prepare_request(self, jobs, request):
        """A reducer type function that is called when preparing the request
        that will be sent to Hypernova. This function receives the current
        running jobs Object and the original jobs Object.

        :type jobs: Dict[str, Job]
        :type request: a Pyramid request object
        :returns: the modified Jobs to be submitted
        :rtype: Dict[str, Job]
        """
        current_jobs = jobs
        original_jobs = jobs
        for plugin in self.plugins:
            current_jobs = plugin.prepare_request(current_jobs, original_jobs, request)
        return current_jobs

    def transform_request_headers(self, headers, request):
        """A reducer type function that is called with the request headers that
        will be sent to Huypernova. Plugins can use this to inject request
        headers, e.g. to add distributed tracing headers (like Zipkin).

        :type headers: Dict[str, str]
        :returns: the modified headers to be submitted
        :type request: a Pyramid request object
        :rtype: Dict[str, str]
        """
        for plugin in self.plugins:
            headers = plugin.transform_request_headers(headers, request)
        return headers

    def should_send_request(self, jobs, request):
        """An every type function. If one returns false then the request is
        canceled.

        :type jobs: Dict[str, Job]
        :returns: False if the request should be cancelled
        :type request: a Pyramid request object
        :rtype: bool
        """
        return all(plugin.should_send_request(jobs, request) for plugin in self.plugins)

    def will_send_request(self, jobs, request):
        """An event type function that is called prior to a request being sent.

        :type jobs: Dict[str, Job]
        :type request: a Pyramid request object
        """
        for plugin in self.plugins:
            plugin.will_send_request(jobs, request)

    def after_response(self, response, request):
        """A reducer type function which receives the current response and
        the original response from the Hypernova service.

        :param response: a response dict, as returned by
            `parse_response`
        :type response: dict
        :type request: a Pyramid request object
        :returns: the new response value
        :rtype: any
        """
        current_response = response
        original_response = response
        for plugin in self.plugins:
            current_response = plugin.after_response(current_response, original_response, request)
        return current_response

    def on_success(self, response, jobs, request):
        """An event type function that is called whenever a request was
        successful.

        :type response: dict
        :type request: a Pyramid request object
        :type jobs: Dict[str, Job]
        """
        for plugin in self.plugins:
            plugin.on_success(response, jobs, request)

    def on_error(self, err, jobs, request):
        """An event type function that is called whenever any error is
        encountered

        :type err: dict
        :type jobs: Dict[str, Job]
        :type request: a Pyramid request object
        """
        for plugin in self.plugins:
            plugin.on_error(err, jobs, request)


class BasePlugin(object):
    """A trivial base plugin that doesn't do anything.

    See https://github.com/airbnb/hypernova/blob/master/docs/client-spec.md
    """

    def get_view_data(self, view_name, data, request):
        """Allows you to alter the data that a "view" will receive

        :param view_name: the name of the component
        :type view_name: string
        :param data: the props that will be passed into the component
        :type data: any
        :type request: a Pyramid request object
        :returns: the new data
        :rtype: any
        """
        return data

    def prepare_request(self, current_jobs, original_jobs, request):
        """A reducer type function that is called when preparing the request
        that will be sent to Hypernova. This function receives the current
        running jobs Object and the original jobs Object.

        :type current_jobs: Dict[str, Job]
        :type original_jobs: Dict[str, Job]
        :type request: a Pyramid request object
        :returns: the modified Jobs to be submitted
        :rtype: Dict[str, Job]
        """
        return current_jobs

    def transform_request_headers(self, headers, request):
        """A reducer type function that is called with the request headers that
        will be sent to Hypernova. Plugins can use this to inject request
        headers, e.g. to add distributed tracing headers (like Zipkin).

        :type headers: Dict[str, str]
        :type request: a Pyramid request object
        :returns: the modified headers to be submitted
        :rtype: Dict[str, str]
        """
        return headers

    def should_send_request(self, jobs, request):
        """An every type function. If one returns false then the request is
        canceled.

        :type jobs: Dict[str, Job]
        :type request: a Pyramid request object
        :returns: False if the request should be cancelled
        :rtype: bool
        """
        return True

    def will_send_request(self, jobs, request):
        """An event type function that is called prior to a request being sent.

        :type jobs: Dict[str, Job]
        :type request: a Pyramid request object
        """

    def after_response(self, current_response, original_response, request):
        """A reducer type function which receives the current response and
        the original response from the Hypernova service.

        :param current_response: the current response value
        :type current_response: any
        :param original_response: a response dict, as returned by
            `parse_response`
        :type original_response: dict
        :type request: a Pyramid request object
        :returns: the new response value
        :rtype: any
        """
        return current_response

    def on_success(self, response, jobs, request):
        """An event type function that is called whenever a request was
        successful.

        :type response: dict
        :type jobs: Dict[str, Job]
        :type request: a Pyramid request object
        """

    def on_error(self, err, jobs, request):
        """An event type function that is called whenever any error is
        encountered

        :type err: dict
        :type jobs: Dict[str, Job]
        :type request: a Pyramid request object
        """
