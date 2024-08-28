#!/usr/bin/env python

'''
ESS: TeBuilder manager service setup module
'''

__version__ = '2.3'
__author__ = 'Mitxel Garcia'
__email__ = 'mitxel.garcia@ericsson.com'

import os
from distutils.core import setup


setup(
    name='rtc_build_handler',
    version=__version__,
    description='Service for HSS build handling',
    author=__author__,
    author_email=__email__,
    classifiers=[
        'Programming Language :: Python :: 2.7'
    ],
    packages=['build_handler'],
    package_dir={'build_handler': 'build_handler'},
    scripts=['rtc_build_handler'],
    install_requires=['e3utils','hss_utils'],
    data_files=[('/etc/dbus-1/system.d', ['com.ericsson.hss.rtc_build_handler.conf'])]
)
