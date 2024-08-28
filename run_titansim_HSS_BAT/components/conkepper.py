#!/usr/bin/python2.7

import time

import hss_utils.connection as connection
import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning

from hss_utils.st_command import *
import hss_utils.node.gentraf
from shared import *
import shared

CONKEEPER = 'ConKeeper'

class ConKeeper(object):
    def __init__(self, conkeeper_definition, password=None):
        assert((conkeeper_definition is None) or (isinstance(conkeeper_definition, tuple)))
        if conkeeper_definition is None:
            # Enter dummy mode
            self.__host = None
            self.__port = None
            self.__node = None
        else:
            _INF('Creating ConKeeper in %s' % conkeeper_definition[0])
            self.__host = conkeeper_definition[0]
            self.__port = conkeeper_definition[1]
            self.__password = password

            self.__node = None
            if self.available:
                if ((self.__host is not None) and
                    (self.__port is not None)):
                    _WRN('There is a ConKeeper already running on %s:%s' % (self.__host, self.__port))
            else:
                access_config = {'host':self.__host,'password':self.__password} 
                try:
                    self.__node = hss_utils.node.gentraf.GenTraf(config = access_config)
                    self.__node.working_dir = '%s_ConKeeper' % shared.EXECUTION_PATH

                except connection.Unauthorized, e: 
                    _ERR('Error: %s' % str(e))
                    quit_program(CONNECTION_ERROR)
                except (connection.ConnectionFailed, connection.ConnectionTimeout), e: 
                    _ERR('Error: %s' % str(e))
                    quit_program(CONNECTION_ERROR)
                except KeyboardInterrupt:
                    _WRN('Cancelled by user')
                    quit_program(USER_CANCEL)
                except Exception, e:
                    _ERR('ConKeeper creation problem: %s' % e)
                    quit_program(CONKEEPER_ERROR)

    def start(self):
        if self.__node is None:
            return None
        prog = CONKEEPER
        try:
            cmd = '%s -p %s' % (prog, self.__port)
            self.__node.run_command_async(cmd, answer = {'ConKeeper up and running': ''},timeout = 5.0)

        except Exception, e:
            _ERR('ConKeeper start problem: %s' % e)
            quit_program(CONKEEPER_ERROR)


    @property
    def available(self):
        status = send_udp_command('getstatus', self.__host, self.__port, timeout=4.0)
        return status is not None

    def kill(self):
        if self.__node is None:
            return
        try:
            _INF('Terminate Conkeeper in %s' % self.__host)
            while self.available:
                send_udp_command('exit', self.__host, self.__port)
                time.sleep(2.0)

            destination = os.getcwd()
            self.__node.clean_working_dir(destination, backup=['\*.log'])
            #self.__node.close_connection()
            self.__node.release()

        except Exception, e:
            _WRN('ConKeeper killing problem: %s' % e)


    def __str__(self):
        return 'Conkeeper running on %s' % self.__host