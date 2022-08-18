from json import JSONEncoder
from unittest import mock

import pyramid.request
import pytest

from pyramid_hypernova.batch import BatchRequest
from pyramid_hypernova.batch import create_fallback_response
from pyramid_hypernova.batch import create_job_groups
from pyramid_hypernova.plugins import PluginController
from pyramid_hypernova.rendering import render_blank_markup
from pyramid_hypernova.request import HypernovaQueryError
from pyramid_hypernova.types import HypernovaError
from pyramid_hypernova.types import Job
from pyramid_hypernova.types import JobResult
from testing.json_encoder import ComplexJSONEncoder

test_jobs = {
    'some-unique-id': Job(
        name='FooBar.js',
        data={'baz': 1234},
        context={},
    ),
    'some-other-unique-id': Job(
        name='MyComponent.js',
        data={'title': 'sup'},
        context={},
    ),
}

test_jobs_with_complex_numbers_in_data = {
    'some-unique-id': Job(
        name='FooBar.js',
        data={'baz': 1 + 2j},
        context={},
    ),
    'some-other-unique-id': Job(
        name='MyComponent.js',
        data={'title': 3 + 4j},
        context={},
    ),
}


@pytest.mark.parametrize('jobs,throw_client_error,json_encoder', [
    (test_jobs, True, JSONEncoder()),
    (test_jobs, False, JSONEncoder()),
    (test_jobs, True, ComplexJSONEncoder()),
    (test_jobs, False, ComplexJSONEncoder()),
    (test_jobs_with_complex_numbers_in_data, True, ComplexJSONEncoder()),
    (test_jobs_with_complex_numbers_in_data, False, ComplexJSONEncoder()),
])
def test_create_fallback_response(jobs, throw_client_error, json_encoder):
    expected_response = {
        identifier: JobResult(
            error=None,
            html=render_blank_markup(identifier, job, throw_client_error, json_encoder),
            job=job,
        )
        for identifier, job in jobs.items()
    }

    assert create_fallback_response(jobs, throw_client_error, json_encoder) == expected_response


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


@pytest.fixture
def spy_get_job_group_url():
    return mock.Mock(return_value='http://localhost:8888')


@pytest.fixture(params=[
    # (data, use_complex_json_encoder)
    ([{'key-1': 'value-1'}, {'key-2': 'value-2'}, {'key-3': 'value-3'}], False),
    ([{'key-1': 'value-1'}, {'key-2': 'value-2'}, {'key-3': 'value-3'}], True),
    ([{'key-1': 1 + 2j}, {'key-2': 3 + 4j}, {'key-3': 5 + 6j}], True),
])
def test_data(request):
    return request.param


@pytest.fixture(params=[None, 1, 2])
def batch_request(spy_get_job_group_url, spy_plugin_controller, test_data, request):
    json_encoder = ComplexJSONEncoder() if test_data[1] else JSONEncoder()
    return BatchRequest(
        get_job_group_url=spy_get_job_group_url,
        plugin_controller=spy_plugin_controller,
        pyramid_request=pyramid.request.Request.blank('/'),
        max_batch_size=request.param,
        json_encoder=json_encoder,
    )


@pytest.fixture
def mock_hypernova_query():
    with mock.patch('pyramid_hypernova.batch.HypernovaQuery') as mock_hypernova_query:
        yield mock_hypernova_query


