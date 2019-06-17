pyramid-hypernova
--------------

[![PyPI version](https://badge.fury.io/py/pyramid-hypernova.svg)](https://pypi.python.org/pypi/pyramid-hypernova)
[![Coverage Status](https://coveralls.io/repos/github/Yelp/pyramid-hypernova/badge.svg)](https://coveralls.io/github/Yelp/pyramid-hypernova)

A Python client for Airbnb's [Hypernova](//github.com/airbnb/hypernova) server, for use with the [Pyramid](http://docs.pylonsproject.org/en/latest/docs/pyramid.html) web framework.

Features include:

* Allows SSR React components to be transparently embedded within Python-based templating languages (Cheetah, jinja2, etc...)

* Batches and parallelizes calls to the Hypernova service.

* Supports plugins, which may hook into any of Hypernova's [lifecycle events](https://github.com/airbnb/hypernova/blob/master/docs/client-spec.md#plugin-lifecycle-api).

Install
-------

```
pip install pyramid-hypernova
```

Usage
-----

In your service's Pyramid configuration (e.g. `webapp.py`), you can configure the Pyramid tween like so:

```python
def get_batch_url():
    return 'https://localhost:8080/batch'

config.registry.settings['pyramid_hypernova.get_batch_url'] = get_batch_url
config.add_tween('pyramid_hypernova.tweens.hypernova_tween_factory')
```


Original Contributors
------------

- [Matt Mulder](https://github.com/mxmul)
- [Mark Larah](https://github.com/magicmark)
- [Chris Kuehl](https://github.com/chriskuehl)
- [Francesco Agosti](https://github.com/fragosti)
- [Jeffrey Xiao](https://github.com/jeffrey-xiao)
