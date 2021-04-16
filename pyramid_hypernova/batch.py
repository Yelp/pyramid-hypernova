# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import sys
import traceback
import uuid
from json import JSONEncoder

from more_itertools import chunked

from pyramid_hypernova.rendering import render_blank_markup
from pyramid_hypernova.rendering import RenderToken
from pyramid_hypernova.request import HypernovaQuery
from pyramid_hypernova.request import HypernovaQueryError
from pyramid_hypernova.types import HypernovaError
from pyramid_hypernova.types import Job
from pyramid_hypernova.types import JobResult


def create_fallback_response(jobs, throw_client_error, json_encoder, error=None):
    """Create a response dict for falling back to client-side rendering.

    :rtype: Dict[str, Job]
    """
    return {
        identifier: JobResult(
            error=error,
            html=render_blank_markup(identifier, job, throw_client_error, json_encoder),
            job=job,
        )
        for identifier, job in jobs.items()
    }


def create_job_groups(jobs, max_batch_size):
    job_groups = []

    if max_batch_size and max_batch_size > 0:
        for names in chunked(jobs, max_batch_size):
            job_groups.append({
                name: jobs[name]
                for name in names
            })
    else:
        job_groups.append(jobs)

    return job_groups


class BatchRequest(object):

    def __init__(
        self,
        get_job_group_url,
        plugin_controller,
        pyramid_request,
        max_batch_size=None,
        json_encoder=JSONEncoder()
    ):
        self.get_job_group_url = get_job_group_url
        self.jobs = {}
        self.plugin_controller = plugin_controller
        self.max_batch_size = max_batch_size
        self.json_encoder = json_encoder
        self.pyramid_request = pyramid_request

    def render(self, name, data, context=None):
        if context is None:  # pragma: no cover
            context = {}

        identifier = str(uuid.uuid4())

        data = self.plugin_controller.get_view_data(name, data, self.pyramid_request)
        job = Job(name, data, context)
        self.jobs[identifier] = job

        return RenderToken(identifier)

    def _parse_response(self, response_json):
        """Parse a raw JSON response into a response dict.

        :rtype: Dict[str, JobResult]
        """
        response = {}
        for identifier, result in response_json['results'].items():
            job = self.jobs[identifier]

            error = None
            if result['error']:
                error = HypernovaError(
                    name=result['error']['name'],
                    message=result['error']['message'],
                    stack=result['error']['stack'],
                )
                self.plugin_controller.on_error(error, {identifier: job}, self.pyramid_request)

            html = result['html']
            if not html:
                html = render_blank_markup(identifier, job, True, self.json_encoder)

            response[identifier] = JobResult(error=error, html=html, job=job)
        return response

    def process_responses(self, query, jobs):
        """Retrieve response from EventualResponse object and calls
        lifecycle methods for corresponding jobs.

        :param query: a HypernovaQuery object
        :type query: HypernovaQuery
        :type jobs: Dict[str, Job]

        :rtype: Dict[str, JobResult]
        """

        pyramid_response = {}

        try:
            response_json = query.json()
            if response_json['error']:
                error = HypernovaError(
                    name=response_json['error']['name'],
                    message=response_json['error']['message'],
                    stack=response_json['error']['stack'],
                )
                pyramid_response = create_fallback_response(jobs, True, self.json_encoder, error)
                self.plugin_controller.on_error(error, jobs, self.pyramid_request)
            else:
                pyramid_response = self._parse_response(response_json)
                self.plugin_controller.on_success(pyramid_response, jobs, self.pyramid_request)

        except (HypernovaQueryError, ValueError) as e:
            # the service is unhealthy. fall back to client-side rendering
            __, __, exc_traceback = sys.exc_info()

            error = HypernovaError(
                type(e).__name__,
                str(e),
                [line.rstrip('\n') for line in traceback.format_tb(exc_traceback)],
            )
            self.plugin_controller.on_error(error, jobs, self.pyramid_request)
            pyramid_response = create_fallback_response(jobs, True, self.json_encoder, error)

        return pyramid_response

    def submit(self):
        """Submit the Hypernova jobs as batches with a max size of self.max_batch_size.

        :rtype: Dict[str, JobResult]
        """
        self.jobs = self.plugin_controller.prepare_request(self.jobs, self.pyramid_request)

        response = {}

        if self.jobs and self.plugin_controller.should_send_request(self.jobs, self.pyramid_request):
            self.plugin_controller.will_send_request(self.jobs, self.pyramid_request)
            job_groups = create_job_groups(self.jobs, self.max_batch_size)
            queries = []

            # Fido is asynchronous and Python2.7 is bad at asynchronous, incurring 10-30ms of overhead
            # when calling and immediately waiting on an HTTP request. If we only have one request to
            # make, use synchronous Requests instead to save a little time.
            synchronous = len(job_groups) == 1

            for job_group in job_groups:
                batch_url = self.get_job_group_url(job_group, self.pyramid_request)
                request_headers = self.plugin_controller.transform_request_headers({}, self.pyramid_request)
                query = HypernovaQuery(job_group, batch_url, self.json_encoder, synchronous, request_headers)
                query.send()
                queries.append((job_group, query))

            for job_group, query in queries:
                response.update(self.process_responses(query, job_group))

        else:
            # fall back to client-side rendering
            response.update(create_fallback_response(
                self.jobs,
                throw_client_error=False,  # client-side rendering was intentional; don't throw an error
                json_encoder=self.json_encoder
            ))

        response = self.plugin_controller.after_response(response, self.pyramid_request)
        return response
