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
from hss_utils.st_command import CommandFailure, ExecutionTimeout

import e3utils.log as logging
_DEB = logging.internal_debug
_WRN = logging.warning
_ERR = logging.error
_INF = logging.info

try:
    import hss_utils.rosetta
    import hss_utils.rosetta.services
    _ROSETTA_AVAILABLE_ = True
except ImportError as e:
    _WRN('Cannot import hss_utils.rosetta: %s' % e)
    _WRN('Rosetta access will be disabled')
    _ROSETTA_AVAILABLE_ = False


class DummyNet(Node):

    def __init__(self, config={}, traffic_type=None):

        Node.__init__(self)

        if 'host' not in config.keys():
            raise ValueError('host missing')
        if 'port' not in config.keys():
            config['port'] = '22'


        self.__config = config
        self.__traffic_type = traffic_type
        self.__session_type=hss_utils.connection.session.StandardLinux
        self.__pipes = {}

        self.create_connection(config=self.config, session_type=hss_utils.connection.session.StandardLinux)
        self.__HSS_peer = {}

        env, config = hss_utils.rosetta.services.get_env_for_localhost()
        if self.__traffic_type == 'ldap':
            self.__HSS_peer.update({'ldap': config.get_cabinet_ldap_vip(cabinet=0)})
        elif self.__traffic_type == 'map':
            self.__HSS_peer.update({'map1': config.get_cabinet_map1(cabinet=0)})
            self.__HSS_peer.update({'map2': config.get_cabinet_map2(cabinet=0)})
        elif self.__traffic_type == 'udm':
            self.__HSS_peer.update({'udm': config.get_cabinet_http_vip(cabinet=0)})

        else:
            raise CommandFailure('Dummynet traffic type "%s" not supportted' % self.__traffic_type)
        self.__out = []
        self.__in = []

    @property
    def config(self):
        return self.__config

    @property
    def session_type(self):
        return self.__session_type

    @property
    def outgoing(self):
        if not self.__out:
            for key, value in self.pipes.iteritems():
                for item in self.__HSS_peer.values():
                    if hss_utils.st_command.is_ip_in_net(value['from'], item):
                            self.__out.append(key)

        return self.__out

    @property
    def incoming(self):
        if not self.__in:
            for key, value in self.pipes.iteritems():
                for item in self.__HSS_peer.values():
                    if hss_utils.st_command.is_ip_in_net(value['to'], item):
                        self.__in.append(key)


        return self.__in

    @property
    def pipes(self):
        if not self.__pipes:
            cmd = 'sudo ipfw list'
            for line in self.run_command(cmd):
                if 'pipe' in line:
                    self.__pipes.update({line.split()[2]:{'from':line.split()[5],'to':line.split()[7],'info':line}})
                    self.pipe_configuration(line.split()[2])


        return self.__pipes


    def pipe_configuration(self,pipe):
        try:
            cmd = 'sudo ipfw pipe show %s 2>/dev/null' % pipe
            answer = self.run_command(cmd)
            self.__pipes[pipe].update({'delay':' '.join(answer[0].split()[2:4])})
            self.__pipes[pipe].update({'plr':answer[1].split()[3]})
        except Exception as e:
            _DEB('Error when showing pipes info:%s' % answer)
            raise CommandFailure('Exception generated:%s' % e)

    @property
    def allowed_pipes(self):
        return self.incoming + self.outgoing


    def enable_pipe(self,pipes,delay,lpr):
        for pipe in pipes:
            if pipe not in self.allowed_pipes:
                raise CommandFailure('Pipe "%s" not valid. Allowed values are %s' % (pipe, (' '.join(self.allowed_pipes))))
            cmd = 'sudo ipfw pipe %s config delay %s plr %s' % (pipe, delay, lpr)
            self.run_command(cmd)

    def disable_pipe(self,pipes):
        for pipe in pipes:
            if pipe not in self.allowed_pipes:
                raise CommandFailure('Pipe "%s" not valid. Allowed values are %s' % (pipe, (' '.join(self.allowed_pipes))))
            cmd = 'sudo ipfw pipe %s config delay 0' % pipe
            self.run_command(cmd)

    def pipe_outgoing(self):
        result = []
        for key, value in self.pipes.iteritems():
            for item in self.__HSS_peer.values():
                if hss_utils.st_command.is_ip_in_net(value['from'], item):
                    result.append(value['info'] + '\tdelay: %s\tplr: %s' % (value['delay'], value['plr']))

        return result

    def pipe_incoming(self):
        result = []
        for key, value in self.pipes.iteritems():
            for item in self.__HSS_peer.values():
                if hss_utils.st_command.is_ip_in_net(value['to'], item):
                    result.append(value['info'] + '\tdelay: %s\tplr: %s' % (value['delay'], value['plr']))

        return result


