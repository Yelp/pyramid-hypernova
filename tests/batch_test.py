# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import mock
import pytest
from fido.exceptions import NetworkError

from pyramid_hypernova.batch import BatchRequest
from pyramid_hypernova.batch import create_fallback_response
from pyramid_hypernova.batch import create_job_groups
from pyramid_hypernova.batch import create_jobs_payload
from pyramid_hypernova.plugins import PluginController
from pyramid_hypernova.rendering import render_blank_markup
from pyramid_hypernova.types import HypernovaError
from pyramid_hypernova.types import Job
from pyramid_hypernova.types import JobResult


@pytest.mark.parametrize('throw_client_error', [
    True,
    False,
])
def test_create_fallback_response(throw_client_error):
    jobs = {
        'some-unique-id': Job(
            name='FooBar.js',
            data={'baz': 1234},
        ),
        'some-other-unique-id': Job(
            name='MyComponent.js',
            data={'title': 'sup'},
        ),
    }

    expected_response = {
        identifier: JobResult(
            error=None,
            html=render_blank_markup(identifier, job, throw_client_error),
            job=job,
        )
        for identifier, job in jobs.items()
    }

    assert create_fallback_response(jobs, throw_client_error) == expected_response


def test_create_jobs_payload():
    jobs = {
        'some-unique-id': Job(
            name='FooBar.js',
            data={'baz': 1234},
        ),
        'some-other-unique-id': Job(
            name='MyComponent.js',
            data={'title': 'sup'},
        ),
    }

    expected_result = {
        'some-unique-id': {
            'name': 'FooBar.js',
            'data': {
                'baz': 1234,
            },
        },
        'some-other-unique-id': {
            'name': 'MyComponent.js',
            'data': {
                'title': 'sup',
            },
        },
    }

    assert create_jobs_payload(jobs) == expected_result


@pytest.mark.parametrize('max_batch_size,expected', [
    (None, [5]),
    (1, [1, 1, 1, 1, 1]),
    (2, [2, 2, 1]),
    (3, [3, 2]),
    (4, [4, 1]),
    (5, [5]),
    (6, [5]),
])
def test_create_job_groups(max_batch_size, expected):
    jobs = {
        'job-1': '1',
        'job-2': '2',
        'job-3': '3',
        'job-4': '4',
        'job-5': '5',
    }

    job_groups = create_job_groups(jobs, max_batch_size)
    sizes = [len(job_group) for job_group in job_groups]

    assert sizes == expected


@pytest.fixture
def spy_plugin_controller():
    plugin_controller = PluginController([])
    return mock.Mock(wraps=plugin_controller)


@pytest.fixture(params=[None, 1, 2])
def batch_request(spy_plugin_controller, request):
    return BatchRequest('http://localhost:8888', spy_plugin_controller, max_batch_size=request.param)


