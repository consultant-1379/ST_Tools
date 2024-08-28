#!/usr/bin/env python
#

import sys
import os
import os.path
from datetime import datetime
import uuid

import socket
HOSTNAME = socket.gethostname()

import time
import re
import getpass
import pexpect
import random
import threading
import copy
import operator
import pprint
import tempfile
import json

from hss_utils.st_command import send_udp_command, execute_cmd, get_stFramework_error_message
from hss_utils.connection import Unauthorized, ConnectionFailed, ConnectionTimeout
from hss_utils.node.gentraf import GenTraf

import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning

from . import ExecutionConfigurationError
from . import ExecutionStartError
from . import ExecutionRunError

RTC_REMOTE_UDP_PORT = 5000


class RTC_Handler(threading.Thread):
    def __init__(self, test_config, service_config, start_event, baseline_test_config,test_suite=None):

        threading.Thread.__init__(self,target=self.run_traffic,args=(start_event,))
        self.test_config = copy.deepcopy(test_config)
        self.__specific_test_suite = test_suite

        if not service_config:
            error_info = '%s missing service configuration: %s' % (self.id, e)
            raise ExecutionStartError(error_info)

        self.service_config = copy.deepcopy(service_config)
        self.baseline_test_config = copy.deepcopy(baseline_test_config)
        self.execution_info_error = None
        self.id = 'rtc_handler'
        self.__node = None
        self.__macro = {}
        self.__access_config={'host':socket.gethostname(),
                              'user':'hss_st',
                              'password':'hss_st'}

        self.ongoing_test = False
        self.__force_exit = False

        try:
            self.__node = GenTraf(config = self.__access_config, allow_x11_forwarding = True)
            answer = self.__node.run_command('get_env_info')
            for line in answer:
                if 'Type' in line:
                    self.__env_type = 'native' if line.split()[-1] == 'CBA' else 'virtual'
                    self.add_to_macro('#ENV_TYPE#',self.__env_type)
                    break

            if self.__env_type is None:
                error_info = '%s Fetching env info from Rosetta has failed' % self.id 
                raise ExecutionStartError(error_info)

            self.__working_dir = '/opt/hss/%s/%s_%s_%s' % (self.__access_config['user'],
                                                           self.test_config['build'],
                                                           time.strftime("%Y%m%d-%H%M%S"),
                                                           self.__env_type)
            self.add_to_macro('#WD#', self.__working_dir)
            self.add_to_macro('#BUILD#', self.test_config['build'])

            self.__channel = self.__node.get_channel()
            self.__node.create_connection(config=self.__access_config, session_type=self.__node.session_type,identity='aux')

        except Unauthorized as e: 
            error_info = '%s creation problem: %s' %  (self.id, e)
            raise ExecutionStartError(error_info)

        except (ConnectionFailed, ConnectionTimeout) as e: 
            error_info = '%s creation problem: %s' % (self.id, e)
            raise ExecutionStartError(error_info)

        except Exception as e:
            error_info = '%s creation problem: %s' % (self.id, e)
            raise ExecutionStartError(error_info)

        try:
            baseline = service_config['service_parameters']['base_release']
            if baseline:
                self.add_to_macro('#BASE_RELEASE#', baseline.replace('.','_'))
        except KeyError as e:
            _WRN('%s missing "base_release" service parameter in rtc service configuration' % self.id)
            _WRN('#BASE_RELEASE# macro will not be provided')

        for key, value in self.test_config['build_info']['packages'].items():
            if value is not None:
                self.add_to_macro('#%s#' % key, value)

        if self.baseline_test_config:
            self.add_to_macro('#BUILD_BASE#', self.baseline_test_config['build'])
            self.add_to_macro('#HSS_VERSION_BASE#', self.baseline_test_config['hss_release'])
            for key, value in self.baseline_test_config['build_info']['packages'].items():
                if value is not None:
                    self.add_to_macro('#%s_BASE#' % key, value)


        if self.__specific_test_suite is None:
            self.test_suite = service_config['service_parameters']['test_suite']
            _INF('%s Common test suite: %s' % (self.id,self.test_suite))
        else:
            self.test_suite = self.__specific_test_suite
            _INF('%s Specific test suite: %s' % (self.id,self.test_suite))

        try:
            self.git_path = service_config['service_parameters']['git_path']
        except KeyError as e:
            _WRN('%s missing "git_path" service parameter in rtc service configuration' % self.id)
            self.git_path = os.path.join(self.__working_dir,'GIT_repos')
            _WRN('%s setting default value  "%s"' % (self.id,self.git_path ))

        try:
            self.folder_to_create = service_config['service_parameters']['folder_to_create']
        except KeyError as e:
            self.folder_to_create = []

        try:
            self.test_result = service_config['service_parameters']['test_result']
        except KeyError as e:
            _WRN('%s missing "test_result" service parameter in rtc service configuration'% self.id)
            self.test_result = os.path.join(self.__working_dir,'test_result')
            _WRN('%s setting default value  "%s"' % (self.id,self.test_result))

        try:
            self.output_dir = service_config['service_parameters']['output_dir']
        except KeyError as e:
            _WRN('%s missing "output_dir" service parameter in rtc service configuration' % self.id)
            self.output_dir = None
            _WRN('%s Output data and logs will be kept on the working directory: %s' % (self.id, self.__working_dir))

        try:
            self.to_pack_and_store = service_config['service_parameters']['to_pack_and_store']
        except KeyError as e:
            _WRN('%s missing "to_pack_and_store" service parameter in rtc service configuration' % self.id)
            self.to_pack_and_store = []
            _WRN('%s Nothing to be be packed and stored' % self.id)


        for element in self.service_config['common.mkr']:
            if element['name'] == 'AUTH_VECTOR' and element['value'] in ['AVG','HLR']:
                return


        self.set_auth_vector()

    @property
    def force_exit(self):
        return self.__force_exit

    def activate_force_exit(self):
        self.__force_exit = True

    @property
    def rtc_cmd_user_parameters(self):
        return self.service_config['service_parameters'].get('rtc_cmd_user_parameters','')

    @property
    def high_priority(self):
        return self.test_config['high_priority']

    @high_priority.setter
    def high_priority(self, value):
        self.test_config['high_priority'] = value
        self.send_rtc_command('set high_priority %s' % value)


    @property
    def CBA_user(self):
        return self.service_config['service_parameters'].get('CBA_user','root')

    def set_auth_vector(self):

        try:
            cmd = 'CBA_get_traffic_info --user %s' % self.CBA_user
            answer = self.execute_cmd(cmd)
            _DEB('\n%s' % '\n'.join(answer))
            info = {}
            for line in answer:
                if line and '=' in line:
                    info.update({'%s' % line.split('=')[0]:'%s' % line.split('=')[1]})

            self.add_to_macro('#AUTH_VECTOR#', info['vector_supplier'])
        except Exception as e:
            error_info = '%s there was a problem with execution of command "%s": %s' % (self.id, cmd, e)
            raise ExecutionStartError(error_info)

    @property
    def command_line(self):
        cmd = 'HSS_rtc -o %s --dbus --cfg %s' % (self.test_result, self.test_suite)
        cmd += ' --macro_file common.mkr'
        cmd += ' --high_priority' if self.high_priority else ''
        cmd += ' --hss_build %s' % self.test_config['build']
        cmd += ' %s' % self.rtc_cmd_user_parameters
        cmd += ' --owner rtc_controller --disable_graph -v'
        cmd += ' --user %s' % self.CBA_user

        return cmd


    def add_to_macro(self, key, value):
        try:
            self.__macro[key] = value
        except KeyError:
            self.__macro.update({key:value})

    def macro_translator(self, text):
        for key, value in self.__macro.iteritems():
            text = text.replace(key, value)
        return text

    def prepare_test_scenario(self):
        self.__node.working_dir = self.__working_dir

        for env_var in self.service_config['env_var']:
            cmd = 'export %s=%s' %  (env_var['name'], env_var['value'])
            self.execute_cmd(cmd)

        for path in self.folder_to_create:
            cmd = 'mkdir -p %s' % path
            self.execute_cmd(cmd)

        cmd = 'mkdir -p %s' % self.test_result
        self.execute_cmd(cmd)

        cmd = 'cd %s' % self.test_result
        self.execute_cmd(cmd)

        cmd = 'pwd'
        temp_dir=self.execute_cmd(cmd)[0]

        cmd = 'cd -'
        self.execute_cmd(cmd)

        temp_file = tempfile.NamedTemporaryFile(delete=False)
        json.dump(self.test_config['build_info'], temp_file, indent=4)
        temp_file.close()

        self.__node.upload(temp_file.name,os.path.join(temp_dir,'test_info.json'))
        cmd = 'chmod 666 %s' % os.path.join(temp_dir,'test_info.json')
        self.execute_cmd(cmd)

        os.remove(temp_file.name)

        cmd = 'mkdir -p %s' % self.git_path
        self.execute_cmd(cmd)

        git_url = 'ssh://git-hss_st:29418/HSS/'
        #git_url = 'ssh://ecemit@gerrit.ericsson.se:29418/HSS/'

        netconf = False
        for repo in self.service_config['git_repos']:
            if repo['repo'] == 'ST_Population_Netconf':
                netconf = True
            git_branch = ''
            try:
                if len(repo['branch']):
                    git_branch = ' -b %s' % repo['branch']
            except Exception as e:
                pass

            cmd = 'git clone%s %s%s %s/%s' % (git_branch, git_url, repo['repo'], self.git_path, os.path.basename(repo['repo']))
            self.execute_cmd(cmd)

            if not len(repo['branch']):
                commit = repo['commit'] if len(repo['commit']) else self.test_config['build_info']['GIT_repos'][repo['repo']]
                cmd = 'cd %s/%s' % (self.git_path, os.path.basename(repo['repo']))
                self.execute_cmd(cmd)
                cmd = 'git checkout %s' % commit
                self.execute_cmd(cmd)
                cmd = 'cd -'
                self.execute_cmd(cmd)

        # Info for the build to be tested
        if netconf:
            cmd = 'cd %s/ST_Population_Netconf' % self.git_path
            self.execute_cmd(cmd)
            cmd = 'cat test_info.data'
            answer = self.execute_cmd(cmd)
            for line in answer:
                if 'HSS_LICENSE:' in line:
                    self.add_to_macro('#HSS_LICENSE#', line.split(':')[1])
                elif 'HSS_LICENSE_CRC' in line:
                    self.add_to_macro('#HSS_LICENSE_CRC#', line.split(':')[1])
                elif 'EXTDB_BACKUP' in line:
                    self.add_to_macro('#EXTDB_BACKUP#', line.split(':')[1])

            cmd = 'git rev-parse --short HEAD'
            answer = self.execute_cmd(cmd)
            self.add_to_macro('#NETCONF_COMMIT#', answer[0])

            cmd = 'cd -'
            self.execute_cmd(cmd)
        else:
            _WRN('%s missing ST_Population_Netconf.' % self.id)
            _WRN('%s The following macros will not be available: HSS_LICENSE, HSS_LICENSE_CRC, EXTDB_BACKUP and NETCONF_COMMIT' % self.id)

        # Info for the baseline
        if self.baseline_test_config and netconf:
            try:
                commit = self.baseline_test_config['build_info']['GIT_repos']['ST_Population_Netconf']
                self.add_to_macro('#NETCONF_COMMIT_BASE#', commit)
                cmd = 'cd %s/ST_Population_Netconf' % self.git_path
                self.execute_cmd(cmd)
                cmd = 'git checkout %s' % commit
                self.execute_cmd(cmd)
                cmd = 'cat test_info.data'
                answer = self.execute_cmd(cmd)
                for line in answer:
                    if 'HSS_LICENSE:' in line:
                        self.add_to_macro('#HSS_LICENSE_BASE#', line.split(':')[1])
                    elif 'HSS_LICENSE_CRC' in line:
                        self.add_to_macro('#HSS_LICENSE_CRC_BASE#', line.split(':')[1])
                    elif 'EXTDB_BACKUP' in line:
                        self.add_to_macro('#EXTDB_BACKUP_BASE#', line.split(':')[1])

                cmd = 'cd -'
                self.execute_cmd(cmd)

            except Exception as e:
                _WRN('%s problem reading  ST_Population_Netconf for baseline' % self.id)
                _WRN('%s The following macro could not be available: HSS_LICENSE_BASE, HSS_LICENSE_CRC_BASE, EXTDB_BACKUP_BASE and NETCONF_COMMIT_BASE' % self.id)



        cmd = 'echo "CBA_PREPARE_UPGRADE:%s/ST_HssUpgradeTool/CBA_prepare_upgrade --node_user %s" >> common.mkr' % (self.git_path,self.CBA_user)
        self.execute_cmd(cmd)

        for element in self.service_config['common.mkr']:
            cmd = 'echo "%s:%s" >> common.mkr' % (element['name'], self.macro_translator(element['value']))
            self.execute_cmd(cmd)

        for key in self.__macro.keys():
            cmd = 'echo "%s:%s" >> common.mkr' % (key.replace('#',''), self.__macro[key])
            self.execute_cmd(cmd, translate=False)


    def shutdown(self):
        if self.__node is None:
            return

        if self.ongoing_test:
            _INF('Stopping RTC')
            self.stop()

    def stop(self):
        self.send_rtc_command('quit')

    def set_test_excution_as_discarded(self):
        self.send_rtc_command('set test_execution_status DISCARDED')

    def resume_test(self):
        self.send_rtc_command('resume')

    def send_rtc_command(self, cmd):
        if self.__node is None:
            return
        try:
            _INF('%s sending to HSS_rtc: "%s"' % (self.id, cmd))
            send_udp_command(cmd, 'localhost', RTC_REMOTE_UDP_PORT)

        except Exception as e:
            _WRN( '%s HSS_rtc command sent problem: %s' %  (self.id, e))

    def run_traffic(self,start_event):

        if self.__node is None: 
            return None

        cmd = 'run_clean_test_environment --exclude %s' % os.getpid()
        try:
            self.execute_cmd(cmd,timeout=600)
        except ExecutionRunError:
            pass

        _INF('%s executing HSS_rtc cmd: %s' % (self.id, self.macro_translator(self.command_line)))
        self.__channel.write_line(self.macro_translator(self.command_line))

        while (not self.force_exit):
            try:
                result = self.__channel.expect([self.__node.get_sync_expression(),
                                        'RTC execution start','\r\n'],timeout=10.0 )

                if result == 0:
                    _INF('%s HSS_rtc execution finished' % self.id)
                    self.ongoing_test = False
                    break

                if result == 1 and not start_event.isSet():
                    _INF('%s HSS_rtc execution started' % self.id)
                    self.ongoing_test = True
                    start_event.set()
                if result == 2:

                    print self.__channel.stdout[1:]
                    continue



            except pexpect.TIMEOUT as e:
                continue

            except pexpect.EOF as e:
                self.execution_info_error = '%s EOF received during HSS_rtc execution' % self.id
                break

        if not start_event.isSet():
            self.execution_info_error = '%s HSS_rtc failed to start' % self.id
            start_event.set()

        else:
            try:
                if self.to_pack_and_store:
                    tar_file = '%s.tar.gz' % os.path.basename(self.__working_dir)
                    cmd = 'tar -czvf %s %s > /dev/null' % (tar_file, ' '.join(self.to_pack_and_store))
                    self.execute_cmd(cmd,timeout=1800)

                if self.output_dir is not None and self.to_pack_and_store:
                    output_dir = os.path.join(self.output_dir, self.test_config['build'])
                    cmd = 'mkdir -p %s' % output_dir
                    self.execute_cmd(cmd)

                    cmd = 'chmod 777 %s' % output_dir
                    self.execute_cmd(cmd)

                    cmd = 'mv %s %s' %  (tar_file, output_dir)
                    self.execute_cmd(cmd,timeout=1800)

                    cmd = 'cd ..'
                    self.execute_cmd(cmd)

                    cmd = 'rm -rf %s' %  os.path.basename(self.__working_dir)
                    self.execute_cmd(cmd,timeout=600)

            except Exception as e:
                _ERR('%s' % e)

        self.__node.release()
        self.__node = None

    def execute_cmd(self, cmd, timeout=300, translate=True):
        if translate:
            cmd = self.macro_translator(cmd)
        _INF('%s executing: %s' % (self.id, cmd))
        answer = self.__node.run_command(cmd,timeout=timeout)
        result_code = self.__node.get_result_code()

        if result_code:
            error_info = '%s problem executing "%s" : %s' % (self.id, cmd, answer)
            raise ExecutionRunError(error_info)

        return answer
