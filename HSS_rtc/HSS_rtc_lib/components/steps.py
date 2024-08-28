#!/usr/bin/env python
#

import sys
import os
import os.path
import time
import filecmp
import signal
import traceback


import hss_utils.st_command as st_command
import hss_utils.connection as connection
import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning

from HSS_rtc_lib.shared import *
from . import ExecutionConfigurationError
from . import ExecutionStartError
from . import ExecutionRunError
from . import SkipPhase
from . import ExitRtc
from . import StopTestCaseOnFail

class StepTranslator(object):
    def __init__(self, id, user_config, output_path, rtc_data, data={}):
        self.__step = id
        self.__data = data
        self.__host = user_config.NODE
        self.__user = user_config.user
        self.__port = user_config.port
        self.__host_controller = user_config.node_controller
        self.__tcname = rtc_data.id
        self.__scxb = user_config.scxb
        self.__extdb = user_config.extdb
        self.__extdb_type = user_config.extdb_type
        self.__hss_backup = user_config.hss_backup
        self.__extdb_backup = user_config.extdb_backup
        _DEB('StepTranslator user_config: %s' % user_config)
        if user_config.node_type == 'CBA':
            self.__step_data = {
                         # step name : [type, command line argument]

                        'restore_hss_backup' : ['framework', 'CBA_restore_backup -v --node %s --user %s --port %s %s' % (self.__host, self.__user,self.__port,
                                                                                                                        ('' if self.__hss_backup == '' else ' -b %s' % self.__hss_backup))],
                        'restore_extdb_backup' : ['framework', '%s_restore_backup -v --node %s %s %s' % (self.__extdb_type, self.__extdb,
                                                                                                      ('-i' if self.__extdb_type == 'GTLA' else '' ),
                                                                                                      ('' if self.__extdb_backup == '' else ' -b %s' % self.__extdb_backup))],
                        'clean_alarms' : ['framework', 'CBA_clean_alarms --node %s --user %s --port %s -v' % (self.__host, self.__user, self.__port)],
                        'clean_alerts' : ['framework', 'CBA_clean_alerts --node %s --user %s --port %s -v' % (self.__host, self.__user, self.__port)],
                        'clean_app_logs' : ['framework', 'CBA_clean_app_logs --node %s --user %s --port %s -v -f' % (self.__host, self.__user, self.__port)],
                        'clean_console_logs' : ['framework', 'CBA_clean_console_logs --node %s --user %s --port %s -v' % (self.__host, self.__user, self.__port)],
                        'clean_pmf_logs' : ['framework', 'CBA_clean_pmf_logs --node %s --user %s --port %s -v' % (self.__host, self.__user, self.__port)],

                        'get_alarms' : ['framework', 'CBA_check_alarms --node %s --user %s --port %s -v -x "Diameter Link Disabled"' % (self.__host, self.__user, self.__port)],
                        'get_nbi_alarms' : ['framework', 'CBA_NBI_check_alarms --node %s -v' % self.__scxb],
                        'get_free_memory' : ['framework', 'CBA_get_free_memory --node %s -o %s --user %s --port %s -v' % (self.__host, output_path, self.__user, self.__port)],
                        'get_node_status' : ['framework', 'CBA_get_node_status --node %s --user %s --port %s -v' % (self.__host, self.__user, self.__port)],
                        'get_vdicos_vars' : ['framework', 'CBA_get_node_vdicos_vars --node %s --user %s --port %s -v' % (self.__host, self.__user, self.__port)],
                        'get_repository_list' : ['framework', 'CBA_get_repository_list --node %s --user %s --port %s -v' % (self.__host, self.__user, self.__port)],
                        'get_capsule_dumps' : ['framework', 'CBA_list_capsule_dumps --node %s --user %s --port %s -v' % (self.__host, self.__user, self.__port)],
                        'get_ExtDb_connections' : ['framework', 'CBA_check_ExtDb_connections --node %s --user %s --port %s -v' % (self.__host, self.__user, self.__port)],
                        'get_Http_connections' : ['framework', 'CBA_check_Http_connections --node %s --user %s --port %s -v' % (self.__host, self.__user, self.__port)],
                        'get_last_pl_reboot' :  ['framework', 'CBA_get_last_pl_reboot --node %s --user %s --port %s -v' % (self.__host, self.__user, self.__port)],
                        'get_dynamic_process' : ['framework', 'CBA_find_dynamic_process --node %s --user %s --port %s -v' % (self.__host, self.__user, self.__port)],
                        'get_all_processes' : ['framework', 'CBA_find_all_processes --node %s --user %s --port %s -v' % (self.__host, self.__user, self.__port)],
                        'get_processes_list' : ['framework', 'CBA_list_processes --node %s --user %s --port %s -v' % (self.__host, self.__user, self.__port)],

                        'health_check' : ['framework', 'CBA_health_check --node %s --user %s --port %s -v -o %s' % (self.__host, self.__user, self.__port,output_path)],

                        'cmw_collect_info' : ['framework', 'CBA_cmw_collect_info --node %s --user %s --port %s -v -o %s -s %s' % (self.__host, self.__user, self.__port, output_path, self.__tcname)],
                        'diacc_collect_info' : ['framework', 'CBA_diacc_collect_info --node %s --user %s --port %s -v -o %s ' % (self.__host, self.__user, self.__port, output_path)],
                        'collect_logs' : ['framework', 'CBA_collect_logs --node %s --user %s --port %s -v -o %s -s %s' % (self.__host, self.__user, self.__port, output_path, self.__tcname)],
                        'pmf_counter_sum' : ['framework', 'CBA_pmf_counter_sum --node %s --user %s --port %s -v -o %s/pmf_counter_sum_%s.txt' % (self.__host, self.__user, self.__port, output_path, self.__tcname)],
                        'pmf_counter_to_csv' : ['external', 'CBA_pmf_counter_to_csv --input %s --user %s --port %s -o %s/pmf_counter_csv_%s --log-path %s> /dev/null 2>&1' % (self.__host, self.__user, self.__port, output_path, self.__tcname,rtc_data.root_path)],

                        'check_pl_reboot' : ['function', "compare_output_files('get_last_pl_reboot', 'PL reboot')"],
                        'check_capsule_dumps' : ['function', "compare_output_files('get_capsule_dumps', 'Capsules')"],
                        'check_all_processes' : ['function', "compare_output_files('get_all_processes', 'Changes in HSS processes')"],
                        'check_alarms' : ['function', "compare_output_files('get_alarms', 'New alarms')"],
                        'check_nbi_alarms' : ['function', "compare_output_files('get_nbi_alarms', 'New NBI alarms')"],
                        'check_node_status' : ['function', "compare_output_files('get_node_status', 'Node status')"],
                        'check_vdicos_vars' : ['function', "compare_output_files('get_vdicos_vars', 'vDicos variables')"],
                        'check_repository_list' : ['function', "compare_output_files('get_repository_list', 'Repository List')"],
                        'check_ExtDb_connections' : ['function', "compare_output_files('get_ExtDb_connections', 'ExtDb connections')"],
                        'check_Http_connections' : ['function', "compare_output_files('get_Http_connections', 'Http connections')"],
                        'check_list_processes' : ['function', "check_list_processes"],
                        'check_free_memory' : ['function', "check_free_memory()"],
                        'check_traffic' : ['function', "check_traffic_result"],
                        'check_epm' : ['function', "check_epm"],
                        "check_load_stability" : ['function', "check_load_stability"],
                        "check_scenario_error_rate" : ['function', "check_scenario_error_rate()"]
                        }
        elif user_config.node_type == 'CLOUD':
            self.__step_data = {
                         # step name : [type, command line argument]

                        'restore_extdb_backup' : ['framework', '%s_restore_backup -v %s %s' % (self.__extdb_type,
                                                                                                      ('-i' if self.__extdb_type == 'GTLA' else '' ),
                                                                                                      ('' if self.__extdb_backup == '' else ' -b %s' % self.__extdb_backup))],
                        'refresh_credentials' : ['framework', 'get_env_info --cloud-credential -v'],
                        'get_nodes_info' : ['framework', 'CLOUD_nodes_info -v'],
                        'get_deployments_info' : ['framework', 'CLOUD_deployments_info -v'],
                        'get_pods_info' : ['framework', 'CLOUD_pods_info -v'],
                        'get_services_info' : ['framework', 'CLOUD_services_info -v'],
                        'get_events_info' : ['framework', 'CLOUD_events_info -v'],
                        'get_nof_pods_per_node' : ['framework', 'CLOUD_nof_pods_per_node -v'],
                        'get_total_nof_pods' : ['framework', 'CLOUD_total_nof_pods -v'],
                        'get_node_resources' : ['framework', 'CLOUD_node_resources -v'],
                        'get_replica' : ['framework', 'CLOUD_replica -v'],
                        'get_alarms' : ['framework', 'CLOUD_get_alarms -v'],
                        'get_kubectl_version' : ['framework', 'CLOUD_kubectl_version -v'],
                        'get_helm_version' : ['framework', 'CLOUD_helm_version -v'],
                        'get_ccd_version' : ['framework', 'CLOUD_ccd_version -v'],
                        'get_software_installed' : ['framework', 'CLOUD_software_installed -v'],

                        'collect_all_containers_logs' : ['framework', 'CLOUD_get_all_containers_logs -v'],
                        'collect_pods_logs' : ['framework', 'CLOUD_get_pods_logs -v'],

                        'check_nof_pods_per_node' : ['function', "compare_output_files('get_nof_pods_per_node', 'Pods per node')"],
                        'check_events_info' : ['function', "compare_output_files('get_events_info', 'Events')"],
                        'check_alarms' : ['function', "compare_output_files('get_alarms', 'Alarms')"],
                        'check_pods_restarts' : ['function', "check_pods_restarts"],

                        'check_all_pods_running' : ['framework', 'CLOUD_check_all_pods_running -v'],
                        'check_all_containers_started' : ['framework', 'CLOUD_check_all_containers_started -v'],
                        'check_all_nodes_ready' : ['framework', 'CLOUD_check_all_nodes_ready -v'],

                        'check_epm' : ['function', "check_epm"],
                        'check_traffic' : ['function', "check_traffic_result"],
                        "check_scenario_error_rate" : ['function', "check_scenario_error_rate()"]
                       }
        else:
            self.__step_data = {
                         # step name : [type, command line argument]

                        'restore_hss_backup' : ['framework', 'TSP_restore_backup -v --node %s %s' % (self.__host_controller, ('' if self.__hss_backup == '' else ' -b %s' % self.__hss_backup))],
                        'restore_extdb_backup' : ['framework', '%s_restore_backup -v --node %s %s %s' % (self.__extdb_type, self.__extdb,
                                                                                                      ('-i' if self.__extdb_type == 'GTLA' else '' ),
                                                                                                      ('' if self.__extdb_backup == '' else ' -b %s' % self.__extdb_backup))],
                        'clean_app_logs' : ['framework', 'TSP_clean_app_logs --node %s -v' % self.__host_controller],
                        'clean_pmf_logs' : ['framework', 'TSP_clean_pmf_logs --node %s -v' % self.__host_controller],

                        'get_alarms' : ['framework', 'TSP_check_alarm --node %s -v -p -x "Diameter, Link Failure" "Diameter, Link Disabled" "Maximum backup interval exceeded" "IO, Archiving Interval Exceeded" "Zone Reloaded From Backup"' % self.__host_controller],
                        'get_capsule_dumps' : ['framework', 'TSP_list_capsule_dumps --node %s -v' % self.__host_controller],
                        'get_processors_info' : ['framework', 'TSP_get_processors_info --node %s -v' % self.__host_controller],
                        'get_dynamic_process' : ['framework', 'TSP_find_dynamic_process --node %s -v' % self.__host_controller],

                        'health_check' : ['framework', 'TSP_health_check --node %s -v -o %s' % (self.__host_controller, output_path)],

                        'collect_logs' : ['framework', 'TSP_collect_logs --node %s -v -o %s -s %s' % (self.__host_controller, output_path, self.__tcname)],
                        'pmf_counter_sum' : ['framework', 'TSP_pmf_counter_sum --node %s -v -o %s/pmf_counter_sum_%s.txt' % (self.__host_controller, output_path, self.__tcname)],
                        'pmf_counter_to_csv' : ['external', 'TSP_pmf_counter_to_csv --input %s -o %s/pmf_counter_csv_%s --log-path %s > /dev/null 2>&1' % (self.__host_controller, output_path, self.__tcname,rtc_data.root_path)],

                        'check_alarms' : ['function', "compare_output_files('get_alarms', 'New alarms')"],
                        'check_capsule_dumps' : ['function', "compare_output_files('get_capsule_dumps', 'Capsules')"],
                        'check_processors_info' : ['function', "compare_output_files('get_processors_info', 'Processor Info')"],
                        'check_traffic' : ['function', "check_traffic_result"],
                        'check_epm' : ['function', "check_epm"],
                        "check_load_stability" : ['function', "check_load_stability()"],
                        "check_scenario_error_rate" : ['function', "check_scenario_error_rate()"]
                       }

    @property
    def cmd(self):
        try:
            return self.__step_data[self.__step][1]

        except KeyError, e:
            try:
                return self.__data['cmd']
            except Exception, e:
                _ERR('Unknown step: %s' % self.__step)
                configuration_error = 'Problem finding %s cmd : %s' % (self.__step, str(e))
                raise ExecutionConfigurationError(configuration_error)

        except Exception, e:
            _ERR('Unknown step: %s' % self.__step)
            configuration_error = 'Problem finding %s cmd : %s' % (self.__step, str(e))
            raise ExecutionConfigurationError(configuration_error)

    @property
    def framework(self):
        return self.__data.get('framework',False)

    @property
    def step_type(self):
        try:
            return self.__step_data[self.__step][0]

        except KeyError, e:
            try:
                return 'framework' if self.framework else 'external'
            except Exception, e:
                _ERR('Unknown step type: %s' % self.__step)
                configuration_error = 'Problem finding %s type : %s' % (self.__step, str(e))
                raise ExecutionConfigurationError(configuration_error)

        except Exception, e:
            _ERR('Unknown step type: %s' % self.__step)
            configuration_error = 'Problem finding %s type : %s' % (self.__step, str(e))
            raise ExecutionConfigurationError(configuration_error)


