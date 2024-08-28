#!/usr/bin/env python

from distutils.core import setup

setup(
    name='ldif_builder',
    version='1.0',
    release='3',
    description='Ldif generation/population script',
    author='Tobias Diaz',
    author_email='tobias.diaz@ericsson.com',
    scripts=['ldif_builder'],
    packages=['ldaphelper'],
    package_dir={
        'ldaphelper': 'ldaphelper'
    }
)
