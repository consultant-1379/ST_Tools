#!/usr/bin/env python
#

import sys
import os
import os.path
from datetime import datetime

import socket
HOSTNAME = socket.gethostname()

import time
import re
import getpass
import pexpect
import random
import threading
import Queue
import pprint
import copy
import operator

import hss_utils.node.gentraf
import hss_utils.st_command as st_command
import hss_utils.connection as connection
import hss_utils.node
import hss_utils.node.cba

import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning

from HSS_rtc_lib.shared import *
import ttcn_monitor
from . import bat_instance
from . import ExecutionConfigurationError
from . import ExecutionStartError
from . import ExecutionRunError



class BAT_telnet(bat_instance.BAT_base):
    def __init__(self, host, cabinet, config, id, instance, root_path, exec_config, executor,disable_graph=False, node_type=None):

        bat_instance.BAT_base.__init__(self, host, cabinet, config, id, instance, root_path, exec_config, executor,disable_graph=disable_graph)

        self.__phase_status = None
        self.__node_type = node_type
        self.__first_phase = ''
        self.__monitor = None
        self.answers = Queue.Queue()

    @property
    def monitor(self):
        return self.__monitor

    @monitor.setter
    def monitor(self, monitor):
        self.__monitor = monitor

    @property
    def node_type(self):
        return self.__node_type

    @property
    def first_phase(self):
        return self.__first_phase

    @first_phase.setter
    def first_phase(self, first_phase):
        self.__first_phase = first_phase

    @property
    def phase_status(self):
        return self.__phase_status

    @phase_status.setter
    def phase_status(self, phase_status):
        self.__phase_status = phase_status

    @property
    def update_parameters(self):
        try:
            if self.config['cps_scheduler']['enable']:
                params = self.config['parameters'].split()
                try:
                    position = params.index('-z')
                    value = params[position + 1].split(':')
                    if len(value) >= 2:
                        value[1] = '10'
                    else:
                        value += ['10']
                    params[position + 1] = ':'.join(value)
                except ValueError:
                    params += ['-z',':10']

                try:
                    position = params.index('-l')
                    value = params[position + 1].split(':')
                    value[0] = ''
                    try:
                        value[1] = ''
                        value[2] = ''
                    except (IndexError, ValueError):
                        pass

                    if len(value) > 1:
                        params[position + 1] = ':'.join(value)
                    else:
                        params[position] = ''
                        params[position + 1] =  ''
                except (IndexError, ValueError):
                    pass

                self.config['parameters'] = ' '.join(params)

        except KeyError:
            pass


        return self.executor.rtc_data.macro_translator(self.config['parameters']) + ' -E "%s"' % self.telnet_value

    @property
    def cmd(self):
        return 'run_titansim_HSS_BAT %s %s %s --force_manual --force-tmp %s --mc-port %s --dia-port-offset %s %s' % (('' if self.node_type == 'CLOUD' else '-V %s' % self.cabinet),
                                                                                                    self.update_parameters,
                                                                                                    self.disable_graph,
                                                                                                    self.temp_dir,
                                                                                                    self.mc_port,
                                                                                                    (100 * int(self.instance)),
                                                                                                    self.access_params)

    @property
    def monitor_ready(self):
        if self.monitor is not None:
            return self.monitor.online
        return False


    def stop_traffic(self):
        if self.execution_state == 'stopped':
            return
        if self.monitor is not None and self.monitor.online:
            self.monitor.shutdown()
            #self.monitor.join()
            #self.monitor = None
        #else:
            #self.channel.write_line(chr(3))


        self.monitor = None
        self.channel.write_line(chr(3))


    def release_monitor(self):
        if self.monitor is not None:
            self.monitor.shutdown()
            self.monitor.join()
            self.monitor = None

    def start_monitor(self):
        try:
            self.monitor = ttcn_monitor.TTCNClient(self.host,self.cli_telnet, self)
            self.monitor.start()
        except Exception, e:
            run_error = 'Problem starting TTCN_CLI %s' % str(e)
            _ERR(run_error)
            raise ExecutionRunError(run_error)



