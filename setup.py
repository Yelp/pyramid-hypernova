from setuptools import find_packages
from setuptools import setup


setup(
    name='pyramid-hypernova',
    version='10.0.2',
    author='Yelp, Inc.',
    author_email='opensource+pyramid-hypernova@yelp.com',
    license='MIT',
    url='https://github.com/Yelp/pyramid-hypernova',
    description="A Python client for Airbnb's Hypernova server, for use with the Pyramid web framework.",
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'License :: OSI Approved :: MIT License',
    ],
    python_requires='>=3.10',
    install_requires=[
        'fido',
        'more-itertools',
        'requests',
    ],
    packages=find_packages(exclude=('tests*', 'testing*')),
)
