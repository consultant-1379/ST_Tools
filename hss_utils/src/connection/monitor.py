#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

#import logging
import e3utils.log as logging
_DEB = logging.internal_debug
_WRN = logging.internal_warning

import Queue
import threading
# 3rdParty
import pexpect

import session
from . import Monitor

class MonitorTspCLI(Monitor):

    def __init__(self, channel):
        Monitor.__init__(self, channel)

        self.__session = None
        self.__channel = channel
        self.__autoclose = False
        self.__ready = False
        self.__running = False
        self.__CLI_server_host = None
        self.__CLI_server_port = None

    @property
    def monitor_type(self):
        return 'MonitorTspCLI'

    @property
    def filter_expression(self):
        raise NotImplementedError()

    @property
    def start_command(self):
        raise NotImplementedError()

    @property
    def session(self):
        return self.__session

    def set_CLI_server(self, host, port):
        self.__CLI_server_host = host
        self.__CLI_server_port = port

    @property
    def ready(self):
        return self.__running

    def bootstrap(self, force_restart = False):
        if self.ready and not force_restart:
            return

        if  force_restart:
            _DEB('Re-Starting %s' % self.monitor_type)
            running = False
        else:
            _DEB('Starting %s' % self.monitor_type)
            running = self.__running
 
        while not running:
            try:
                self.__session = session.TelorbCLI(self.__channel.clone())
                self.__session.set_CLI_server(self.__CLI_server_host, self.__CLI_server_port)
                self.__session.open()
                answer = {'To exit monitor mode type Ctrl-c': ''}
                self.session.sendoptionallines(self.start_command, answer, synchronous=False)
                running = True
                self.__running = True

            except Exception, e:
                _DEB('Problem in bootstrap: %s' % e)
                self.__session.close()


    def stop(self):
        if self.ready:
            _DEB('Stopping %s' % self.monitor_type)

        self.__running = False

    def shutdown(self):
        _DEB('Executing  shutdown for %s' % self.monitor_type)
        if self.session.ready:
            self.session.echo_removal = False
            self.session.sendline(chr(3), synchronous=True)
            self.session.close()


class TspNotificationMonitor(MonitorTspCLI):

    def __init__(self, channel):
        MonitorTspCLI.__init__(self, channel)

    @property
    def monitor_type(self):
        return 'Tsp Notification Monitor'

    @property
    def filter_expression(self):
        return 'NOTIFICATION(.+)NotificationType:.+\r\n'

    @property
    def start_command(self):
        return '/CLI/AlarmsAndNotifications/notificationsmonitor'

class TspAlarmMonitor(MonitorTspCLI):

    def __init__(self, channel):
        MonitorTspCLI.__init__(self, channel)

        self.__extra_info = False

    def enable_extra_info(self):
        self.__extra_info = True

    @property
    def monitor_type(self):
        return 'Tsp Alarm Monitor'

    @property
    def filter_expression(self):
        if self.__extra_info:
            return 'ALARM (.)+\r\n\r\n'

        return 'ALARM (.)+\r\n'

    @property
    def start_command(self):
        if self.__extra_info:
            return '/CLI/AlarmsAndNotifications/alarmsmonitor -d'

        return '/CLI/AlarmsAndNotifications/alarmsmonitor'
