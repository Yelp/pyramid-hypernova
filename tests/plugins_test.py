from unittest import mock

import pytest

from pyramid_hypernova.plugins import BasePlugin
from pyramid_hypernova.plugins import PluginController


@pytest.fixture
def plugins():
    return [mock.Mock(), mock.Mock()]


@pytest.fixture
def plugin_controller(plugins):
    return PluginController(plugins)


class TestPluginController:
    def test_get_view_data(self, plugins, plugin_controller):
        pyramid_request = mock.Mock()

        data = plugin_controller.get_view_data(
            'MyComponent.js',
            {'title': 'sup'},
            pyramid_request,
        )

        plugins[0].get_view_data.assert_called_once_with(
            'MyComponent.js',
            {'title': 'sup'},
            pyramid_request,
        )
        plugins[1].get_view_data.assert_called_once_with(
            'MyComponent.js',
            plugins[0].get_view_data.return_value,
            pyramid_request,
        )
        assert data == plugins[1].get_view_data.return_value

    def test_prepare_request(self, plugins, plugin_controller):
        original_jobs = [mock.Mock()]
        pyramid_request = mock.Mock()

        jobs = plugin_controller.prepare_request(original_jobs, pyramid_request)

        plugins[0].prepare_request.assert_called_once_with(
            original_jobs,
            original_jobs,
            pyramid_request
        )
        plugins[1].prepare_request.assert_called_once_with(
            plugins[0].prepare_request.return_value,
            original_jobs,
            pyramid_request
        )

        assert jobs == plugins[1].prepare_request.return_value

    @pytest.mark.parametrize(
        'plugin_0_return_value,plugin_1_return_value,expected_value',
        [
            (True, True, True),
            (True, False, False),
            (False, True, False),
            (False, False, False),
        ],
    )
    def test_should_send_request(
        self,
        plugins,
        plugin_controller,
        plugin_0_return_value,
        plugin_1_return_value,
        expected_value
    ):
        pyramid_request = mock.Mock()
        plugins[0].should_send_request.return_value = plugin_0_return_value
        plugins[1].should_send_request.return_value = plugin_1_return_value
        jobs = mock.Mock()
        assert plugin_controller.should_send_request(jobs, pyramid_request) is expected_value

    def test_transform_request_headers(self, plugins, plugin_controller):
        pyramid_request = mock.Mock()
        plugins[0].transform_request_headers.side_effect = lambda x, r: dict(x, header1='yes')
        plugins[1].transform_request_headers.side_effect = lambda x, r: dict(x, header2='yes')
        assert plugin_controller.transform_request_headers({'foo': 'bar'}, pyramid_request) == {
            'foo': 'bar',
            'header1': 'yes',
            'header2': 'yes',
        }

    def test_will_send_request(self, plugins, plugin_controller):
        jobs = mock.Mock()
        pyramid_request = mock.Mock()
        plugin_controller.will_send_request(jobs, pyramid_request)
        plugins[0].will_send_request.assert_called_once_with(jobs, pyramid_request)
        plugins[1].will_send_request.assert_called_once_with(jobs, pyramid_request)

    def test_after_response(self, plugins, plugin_controller):
        original_response = mock.Mock()
        pyramid_request = mock.Mock()

        response = plugin_controller.after_response(original_response, pyramid_request)

        plugins[0].after_response.assert_called_once_with(
            original_response,
            original_response,
            pyramid_request,
        )
        plugins[1].after_response.assert_called_once_with(
            plugins[0].after_response.return_value,
            original_response,
            pyramid_request,
        )

        assert response == plugins[1].after_response.return_value

    def test_on_success(self, plugins, plugin_controller):
        response = mock.Mock()
        jobs = mock.Mock()
        pyramid_request = mock.Mock()
        plugin_controller.on_success(response, jobs, pyramid_request)
        plugins[0].on_success.assert_called_once_with(response, jobs, pyramid_request)
        plugins[1].on_success.assert_called_once_with(response, jobs, pyramid_request)

    def test_on_error(self, plugins, plugin_controller):
        err = mock.Mock()
        jobs = mock.Mock()
        pyramid_request = mock.Mock()

        plugin_controller.on_error(err, jobs, pyramid_request)
        plugins[0].on_error.assert_called_once_with(err, jobs, pyramid_request)
        plugins[1].on_error.assert_called_once_with(err, jobs, pyramid_request)


class TestBasePlugin:
    """Reducer functions on the BasePlugin should be identity functions."""

    def test_get_view_data(self):
        plugin = BasePlugin()
        data = mock.sentinel.data
        pyramid_request = mock.Mock()
        assert plugin.get_view_data('MyComponent.js', data, pyramid_request) == data

    def test_prepare_request(self):
        plugin = BasePlugin()
        current_jobs = mock.sentinel.current_jobs
        original_jobs = mock.sentinel.original_jobs
        pyramid_request = mock.Mock()
        assert plugin.prepare_request(
            current_jobs,
            original_jobs,
            pyramid_request
        ) == current_jobs

    def test_transform_request_headers(self):
        plugin = BasePlugin()
        pyramid_request = mock.Mock()
        assert plugin.transform_request_headers({'foo': 'bar'}, pyramid_request) == {'foo': 'bar'}

    def test_should_send_request(self):
        pyramid_request = mock.Mock()
        plugin = BasePlugin()
        jobs = mock.sentinel.jobs
        assert plugin.should_send_request(jobs, pyramid_request)

    def test_after_response(self):
        plugin = BasePlugin()
        current_response = mock.sentinel.current_response
        original_response = mock.sentinel.original_response
        pyramid_request = mock.Mock()
        assert plugin.after_response(
            current_response,
            original_response,
            pyramid_request,
        ) == current_response
