#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='hss_bat_builder',
    version='3.1',
    description='Tool for creating symb_links, Makefile and rpm of HSS BAT',
    author='Mitxel Garcia',
    author_email='mitxel.garcia@ericsson.com',
    scripts=['HSS_BAT_Builder']
)
