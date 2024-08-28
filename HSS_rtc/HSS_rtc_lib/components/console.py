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
from . import ExecutionConfigurationError
from . import ExecutionRunError

class Console(threading.Thread):
    def __init__(self, id, host, port, root_path):
        threading.Thread.__init__(self)
        self.__id = 'CONSOLE_%s' % id
        self.__host = host
        self.__port = port
        self.__channel = None
        self.__buffer = ''
        self.__running = False
        self.__force_exit = False
        self.__filename = os.path.join(root_path, '%s.txt' % self.id.lower())
        self.__fd = None

    @property
    def force_exit(self):
        return self.__force_exit

    def activate_force_exit(self):
        self.__force_exit = True

    @property
    def id(self):
        return self.__id 

    def connect(self):
        if self.__channel is None:

            try:
                access_config = {'host':self.__host,'port':self.__port}
                endpoint = connection.telnet.TelnetEndpoint(access_config)
                self.__channel = connection.telnet.CBA_console_TelnetChannel(endpoint, timeout=10.0)
                self.__channel.open()
                _INF('%s connected' % self.__id)
                self.__running = True

            except KeyboardInterrupt:
                _WRN('Cancelled by user')

            except Exception, e:
                run_error = '%s cannot open telnet connection: %s' % (self.__id, e)
                raise ExecutionRunError(run_error)

        return self.__channel

    def close(self):
        if self.__fd is not None:
            self.__fd.close()
            self.__fd = None

        if self.__channel is None:
            self.__running = False
            return
        try:
            self.__channel.close()
        except Exception ,e :
            _DEB('%s Problem closing telnet channel: %s' % (self.__id, e))
            pass

        self.__channel = None
        self.__running = False
        _INF('%s connection closed' % self.__id)

    def shutdown(self):
        _INF('%s shutdown received' % self.__id)
        self.__force_exit = True
        self.close()

    @property
    def online(self):
        return self.__running and self.__channel is not None

    def start_handling(self):
        self.connect()
        self.__fd = open(self.__filename, 'w')
        self.start()

    def run(self):
        while (self.online):
            if self.force_exit:
                return

            result = self.__channel.expect(['\n'])
            try:
                if result == 0 and None not in [self.__channel,self.__fd ]:
                    self.__fd.write('%s\n' % self.__channel.stdout)
            except IOError as e:
                run_error = '%s Problem saving info in file %s: %s' % (self.__id, self.__filename, e)
                raise ExecutionRunError(run_error)

        _INF('%s end of thread execution' % self.id)


