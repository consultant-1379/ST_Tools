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
import hss_utils.node.gentraf
from . import ExecutionTimeout
from . import NotFound
from . import CommandFailure
from . import WrongParameter
from . import ip2int
from . import is_ip_in_net


def GTLA_list_backup_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-b','--btype',
                      action='store', default='all',
                      choices = ['local', 'remote', 'all'],
                      help='Type of backup',
                      dest='btype')

    return (parser)

def run_GTLA_list_backup(user_config, node):

    btypes = []
    if user_config.btype == 'all':
        btypes = ['local', 'remote']
    else:
        btypes.append(user_config.btype)

    backups = node.allowed_backups

    for btype in btypes:
        backup_list = []
        for backup in backups.keys():
            if backups[backup]['type'] == btype:
                backup_list.append(backups[backup]['name'])
        if backup_list:
            print '%s backups\n\t%s' % (btype, '\n\t'.join(backup_list))



def run_GTLA_get_active_backup(user_config, node):

    if node.active_backup is None:
        raise NotFound('Active backup not found')

    print node.active_backup



def GTLA_restore_backup_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-b','--backupname',
                      action='store', default=None,
                      help='Backup name to be restored. By default the active backup will be restored',
                      dest='backupname')
    command_params.add_argument('-i','--initialize',
                      action='store_true', default=False,
                      help='Before restoring backup execute a GTLA factory reset',
                      dest='initialize')
    command_params.add_argument('-t',type=int,
                      action='store', default=300,
                      help='Max time in sec waiting for command. By default is "%(default)s".',
                      dest='max_time')

    return (parser)


def run_GTLA_restore_backup(user_config, node):

    if user_config.backupname is None:
        user_config.backupname = node.active_backup
    elif not node.is_backup_allowed(user_config.backupname):
        raise WrongParameter('%s is not a valid backup. Use GTLA_list_backup' % user_config.backupname)

    if user_config.initialize:
        node.initialize()

    node.restore_backup(user_config.backupname, user_config.max_time)
    status = node.openldap_status
    if not status.startswith('RUNNING'):
        raise CommandFailure('Faulty OpenLdap status after restore: %s '% status)



def GTLA_check_backup_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('BACKUPNAME',
                        help='Backup name used as filter')

    return (parser)


def run_GTLA_check_backup(user_config, node):

    if not node.is_backup_allowed(user_config.BACKUPNAME):
        raise NotFound('%s is not a valid backup' % user_config.BACKUPNAME)

def GTLA_create_backup_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('BACKUPNAME',
                        help='Backup name used as filter')
    command_params.add_argument('-s','--skip-export',
                      action='store_true', default=False,
                      help='DO NOT export the backup. Keep it as local backup',
                      dest='skip_export')
    command_params.add_argument('-t',
                      action='store', default=600,
                      help='Max time in sec waiting for command. By default is "%(default)s".',
                      dest='max_time')

    return (parser)


def run_GTLA_create_backup(user_config, node):

    if node.is_backup_allowed(user_config.BACKUPNAME):
        raise CommandFailure('%s backup already exists' % user_config.BACKUPNAME)

    node.set_label(user_config.BACKUPNAME)
    node.make_backup(user_config.BACKUPNAME, user_config.max_time)

    if not user_config.skip_export:
        node.export_backup(user_config.BACKUPNAME)


def run_GTLA_restart(user_config, node):

    node.stop()
    status = node.openldap_status
    if not status.startswith('STOPPED'):
        raise CommandFailure('Faulty OpenLdap status after stop_ldap: %s '% status)
    print status
    node.start()
    status = node.openldap_status
    if not status.startswith('RUNNING'):
        raise CommandFailure('Faulty OpenLdap status after start_ldap: %s '% status)
    print status


def run_GTLA_get_status(user_config, node):

    print node.openldap_status






