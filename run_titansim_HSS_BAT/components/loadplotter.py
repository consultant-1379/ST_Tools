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

LOADPLOTTER = 'LoadPlotter'

class LoadPlotter(object):
    def __init__(self, load_plotter_definition, password=None):
        assert((load_plotter_definition is None) or (isinstance(load_plotter_definition, tuple)))
        if load_plotter_definition is None:
            # Enter dummy mode
            self.__host = None
            self.__port = None
            self.__node = None
        else:
            _INF('Creating LoadPlotter in %s' % load_plotter_definition[0])
            self.__host = load_plotter_definition[0]
            self.__port = load_plotter_definition[1]
            self.__password = password
            self.__cmd = None

            self.__node = None
            if self.available:
                if ((self.__host is not None) and
                    (self.__port is not None)):
                    _WRN('There is a LoadPlotter already running on %s:%s' % (self.__host, self.__port))
            else:
                access_config = {'host':self.__host,'password':self.__password} 
                try:
                    self.__node = hss_utils.node.gentraf.GenTraf(config = access_config, allow_x11_forwarding = True)
                    self.__node.working_dir = '%s_LoadPlotter' % shared.EXECUTION_PATH
                    self.__node.create_connection(config=access_config, session_type=self.__node.session_type,identity='aux')
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
                    _ERR('Loadplotter creation problem: %s' % e)
                    quit_program(LOADPLOTTER_ERROR)

    def start(self):
        if self.__node is None:
            return None
        prog = LOADPLOTTER
        try:
            self.__cmd = '%s -p %s' % (prog, self.__port)
            self.__node.run_command_async(self.__cmd, answer = {'LoadPlotter up and running': ''},timeout = 5.0)
            _INF('LoadPlotter up and running in %s:%s' % (self.__host, self.__port))

        except Exception, e:
            _ERR('Loadplotter start problem: %s' % e)
            quit_program(LOADPLOTTER_ERROR)

    @property
    def running(self):
            cmd = 'ps -eaf | grep "%s" | grep -v grep' % self.__cmd
            answer = self.__node.run_command(cmd,identity='aux')
            return len(answer)>0

    @property
    def available(self):
        status = send_udp_command('getstatus', self.__host, self.__port, timeout=4.0)
        return status is not None

    def kill(self):
        if self.__node is None:
            return
        try:
            _INF('Terminate Loadplotter in %s' % self.__host)
            while self.running:
                send_udp_command('exit', self.__host, self.__port)
                time.sleep(5.0)

            destination = os.getcwd()
            self.__node.clean_working_dir(destination, backup=['\*.log', '\*.gif', '\*.data', '\*.cmd'])
            self.__node.release()

        except Exception, e:
            _WRN('Loadplotter killing problem: %s' % e)

    def __str__(self):
        return 'Loadplotter running on %s' % self.__host