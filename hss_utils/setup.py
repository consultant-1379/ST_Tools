#!/usr/bin/env python

import sys
import copy

from distutils.core import setup
from distutils.command.install import install

_PACKAGES_ = [
    'hss_utils',
    'hss_utils.dbus',
    'hss_utils.connection',
    'hss_utils.node',
    'hss_utils.st_command',
    'hss_utils.log',
    'hss_utils.rosetta']

_PACKAGE_DIR_ = {
    'hss_utils' :'src',
    'hss_utils.dbus': 'src/dbus',
    'hss_utils.connection': 'src/connection',
    'hss_utils.node' : 'src/node',
    'hss_utils.st_command' : 'src/st_command',
    'hss_utils.log':'src/log',
    'hss_utils.rosetta': 'src/rosetta'}

_BASIC_LIBRARIES_ = [
    'hss_utils',
    'hss_utils.log',
    'hss_utils.connection']


# Hidden option (do not show in --help)
if '--only-basic' in sys.argv:
    sys.argv.remove('--only-basic')
    packages = copy.copy(_PACKAGES_)
    for package in packages:
        if package not in _BASIC_LIBRARIES_:
            _PACKAGES_.remove(package)
            del(_PACKAGE_DIR_[package])


setup(
    name='hss_utils',
    version='7.60',
    description='Automation framework library',
    author='Mitxel Garcia',
    author_email='mitxel.garcia@ericsson.com',
    packages=_PACKAGES_,
    package_dir=_PACKAGE_DIR_
)
