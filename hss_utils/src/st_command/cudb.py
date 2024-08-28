#!/usr/bin/env python
#

import sys
import os
CWD = os.getcwd()
import os.path
import time
import traceback
import argparse
import re
import random

import e3utils.log as logging
_DEB = logging.internal_debug
_WRN = logging.warning
_ERR = logging.error
_INF = logging.info

import hss_utils.rosetta
import hss_utils.rosetta.services
import hss_utils.node.cudb
from . import ExecutionTimeout
from . import NotFound
from . import CommandFailure
from . import WrongParameter
from . import ip2int
from . import is_ip_in_net


def CUDB_list_backup_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-b','--btype',
                      action='store', default='ALL',
                      choices = ['SYSTEM', 'CLUSTER', 'ALL'],
                      help='Type of backup',
                      dest='btype')

    return (parser)

def run_CUDB_list_backup(user_config, node):

    btypes = []
    if user_config.btype == 'ALL':
        btypes = ['SYSTEM', 'CLUSTER']
    else:
        btypes.append(user_config.btype)

    backups = node.allowed_backups
    for backuptype, backuplist in backups.iteritems():
        if backuptype not in btypes:
            continue
        print '\n%s BACKUP' % backuptype
        for backup in backuplist:
            name, date = backup
            print '\t%s\t%s' % (date, name)


def CUDB_restore_backup_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-b','--backupname',
                      action='store', default=None,
                      help='Backup name to be restored.',
                      dest='backupname')
    command_params.add_argument('-t',
                      action='store', default=3600,
                      help='Max time in sec waiting for command. By default is "%(default)s".',
                      dest='max_time')

    return (parser)


def run_CUDB_restore_backup(user_config, node):

    if user_config.backupname is None:
        raise WrongParameter('Missing backup name parameter')

    backups = node.allowed_backups
    for backuptype, backuplist in backups.iteritems():
        for backup in backuplist:
            name, date = backup
            if user_config.backupname == name:
                node.restore_backup(backuptype, name, int(user_config.max_time))
                return

    raise WrongParameter('%s backup not found' % user_config.backupname)






