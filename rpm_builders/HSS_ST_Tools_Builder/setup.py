#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='hss_st_tools_builder',
    version='3.0',
    description='Tool for generating RPM of C++ HSS ST tools ',
    author='Mitxel Garcia',
    author_email='mitxel.garcia@ericsson.com',
    scripts=['HSS_ST_Tools_Builder']
)
