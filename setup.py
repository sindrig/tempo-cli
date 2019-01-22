import os

import setuptools


PACKAGE_NAME = 'Tempo CLI'


def read(filename):
    return open(os.path.join(os.path.dirname(__file__), filename)).read()


setup_kwargs = dict(
    name=PACKAGE_NAME,
    version='0.0.1',
    description="Log work using the command line",
    long_description=read("README.md"),
    packages=setuptools.find_packages(exclude=['tests']),
    zip_safe=False,
    include_package_data=True,
    scripts=['bin/tempo-cli'],
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    install_requires=[
        'requests==2.21.0',
        'appdirs==1.4.3',
        'oauth2-client==1.1.0',
    ]
)


setuptools.setup(**setup_kwargs)
