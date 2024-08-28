#!/usr/bin/env python

from distutils.core import setup

setup(
    name='run_titansim_HSS_BAT',
    version='5.16',
    description='Configure and control the HSS TitanSim application',
    author='Mitxel Garcia, Tobias Diaz',
    author_email='mitxel.garcia@ericsson.com, tobias.diaz@ericsson.com',
    scripts=['run_titansim_HSS_BAT'],
    packages=['shared','scenario','components'],
    package_dir={
        'shared': 'shared',
        'scenario': 'scenario',
        'components': 'components'
    }
)