class Step(object):
    def __init__(self, config, user_config, phase, output_path, rtc_data):
        self.__config = config
        self.__rtc_data = rtc_data
        self.__id = config['id']
        self.__user_config = user_config
        self.__phase = phase
        self.__output_path = output_path
        self.__step = StepTranslator(self.__id, user_config, output_path, rtc_data, config)
        self.__stdout = ''
        self.__stderr = ''
        self.__error_info = ''
        self.__returncode = None
        _DEB('Step user_config: %s' % user_config)
        _DEB('Step config: %s' % config)
        _DEB('Step rtc_data: %s' % rtc_data)

    @property
    def id(self):
        return self.__id

    @property
    def rtc_data(self):
        return self.__rtc_data

    @property
    def exit_rtc_on_fail(self):
        return self.__config.get('exit_rtc_on_fail',False)

    @property
    def stop_on_fail(self):
        return self.__config.get('stop_on_fail',False)

    @property
    def skip_phase_on_fail(self):
        return self.__config.get('skip_phase_on_fail',False)

    @property
    def report_not_valid(self):
        return self.__config.get('report_not_valid',False)

    @property
    def repeat(self):
        return self.__config.get('repeat',False)

    @property
    def add_to_verdict(self):
        return self.__config.get('add_to_verdict',False)

    @property
    def add_to_summary(self):
        return self.__config.get('add_to_summary',False)

    @property
    def extra_parameters(self):
        return self.__config.get('extra_parameters','')

    @property
    def max_time(self):
        return self.__config.get('max_time',-1)

    @property
    def background(self):
        return self.__config.get('background',False)

    @property
    def cmd(self):
        cmd = self.__step.cmd + ' %s' % self.extra_parameters
        if '#' in cmd:
            cmd = self.rtc_data.macro_translator(cmd)
        return cmd

    @property
    def function(self):
        function = self.__step.cmd
        if '(' not in function:
            function = self.__step.cmd + '(%s)' % self.extra_parameters

        if '#' in function:
            function = self.rtc_data.macro_translator(function)

        return function

    @property
    def step_type(self):
        return self.__step.step_type

    @property
    def stdout(self):
        return self.__stdout

    @property
    def returncode(self):
        return self.__returncode

    @property
    def error_info(self):
        return self.__error_info

    def get_error_info(self,stderr):

        error_info = st_command.get_stFramework_error_message(stderr)
        if error_info is None:
            error_info = st_command.get_stFramework_error_message(stderr, header='stTool_message ')
        if error_info is None:
            error_info = 'unknown'
        return error_info

    def run(self):
        if self.step_type in ['framework', 'external']:
            if self.background:
                cmd = st_command.BackgroundCommand(self.cmd)
                _INF('Executing in background: %s' % self.cmd)

                try:
                    cmd.run()
                    time.sleep(5)
                    if not cmd.is_running:
                        raise ExecutionConfigurationError('Failed to run "%s"' % self.cmd)
                    self.rtc_data.add_background_command(cmd)
                except Exception as e:
                    self.__error_info = '%s' % e
                    self.__returncode = 1

            else:
                _INF('Executing: %s' % self.cmd)
                cmd = '%s%s' % (('run_command_node ' if self.step_type == 'framework' else ''), self.cmd)
                if self.max_time > 1:
                    cmd_timed = st_command.Command(cmd, stderr = True)
                    self.__stdout, self.__stderr, self.__returncode = cmd_timed.run(timeout=self.max_time)
                    if len(self.__stderr.splitlines()):
                        last_stderr_line = self.__stderr.splitlines()[-1]
                        if 'Command Timeout' in last_stderr_line:
                            self.__error_info = last_stderr_line
                else:
                    self.__stdout, self.__stderr, self.__returncode = st_command.execute_cmd('%s' % cmd ,stderr = True)

                if len(self.__stdout)>1:
                    self.save_info_to_file('%s.data'  % self.__id)

                if self.__returncode or self.__user_config.verbose:
                    self.save_log_to_file('%s_%s.log'  % (self.__phase, self.__id))
                    if not self.__error_info:
                        self.__error_info = self.get_error_info(self.__stderr)

            if self.__returncode:
                if self.add_to_verdict or self.stop_on_fail or self.exit_rtc_on_fail or self.report_not_valid:
                    self.rtc_data.update_verdict(False,error_info='%s %s: %s' % (self.__phase, self.cmd,self.__error_info),repeat=self.repeat)

                _ERR('FAILED    %s' % self.__error_info)

                if self.report_not_valid:
                    self.rtc_data.set_test_suite_execution_status('FAILED')

                self.rtc_data.add_faulty_step('%-*s%s\n\t\t\t   %s\n' % (15, self.__phase, self.cmd, self.__error_info))

                if self.exit_rtc_on_fail:
                    raise ExitRtc('configured in %s at %s phase' % (self.__id, self.__phase))

                if self.stop_on_fail:
                    raise StopTestCaseOnFail('configured in %s at %s phase' % (self.__id, self.__phase))

                if self.skip_phase_on_fail:
                    raise SkipPhase('configured in %s at %s phase' % (self.__id, self.__phase))

            else:
                _INF('SUCCESS')

        elif self.step_type == 'function':
            return self.function

        else:
            configuration_error = 'Unknown step: %s' % self.__id
            raise ExecutionConfigurationError(configuration_error)


    def save_info_to_file(self, filename):
        try:
            filename = os.path.join(self.__output_path, filename)

            with open(filename , "w") as text_file:
                text_file.write('%s' % self.__stdout) 
        except Exception, e:
            run_error = 'Error saving file: %s' % str(e)
            raise ExecutionRunError(run_error)

    def save_log_to_file(self, filename):
        try:
            log_path = os.path.join(self.__output_path, '../command_log')
            if not os.path.exists(log_path):
                os.makedirs(log_path)

            filename = os.path.join(log_path, filename)
            with open(filename , "w") as text_file:
                text_file.write('%s' % self.__stderr) 
        except Exception, e:
            run_error = 'Error saving file: %s' % str(e)
            raise ExecutionRunError(run_error)


