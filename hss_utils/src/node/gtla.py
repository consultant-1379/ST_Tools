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
from . import Node

import e3utils.log as logging
_DEB = logging.internal_debug
_WRN = logging.warning
_ERR = logging.error
_INF = logging.info

LOCAL_BACKUP_STORAGE = '/opt/gtla/backups/'
REMOTE_BACKUP_STORAGE = '/tsp/tcm_env/node_tools/gtla/backups/'

class CreateGtlaKeyFile(Exception):
    def __init__(self, message='Error creating gtla ssh key file'):
        self.__err = message

    def __str__(self):
        return '%s' % self.__err


USER_SSH_KEY_PATH = '~/.ssh/id_rsa_gtla'

class Gtla(Node):

    def __init__(self, config={}):

        Node.__init__(self)

        if 'host' not in config.keys():
            raise ValueError('host missing')
        if 'port' not in config.keys():
            config['port'] = '22'
        config['user'] = 'telorb'
        _DEB('GTLA config:%s' % config)

        self.__config = config
        self.__session_type=hss_utils.connection.session.StandardLinux
        self.__check_ssh_key_file()

        self.create_connection(config=self.config, session_type=hss_utils.connection.session.StandardLinux,ssh_key=os.path.expanduser(USER_SSH_KEY_PATH))
        self.set_default_connection()
        self.__allowed_backups = {}

    @property
    def config(self):
        return self.__config

    @property
    def session_type(self):
        return self.__session_type

    def __check_ssh_key_file(self):
        if not os.path.isfile(os.path.expanduser(USER_SSH_KEY_PATH)):
            cmd = 'mkdir -p ~/.ssh'
            stdout_value, stderr_value, returncode = hss_utils.st_command.execute_cmd(cmd,stdout= True,stderr = True)
            if returncode:
                raise CreateGtlaKeyFile
            cmd = 'cp /proj/hss_est/tcm_env/node_tools/generators/etc/id_rsa_gtla ~/.ssh/'
            stdout_value, stderr_value, returncode = hss_utils.st_command.execute_cmd(cmd,stdout= True,stderr = True)
            if returncode:
                raise CreateGtlaKeyFile

            cmd = 'chmod 600 ~/.ssh/id_rsa_gtla'
            stdout_value, stderr_value, returncode = hss_utils.st_command.execute_cmd(cmd,stdout= True,stderr = True)
            if returncode:
                raise CreateGtlaKeyFile


    @property
    def allowed_backups(self):
        if not self.__allowed_backups:
            cmd = 'sudo gtlactrl show_backups'
            answer = self.run_command(cmd, timeout=120.0)
            error_code = self.get_return_code()
            if error_code != 0:
                raise hss_utils.st_command.CommandFailure(answer)

            btype = None
            for line in answer:
                line = line.strip()
                if line in ['local backups:', 'remote backups:']:
                    btype = line.split()[0]
                    continue
                if btype is not None:
                    self.__allowed_backups.update({line.split()[1][1:-1]:{'name':line.split()[0], 'type':btype}})

        return self.__allowed_backups


    @property
    def active_backup(self):
        cmd = 'sudo gtlactrl'
        answer = self.run_command(cmd)

        label = None
        for line in answer:
            line = line.strip()
            if line.startswith('Base backup:'):
                label = line.split()[2]
                return self.allowed_backups[label]['name']

    @property
    def openldap_status(self):
        cmd = 'sudo gtlactrl'
        answer = self.run_command(cmd)
        for line in answer:
            line = line.strip()
            if line.startswith('OpenLDAP instance is'):
                return line.split()[3]

    def initialize(self):
        cmd = 'sudo gtlactrl initialize'
        answer = self.run_command(cmd)
        error_code = self.get_return_code()
        if error_code != 0:
            raise hss_utils.st_command.CommandFailure(answer)

    def start(self):
        cmd = 'sudo gtlactrl start_ldap'
        answer = self.run_command(cmd)
        error_code = self.get_return_code()
        if error_code != 0:
            raise hss_utils.st_command.CommandFailure(answer)

    def stop(self):
        cmd = 'sudo gtlactrl stop_ldap'
        answer = self.run_command(cmd)
        error_code = self.get_return_code()
        if error_code != 0:
            raise hss_utils.st_command.CommandFailure(answer)

    def set_label(self, label):
        cmd = 'sudo gtlactrl set_label "%s"' % label
        answer = self.run_command(cmd)
        error_code = self.get_return_code()
        if error_code != 0:
            raise hss_utils.st_command.CommandFailure(answer)

    def make_backup(self,name, timeout):
        cmd = 'sudo gtlactrl make_backup %s' % name
        answer = self.run_command(cmd, timeout=timeout)
        error_code = self.get_return_code()
        if error_code != 0:
            raise hss_utils.st_command.CommandFailure(answer)

    def export_backup(self,name):
        self.download('%s%s.zip' % (LOCAL_BACKUP_STORAGE, name), REMOTE_BACKUP_STORAGE)

    def restore_backup(self, backup, timeout):
        if backup == 'tcm_hss_empty':
            cmd = 'sudo gtlactrl clear_db'
        else:
            cmd = 'sudo gtlactrl load_backup %s' % backup

        answer = self.run_command(cmd, timeout=timeout)
        error_code = self.get_return_code()
        if error_code != 0:
            raise hss_utils.st_command.CommandFailure(answer)


    def is_backup_allowed(self, backup):
        for key in self.allowed_backups.keys():
            if backup == self.allowed_backups[key]['name']:
                return True

        return False
