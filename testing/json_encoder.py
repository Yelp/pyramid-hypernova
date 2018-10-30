# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import json


class ComplexJSONEncoder(json.JSONEncoder):
    """ A custom JSONEncoder that, in addition to everything that the generic JSONEncoder already
    supports, also encodes complex numbers. Copied from https://docs.python.org/2/library/json.html
    """

    def default(self, obj):
        if isinstance(obj, complex):
            return [obj.real, obj.imag]
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)
