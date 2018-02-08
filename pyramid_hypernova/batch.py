# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import json
import sys
import traceback
import uuid

import fido
from fido.exceptions import NetworkError
from more_itertools import chunked

from pyramid_hypernova.rendering import render_blank_markup
from pyramid_hypernova.rendering import RenderToken
from pyramid_hypernova.types import HypernovaError
from pyramid_hypernova.types import Job
from pyramid_hypernova.types import JobResult


def create_fallback_response(jobs, throw_client_error, error=None):
    return {
        identifier: JobResult(
            error=error,
            html=render_blank_markup(identifier, job, throw_client_error),
            job=job,
        )
        for identifier, job in jobs.items()
    }


def create_jobs_payload(jobs):
    return {
        identifier: {'name': job.name, 'data': job.data}
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

    def __init__(self, batch_url, plugin_controller, max_batch_size=None):
        self.batch_url = batch_url
        self.jobs = {}
        self.plugin_controller = plugin_controller
        self.max_batch_size = max_batch_size

    def render(self, name, data):
        identifier = str(uuid.uuid4())

        data = self.plugin_controller.get_view_data(name, data)
        job = Job(name, data)
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
                self.plugin_controller.on_error(error, {identifier: job})

            html = result['html']
            if not html:
                html = render_blank_markup(identifier, job, True)

            response[identifier] = JobResult(error=error, html=html, job=job)
        return response

    def process_responses(self, future, jobs):
        """Retrieve response from EventualResponse object and calls
        lifecycle methods for corresponding jobs.

        :param future: a future for the HTTP request to render `jobs`
        :type future: EventualResult
        :type jobs: Dict[str, Job]

        :rtype: Dict[str, JobResult]
        """

        response = {}

        try:
            r = future.wait()
            response_json = r.json()
            if response_json['error']:
                error = HypernovaError(
                    name=response_json['error']['name'],
                    message=response_json['error']['message'],
                    stack=response_json['error']['stack'],
                )
                response = create_fallback_response(jobs, True, error)
                self.plugin_controller.on_error(error, jobs)
            else:
                response = self._parse_response(response_json)
                self.plugin_controller.on_success(response, jobs)

        except (NetworkError, ValueError) as e:
            # the service is unhealthy. fall back to client-side rendering
            __, __, exc_traceback = sys.exc_info()

            error = HypernovaError(
                repr(type(e)),
                str(e),
                traceback.format_tb(exc_traceback),
            )
            self.plugin_controller.on_error(error, jobs)
            response = create_fallback_response(jobs, True, error)

        return response

    def submit(self):
        """Submit the Hypernova jobs as batches with a max size of self.max_batch_size.

        :rtype: Dict[str, JobResult]
        """
        self.jobs = self.plugin_controller.prepare_request(self.jobs)

        response = {}

        if self.jobs and self.plugin_controller.should_send_request(self.jobs):
            self.plugin_controller.will_send_request(self.jobs)
            job_groups = create_job_groups(self.jobs, self.max_batch_size)
            futures = []

            for job_group in job_groups:
                job_bytes = json.dumps(create_jobs_payload(job_group)).encode('utf-8')
                futures.append(
                    fido.fetch(
                        url=self.batch_url,
                        headers={
                            'Content-Type': ['application/json'],
                        },
                        method='POST',
                        body=job_bytes,
                    )
                )

            for job_group, future in zip(job_groups, futures):
                response.update(self.process_responses(future, job_group))

        else:
            # fall back to client-side rendering
            response.update(create_fallback_response(self.jobs, True))

        response = self.plugin_controller.after_response(response)
        return response
