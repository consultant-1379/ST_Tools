#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='ttcn_monitor',
    version='1.0',
    description='Monitor for handling TitanSim application variables via telnet',
    author='Mitxel Garcia, Tobias Diaz',
    author_email='mitxel.garcia@ericsson.com, tobias.diaz@ericsson.com',
    scripts=['ttcn_monitor']
)
