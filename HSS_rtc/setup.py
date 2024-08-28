#!/usr/bin/env python

from distutils.core import setup

setup(
    name='hss_rtc',
    version='4.28',
    description='Automatic execution of a Test Spec for HSS',
    author='Mitxel Garcia',
    author_email='mitxel.garcia@ericsson.com',
    scripts=['HSS_rtc'],
    packages=['HSS_rtc_lib',
              'HSS_rtc_lib.components',
              'HSS_rtc_lib.shared'],
    package_dir={
        'HSS_rtc_lib': 'HSS_rtc_lib',
        'HSS_rtc_lib.components': 'HSS_rtc_lib/components',
        'HSS_rtc_lib.shared': 'HSS_rtc_lib/shared'
    },
    data_files=[('HSS_rtc_templates', [
        'HSS_rtc_templates/CBA_test_case_template.json',
        'HSS_rtc_templates/TSP_test_case_template.json']
    )]
)
