#!/usr/bin/python2.7

import time
import traceback
import pexpect
import re
import os

import hss_utils.connection as connection
import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning

from scenario.config_handler import get_BAT_config
from hss_utils.st_command import *
import hss_utils.node.gentraf
from shared import *
import shared



# Factory to get a valid MC depending on titansim version
def create_MC(host, config_file, password=None, overwrite={}):
    return MC(host, config_file, password, overwrite)

class MC(object):
    def __init__(self, host, config_file, password=None, config_overwrite={}):

        assert(isinstance(host, tuple))
        _INF('Create MC in %s' % host[0])
        self.__host = host[0]
        self.__port = host[1]
        self.__config = config_file
        self.__config_contents = get_BAT_config(self.__config)
        self.__config_contents.update(config_overwrite)

        self.__password = password
        self.__node = None
        self.started = False
        self.__pid = None
        self.__shell_pid = ''

        if not self.config['cli_nologin']:
            _ERR('MC cli with login not supported yet. BAT and TTCN version are not alligned')
            quit_program(MC_ERROR)
        self.__telnet_available = True
        self.__already_shutdown = False
        self.__killing = False
        self.__mtc_host= None
        self.__ttcn_bat_cli_port = int(self.config['cli_port'])
        self.__aliases = {}
        try:
            access_config = {'host':self.__host,'password':self.__password}
            self.__node = hss_utils.node.gentraf.GenTraf(config = access_config)
            self.__node.working_dir = '%s_MC' % shared.EXECUTION_PATH

            destination = '%s_MC' % shared.EXECUTION_PATH
            _INF('Upload "%s" to %s' % (self.__config, destination))
            self.__node.upload(self.__config, destination)
            self.set_ttcn_version(shared.TTCN_VERSION)
            cmd = 'export BAT_CFG_PATH=%s' % shared.BAT_CONFIG_FOLDER
            self.__node.run_command(cmd)
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
            _ERR('MC creation problem: %s' % str(e))
            quit_program(MC_ERROR)

        self.__channel = self.__node.get_channel()

    @property
    def config(self):
        return self.__config_contents

    @property
    def process(self):
        return self.__node

    @property
    def host(self):
        return self.__host

    @property
    def port(self):
        return self.__port

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
            shell = self.__node.run_command('echo $BASHPID')
            self.__shell_pid = shell[0]
            cmd = 'mctr_cli %s' % os.path.basename(self.__config)
            self.__channel.write_line(cmd)

            result = self.__channel.expect(['Listening on TCP port', #'to connect'
                                    'The license key has already expired',
                                    'Initialization of TCP server failed.',
                                    'Cannot create MC.',
                                    'Parse error in configuration file.*\n',
                                    "Cannot open config file.*`.*'",
                                    'Address already in use'],timeout=20.0 )

            cause = self.__channel.last_match
            _DEB('Received from MC: %s' % cause)

            if result == 0:
                self.mctr_pid()
                self.started = True

            elif result == 1:
                _ERR('%s' % cause)
                _ERR('Problem starting MC')
                quit_program(TTCNLIC_ERROR)
            else:
                _ERR('MC %s' % cause)
                _ERR('Problem starting MC')
                quit_program(CONFIG_ERROR)

        except KeyboardInterrupt:
            _ERR('Cancelled by user')
            quit_program(USER_CANCEL)

        except pexpect.TIMEOUT, e:
            _ERR('Timeout waiting to MC')
            quit_program(MC_ERROR)

        except pexpect.EOF, e:
            _ERR('EOF waiting to MC')
            quit_program(MC_ERROR)


    def load_alias(self, alias):
        _DEB('Adding aliases: %s' % alias)
        self.__aliases.update(alias)

    @property
    def mtc_host(self):
        return self.__mtc_host

    def set_mtc_host(self, mtc_host):
        self.__mtc_host= mtc_host

    def __send_aliases__(self):
        if not self.__telnet_available:
            _ERR('Requesting alias upload but telnet CLI is not available!')
            return
        _INF('Sending alias...')
        tries = 5
        while tries > 0:
            try:
                access_config = {'host':self.config['generators'][0],'port':self.__ttcn_bat_cli_port}
                connection = hss_utils.node.gentraf.TTCN_cli(config = access_config)

                for original_variable in self.__aliases.keys():
                    alias_name = self.__aliases[original_variable]
                    connection.send_line('alias %s %s' % (original_variable, alias_name))
                _INF('Alias sent')
                connection.close()
                self.__telnet_available = True
                return True

            except KeyboardInterrupt:
                _WRN('Cancelled by user')
                return False

            except Exception, e:
                _WRN('Cannot send "alias" to CLI (%s)' % e)
            tries -= 1
            _WRN('Remaining retries: %s' % tries)
        _WRN('Cannot use telnet access!')
        self.__telnet_available = False
        return False

    def mctr_pid(self):
        pid= []
        answer = self.__node.run_command('ps -eaf --sort=start_time | grep mctr_cli | grep %s' % self.__shell_pid,identity='aux')

        for line in answer:
            if 'grep' not in line:
                pid.append(line.split()[1])
        if len(pid):
            self.__pid = pid[-1]
            _INF('mctr_cli pid %s' % self.__pid)


    def wait_END(self, timeout, autokill=True):
        _INF('Waiting for termination or for sending alias')
        if not self.started:
            _DEB('Skipping wait_END() because mctr_cli not started')
            return

        wait_for_end = True
        max_time_wait_for_end = timeout
        while wait_for_end:
            now = time.time()
            try:
                expect_list = ['XTDP connection thread END.',
                               'ScenarioGroup: [0-9]+ finished',
                               'Shutdown complete',
                               'Exiting.',
                               "GUI done",
                               'MTC terminated']

                result = self.__channel.expect(expect_list,
                                       timeout=10.0)

                _DEB('Received from MC: %s' % self.__channel.last_match)
                if self.__telnet_available:
                    self.__telnet_available = (result in [1, 4])
 
                self.__already_shutdown = (result == 2)

                if result in [0,5]:
                    self.__telnet_available = False
                    self.__already_shutdown = True

            except KeyboardInterrupt:
                if self.config['execution_mode'] == 'Manual':
                    _INF('User send Ctrl-C in Manual mode')
                else:
                    _INF('Automatic mode cancelled by user')
                result = 7
                wait_for_end = True

            except pexpect.TIMEOUT, e:

                if not self.__mtc_host.mtc_is_finished:
                    if max_time_wait_for_end is not None:
                        max_time_wait_for_end -= time.time() - now

                        if max_time_wait_for_end < 0:
                            _INF('TIME waiting for BAT end has expired: %s seconds' % timeout)
                            result = 6
                        else:
                            continue
                    else:
                        continue
                else:
                    _INF('Main Test case terminated')
                    result = 2
                    self.__already_shutdown = True

            except pexpect.EOF, e:
                _DEB('EOF Exception waiting for BAT end: %s' % e.get_trace())
                result = 6
                self.__already_shutdown = True

            if result == 4:

                if not self.__send_aliases__():
                    self.__telnet_available = False
                    wait_for_end = True
                    result = 7
                    self.kill(skip_clean = True)
                else:
                    _INF('Waiting for termination.....')
                    continue

            _DEB('MC termination result: %s' % result)

            if result in [ 0, 6, 7]:
                try:
                    if autokill:
                        self.kill(skip_clean = True)

                except KeyboardInterrupt:
                    _WRN('MC killing cancelled by user')
            elif result == 1:
                if self.config['execution_mode'] != 'Manual':
                    _INF('Automatic mode detected, sleeping 25 seconds to go')
                    try:
                        time.sleep(25.0)
                    except KeyboardInterrupt:
                        _WRN('Automatic sleep cancelled by user')
                    if autokill:
                        self.kill(skip_clean = True)
                else:
                    _INF('Traffic finished in Manual Mode. Waiting for user to stop execution')
                    _DEB('Manual mode detected, expecting again')
                    continue
            wait_for_end = False

        return result

    def kill(self, skip_clean = False):
        if self.__killing:
            _WRN('Ignoring double kill()')

        self.__killing = True
        if self.started:
            try:
                if not self.__already_shutdown:

                    _INF('Terminate MC in %s' % self.host)
                    if self.__telnet_available:
                        try:
                            access_config = {'host':self.config['generators'][0],'port':self.config['cli_port']}
                            cli = hss_utils.node.gentraf.TTCN_cli(config = access_config)
                            result = cli.send_line('stop')
                            cli.close()

                        except Exception, e:
                            self.__telnet_available = False
                            _WRN('Cannot send "stop" to CLI')
                            _INF('Sending Ctrl-C')
                            self.__channel.write_line('\x03')
                    else:
                        _WRN('Telnet not available, sending Ctrl-C')
                        self.__channel.write_line('\x03')

                    now = time.time()
                    max_time_for_shutdown = float(60)
                    wait_for_shutdown = True
                    _INF('Wait for shutdown...max waiting time is 60 seconds')
                    while wait_for_shutdown:
                        wait_for_shutdown = False
                        try:
                            result = self.__channel.expect(['Shutdown complete',
                                                            'MTC terminated'],timeout=5.0 )

                        except pexpect.EOF, e:
                            _WRN('EOF received waiting for shutdown.')

                        except pexpect.TIMEOUT, e:
                            if not self.__mtc_host.mtc_is_finished:
                                max_time_for_shutdown -= time.time() - now
                                if max_time_for_shutdown > 0:
                                    wait_for_shutdown = True
                                    continue

                                _INF('TIME waiting for BAT shutdown has expired: 60 seconds')

                            else:
                                _INF('BAT shutdown')
                                wait_for_shutdown = False

                        except KeyboardInterrupt:
                            _WRN('User skips wait for shutdown')

                self.started = False

            except Exception, e:
                _WRN('MC killing problem: %s' % e)
                _DEB('** STACK TRACE **')
                exc_type, exc_value, exc_traceback = sys.exc_info()
                for tb in traceback.format_tb(exc_traceback):
                    _DEB(tb)
                for tb in traceback.format_exception(exc_type, exc_value,
                                                    exc_traceback):
                    _DEB(tb)

            except KeyboardInterrupt:
                _WRN('User forces kill()')

            self.__killing = False

        if skip_clean:
            return
        try:
            _DEB('Calling clean_working_dir()')
            destination = os.getcwd()
            answer = self.__node.run_command('kill %s' % self.__pid,identity='aux')
            _INF('Stopping mctr_cli pid %s' % self.__pid)
            self.process.clean_working_dir()
        except Exception, e:
            _WRN('Killing problem: %s' % e)

        self.__node.release()

    def __str__(self):
        return 'MC running on %s' % self.__host