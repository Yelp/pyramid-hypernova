from collections import namedtuple

import fido
import requests
from fido.exceptions import NetworkError
from requests.exceptions import ConnectionError
from requests.exceptions import HTTPError
from requests.exceptions import JSONDecodeError

ErrorData = namedtuple('ErrorData', ['name', 'message', 'stack'], defaults=[None, None, None])


def format_response_error_data(response_error_data):
    if response_error_data and isinstance(response_error_data, dict):
        name = response_error_data.get('name', None)
        message = response_error_data.get('message', None)
        stack = response_error_data.get('stack', None)

        if name or message or stack:
            return ErrorData(name, message, stack)

    return None


def create_jobs_payload(jobs):
    return {
        identifier: {'name': job.name, 'data': job.data, 'context': job.context}
        for identifier, job in jobs.items()
    }


class HypernovaQueryError(Exception):
    """Creates a HypernovaQueryError object

        :param child_error: Exception object
        :param error_data: Optional argument of type ErrorData (namedtuple)
    """

    def __init__(self, child_error, error_data=None):
        super().__init__(str(child_error))
        self.error_data = error_data


class HypernovaQuery:
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
        self.job_bytes = job_str.encode('utf-8')

        self.request_headers = dict(self.request_headers)
        self.request_headers['Content-Type'] = 'application/json'

        if self.synchronous:
            # do nothing! requests.post() will throw an HTTPError if there's no healthy SSR
            # upstream. we're not expecting this method to ever throw an exception,
            # so make synchronous SSR requests in json() instead, where we're equipped to
            # catch and deal with them.
            pass
        else:
            self.response = fido.fetch(
                url=self.url,
                headers={key: [value] for key, value in self.request_headers.items()},
                method='POST',
                body=self.job_bytes,
            )

    def json(self):
        """
        Get the JSON response from Hypernova.
        :rtype: Dict
        """
        if self.synchronous:
            try:
                self.response = requests.post(
                    url=self.url,
                    headers=self.request_headers,
                    data=self.job_bytes,
                )
                self.response.raise_for_status()
                json = self.response.json()
            except HTTPError as e:
                try:
                    response_error_data = self.response.json().get('error', None)
                    error_data = format_response_error_data(response_error_data)
                except JSONDecodeError:
                    error_data = format_response_error_data({
                        'message': self.response.text or 'SSRS did not return any content',
                    })

                raise HypernovaQueryError(e, error_data)
            except ConnectionError as e:
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
