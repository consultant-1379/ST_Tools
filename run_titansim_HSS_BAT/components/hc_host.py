#!/usr/bin/python2.7

import os
import os.path
import pexpect
from distutils.spawn import find_executable

import hss_utils.connection as connection
import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning

from shared import *
import shared
from hss_utils.st_command import *
import hss_utils.node.gentraf



class GUI(object):
    def __init__(self, gui_definition, gui_kept, password=None):
        assert((gui_definition is None) or (isinstance(gui_definition, tuple)))
        self.__password = password
        self.__gui_kept = gui_kept
        if (gui_definition is None):
            # Enter dummy mode
            self.__host = None
            self.__port = None
            self.__node = None
        elif  gui_definition[0] is None:
            # Enter dummy mode
            self.__host = None
            self.__port = None
            self.__node = None
        else:
            _INF('Creating GUI in %s' % gui_definition[0])
            self.__host = gui_definition[0]
            self.__port = gui_definition[1]
            access_config = {'host':self.__host,'password':self.__password} 

            try:
                self.__node = hss_utils.node.gentraf.GenTraf(config = access_config, allow_x11_forwarding = True)
                if shared.JAVA is not None:
                    self.__node.run_command('setenv PATH %s:$PATH' % os.path.join(shared.JAVA, 'bin'), timeout=-1)
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
                _ERR('GUI creation problem: %s' % e)
                quit_program(GUI_ERROR)

    def start(self):
        if self.__node:
            gui_command = '%s listen %s %s' % (
                find_executable('ttcn3_runtime_gui.sh'),
                self.__port,
                XUL_PATH)

            try:
                self.__node.run_command_async(gui_command,
                                              answer = {'Waiting for client to be connected':''},
                                              timeout=120.0)

                _INF('GUI started and ready!')
            except KeyboardInterrupt:
                _WRN('Cancelled by user')
                quit_program(USER_CANCEL)
            except Exception, e:
                _ERR('Start GUI problem: %s' % str(e))
                quit_program(GUI_ERROR)

    def kill(self):
        try:
            if self.__node is None:
                return
            if self.__gui_kept:
                _INF('Skipping GUI termination')
                return

            self.__node.stop_command_async()
            self.__node.release()
            _INF('Terminate GUI in %s' % self.__host)
        except Exception, e:
            _WRN('GUI killing problem: %s' % e)

    def __str__(self):
        return 'GUI running on %s' % self.__host

class HC(object):
    def __init__(self, generator, mc, binary_file, password=None, instanceno=None):
        assert(isinstance(generator, str))
        assert(isinstance(binary_file, str))
        if instanceno is None:
            self.__instance_id = ''
        else:
            self.__instance_id = '_%s' % instanceno
        _INF('Create HC%s in %s associated with %s' % (self.__instance_id, generator, mc.host))
        self.__host = generator
        self.__mc = mc
        self.__binary = binary_file
        self.__password = password
        self.__node = None
        self.__additional_connection = None
        self.__working_dir = '%s_LGen%s' % (shared.EXECUTION_PATH, self.__instance_id)

        try:
            access_config = {'host':self.__host,'password':self.__password}
            self.__node = hss_utils.node.gentraf.GenTraf(config = access_config)
            self.__node.working_dir = self.__working_dir
            self.set_ttcn_version(shared.TTCN_VERSION)
            #if self.__binary.startswith('/opt/hss/'):
                #destination = '%s_MC' % shared.EXECUTION_PATH
                #INF('Upload "%s" to %s' % (self.__binary, self.__node.working_dir ))
                #self.__node.upload(self.__binary, self.__node.working_dir )
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
            _ERR('Host controller creation problem: %s' % e)
            quit_program(HC_ERROR)

    @property
    def __bat_bin(self):
        raise NotImplementedError()

    def set_ttcn_version(self, version):
        if version == '':
            return

        cmd = 'ttcnset %s' % version   
        try:
            answer = self.__node.run_command(cmd)
            if 'You are trying to set a wrong TITAN version.' in ' '.join(answer):
                _ERR('TTCN version %s is not valid' % version)
                quit_program(TTCNVER_ERROR)

        except KeyboardInterrupt:
            _WRN('Cancelled by user')
            quit_program(USER_CANCEL)
        except Exception, e:
            _ERR('Set TTCN version problem: %s' % str(e))
            quit_program(TTCNVER_ERROR)

    def start(self):
        try:

            cmd = '%s %s %s -s %s' % (self.__binary,
                                            self.__mc.host,
                                            self.__mc.port,
                                            self.__host)
            self.__node.run_command_async(cmd)

        except Exception, e:
            _ERR('Host controller problem: %s' % e)
            quit_program(CONNECTION_ERROR)

    @property
    def mtc_is_finished(self):
        if self.__additional_connection is None:
            try:
                self.__additional_connection = self.__node.clone_connection(identity ='control',force_open=True)
            except (Exception, KeyboardInterrupt) as e:
                _DEB('%s' % e)
                return True

        cmd = 'grep "Main Test case execution finished" %s/mtc*.log' % self.__working_dir
        try:
            answer = self.__node.run_command(cmd, identity ='control')
            return 'Main Test case execution finished' in ' '.join(answer)
        except (Exception, KeyboardInterrupt) as e:
            _DEB('%s' % e)
            return True


    def kill(self):
        if self.__node is None:
            return
        try:
            _INF('Terminate HC%s in %s associated with %s' % (self.__instance_id, self.__host, self.__mc.host))
            self.__node.stop_command_async()

            destination = os.getcwd()
            self.__node.clean_working_dir(destination, backup=['\*.log', '\*.txt', '\*.data'])
            self.__node.release()

        except Exception, e:
            _WRN('Killing problem: %s' % e)

    def __str__(self):
        return 'HC%s running on %s' % (self.__instance_id, self.__host)
