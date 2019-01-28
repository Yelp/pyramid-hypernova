# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import fido
import requests
from fido.exceptions import NetworkError
from requests.exceptions import HTTPError


def create_jobs_payload(jobs):
    return {
        identifier: {'name': job.name, 'data': job.data}
        for identifier, job in jobs.items()
    }


class HypernovaQueryError(Exception):
    def __init__(self, child_error):
        super(HypernovaQueryError, self).__init__(str(child_error))


class HypernovaQuery(object):
    """ Abstract Hypernova query """

    def __init__(self, job_group, url, json_encoder, synchronous):
        """
        Build a Hypernova query.
        :param job_group: A job group (see create_job_groups)
        :param url: the URL of the Hypernova server we should query
        :param json_encoder: A JSON encoder to encode the query with
        :param synchronous: True to synchronously query CRS (faster), False to
            query asynchronously (allows parallelization)
        """
        self.job_group = job_group
        self.url = url
        self.json_encoder = json_encoder
        self.synchronous = synchronous

    def send(self):
        """ Query Hypernova """
        job_str = self.json_encoder.encode(create_jobs_payload(self.job_group))
        job_bytes = job_str.encode('utf-8')

        if self.synchronous:
            self.response = requests.post(
                url=self.url,
                headers={
                    'Content-Type': 'application/json',
                },
                data=job_bytes,
            )
        else:
            self.response = fido.fetch(
                url=self.url,
                headers={
                    'Content-Type': ['application/json'],
                },
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
                json = result.json()
            except NetworkError as e:
                raise HypernovaQueryError(e)
        return json
