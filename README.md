pyramid_hypernova
--------------

This project contains a [Pyramid](http://docs.pylonsproject.org/en/latest/docs/pyramid.html) tween that implements a client for Airbnb's [Hypernova](//github.com/airbnb/hypernova) service.

Features include:

* Allows SSR React components to be transparently embedded within Python-based templating languages (Cheetah, jinja2, etc...)

* Batches and parallelizes calls to the Hypernova service.

* Supports plugins, which may hook into any of Hypernova's [lifecycle events](https://github.com/airbnb/hypernova/blob/master/docs/client-spec.md#plugin-lifecycle-api).

Install
-------

```
    pip install pyramid_hypernova
```

Usage
-----

In your service's webapp, you can configure the Pyramid tween like so:

```
    def get_batch_url():
        return 'https://localhost:8080/batch'

    config.registry.settings['pyramid_hypernova.get_batch_url'] = get_batch_url
    config.add_tween('pyramid_hypernova.tweens.hypernova_tween_factory')
```
