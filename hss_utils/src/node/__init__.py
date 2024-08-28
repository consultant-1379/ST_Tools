#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import Queue
import ntpath
import re
import os
import time
import pexpect
import hss_utils.connection as connection
from hss_utils.st_command import clear_ansi

import e3utils.log as logging
_DEB = logging.internal_debug
_WRN = logging.warning
_ERR = logging.error
_INF = logging.info

CONNECTION = 0
OPENNED = 1


class Node(object):
    def __init__(self):

        self.__default_connection = 'main'
        self.__connections = {}
        self.__monitors = {}

    def __str__(self):
        info = ''
        for connection in self.__connections.iterkeys():
            info += '(ConId:%s Endpoint:%s Opened:%s) ' % (connection, self.get_channel(connection).endpoint, self.__connections[connection]['opened']) 

        return info

    @property
    def datetime(self):
        cmd = 'date +"%Y-%m-%dT%H:%M:%S"'
        answer = self.run_command(cmd)
        return answer[-1]

    def get_channel(self, identity = 'main'):
        if not self.__connections[identity]['opened']:
            self.__connections[identity]['connection'].open()
            self.__connections[identity]['opened'] = True

        return self.__connections[identity]['connection'].channel

    def get_sync_expression(self, identity = 'main'):
        return self.__connections[identity]['connection'].sync_expression

    def get_connection(self, identity = 'main'):
        if not self.__connections[identity]['opened']:
            self.__connections[identity]['connection'].open()
            self.__connections[identity]['opened'] = True

        return self.__connections[identity]['connection']

    def check_available_connection(self, identity):
        return identity in  self.__connections.keys()

    def add_connection(self, identity, connection):
        self.__connections.update({str(identity) : connection})

    def add_monitor(self, identity, monitor):
        self.__monitors.update({str(identity) : monitor})

    def del_monitor(self, identity):
        del self.__monitors[str(identity)]

    def connection(self, identity = None):
        if identity is None:
            identity = self.__default_connection
        if not self.__connections[identity]['opened']:
            self.__connections[identity]['connection'].open()
            self.__connections[identity]['opened'] = True

        return self.__connections[identity]['connection']

    def open_connection(self, identity = 'main'):
        if not self.__connections[identity]['opened']:
            self.__connections[identity]['connection'].open()
            self.__connections[identity]['opened'] = True

    def create_connection(self,config, session_type, identity ='main', allow_x11_forwarding = False,force_open=False, ssh_key=None,timeout=60.0):
        if identity in self.__connections.keys():
            return self.__connections[identity]['connection']

        endpoint = connection.ssh.SSHEndpoint(config)
        channel = connection.ssh.SSHChannel(endpoint, timeout=timeout)
        if allow_x11_forwarding:
            channel.enable_x11_forwarding()

        if ssh_key is not None:
            channel.ssh_key=ssh_key

        new_connection =  session_type(channel)

        if force_open:
            new_connection.open()
            self.add_connection(identity,{'connection': new_connection, 'opened' : True, 'extended':False, 'childs':[]})
        else:
            self.add_connection(identity,{'connection': new_connection, 'opened' : False, 'extended':False, 'childs':[]})

        return new_connection

    def extend_connection(self, identity, config, session_type, parent = 'main'):
        if identity in self.__connections.keys():
            if self.__connections[identity]['opened']:
                return self.__connections[identity]['connection']
            del self.__connections[identity]

        endpoint = connection.ssh.SSHEndpoint(config)
        channel = connection.ssh.SSHChannelExtension(self.get_channel(parent).clone(), endpoint)
        new_connection = session_type(channel)
        _DEB('new connection %s opened ' % new_connection)
        self.__connections[parent]['childs'].append(identity)
        self.add_connection(identity,{'connection': new_connection, 'opened' : False, 'extended':True, 'childs':[]})

        return new_connection

    def create_monitor(self,config, monitor_type, identity):
        if identity in self.__monitors.keys():
            return self.__monitors[identity]['monitor']

        endpoint = connection.ssh.SSHEndpoint(config)
        channel = connection.ssh.SSHChannel(endpoint, timeout=20.0)
        monitor =  monitor_type(channel)
        self.add_monitor(identity,{'monitor': monitor, 'running' : False})
        return monitor

    def start_monitor(self, identity):
        if not self.__monitors[identity]['running']:
            self.__monitors[identity]['monitor'].start()
            self.__monitors[identity]['running'] = True
            while not self.__monitors[identity]['monitor'].ready:
                time.sleep(float(1))
                _DEB('Waiting for monitor start: %s' % identity)

    def wait_event(self, identity, timeout=-1):
        self.start_monitor(identity)
        try:
            return self.__monitors[identity]['monitor'].get(timeout=timeout)
        except Queue.Empty as e:
            return None

    def stop_monitor(self, identity):
        if self.__monitors[identity]['running'] and self.__monitors[identity]['monitor'].is_alive():
                _DEB('Stopping monitor: %s' % identity)
                self.__monitors[identity]['monitor'].stop()
                self.__monitors[identity]['monitor'].join()
                self.__monitors[identity]['running'] = False
                _DEB('Stopped monitor: %s' % identity)

    def remove_monitor(self, identity):
        self.stop_monitor(identity)
        self.del_monitor(identity)

    def set_default_connection(self, identity ='main'):
        self.__default_connection = str(identity)

    def extract_answer(self, full_answer):
        _DEB('Answer received:%s' % repr(full_answer))
        return clear_ansi(full_answer).split('\r\n')[:-1]

    def run_command(self, cmd, identity = None, answer = {}, timeout = None, full_answer = False):
        connection = self.connection(identity)

        _DEB('Execute sync cmd: %s by connection %s' % (cmd, connection))
        if full_answer:
            return clear_ansi(connection.sendoptionallines(cmd, answer, synchronous=True, timeout = timeout))

        return self.extract_answer(connection.sendoptionallines(cmd, answer, synchronous=True, timeout = timeout))  

    def run_command_async(self, cmd, identity = 'main', answer = {}, parent = None, timeout = None):
        if identity not in self.__connections:
            if parent is None:
                parent = self.__default_connection
            self.add_connection(str(identity),{'connection':self.__connections[parent]['connection'].clone() , 'opened' : False})

        _DEB('Execute async cmd: %s by connection %s' % (cmd, self.__connections[str(identity)]))
        self.connection(str(identity)).sendoptionallines(cmd , answer,synchronous=False, timeout = timeout)

    def get_return_code(self, identity = None):
        cmd = 'echo $?'
        answer = self.run_command(cmd, identity=identity)
        if '0' in answer:
            return 0
        else:
            return 1

    def get_output_command_async(self, identity = 'main'):
        return self.connection(str(identity)).channel.stdout

    def stop_command_async(self, identity = 'main',answer={}):
        _DEB('Stop async cmd: %s' % identity)
        output = self.connection(str(identity)).sendoptionallines(chr(3),answer, timeout=-1)
        if identity != 'main':
            self.connection(str(identity)).sendline('exit')

        return output

    def download(self,source, destination, identity= 'main', timeout = None):
        if timeout is not None:
            self.__connections[identity]['connection'].channel.set_transfer_timeout(float(timeout))

        return self.__connections[identity]['connection'].channel.download(source, destination)

    def upload(self,source, destination, identity= 'main', timeout = None):
        if timeout is not None:
            self.__connections[identity]['connection'].channel.set_transfer_timeout(float(timeout))
        return self.__connections[identity]['connection'].channel.upload(source, destination)

    def close_connection(self, identity = 'main'):
        _DEB('Close connection for identity: %s' % identity)

        if identity not in self.__connections.keys():
            _DEB('Connection %s does not exist' % identity)
            return

        if not self.__connections[identity]['opened']:
            _DEB('Connection %s seems to be already closed' % identity)
            return

        childs = self.__connections[identity].get('childs',[])
        for conId in childs:
            self.close_connection(identity = conId)

        try:
            self.__connections[identity]['connection'].close()

        except (connection.ConnectionFailed, connection.ConnectionTimeout) as e:
            _WRN('Close connection problem: %s' % e )
        except OSError as e:
            _WRN('Close connection problem: %s' % e )
        except pexpect.ExceptionPexpect as e:
            _WRN('Close connection problem: %s' % e )
        except Exception as e:
            _WRN('Close connection problem: %s' % e )

        self.__connections[identity]['opened'] = False

    def check_open_connection(self, identity = 'main'):
        _DEB('Check open connection for: %s' % identity)
        try:
            return self.__connections[identity]['opened']
        except KeyError as e:
            _WRN('Connection not found: %s' % e )
            return False

    def release_connection(self, identity = 'main'):
        _DEB('Release connection for: %s' % identity)

        if identity not in self.__connections.keys():
            _DEB('Connection %s does not exist' % identity)
            return

        childs = self.__connections[identity].get('childs',[])
        for conId in childs:
            self.release_connection(identity = conId)

        self.close_connection(identity)

        try:
            del self.__connections[identity]
        except KeyError:
            _DEB('Connection %s seems to be already released' % identity)

    def release(self):
        _DEB('Releasing current connections')
        current_connections = self.__connections.keys()
        for connection in current_connections:
            self.close_connection(identity = connection)

        for monitor in self.__monitors.keys():
            try:
                self.stop_monitor(monitor)
            except KeyError:
                continue

        self.__monitors={}
        self.__connections={}

    def file_exist(self, fname, identity = None):
        if identity is None:
            identity = self.__default_connection
        cmd = 'ls %s' % fname
        return 'No such file or directory' not in self.run_command(cmd, identity)[0]










