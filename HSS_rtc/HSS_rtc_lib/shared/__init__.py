#!/usr/bin/env python
# -*- coding: utf-8 -*-


import sys
import os
import os.path
import getpass
from datetime import datetime
import time
import shutil
import hashlib
import ntpath
import json
import threading
import hss_utils.dbus

import socket
HOSTNAME = socket.gethostname()

import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning


EXIT_ERRORS =  {
0: 'Success',
1: 'Not found / do not exist',
2: 'Execution error',
3: 'Execution Timeout',
4: 'Connection error',
5: 'Authentication error',
6: 'BAT error',
10: 'Wrong parameter value',
20: 'Command not supported',
30: 'Execution stopped by user',
40: 'Rosetta error',
100: 'Implementation error'
    }

# Exit status
EXIT_CODE = 0
SUCCESS = 0
NOT_FOUND = 1
EXECUTION_ERROR = 2
TIMEOUT = 3
CONNECTION_ERROR = 4
AUTHENTICATION_ERROR = 5
BAT_ERROR = 6
WRONG_PARAMETER = 10
NOT_SUPPORTED = 20
USER_CANCEL = 30
ROSETTA_ERROR = 40
IMPLEMENTATION_ERROR = 100

def get_exit_status():
    exit_status = '''\
    EXIT STATUS
'''
    for key in sorted(EXIT_ERRORS):
        exit_status += '\t%s\t%s\n' % (key, EXIT_ERRORS[key])

    return exit_status



NODE=None
def set_node(node):
    global NODE
    NODE = node

RTC = None
def set_rtc(rtc):
    global RTC
    RTC = rtc

OUTPUT_PATH_DEFAULT = '/opt/hss/%s' % getpass.getuser()

def finish_threads(skip=[]):
    for thread in threading.enumerate():

        try:
            if not isinstance(thread,threading._MainThread):
                if thread.id not in skip:
                    _WRN('Forcing to stop Thread %s that is still running' % thread.id)
                    thread.activate_force_exit()

        except Exception, e:
            print str(e)
BUILD=None
def set_build(build):
    global BUILD
    BUILD = build

DBUS=None
def set_dbus(dbus):
    global DBUS
    DBUS = dbus

def quit_program(exit_code, message=''):
    global NODE
    global RTC

    finish_threads()

    if NODE is not None:
        try:
            NODE.release()
        except Exception, e:
            _DEB('Problem during release node: %s' % str(e))


    if RTC is not None:
        if DBUS:
            hss_utils.dbus.emit('test_tool_shutdown',BUILD, RTC.rtc_data.TestSuite._as_dict)
        RTC.release()

    if message != '':
        _DEB('run_test_case_message %s ' % message)

    _DEB('Exit code: %s (%s)' % (exit_code, EXIT_ERRORS.get(exit_code, 'unknown error code')))
    sys.exit(exit_code)


def remove_colors(line):
    colors= ['\x1b[0;31m','\x1b[0;32m','\x1b[0;33m','\x1b[0m']
    for color in colors:
        line = line.replace(color,'')
    return line

