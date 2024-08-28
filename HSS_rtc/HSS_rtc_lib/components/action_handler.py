#!/usr/bin/env python
#

import time
import os
import sys
import traceback
import pexpect
import re
import threading
import collections
import Queue
import socket
import getpass

import hss_utils.st_command as st_command
import hss_utils.connection as connection
import hss_utils.node.gentraf
import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning


from hss_utils.st_command import *
import hss_utils.node.gentraf
from HSS_rtc_lib.shared import *
from . import ExecutionConfigurationError
from . import ExecutionStartError
from . import ExecutionRunError


USERID = getpass.getuser()
HOSTNAME = socket.gethostname()

class ActionHandler(threading.Thread):
    def __init__(self, executor, config, phase_path):
        threading.Thread.__init__(self)

        self.__id = 'ACTION_HANDLER'
        self.__running = False

        self.executor = executor
        self.__ready = False
        self.__node = None
        self.__executing_cmd = False
        self.__error_code = 0
        self.__actions = []
        self.__action_index = 0
        self.__logfilename = os.path.join(phase_path, '%s.log' % self.id.lower())
        self.__logfile = open(self.__logfilename, "w")
        self.__force_exit = False
        self.__mutex = st_command.QLock()
        self.udp_messages = Queue.Queue()
        for cmd in ['start_scenario_stable_check','stop_scenario_stable_check','cancel_action','add_info_to_summary']:
            self.executor.rtc_data.remote_control.subscribe(cmd,self)

        self.__load_monitor_needed = False
        for action in config['action']:
            try:
                enable = action["enable"]
                if isinstance(enable,str) or isinstance(enable,unicode):
                    enable = self.executor.rtc_data.get_macro_value(enable)
                    enable = (enable == 'true')

                if enable:
                    self.__actions.append(action)
                else:
                    continue

                cmd = action['cmd']
                id = action['id']
                trigger = action['trigger']['load']

                if trigger != -1 and not self.executor.execution_with_traffic:
                    configuration_error = 'Load trigger for %s action shall be -1 in a scenario without traffic' % id
                    raise ExecutionConfigurationError(configuration_error)

                trigger2 = action['trigger']['time']

            except KeyError as e:
                configuration_error = 'Missing %s action field in json file' % str(e)
                raise ExecutionConfigurationError(configuration_error)

            if not isinstance(action['trigger']['load'],int):
                load = self.executor.rtc_data.get_load_monitor_target_from_reference(action['trigger']['load'])
                if load == -1:
                    configuration_error = 'Action load trigger for %s not found' % action['trigger']['load']
                    raise ExecutionConfigurationError(configuration_error)

                action['trigger']['load'] = load
                _INF('%s Using trigger load %s' % (self.id, load))

            if action['trigger']['load'] != -1 or action.get('disable_load_monitor', False):
                self.__load_monitor_needed = True

        if len(self.__actions):
            if self.executor.execution_with_traffic and self.__load_monitor_needed and self.executor.load_monitor.id == 'FakeMonitor':
                configuration_error = 'Monitor load is mandatory when there are actions with load trigger != -1 or disable_load_monitor == True'
                raise ExecutionConfigurationError(configuration_error)

            if self.executor.execution_with_traffic and self.executor.error_monitor.id == 'FakeMonitor':
                configuration_error = 'Monitor error is mandatory when using action'
                raise ExecutionConfigurationError(configuration_error)

            access_config = {'host':HOSTNAME}
            self.__node = hss_utils.node.gentraf.GenTraf(config = access_config)
            try:
                if phase_path.startswith('/'):
                    self.__node.working_dir = os.path.join(phase_path,self.__id)
                else:
                    self.__node.working_dir = os.path.join(os.getcwd(),phase_path,self.__id)
                self.__channel = self.__node.get_channel()
                self.__ready = True

            except (connection.Unauthorized,connection.ConnectionFailed, connection.ConnectionTimeout) as e:
                _ERR('%s creation problem: %s' % (self.__id, str(e)))

            except KeyboardInterrupt:
                _WRN('%s creation cancelled by user' % self.__id)

            except Exception as e:
                _ERR('%s creation problem: %s' % (self.__id, str(e)))

        self.log_event('', '%s created with %s actions configured' % (self.__id, len(self.__actions)), True)


    @property
    def force_exit(self):
        return self.__force_exit

    def activate_force_exit(self):
        self.__force_exit = True

    @property
    def logfile(self):
        return self.__logfile

    def log_event(self, level, event_info, add_timestamp=False):
        timestamp = ''
        if add_timestamp:
            timestamp = '%s: ' % datetime.now()
        info = '%s%s' % (timestamp, event_info)
        if self.logfile is not None:
            try:
                self.logfile.write('%s\n' % info)
            except ValueError:
                pass

        if level == 'info':
            _INF(event_info)
        elif level == 'error':
            _ERR(event_info)
        elif level == 'warning':
            _WRN(event_info)


    @property
    def action(self):
        return self.__actions[self.__action_index]

    @property
    def action_id(self):
        return self.action.get('id','DEFAULT_ACTION')

    @property
    def cmd(self):
        try:
            if '#' in self.action['cmd']:
                self.action['cmd'] = self.executor.rtc_data.macro_translator(self.action['cmd'])
            return self.action['cmd']
        except KeyError as e:
            pass

    @property
    def stop_on_fail(self):
        return self.action.get('stop_on_fail', False)

    @property
    def report_not_valid(self):
        return self.action.get('report_not_valid', False)

    @property
    def add_to_verdict(self):
        return self.action.get('add_to_verdict', False)

    @property
    def display_execution(self):
        return self.action.get('display_execution', False)

    @property
    def time_running_traffic_after_execution(self):
        return self.action.get('time_running_traffic_after_execution', -1)

    @property
    def max_action_time(self):
        return self.action.get('max_action_time', -1)

    @property
    def is_timed(self):
        return (self.max_action_time > 0)

    @property
    def disable_load_monitor(self):
        return self.action.get('disable_load_monitor', False)

    @property
    def stop_error_scenario_register(self):
        return self.action.get('stop_error_scenario_register', False)

    @property
    def allow_info_to_summary(self):
        return self.action.get('allow_info_to_summary', True)

    @property
    def trigger_load(self):
        try:
            return self.action['trigger']['load']
        except KeyError as e:
            return -1

    @property
    def trigger_time(self):
        try:
            return self.action['trigger']['time']
        except KeyError as e:
            return -1

    @property
    def max_trigger_time(self):
        return self.action.get('max_trigger_time', -1)

    @property
    def id(self):
        return self.__id 

    @property
    def online(self):
        return self.__running

    @property
    def triggered(self):
        trigger_time = float(int(self.trigger_time))
        max_trigger_time = float(int(self.max_trigger_time))
        check_max_trigger_time = (int(self.max_trigger_time) != -1)
        self.log_event('', '%s time trigger condition %s' % (self.id, trigger_time), True)
        while self.online:
            if self.force_exit:
                return False
            now = time.time()
            time.sleep(1.0)
            trigger_time -= time.time() - now
            max_trigger_time -= time.time() - now
            if check_max_trigger_time and max_trigger_time < 0:
                error_info = '%s Max time waiting for trigger expired:  %s seconds' % (self.id, self.max_trigger_time)
                self.log_event('error', error_info, True)
                if self.add_to_verdict:
                    self.executor.rtc_data.update_verdict(False, error_info=error_info)
                if self.report_not_valid:
                    self.executor.rtc_data.set_test_suite_execution_status('FAILED')

                self.log_event('', '%s requesting loadgen phase stop' % self.id, True)
                self.executor.request_stop_phase()

                return False

            if self.trigger_load != -1:
                if self.executor.load_monitor.load_status == 'STABLE' and self.executor.load_monitor.target_load == int(self.trigger_load):
                    if trigger_time < 0:
                        self.log_event('info', '%s Trigger action conditions load:%s time:%s reached.' % (self.id, self.trigger_load, self.trigger_time), True)
                        return True
                else:
                    trigger_time = float(int(self.trigger_time))
            elif trigger_time < 0:
                self.log_event('info', '%s Trigger action conditions load:%s time:%s reached.' % (self.id, self.trigger_load, self.trigger_time), True)
                return True

        return False

    def shutdown(self):
        self.log_event('info', '%s shutdown received' % self.id, True)
        if self.__running:
            self.__mutex.acquire()
            if self.__node is not None:
                if self.__executing_cmd:
                    self.stop_cmd()
                self.__node.release()
                self.__node = None
                self.__ready = False
            self.log_event('info', '%s shutdown proccessed' % self.id, True)
            self.__mutex.release()

        self.__running = False
        if self.logfile is not None:
            self.logfile.close()
            self.__logfile = None


    def stop_cmd(self):

        self.log_event('info', '%s stop cmd received' % self.id, True)
        if self.__node is not None:
            self.__channel.write_line('\x03')

            now = time.time()
            max_time_for_shutdown = float(30)
            wait_for_shutdown = True
            self.log_event('info', '%s Wait for cmd stopped...max waiting time is %s seconds' % (self.id, max_time_for_shutdown), True)
            while wait_for_shutdown:
                if self.force_exit:
                    return
                wait_for_shutdown = False
                try:
                    result = self.__channel.expect([self.__node.get_sync_expression()],timeout=5.0 )
                    if result == 0:
                        self.log_event('info', '%s cmd stopped.' % self.id, True)
                        wait_for_shutdown = False

                except pexpect.EOF as e:
                    self.log_event('warning', '%s EOF received waiting for cmd stopped.' % self.id, True)

                except pexpect.TIMEOUT as e:
                    max_time_for_shutdown -= time.time() - now
                    if max_time_for_shutdown > 0:
                        wait_for_shutdown = True
                        continue

                    self.log_event('info', '%s TIME waiting for cmd stopped has expired.' % self.id, True)

                    wait_for_shutdown = False

                except KeyboardInterrupt:
                    self.log_event('warning', '%s User skips wait for cmd stopped' % self.id, True)



            error_info = '%s Cmd "%s" stopped by user' % (self.id, self.cmd)
            self.log_event('varning', error_info, True)
            if self.add_to_verdict:
                self.executor.rtc_data.update_verdict(False, error_info=error_info)

        self.__executing_cmd = False

    def start_handling(self):

        if self.__ready:
            self.start()

    def get_return_code(self):
        if self.__node is not None:
            cmd = 'echo EL:$?'
            full_answer = self.__node.run_command(cmd, timeout = 2.0, full_answer = True)

            if len(full_answer) == 0:
                return 0

            for line in full_answer.split('\r\n'):
                searchObj = re.search(r'EL:\d+',line)
                if searchObj:
                    error_code = searchObj.group()[3:]
                    try:
                        return  int(error_code)
                    except Exception as e:
                        self.log_event('', '%s get_return_code problem: %s' % (self.id, e), True)
                    return 0

        self.log_event('warning', '%s get_return_code problem: shell is already closed' % self.id, True)
        return -1

    def get_error_info(self,stderr):
        if self.__node is not None:
            if stderr == '':
                cmd = 'tail -5 "%s.stderr"' % self.action_id
                stderr = self.__node.run_command(cmd, full_answer = True)
            error_info = st_command.get_stFramework_error_message(stderr)
            if error_info is None:
                error_info = st_command.get_stFramework_error_message(stderr, header='stTool_message ')
            return error_info

        return 'unknown'

    def read_udp_cmd(self):
        try:
            data, client_answers = self.udp_messages.get(True, timeout=1.0)
            self.log_event('info', '%s UDP command received: %s' % (self.id, data), True)

            try:
                cmd = data.split(' ',1)[0]
            except IndexError:
                answer = '%s "data" NOT VALID' % self.id
                client_answers.put_nowait(answer)
                return

            if len(data.split(' ',1)) > 1:
                params = data.split(' ',1)[1]

            if cmd in ['cancel_action']:
                client_answers.put_nowait('ORDERED')
                eval('self.%s()' % cmd)

            elif cmd in ['add_info_to_summary']:
                return_data = eval('self.%s(params)' % cmd)
                client_answers.put_nowait(return_data)

            elif cmd in ['start_scenario_stable_check', 'stop_scenario_stable_check']:
                return_data = eval('self.%s()' % cmd)
                client_answers.put_nowait(return_data)

            else:
                client_answers.put_nowait('%s cmd not handled by %s' %(cmd, self.id))
        except Queue.Empty:
            pass

    def cancel_action(self):
        self.stop_cmd()


    def add_info_to_summary(self, params):
        answer = 'allow_info_to_summary not allowed'
        if params and self.allow_info_to_summary:
            self.executor.rtc_data.add_action_info(self.action_id, params)
            answer = 'OK'
        return answer


    def start_scenario_stable_check(self):
        if self.disable_load_monitor or self.stop_error_scenario_register:
            if self.stop_error_scenario_register:
                self.executor.error_monitor.start_monitoring(phase='loadgen')
            return 'OK'
        else:
            return 'NOT CONFIGURED'


    def stop_scenario_stable_check(self):
        error_rate = -1
        load_status = 'EVALUATION NOT CONFIGURED'
        if self.stop_error_scenario_register:
            error_rate = self.executor.error_monitor.stop_monitoring()
            self.executor.error_monitor.skip_check_last_register()

        if self.disable_load_monitor:
            load_status = self.executor.load_monitor.load_status

        if load_status in ['STABLE','EVALUATION NOT CONFIGURED'] and error_rate < self.executor.error_monitor.error_rate:
            return 'OK: Load:%s   Error rate:%s' % (load_status, error_rate)

        return 'FAILED: Load:%s   Error rate:%s' % (load_status, error_rate)


    def run(self):
        self.log_event('info', '%s start thread execution' % self.id, True)
        self.__running = True

        for index in range(len(self.__actions)):
            if self.force_exit:
                return

            self.log_event('', '%s Cmd index: %s' % (self.id, index ), True)
            self.__action_index = index

            if not self.triggered:
                return

            if self.executor.execution_with_traffic and self.disable_load_monitor:
                self.log_event('', '%s disabling load monitor' % self.id, True)
                self.executor.load_monitor.disable()

            if self.executor.execution_with_traffic and self.stop_error_scenario_register:
                self.log_event('', '%s disabling error scenario register' % self.id, True)
                self.executor.error_monitor.stop_monitoring()

            cmd = self.cmd
            self.log_event('info', '%s Executing "%s"' % (self.id, cmd), True)
            if self.display_execution:
                self.__channel.write_line('%s' % cmd)
            else:
                self.__channel.write_line('%s 1>%s.stdout 2>%s.stderr' % (cmd, self.action_id, self.action_id))

            self.__executing_cmd = True
            stderr=''
            sync_expression = self.__node.get_sync_expression()
            timeout = float(self.max_action_time)
            while self.__executing_cmd:
                if self.force_exit:
                    return
                now = time.time()
                try:
                    self.__mutex.acquire()
                    if self.__node is None:
                        self.__mutex.release()
                        return
                    result = self.__channel.expect([sync_expression,
                                                    '\r\n'],
                                                    timeout=2.0 )

                    if result == 0 and self.__executing_cmd:
                        if self.display_execution:
                            if not self.__channel.stdout.startswith('debug') and  len(self.__channel.stdout) > 4:
                                print '%s   %s' % (self.id, self.__channel.stdout[1:])

                        self.__error_code = self.get_return_code()
                        if self.__error_code:
                            if 'stTool_message' in self.__channel.stdout[1:]:
                                stderr=self.__channel.stdout[1:]

                            error_info = self.get_error_info(stderr)
                            if error_info is None:
                                result_info = 'error code: %s' % self.__error_code
                            else:
                                result_info = 'error info: %s' % error_info

                            error_info = '%s Cmd "%s" failed with %s' % (self.id, self.cmd , result_info)
                            self.log_event('error', error_info, True)
                            if self.add_to_verdict:
                                self.executor.rtc_data.update_verdict(False, error_info=error_info)
                            if self.report_not_valid:
                                self.executor.rtc_data.set_test_suite_execution_status('FAILED')
                        else:
                            result_info = 'SUCCESS'
                            self.log_event('info', '%s Cmd "%s" SUCCESS' % (self.id, self.cmd ), True)

                        self.executor.rtc_data.add_action_result('%-*s:   %s\n' % (25,self.action_id, result_info))

                        self.__executing_cmd = False
                        self.__mutex.release()
                        break
 
                    if result == 1 and self.display_execution:
                        if not self.__channel.stdout.startswith('debug') and  len(self.__channel.stdout) > 4:
                            print '%s   %s' % (self.id, self.__channel.stdout[1:])
                        if 'stTool_message' in self.__channel.stdout[1:]:
                            stderr=self.__channel.stdout[1:]

                    self.__mutex.release()
                except pexpect.TIMEOUT as e:
                    self.read_udp_cmd()
                    self.__mutex.release()
                    if self.is_timed:
                        timeout -= time.time() - now
                        if timeout < float(0):
                            error_info = '%s Timeout for "%s" execution' % (self.id, self.cmd)
                            self.log_event('error', error_info, True)
                            if self.add_to_verdict:
                                self.executor.rtc_data.update_verdict(False, error_info=error_info)
                            self.shutdown()
                    
                    continue

                except pexpect.EOF as e:
                    if self.__node is None:
                        self.__mutex.release()
                        break
                    else:
                        error_info = '%s EOF waiting for "%s" execution' % (self.id, self.cmd)
                        self.log_event('error', error_info, True)
                        if self.add_to_verdict:
                            self.executor.rtc_data.update_verdict(False, error_info=error_info)
                        self.__mutex.release()
                        self.shutdown()


            if self.executor.execution_with_traffic and self.disable_load_monitor:
                self.log_event('', '%s enabling load monitor' % self.id, True)
                self.executor.load_monitor.enable()

            if self.executor.execution_with_traffic and self.stop_error_scenario_register:
                self.log_event('', '%s enabling error scenario register' % self.id, True)
                self.executor.error_monitor.start_monitoring(phase='loadgen')

            if self.stop_on_fail and self.__error_code:
                run_error = '%s stop on fail with error code: %s' % (self.id, self.__error_code)
                self.log_event('', run_error, True)
                self.shutdown()
                if self.executor.execution_with_traffic:
                    self.executor.request_stop_phase()
                else:
                    break

            if self.executor.execution_with_traffic and self.time_running_traffic_after_execution > 1:
                self.log_event('', '%s start time_running_traffic_after_execution timer %s' % (self.id, self.time_running_traffic_after_execution), True)
                max_time = float(int(self.time_running_traffic_after_execution))
                while self.online:
                    if self.force_exit:
                        return
                    now = time.time()
                    time.sleep(5.0)
                    max_time -= time.time() - now
                    if max_time < 0:
                        break
                self.log_event('', '%s stop time_running_traffic_after_execution timer %s' % (self.id, self.time_running_traffic_after_execution), True)

        if not self.executor.execution_with_traffic:
            self.log_event('', '%s requesting EXECUTOR to finish' % self.id, True)
            self.executor.wait_for_action_handler = False


        elif self.time_running_traffic_after_execution != -1:
            self.log_event('', '%s requesting loadgen phase stop' % self.id, True)
            self.executor.request_stop_phase()

