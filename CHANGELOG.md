# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [8.0.0] - 2021-04-16

### Changed

`BatchRequest` now accepts a function, `get_job_group_url`, in place of `batch_url`. This allows for increased flexibility in routing hypernova requests.

You'll need to update your `pyramid_hypernova.get_batch_url` to the `pyramid_hypernova.get_job_group_url` setting.

Before:
```py
def get_batch_url():
    return 'https://localhost:8080/batch'

registry.settings.update({
    'pyramid_hypernova.get_batch_url': get_batch_url,
})
```

After:
```py
def get_job_group_url():
    return 'https://localhost:8080/batch'

registry.settings.update({
    'pyramid_hypernova.get_job_group_url': get_job_group_url,
})
```

-----

Additionally, If you were manually supplying a BatchRequest factory via the `pyramid_hypernova.batch_request_factory` setting, you'll need
to update its API to accept `get_job_group_url` and pass it along to the `BatchRequest` class. Example:

Before:
```py
def batch_request_factory(batch_url, plugin_controller, json_encoder, pyramid_request):
    return BatchRequest(
        batch_url=batch_url,
        plugin_controller=plugin_controller,
        json_encoder=json_encoder,
        pyramid_request=pyramid_request,
    )

registry.settings.update({
    'pyramid_hypernova.batch_request_factory': batch_request_factory,
})
```

After:
```py
def batch_request_factory(get_job_group_url, plugin_controller, json_encoder, pyramid_request):
    return BatchRequest(
        get_job_group_url=get_job_group_url,
        plugin_controller=plugin_controller,
        json_encoder=json_encoder,
        pyramid_request=pyramid_request,
    )

registry.settings.update({
    'pyramid_hypernova.batch_request_factory': batch_request_factory,
})
```

`get_job_group_url` will be supplied two parameters - the **job group** that pyramid_hypernova will be making a request for and the **pyramid request**:

```py
def get_batch_url(job_group, pyramid_request): ...
```

This will be called right before send _on every job group request_. If you're doing an expensive operation to retrieve this url, consider memoizing it.
