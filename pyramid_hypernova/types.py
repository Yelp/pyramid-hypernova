# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from collections import namedtuple


Job = namedtuple('Job', (
    'name',
    'data',
    # `context` is passed to pyramid-hypernova by consuming applications from the render function.
    # It is forwarded verbatim to the Hypernova server, and can be used to pass extra arbitrary
    # request or component level information.
    'context',
))


JobResult = namedtuple('JobResult', (
    'error',
    'html',
    'job',
))

HypernovaError = namedtuple('HypernovaError', (
    'name',
    'message',
    'stack',
))