class TestBatchRequest(object):

    def test_successful_batch_request(self, spy_plugin_controller, batch_request):
        token_1 = batch_request.render('component-1.js', {'key-1': 'value-1'})
        token_2 = batch_request.render('component-2.js', {'key-2': 'value-2'})
        token_3 = batch_request.render('component-3.js', {'key-3': 'value-3'})
        assert batch_request.jobs == {
            token_1.identifier: Job(
                name='component-1.js',
                data={'key-1': 'value-1'},
            ),
            token_2.identifier: Job(
                name='component-2.js',
                data={'key-2': 'value-2'},
            ),
            token_3.identifier: Job(
                name='component-3.js',
                data={'key-3': 'value-3'},
            ),
        }

        fake_response_json = {
            'error': None,
            'results': {
                token_1.identifier: {
                    'error': None,
                    'html': '<div>component 1</div>',
                },
                token_2.identifier: {
                    'error': None,
                    'html': '<div>component 2</div>',
                },
                token_3.identifier: {
                    'error': None,
                    'html': '<div>component 3</div>',
                },
            }
        }

        with mock.patch('fido.fetch') as mock_fetch:
            mock_fetch.return_value.wait.return_value.json.return_value = fake_response_json
            response = batch_request.submit()

        if batch_request.max_batch_size is None:
            assert mock_fetch.call_count == 1
        else:
            # Division (rounded-up) up to get total number of calls
            jobs_count = len(batch_request.jobs)
            max_batch_size = batch_request.max_batch_size
            assert mock_fetch.call_count == (jobs_count + (max_batch_size - 1)) // max_batch_size

        assert response == {
            token_1.identifier: JobResult(
                error=None,
                html='<div>component 1</div>',
                job=Job(name='component-1.js', data={'key-1': 'value-1'})
            ),
            token_2.identifier: JobResult(
                error=None,
                html='<div>component 2</div>',
                job=Job(name='component-2.js', data={'key-2': 'value-2'})
            ),
            token_3.identifier: JobResult(
                error=None,
                html='<div>component 3</div>',
                job=Job(name='component-3.js', data={'key-3': 'value-3'})
            ),
        }

    def test_batch_request_with_no_jobs_doesnt_post(self, spy_plugin_controller, batch_request):
        with mock.patch('fido.fetch') as mock_fetch:
            response = batch_request.submit()

        assert not mock_fetch.called
        assert response == {}

    def test_batch_request_with_component_errors(self, spy_plugin_controller, batch_request):
        token_1 = batch_request.render('MyComponent1.js', {'foo': 'bar'})
        token_2 = batch_request.render('MyComponent2.js', {'foo': 'baz'})
        job_2 = Job(name='MyComponent2.js', data={'foo': 'baz'})

        fake_response_json = {
            'error': None,
            'results': {
                token_1.identifier: {
                    'error': None,
                    'html': '<div>wow such SSR</div>',
                },
                token_2.identifier: {
                    'error': {
                        'name': 'SomeError',
                        'message': 'we goofed',
                        'stack': ['line 1', 'line 2']
                    },
                    'html': None,
                }
            }
        }

        with mock.patch('fido.fetch') as mock_fetch:
            mock_fetch.return_value.wait.return_value.json.return_value = fake_response_json
            response = batch_request.submit()

        if batch_request.max_batch_size is None:
            assert mock_fetch.call_count == 1
        else:
            # Division (rounded-up) up to get total number of calls
            jobs_count = len(batch_request.jobs)
            max_batch_size = batch_request.max_batch_size
            assert mock_fetch.call_count == (jobs_count + (max_batch_size - 1)) // max_batch_size

        assert response == {
            token_1.identifier: JobResult(
                error=None,
                html='<div>wow such SSR</div>',
                job=Job(name='MyComponent1.js', data={'foo': 'bar'})
            ),
            token_2.identifier: JobResult(
                error=HypernovaError(
                    name='SomeError',
                    message='we goofed',
                    stack=['line 1', 'line 2'],
                ),
                html=render_blank_markup(token_2.identifier, job_2, True),
                job=job_2,
            )
        }

    def test_batch_request_with_application_error(self, spy_plugin_controller, batch_request):
        job = Job(name='MyComponent.js', data={'foo': 'bar'})
        token = batch_request.render('MyComponent.js', {'foo': 'bar'})

        fake_response_json = {
            'error': {
                'name': 'SomeError',
                'message': 'yikes',
                'stack': ['line 1', 'line 2']
            }
        }

        with mock.patch('fido.fetch') as mock_fetch:
            mock_fetch.return_value.wait.return_value.json.return_value = fake_response_json
            response = batch_request.submit()

        if batch_request.max_batch_size is None:
            assert mock_fetch.call_count == 1
        else:
            # Division (rounded-up) up to get total number of calls
            jobs_count = len(batch_request.jobs)
            max_batch_size = batch_request.max_batch_size
            assert mock_fetch.call_count == (jobs_count + (max_batch_size - 1)) // max_batch_size

        assert response == {
            token.identifier: JobResult(
                error=HypernovaError(
                    name='SomeError',
                    message='yikes',
                    stack=['line 1', 'line 2'],
                ),
                html=render_blank_markup(token.identifier, job, True),
                job=job,
            ),
        }

    def test_batch_request_with_unhealthy_service(self, spy_plugin_controller, batch_request):
        job = Job(name='MyComponent.js', data={'foo': 'bar'})
        token = batch_request.render('MyComponent.js', {'foo': 'bar'})

        with mock.patch('fido.fetch') as mock_fetch:
            mock_fetch.return_value.wait.return_value.json.side_effect = NetworkError('oh no')
            response = batch_request.submit()

        if batch_request.max_batch_size is None:
            assert mock_fetch.call_count == 1
        else:
            # Division (rounded-up) up to get total number of calls
            jobs_count = len(batch_request.jobs)
            max_batch_size = batch_request.max_batch_size
            assert mock_fetch.call_count == (jobs_count + (max_batch_size - 1)) // max_batch_size

        assert response == {
            token.identifier: JobResult(
                error=HypernovaError(
                    name="<class 'fido.exceptions.NetworkError'>",
                    message='oh no',
                    stack=mock.ANY,
                ),
                html=render_blank_markup(token.identifier, job, True),
                job=job,
            ),
        }


