#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import Queue
import ntpath
import re
import os
import socket

import hss_utils.connection
import hss_utils.connection.session
import hss_utils.connection.ssh
import hss_utils.st_command

from hss_utils.st_command import clear_ansi
from . import Node

import e3utils.log as logging
_DEB = logging.internal_debug
_WRN = logging.warning
_ERR = logging.error
_INF = logging.info

CLUSTER_BACKUP_STORAGE = '/local/cudb/mysql/ndbd/backup/BACKUP/'
SYSTEM_BACKUP_STORAGE = '/cluster/tmp/backups/'


class Cudb(Node):

    def __init__(self, config={}):

        Node.__init__(self)

        if 'host' not in config.keys():
            raise ValueError('host missing')
        if 'port' not in config.keys():
            config['port'] = '22'
        if 'user' not in config.keys():
            config['user'] = 'root'
        if 'password' not in config.keys():
            config['password'] = 'ericsson'

        self.__config = config
        self.__session_type=hss_utils.connection.session.StandardLinux

        self.create_connection(config=self.config, session_type=self.session_type)
        self.set_default_connection()
        self.__allowed_backups = {}

    @property
    def config(self):
        return self.__config

    @property
    def session_type(self):
        return self.__session_type

    def extend_connection(self, identity, host, port = '22', user='root',password='ericsson', parent = 'main'):
        config = {'host':host, 'port':port,'user':user,'password': password}

        return Node.extend_connection(self, identity,config=config, session_type=self.session_type, parent=parent)

    @property
    def allowed_backups(self):
        if not self.__allowed_backups:
            cmd = 'ls -ltr %s' % SYSTEM_BACKUP_STORAGE
            lines = self.run_command(cmd)
            error_code = self.get_return_code()
            if error_code != 0:
                raise hss_utils.st_command.CommandFailure(lines)
            for line in lines:
                if line.startswith('d'):
                    backup_name = clear_ansi(line).split()[-1]
                    backup_date = ' '.join(clear_ansi(line).split()[5:-1])
                    try:
                        self.__allowed_backups['SYSTEM'].append((backup_name,backup_date))
                    except KeyError:
                        self.__allowed_backups.update({'SYSTEM':[(backup_name,backup_date)]})


            payload = self.processors[0]
            self.extend_connection(payload, payload)
            cmd = 'ls -ltr %s' % CLUSTER_BACKUP_STORAGE
            lines = self.run_command(cmd, identity=payload)
            error_code = self.get_return_code()
            if error_code != 0:
                raise hss_utils.st_command.CommandFailure(lines)
            for line in lines:
                if line.startswith('d'):
                    backup_name = clear_ansi(line).split()[-1]
                    backup_date = ' '.join(clear_ansi(line).split()[5:-1])
                    try:
                        self.__allowed_backups['CLUSTER'].append((backup_name,backup_date))
                    except KeyError:
                        self.__allowed_backups.update({'CLUSTER':[(backup_name,backup_date)]})
        return self.__allowed_backups

    @property
    def restore_cluster_backup_cmd(self):
        return 'cudbManageStore -a -o restore -l %s' % CLUSTER_BACKUP_STORAGE

    @property
    def restore_system_backup_cmd(self):
        return 'cudbSystemDataBackupAndRestore -f -F --restore %s' % SYSTEM_BACKUP_STORAGE

    @property
    def processors(self):
        processors = []
        cmd = 'cat /etc/hosts | grep PL_'
        lines = self.run_command(cmd)
        for line in lines:
            processors.append(line.split()[1])

        return processors



    def backup_type(self,backupname):
        pass


    @property
    def active_backup(self):
        pass


    def make_backup(self,name, timeout):
        pass


    def restore_backup(self, backuptype, name, timeout):
        if backuptype == 'CLUSTER':
            cmd = '%s%s' % (self.restore_cluster_backup_cmd, name)
            answer = self.run_command(cmd, timeout=timeout)
        else:
            cmd = '%s%s' % (self.restore_system_backup_cmd, name)
            answer = self.run_command(cmd, answer={'Are you sure you want to continue \(y\/n\)\?' : 'y'}, timeout=timeout)



