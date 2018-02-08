# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

from collections import namedtuple


Job = namedtuple('Job', (
    'name',
    'data',
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