class TestBatchRequestLifecycleMethods(object):
    """Test that BatchRequest calls plugin lifecycle methods at the
    appropriate times.
    """

    def test_calls_get_view_data(self, spy_plugin_controller, batch_request):
        token = batch_request.render('MyComponent.js', {'foo': 'bar'})

        spy_plugin_controller.get_view_data.assert_called_once_with(
            'MyComponent.js',
            {'foo': 'bar'},
        )

        job = batch_request.jobs[token.identifier]

        assert job.data == spy_plugin_controller.get_view_data(
            'MyComponent.js',
            {'foo': 'bar'},
        )

    def test_calls_prepare_request(self, spy_plugin_controller, batch_request):
        batch_request.render('MySsrComponent.js', {'foo': 'bar'})

        original_jobs = dict(batch_request.jobs)

        with mock.patch('fido.fetch'):
            batch_request.submit()

        spy_plugin_controller.prepare_request.assert_has_calls([
            mock.call(original_jobs),
        ])

        assert batch_request.jobs == spy_plugin_controller.prepare_request(
            original_jobs
        )

    def test_calls_will_send_request(self, spy_plugin_controller, batch_request):
        batch_request.render('MySsrComponent.js', {'foo': 'bar'})

        with mock.patch('fido.fetch'):
            batch_request.submit()

        spy_plugin_controller.will_send_request.assert_has_calls([
            mock.call(batch_request.jobs),
        ])

    def test_calls_after_response(self, spy_plugin_controller, batch_request):
        ssr_token = batch_request.render('MySsrComponent.js', {'foo': 'bar'})

        fake_response_json = {
            'error': None,
            'results': {
                ssr_token.identifier: {
                    'error': None,
                    'html': '<div>wow such SSR</div>',
                }
            }
        }

        with mock.patch('fido.fetch') as mock_fetch:
            mock_fetch.return_value.wait.return_value.json.return_value = fake_response_json
            response = batch_request.submit()

        assert spy_plugin_controller.after_response.called

        parsed_response = {
            ssr_token.identifier: JobResult(
                error=None,
                html='<div>wow such SSR</div>',
                job=batch_request.jobs[ssr_token.identifier],
            ),
        }

        assert response == spy_plugin_controller.after_response(parsed_response)

    def test_calls_on_success(self, spy_plugin_controller, batch_request):
        ssr_token = batch_request.render('MySsrComponent.js', {'foo': 'bar'})

        fake_response_json = {
            'error': None,
            'results': {
                ssr_token.identifier: {
                    'error': None,
                    'html': '<div>wow such SSR</div>',
                }
            }
        }

        with mock.patch('fido.fetch') as mock_fetch:
            mock_fetch.return_value.wait.return_value.json.return_value = fake_response_json
            response = batch_request.submit()

        spy_plugin_controller.on_success.assert_called_once_with(
            response,
            batch_request.jobs,
        )

    def test_calls_on_error(self, spy_plugin_controller, batch_request):
        batch_request.render('MyComponent.js', {'foo': 'bar'})

        fake_response_json = {
            'error': {
                'name': 'EverythingIsOnFire',
                'message': 'ya goofed',
                'stack': []
            }
        }

        with mock.patch('fido.fetch') as mock_fetch:
            mock_fetch.return_value.wait.return_value.json.return_value = fake_response_json
            batch_request.submit()

        spy_plugin_controller.on_error.assert_called_once_with(
            HypernovaError(
                name='EverythingIsOnFire',
                message='ya goofed',
                stack=[],
            ),
            batch_request.jobs,
        )

    def test_calls_on_error_on_unhealthy_service(self, spy_plugin_controller, batch_request):
        batch_request.render('MyComponent.js', {'foo': 'bar'})

        with mock.patch(
            'fido.fetch'
        ) as mock_fetch, mock.patch(
            'traceback.format_tb'
        ) as mock_format_tb:
            mock_fetch.return_value.wait.return_value.json.side_effect = NetworkError('oh no')
            batch_request.submit()

        spy_plugin_controller.on_error.assert_called_once_with(
            HypernovaError(
                name="<class 'fido.exceptions.NetworkError'>",
                message='oh no',
                stack=mock_format_tb.return_value,
            ),
            batch_request.jobs,
        )
