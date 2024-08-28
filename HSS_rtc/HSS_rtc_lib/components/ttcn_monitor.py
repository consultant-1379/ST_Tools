#!/usr/bin/env python
#

import time
import sys
import traceback
import pexpect
import re
import threading
import Queue

import hss_utils.st_command as st_command
import hss_utils.connection as connection
import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning


from hss_utils.st_command import *
import hss_utils.node.gentraf
from HSS_rtc_lib.shared import *


class TTCNClient(threading.Thread):
    def __init__(self, host, port, owner):
        threading.Thread.__init__(self)

        self.__owner = owner
        self.__id = 'TTCN_CLI_%s' % owner.id
        self.__host = host
        self.__port = port
        self.__connection = None
        self.__buffer = ''
        self.__running = False
        self.__last_action = 0
        self.requests = Queue.Queue()

        self.__phase_control = {
            'mode': 'ScGrpMode',
            'phase': 'ScGrpCurrentPhase',
            'start': 'ScGrpStart',
            'terminate': 'ScGrpTerminate',
            'status': 'ScGrpStatus'
            }

        self.__force_exit = False

    @property
    def force_exit(self):
        return self.__force_exit

    def activate_force_exit(self):
        self.__force_exit = True

    @property
    def id(self):
        return self.__id 

    @property
    def phase_control(self):
        return self.__phase_control

    def set_phase_control(self, key, value):
        if key not in self.__phase_control.keys():
            return False
        self.__phase_control[key] = value
        return True

    def _R_(self, variable):
        return 'read_%s' % variable

    def _W_(self, variable):
        return 'write_%s' % variable

    @property
    def online(self):
        return self.__running and self.__connection

    def connect(self):
        if self.__connection is None:

            try:
                access_config = {'host':self.__host,'port':self.__port}
                self.__connection = hss_utils.node.gentraf.TTCN_cli(config = access_config, owner=self)
                _INF('%s connected' % self.__id)
                self.__running = True
                self.__last_action = time.time()

            except KeyboardInterrupt:
                _WRN('Cancelled by user')

            except Exception as e:
                _ERR('Cannot open telnet connection CLI (%s)' % e)

        return self.__connection

    def close(self):
        if self.__connection is None:
            self.__running = False
            return
        try:
            self.__connection.close()
        except OSError:
            pass

        self.__connection = None
        self.__running = False
        _INF('%s connection closed' % self.__id)

    def shutdown(self):
        _INF('%s shutdown received' % self.__id)
        if self.__connection is None:
            self.__running = False
            return
        #self.__connection.send_line('stop')
        #self.__last_action = time.time()
        self.close()

    def __parse_get_buffer__(self):
        buffer = self.__buffer.splitlines()
        aliases = {}
        for line in buffer[1:]:
            if line.startswith('The variable "'):
                return None
            line = line.strip()
            line = line.split(':=')
            if len(line) < 2:
                _WRN('Cannot parse value definition: "%s"' % repr(line))
                continue
            return line[-1].strip()

    def __parse_set_buffer__(self):

        buffer = self.__buffer.splitlines()
        for line in buffer[1:]:
            if line.startswith('The variable "'):
                return False
            if line.startswith('Usage:'):
                return False
            if line.startswith('Cannot set variable '):
                return False
            if line.startswith('Set content OK.'):
                return True
            _WRN('Cannot parse SET output: "%s"' % repr(line))
        # Asume NO-OK
        _WRN('Unknown SET output, assuming NOK')
        return False

    def keepalive(self):
        if self.__connection is None:
            self.__running = False
            return False

        if time.time() - self.__last_action > 10:
            try:
                _INF('%s keepalive' % self.__id)
                self.__connection.send_line('')
                self.__last_action = time.time()
            except Exception as e:
                _WRN('%s keepalive Problem: %s' % (self.__id, str(e)))
                self.close()

    def get_value(self, variable_name, led = False):
        if self.__connection is None:
            self.__running = False
            return
        try:
            result = self.__connection.send_line('get $%s$' % self._R_(variable_name))
        except Exception as e:
            _ERR('%s Error get_value: %s' % (self.__id, str(e)))
            self.close()
            return

        self.__last_action = time.time()
        if result == 0:
            self.__buffer = self.__connection.stdout
            value = self.__parse_get_buffer__()
            if led and value:
                if ('[' in value) and (']' in value):
                    st = value[:value.index('[')] + value[value.rindex(']') + 1:]
                    value = st.strip()
                else:
                    _WRN('Led status not found, ignored')

            return value

        else:
            _ERR('%s TTCN prompt lost' % self.__id)
            self.close()


    def set_value(self, variable_name, value):
        if self.__connection is None:
            self.__running = False
            return

        try:
            result = self.__connection.send_line('set $%s$:=%s' % (self._W_(variable_name),value))
        except Exception, e:
            _ERR('%s Error set_value: %s' % (self.__id, str(e)))
            self.close()

        self.__last_action = time.time()
        if result == 0:
            self.__buffer = self.__connection.stdout
            return self.__parse_set_buffer__()
        else:
            _ERR('%s TTCN prompt lost' % self.__id)
            self.close()
            return False


    def start_phase(self, phase_name):
        _INF('%s  start phase %s' % (self.__id,phase_name))
        if phase_name not in ['preexec', 'loadgen', 'postexec']:
            _WRN('%s Wrong phase %s' % (self.__id,phase_name, phase_name))
            return False
        if not self.set_value(self.__phase_control['mode'], 'MANUAL'):
            _WRN('%s Cannot set mode to MANUAL' % self.__id)
            return False
        if not self.set_value(self.__phase_control['phase'], phase_name):
            _WRN('%s Cannot set phase to "%s"' %  (self.__id, phase_name))
            return False
        if not self.set_value(self.__phase_control['start'], 'true'):
            _WRN('%s Cannot start phase' % self.__id)
            return False
        return True

    def stop_phase(self):
        if not self.set_value(self.__phase_control['terminate'], 'true'):
            _WRN('Cannot set terminate to "true"')
            return False
        return True

    def run_command(self,cmd):
        answer = eval('self.%s(%s)' % (cmd['action'],','.join(cmd['args'])))
        return answer

    @property
    def phase_status(self):
        return self.get_value(self.__phase_control['status'], led = True)

    @property
    def is_owner_running(self):
        return self.__owner.execution_state == 'running'

    def run(self):
        self.connect()
        while (self.online):
            if self.force_exit:
                return
            if not self.is_owner_running:
                self.close()
                break;
            try:
                command, client_answers = self.requests.get(True, timeout=10.0)
                response = self.run_command(command)
                client_answers.put_nowait(response)
            except Queue.Empty:
                self.keepalive()
        _INF('%s end of thread execution' % self.id)

