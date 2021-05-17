# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from setuptools import find_packages
from setuptools import setup


setup(
    name='pyramid-hypernova',
    version='8.0.0',
    author='Yelp, Inc.',
    author_email='opensource+pyramid-hypernova@yelp.com',
    license='MIT',
    url='https://github.com/Yelp/pyramid-hypernova',
    description="A Python client for Airbnb's Hypernova server, for use with the Pyramid web framework.",
    classifiers=[
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'License :: OSI Approved :: MIT License',
    ],
    install_requires=[
        'fido',
        'more-itertools',
        'requests',
    ],
    packages=find_packages(exclude=('tests*', 'testing*')),
)