class TestBatchRequest:

    def test_successful_batch_request(self, spy_get_job_group_url, test_data, batch_request, mock_hypernova_query):
        data = test_data[0]
        token_1 = batch_request.render('component-1.js', data[0])
        token_2 = batch_request.render('component-2.js', data[1])
        token_3 = batch_request.render('component-3.js', data[2])
        assert batch_request.jobs == {
            token_1.identifier: Job(
                name='component-1.js',
                data=data[0],
                context={},
            ),
            token_2.identifier: Job(
                name='component-2.js',
                data=data[1],
                context={},
            ),
            token_3.identifier: Job(
                name='component-3.js',
                data=data[2],
                context={},
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

        mock_hypernova_query.return_value.json.return_value = fake_response_json
        response = batch_request.submit()

        if batch_request.max_batch_size is None:
            assert spy_get_job_group_url.call_count == 1
            # get_job_group_url is supplied with the job group
            assert len(spy_get_job_group_url.mock_calls[0].args[0]) == 3
            assert mock_hypernova_query.call_count == 1
        else:
            # Division (rounded-up) up to get total number of calls
            jobs_count = len(batch_request.jobs)
            max_batch_size = batch_request.max_batch_size
            batch_count = (jobs_count + (max_batch_size - 1)) // max_batch_size
            assert spy_get_job_group_url.call_count == batch_count
            assert mock_hypernova_query.call_count == batch_count
            mock_hypernova_query.assert_called_with(mock.ANY, 'http://localhost:8888', mock.ANY, batch_count == 1, {})

        assert response == {
            token_1.identifier: JobResult(
                error=None,
                html='<div>component 1</div>',
                job=Job(name='component-1.js', data=data[0], context={})
            ),
            token_2.identifier: JobResult(
                error=None,
                html='<div>component 2</div>',
                job=Job(name='component-2.js', data=data[1], context={})
            ),
            token_3.identifier: JobResult(
                error=None,
                html='<div>component 3</div>',
                job=Job(name='component-3.js', data=data[2], context={})
            ),
        }

    def test_batch_request_with_no_jobs_doesnt_post(self, spy_plugin_controller, batch_request, mock_hypernova_query):
        response = batch_request.submit()

        assert not mock_hypernova_query.called
        assert response == {}

    def test_batch_request_with_component_errors(
        self,
        spy_plugin_controller,
        test_data,
        batch_request,
        mock_hypernova_query,
    ):
        data = test_data[0]
        token_1 = batch_request.render('MyComponent1.js', data[0])
        token_2 = batch_request.render('MyComponent2.js', data[1])
        job_2 = Job(name='MyComponent2.js', data=data[1], context={})

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

        mock_hypernova_query.return_value.json.return_value = fake_response_json
        response = batch_request.submit()

        if batch_request.max_batch_size is None:
            assert mock_hypernova_query.call_count == 1
        else:
            # Division (rounded-up) up to get total number of calls
            jobs_count = len(batch_request.jobs)
            max_batch_size = batch_request.max_batch_size
            batch_count = (jobs_count + (max_batch_size - 1)) // max_batch_size
            assert mock_hypernova_query.call_count == batch_count
            mock_hypernova_query.assert_called_with(mock.ANY, mock.ANY, mock.ANY, batch_count == 1, {})

        assert response == {
            token_1.identifier: JobResult(
                error=None,
                html='<div>wow such SSR</div>',
                job=Job(name='MyComponent1.js', data=data[0], context={})
            ),
            token_2.identifier: JobResult(
                error=HypernovaError(
                    name='SomeError',
                    message='we goofed',
                    stack=['line 1', 'line 2'],
                ),
                html=render_blank_markup(token_2.identifier, job_2, True, batch_request.json_encoder),
                job=job_2,
            )
        }

    def test_batch_request_with_application_error(
        self,
        spy_plugin_controller,
        test_data,
        batch_request,
        mock_hypernova_query,
    ):
        data = test_data[0]
        job = Job(name='MyComponent.js', data=data[0], context={})
        token = batch_request.render('MyComponent.js', data[0])

        fake_response_json = {
            'error': {
                'name': 'SomeError',
                'message': 'yikes',
                'stack': ['line 1', 'line 2']
            }
        }

        mock_hypernova_query.return_value.json.return_value = fake_response_json
        response = batch_request.submit()

        if batch_request.max_batch_size is None:
            assert mock_hypernova_query.call_count == 1
        else:
            # Division (rounded-up) up to get total number of calls
            jobs_count = len(batch_request.jobs)
            max_batch_size = batch_request.max_batch_size
            batch_count = (jobs_count + (max_batch_size - 1)) // max_batch_size
            assert mock_hypernova_query.call_count == batch_count
            mock_hypernova_query.assert_called_with(mock.ANY, mock.ANY, mock.ANY, batch_count == 1, {})

        assert response == {
            token.identifier: JobResult(
                error=HypernovaError(
                    name='SomeError',
                    message='yikes',
                    stack=['line 1', 'line 2'],
                ),
                html=render_blank_markup(token.identifier, job, True, batch_request.json_encoder),
                job=job,
            ),
        }

    def test_batch_request_with_unhealthy_service(
        self,
        spy_plugin_controller,
        test_data,
        batch_request,
        mock_hypernova_query,
    ):
        data = test_data[0]
        job = Job(name='MyComponent.js', data=data[0], context={})
        token = batch_request.render('MyComponent.js', data[0])

        mock_hypernova_query.return_value.json.side_effect = HypernovaQueryError('oh no')
        response = batch_request.submit()

        if batch_request.max_batch_size is None:
            assert mock_hypernova_query.call_count == 1
        else:
            # Division (rounded-up) up to get total number of calls
            jobs_count = len(batch_request.jobs)
            max_batch_size = batch_request.max_batch_size
            batch_count = (jobs_count + (max_batch_size - 1)) // max_batch_size
            assert mock_hypernova_query.call_count == batch_count
            mock_hypernova_query.assert_called_with(mock.ANY, mock.ANY, mock.ANY, batch_count == 1, {})

        assert response == {
            token.identifier: JobResult(
                error=HypernovaError(
                    name='HypernovaQueryError',
                    message='oh no',
                    stack=mock.ANY,
                ),
                html=render_blank_markup(token.identifier, job, True, batch_request.json_encoder),
                job=job,
            ),
        }


class TestBatchRequestLifecycleMethods:
    """Test that BatchRequest calls plugin lifecycle methods at the
    appropriate times.
    """

    def test_calls_get_view_data(self, spy_plugin_controller, test_data, batch_request):
        data = test_data[0]
        token = batch_request.render('MyComponent.js', data[0])

        spy_plugin_controller.get_view_data.assert_called_once_with(
            'MyComponent.js',
            data[0],
            batch_request.pyramid_request,
        )

        job = batch_request.jobs[token.identifier]

        assert job.data == spy_plugin_controller.get_view_data(
            'MyComponent.js',
            data[0],
            batch_request.pyramid_request,
        )

    def test_calls_prepare_request(self, spy_plugin_controller, test_data, batch_request, mock_hypernova_query):
        data = test_data[0]
        batch_request.render('MySsrComponent.js', data[0])

        batch_request.submit()

        spy_plugin_controller.prepare_request.assert_called_once_with(
            batch_request.jobs,
            batch_request.pyramid_request
        )

    def test_calls_will_send_request(self, spy_plugin_controller, test_data, batch_request, mock_hypernova_query):
        data = test_data[0]
        batch_request.render('MySsrComponent.js', data[0])

        batch_request.submit()

        spy_plugin_controller.will_send_request.assert_called_once_with(
            batch_request.jobs,
            batch_request.pyramid_request,
        )

    def test_calls_after_response(self, spy_plugin_controller, test_data, batch_request, mock_hypernova_query):
        data = test_data[0]
        ssr_token = batch_request.render('MySsrComponent.js', data[0])

        fake_response_json = {
            'error': None,
            'results': {
                ssr_token.identifier: {
                    'error': None,
                    'html': '<div>wow such SSR</div>',
                }
            }
        }

        mock_hypernova_query.return_value.json.return_value = fake_response_json
        response = batch_request.submit()

        assert spy_plugin_controller.after_response.called

        parsed_response = {
            ssr_token.identifier: JobResult(
                error=None,
                html='<div>wow such SSR</div>',
                job=batch_request.jobs[ssr_token.identifier],
            ),
        }

        assert response == spy_plugin_controller.after_response(parsed_response, batch_request.pyramid_request)

    def test_calls_on_success(self, spy_plugin_controller, test_data, batch_request, mock_hypernova_query):
        data = test_data[0]
        ssr_token = batch_request.render('MySsrComponent.js', data[0])

        fake_response_json = {
            'error': None,
            'results': {
                ssr_token.identifier: {
                    'error': None,
                    'html': '<div>wow such SSR</div>',
                }
            }
        }

        mock_hypernova_query.return_value.json.return_value = fake_response_json
        response = batch_request.submit()

        spy_plugin_controller.on_success.assert_called_once_with(
            response,
            batch_request.jobs,
            batch_request.pyramid_request,
        )

    def test_calls_on_error(self, spy_plugin_controller, test_data, batch_request, mock_hypernova_query):
        data = test_data[0]
        batch_request.render('MyComponent.js', data[0])

        fake_response_json = {
            'error': {
                'name': 'EverythingIsOnFire',
                'message': 'ya goofed',
                'stack': []
            }
        }

        mock_hypernova_query.return_value.json.return_value = fake_response_json
        batch_request.submit()

        spy_plugin_controller.on_error.assert_called_once_with(
            HypernovaError(
                name='EverythingIsOnFire',
                message='ya goofed',
                stack=[],
            ),
            batch_request.jobs,
            batch_request.pyramid_request
        )

    def test_calls_on_error_on_unhealthy_service(
        self,
        spy_plugin_controller,
        test_data,
        batch_request,
        mock_hypernova_query,
    ):
        data = test_data[0]
        batch_request.render('MyComponent.js', data[0])

        with mock.patch(
            'traceback.format_tb',
            return_value=[
                'Traceback:\n',
                '  foo:\n',
            ],
        ):
            mock_hypernova_query.return_value.json.side_effect = HypernovaQueryError('oh no')
            batch_request.submit()

        spy_plugin_controller.on_error.assert_called_once_with(
            HypernovaError(
                name='HypernovaQueryError',
                message='oh no',
                stack=['Traceback:', '  foo:'],
            ),
            batch_request.jobs,
            batch_request.pyramid_request
        )
