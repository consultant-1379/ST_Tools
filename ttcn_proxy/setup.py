#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='ttcn_proxy',
    version='1.0',
    description='Telnet proxy for connecting to TitanSim application',
    author='Mitxel Garcia, Tobias Diaz',
    author_email='mitxel.garcia@ericsson.com, tobias.diaz@ericsson.com',
    scripts=['ttcn_proxy']
)
