#!/usr/bin/env python

__version__ = '2.3'
__author__ = 'Mitxel Garcia'
__email__ = 'mitxel.garcia@ericsson.com'

import os
from distutils.core import setup


setup(
    name='rtc_gateway',
    version=__version__,
    description='Service for RTC Gateway',
    author=__author__,
    author_email=__email__,
    classifiers=[
        'Programming Language :: Python :: 2.7'
    ],
    packages=['gateway'],
    package_dir={'gateway': 'gateway'},      
    scripts=['rtc_gateway'],
    install_requires=['e3utils','hss_utils'],
    data_files=[('/usr/lib/systemd/system', ['rtc_gateway.service']),
                ('/etc/dbus-1/system.d', ['com.ericsson.hss.rtc_gateway.conf'])]
)
