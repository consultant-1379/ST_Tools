#!/usr/bin/env python

__version__ = '3.2'
__author__ = 'Mitxel Garcia'
__email__ = 'mitxel.garcia@ericsson.com'

import os
from distutils.core import setup


setup(
    name='rtc_controller',
    version=__version__,
    description='Service for RTC execution controller',
    author=__author__,
    author_email=__email__,
    classifiers=[
        'Programming Language :: Python :: 2.7'
    ],
    packages=['controller'],
    package_dir={'controller': 'controller'},
    scripts=['rtc_controller'],
    install_requires=['e3utils','hss_utils'],
    data_files=[('/etc/dbus-1/system.d', ['com.ericsson.hss.rtc_controller.conf']),
                ('/etc/rtc_controller',['service_configuration_template.json'])]
)
