# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import fido
import requests
from fido.exceptions import NetworkError
from requests.exceptions import HTTPError


def create_jobs_payload(jobs):
    return {
        identifier: {'name': job.name, 'data': job.data, 'context': job.context}
        for identifier, job in jobs.items()
    }


class HypernovaQueryError(Exception):
    def __init__(self, child_error):
        super(HypernovaQueryError, self).__init__(str(child_error))


class HypernovaQuery(object):
    """ Abstract Hypernova query """

    def __init__(self, job_group, url, json_encoder, synchronous, request_headers):
        """
        Build a Hypernova query.
        :param job_group: A job group (see create_job_groups)
        :param url: the URL of the Hypernova server we should query
        :param json_encoder: A JSON encoder to encode the query with
        :param synchronous: True to synchronously query hypernova (faster),
            False to query asynchronously (allows parallelization)
        :param request_headers: dict of request headers to add
        """
        self.job_group = job_group
        self.url = url
        self.json_encoder = json_encoder
        self.synchronous = synchronous
        self.request_headers = request_headers

    def send(self):
        """ Query Hypernova """
        job_str = self.json_encoder.encode(create_jobs_payload(self.job_group))
        job_bytes = job_str.encode('utf-8')

        request_headers = dict(self.request_headers)
        request_headers['Content-Type'] = 'application/json'

        if self.synchronous:
            self.response = requests.post(
                url=self.url,
                headers=request_headers,
                data=job_bytes,
            )
        else:
            self.response = fido.fetch(
                url=self.url,
                headers={key: [value] for key, value in request_headers.items()},
                method='POST',
                body=job_bytes,
            )

    def json(self):
        """
        Get the JSON response from Hypernova.
        :rtype: Dict
        """
        if self.synchronous:
            try:
                self.response.raise_for_status()
                json = self.response.json()
            except HTTPError as e:
                raise HypernovaQueryError(e)
        else:
            try:
                result = self.response.wait()
            except NetworkError as e:
                raise HypernovaQueryError(e)
            else:
                # NetworkError is only called raised there's an actual network
                # problem (socket closed, etc.) and not for non-2xx statuses.
                if result.code != 200:
                    raise HypernovaQueryError(
                        'Received response with status code {} from Hypernova. Response body:\n'
                        '{}'.format(result.code, result.body.decode('UTF-8', 'ignore')),
                    )
                else:
                    json = result.json()
        return json
