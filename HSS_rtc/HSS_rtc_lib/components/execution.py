#!/usr/bin/env python
#

import sys
import os
import os.path
import time
import filecmp
import signal
import Queue
import threading
import copy
import pprint
from datetime import datetime

import hss_utils.st_command as st_command
import hss_utils.connection as connection
import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning

from HSS_rtc_lib.shared import *
from . import bat_instance
from . import bat_instance_with_telnet
from . import phases
from . import scheduler
from . import monitor
from . import diaproxy_handler
from . import action_handler
from . import ExecutionConfigurationError
from . import ExecutionStartError
from . import ExecutionRunError
from . import BatError

class EXECUTION(phases.Phase):
    def __init__(self, config , user_config, rtc_data):

        phases.Phase.__init__(self, config , 'EXECUTION', user_config, rtc_data)

        self.__cabinet = user_config.cabinet
        self.__faulty_scenario = False
        self.answers = Queue.Queue()
        self.__stop_phase_pending = False
        self.__running_phase = ''
        self.__wait_for_action_handler = False
        self.__started_component = []
        self.__external_tools = []
        self.__Memory_monitor = monitor.FakeComponent(id='FakeMonitor')
        self.__Load_monitor = monitor.FakeComponent(id='FakeMonitor')
        self.__Error_monitor = monitor.FakeComponent(id='FakeMonitor')
        self.__Alarm_monitor = monitor.FakeComponent(id='FakeMonitor')
        self.__Diaproxy_handler = monitor.FakeComponent(id='FakeDiaproxyHandler')
        self.__Action_handler = monitor.FakeComponent(id='FakeActionHandler')
        self.__CPS_scheduler = None
        self.__phase_path = os.path.join(rtc_data.root_path, 'EXECUTION')
        if not os.path.exists(self.__phase_path):
            os.makedirs(self.__phase_path)

        self.__execution_with_traffic = False

        _DEB('%s Initialize ' % self.id)
        _DEB('%s Configuration is %s' % (self.id, self.config['configuration']))
        try:
            if not isinstance(self.config['instances'],dict):
                reference = self.config['instances']
                instances = rtc_data.get_bat_instances_from_reference(reference)
                if not instances:
                    configuration_error = 'BAT instances configuration for %s not found' % reference
                    self.release(ExecutionConfigurationError(configuration_error))

                self.config['instances'] = instances
                _INF('%s Using traffic reference %s' % (self.id, reference))

            for BAT_instance in self.config['instances'].keys():
                if self.config['instances'][BAT_instance]['enable']:
                    self.__execution_with_traffic = True
                    break

        except KeyError:
            pass

        if self.__execution_with_traffic:
            self.__CPS_scheduler = scheduler.Scheduler(self, self.config, user_config,self.__phase_path)

        try:
            try:
                if self.config['configuration']['monitor_memory']['enable']:
                    self.__Memory_monitor = monitor.Memory_Monitor(self, self.config, self.user_config,self.working_path)
                    self.__started_component.append(self.__Memory_monitor)
            except KeyError:
                pass

            try:
                if self.config['configuration']['monitor_load']['enable']:
                    self.__Load_monitor = monitor.LoadMonitor(self, self.config['configuration'], self.__phase_path)
                    self.__started_component.append(self.__Load_monitor)
            except KeyError:
                pass

            try:
                if any(self.config['configuration']['monitor_error']['enable'].values()):
                    self.__Error_monitor = monitor.ErrorMonitor(self, self.config['configuration'], self.__phase_path)
                    self.__started_component.append(self.__Error_monitor)
            except KeyError:
                pass

            try:
                if self.config['configuration']['monitor_alarm']['enable']:
                    self.__Alarm_monitor = monitor.AlarmMonitor(self.config['configuration'],user_config, self.__phase_path)
                    self.__started_component.append(self.__Alarm_monitor)
            except KeyError:
                pass

            try:
                for tool in self.config['configuration']['external_tools']:
                    if tool.get('enable',False):
                        self.__external_tools.append(monitor.ExternalTool(self,tool, self.__phase_path)) 
            except KeyError:
                pass

            try:
                for element in self.config['configuration']['diaproxy_reports'].keys():
                    if self.config['configuration']['diaproxy_reports'][element]['enable']:
                        self.__Diaproxy_handler = diaproxy_handler.DiaproxyHandler(self, self.config['configuration'], self.__phase_path)
                        self.__started_component.append(self.__Diaproxy_handler)
                        break

            except KeyError:
                pass

            try:
                if self.config['configuration']['action']:
                    self.__Action_handler = action_handler.ActionHandler(self, self.config['configuration'], self.__phase_path)
                    self.__started_component.append(self.__Action_handler)
            except KeyError:
                pass

            try:
                if self.config['configuration']['Capacity_handler']['enable']:
                    self.__CPS_scheduler = scheduler.EC_Scheduler(self, self.config, user_config,self.__phase_path)
            except KeyError:
                pass

            if self.__CPS_scheduler:
                self.__started_component.append(self.__CPS_scheduler)

            if not self.__execution_with_traffic:
                _INF('%s Execution without traffic' % self.id)
                return

            self.create_BATs()

        except ExecutionConfigurationError, e:
            _ERR('EXECUTION %s' % str(e))
            self.release(e)

        except Exception as e:
            _WRN('%s Problem building component: %s' % (self.id, str(e)))
            self.release(e)

        try:
            self.__wait_pmf_counters = self.config['configuration']['wait_pmf_counters_update']
        except KeyError:
            self.__wait_pmf_counters = False

        try:
            self.__skip_postexec = self.config['configuration']['skip_postexec']
            _DEB('%s skip_postexec is %s' % (self.id, self.__skip_postexec))
            if self.__skip_postexec > 1: ## Different to  True or False
                if "#" in self.__skip_postexec:
                    value = self.rtc_data.get_macro_value(self.__skip_postexec)
                    _DEB('Value for skip_postexec macro is %s' % value)
                    if value == "True" or value == "true":
                        self.__skip_postexec = True
                        _DEB('Setting skip_postexec to true')
                    else:
                        self.__skip_postexec = False
                        _DEB('Setting skip_postexec to False')
                else:
                    self.__skip_postexec = False
                    _DEB('Not macro. Setting skip_postexec to False')
            _DEB('%s Final skip_postexec is %s' % (self.id, self.__skip_postexec))

        except KeyError:
            self.__skip_postexec = False
            _DEB('%s Key Error: skip_postexec is %s' % (self.id, self.__skip_postexec))

    def release(self, reason):
        error_info = '%s release for %s' % (self.id, reason)

        for tool in self.__external_tools:
            tool.shutdown()

        for component in reversed(self.__started_component):
            component.shutdown()

        for component in reversed(self.__started_component):
            if component.is_alive():
                component.join(5.0)

        self.stop_BATs()
        raise reason


    def request_stop_phase(self):
        self.__stop_phase_pending = True

    @property
    def time_between_bat_instances(self):
        value = self.rtc_data.get_macro_value('#TIME_BETWEEN_BAT_INSTANCES#')
        if value:
            return int(value)
        return 0

    @property
    def execution_with_traffic(self):
        return self.__execution_with_traffic

    @property
    def run_postexec(self):
        return not self.__skip_postexec

    @property
    def load_monitor(self):
        return self.__Load_monitor

    @property
    def error_monitor(self):
        return self.__Error_monitor

    @property
    def diaproxy_handler(self):
        return self.__Diaproxy_handler

    @property
    def alarm_monitor(self):
        return self.__Alarm_monitor

    @property
    def running_phase(self):
        return self.__running_phase

    @property
    def wait_pmf_counters(self):
        return self.__wait_pmf_counters

    @property
    def wait_for_action_handler(self):
        return self.__wait_for_action_handler

    @wait_for_action_handler.setter
    def wait_for_action_handler(self, wait_for_action_handler):
        self.__wait_for_action_handler = wait_for_action_handler

    @property
    def faulty_scenario(self):
        return self.__faulty_scenario

    @faulty_scenario.setter
    def faulty_scenario(self, faulty_scenario):
        self.__faulty_scenario = faulty_scenario

    def create_BATs(self):
        if not self.execution_with_traffic:
            return

        instances = 0
        for BAT_instance in self.config['instances'].keys():
            if self.config['instances'][BAT_instance]['enable']:
                host = self.user_config.generators[instances %len (self.user_config.generators)]
                if self.config['configuration']['manual_control']:
                    bat = bat_instance.BAT(host, self.user_config.NODE,
                            self.config['instances'][BAT_instance],
                            BAT_instance,
                            instances,
                            self.__phase_path,
                            self.config['configuration'],
                            self,
                            self.user_config.disable_graph) 
                    self.rtc_data.add_BAT_instance(bat)

                else:
                    bat = bat_instance_with_telnet.BAT_telnet(host, self.user_config.NODE,
                            self.config['instances'][BAT_instance],
                            BAT_instance,
                            instances,
                            self.__phase_path,
                            self.config['configuration'],
                            self,
                            self.user_config.disable_graph,
                            self.user_config.node_type) 
                    self.rtc_data.add_BAT_instance(bat)

                instances +=1

    def run_ttcn_cli_command(self, cmd, cli):
        answer = None
        try:
            cli.requests.put_nowait((cmd, self.answers))
            try:
                answer = self.answers.get(True, timeout=10.0)
            except Queue.Empty:
                _WRN('%s No answer received from %s' % (self.id, cli.id))
                pass

            return answer
        except Exception as e:
            action = '%s(%s)' % (cmd['action'],','.join(cmd['args']))
            run_error = '%s Problem executing "%s" in %s:  %s' % (self.id, action, cli.id, str(e))
            _ERR(run_error)
            self.release(ExecutionRunError(run_error))

    def read_traffic_phase(self, bat):
        if bat.execution_state != 'running':
            run_error = '%s Problem reading traffic phase. %s is not running' % (self.id, bat.id)
            _ERR(run_error)
            self.release(BatError(run_error))

        cmd ={'action':'get_value','args':["'ScGrpStatus'",'led = True']}
        return self.run_ttcn_cli_command(cmd, bat.monitor)

    def read_ScStatus(self, bat):
        if bat.execution_state != 'running':
            run_error = '%s Problem reading ScStatus. %s is not running' % (self.id, bat.id)
            _ERR(run_error)
            self.release(BatError(run_error))

        cmd ={'action':'get_value','args':["'ScStatus'",'led = True']}
        answer = self.run_ttcn_cli_command(cmd, bat.monitor)
        if not answer:
            run_error = '%s Problem with telnet connection for %s BAT when reading ScStatus.' % (self.id, bat.id)
            _ERR(run_error)
            self.release(BatError(run_error))

        return answer

    def get_all_diaproxys(self):
        diaproxys = []
        for bat in self.rtc_data.BAT_instances:
            diaproxys += bat.Diaproxys
        return diaproxys

    def start_Diaproxy_report(self):
        if self.__Diaproxy_handler.id != 'FakeDiaproxyHandler':
            self.__Diaproxy_handler.configure(diaproxys=self.get_all_diaproxys())
            self.__Diaproxy_handler.start_handling()

    def start_monitor_load(self):
        if self.load_monitor.id != 'FakeMonitor':
            self.load_monitor.configure(loadplotter=self.get_loadplotter())
            self.load_monitor.start_monitoring()

    def start_monitor_alarm(self):
        if self.alarm_monitor.id != 'FakeMonitor':
            self.alarm_monitor.start_monitoring()

    def start_Action_handler(self):
        if self.__Action_handler.id != 'FakeActionHandler':
            self.__Action_handler.start_handling()

    def get_loadplotter(self):
        for bat in self.rtc_data.BAT_instances:
            if bat.Loadplotter is not None:
                return bat.Loadplotter

    def start_phase(self, phase):
        self.error_monitor.start_monitoring(phase=phase)
        for bat in self.rtc_data.BAT_instances:
            if bat.execution_state != 'running':
                run_error = '%s %s not running' % (self.id, bat.id)
                _ERR(run_error)
                self.release(ExecutionRunError(run_error))

            current_phase = self.read_traffic_phase(bat)
            if (current_phase is not None and phase in current_phase) or phase == 'postexec':
                self.__running_phase = phase
                self.__CPS_scheduler.start_phase(phase, [bat])
                cmd ={'action':'start_phase','args':["'%s'"% phase]}
                result = self.run_ttcn_cli_command(cmd, bat.monitor)

                if result:
                    bat.traffic_phase = phase.split()[0]
                else:
                    run_error = '%s problems starting %s phase for %s' % (self.id, phase, bat.id)
                    _ERR(run_error)
                    self.release(ExecutionRunError(run_error))

            else:
                bat.phase_status == 'not_needed'

 
    def stop_phase(self):
        if self.running_phase == 'loadgen':
            self.load_monitor.shutdown()
        for bat in self.rtc_data.BAT_instances:
            if bat.execution_state != 'running':
                run_error = '%s problems stopping phase for %s' % (self.id, bat.id)
                _ERR(run_error)
                self.release(ExecutionRunError(run_error))

            cmd ={'action':'stop_phase','args':[]}
            result = self.run_ttcn_cli_command(cmd, bat.monitor)

            if not result:
                run_error = '%s problems stopping phase for %s' % (self.id, bat.id)
                _ERR(run_error)
                self.release(ExecutionRunError(run_error))


        all_ready = False
        while not all_ready :
            time.sleep(5.0)
            all_ready = True
            for bat in self.rtc_data.BAT_instances:
                if bat.execution_state not in ['running']:
                    run_error = '%s problems stopping phase for %s' % (self.id, bat.id)
                    _ERR(run_error)
                    self.release(ExecutionRunError(run_error))

                if self.read_ScStatus(bat) not in ['Stopped','Terminated']:
                    all_ready = False

        self.__stop_phase_pending = False
        self.error_monitor.stop_monitoring()

    def expected_phase_status(self, phase, bat):
        if phase == 'preexec':
            return 'loadgen - IDLE'
        elif phase == 'loadgen':
            return 'postexec - IDLE'
        else:
            return bat.first_phase

    def wait_phase_end(self, phase):
        all_ready = False
        max_waiting_time = 60.0
        while not all_ready:
            try:
                now = time.time()
                time.sleep(5.0)
                all_ready = True
                bat_to_refresh = []
                for bat in self.rtc_data.BAT_instances:
                    scStatus = self.read_ScStatus(bat)
                    #print 'scStatus %s  max_waiting_time %s' % (scStatus,max_waiting_time)
                    if scStatus in ['Stopped','Terminated']:
                        _DEB('%s scStatus %s for %s' % (self.id,scStatus,bat.id))
                        if max_waiting_time > 0.0:
                            all_ready = False
                        continue

                    if bat.execution_state not in ['running']:
                        run_error = '%s problems waiting for end %s phase for %s' % (self.id, phase, bat.id)
                        _ERR(run_error)
                        self.release(ExecutionRunError(run_error))

                    if bat.phase_status == 'not_needed':
                        continue
                    read_traffic_phase = self.read_traffic_phase(bat)
                    expected_phase_status = self.expected_phase_status(phase, bat)
                    #print 'read_traffic_phase %s   expected_phase_status  %s ' % (read_traffic_phase, expected_phase_status)
                    if read_traffic_phase != expected_phase_status:
                        all_ready = False
                        bat_to_refresh.append(bat)

                    elif self.running_phase == 'loadgen':
                        self.load_monitor.shutdown()

                self.__CPS_scheduler.refresh(bat_to_refresh)
                if max_waiting_time >= 0.0:
                    max_waiting_time -= time.time() - now

            except KeyboardInterrupt:
                if self.rtc_data.exit_test_case:
                    raise KeyboardInterrupt
                if phase == 'loadgen':
                    print '\n\n[Press Enter to execute postexec or Ctrl-C to stop traffic]'
                    try:
                        raw_input()
                        _INF('%s Stopping phase %s for BATs' % (self.id,phase))
                        self.stop_phase()
                        return
                    except KeyboardInterrupt:
                        raise KeyboardInterrupt

            if phase == 'loadgen' and self.__stop_phase_pending:
                _INF('%s Stopping phase %s for BATs' % (self.id,phase))
                self.stop_phase()
                return

        self.error_monitor.stop_monitoring()


    def is_traffic_running(self):
        all_ready = False
        while not all_ready:
            time.sleep(5.0)
            all_ready = True
            for bat in self.rtc_data.BAT_instances:
                if bat.execution_state in ['failed', 'stopped']:
                    return False
                if not bat.monitor_ready:
                    all_ready = False
        return True

    def telnet_control(self):

        _INF('%s Waitting for BATs' % self.id)
        if self.is_traffic_running():
            time.sleep(2.0)
            self.start_monitor_alarm()

            for tool in self.__external_tools:
                if tool.start_before == 'preexec':
                    _INF('%s Starting %s tool before "preexec"' %(self.id,tool.id))
                    tool.start_execution()


            _INF('%s Starting preexec' % self.id)
            self.start_phase('preexec')
            start = datetime.now()
            timestamp = start.strftime("%Y-%m-%dT%H:%M:%S")
            try:
                timestamp = self.__cabinet.datetime
            except Exception as e:
                _WRN('\tProblem reading datetime: %s' % e)

            self.rtc_data.add_to_macro('#TIME_TRAFFIC_START#',timestamp)
            _INF('%s Creating #TIME_TRAFFIC_START# with %s' %(self.id, timestamp))

            _INF('%s Starting scheduler' % self.id)
            self.__CPS_scheduler.start_execution()
            _INF('%s Wait until the end of preexec' % self.id)
            self.wait_phase_end('preexec')

            for tool in self.__external_tools:
                if tool.stop_after == 'preexec':
                    _INF('%s Stopping %s tool after "preexec"' %(self.id,tool.id))
                    tool.shutdown()

            time.sleep(5.0)

            for tool in self.__external_tools:
                if tool.start_before == 'loadgen':
                    _INF('%s Starting %s tool before "loadgen"' %(self.id,tool.id))
                    tool.start_execution()

            self.start_monitor_load()
            self.start_Diaproxy_report()
            self.start_Action_handler()

            _INF('%s Starting loadgen' % self.id)
            self.start_phase('loadgen')
            start = datetime.now()
            timestamp = start.strftime("%Y-%m-%dT%H:%M:%S")
            try:
                timestamp = self.__cabinet.datetime
            except Exception as e:
                _WRN('\tProblem reading datetime: %s' % e)

            self.rtc_data.add_to_macro('#TIME_TRAFFIC_LOAD_START#',timestamp)
            _INF('%s Creating #TIME_TRAFFIC_LOAD_START# with %s' %(self.id, timestamp))

            _INF('%s Wait until the end of loadgen' % self.id)
            self.wait_phase_end('loadgen')

            _INF('%s loadgen phase finished' % self.id)
            start = datetime.now()
            timestamp = start.strftime("%Y-%m-%dT%H:%M:%S")
            try:
                timestamp = self.__cabinet.datetime
            except Exception as e:
                _WRN('\tProblem reading datetime: %s' % e)

            self.rtc_data.add_to_macro('#TIME_TRAFFIC_LOAD_FINISHED#',timestamp)
            _INF('%s Creating #TIME_TRAFFIC_LOAD_FINISHED# with %s' %(self.id, timestamp))

            self.__Action_handler.shutdown()
            if self.__Action_handler.is_alive():
                self.__Action_handler.join(5.0)

            self.__Diaproxy_handler.shutdown()
            if self.__Diaproxy_handler.is_alive():
                self.__Diaproxy_handler.join(5.0)

            self.load_monitor.shutdown()
            if self.load_monitor.is_alive():
                self.load_monitor.join(5.0)

            self.alarm_monitor.shutdown()
            if self.alarm_monitor.is_alive():
                self.alarm_monitor.join(5.0)

            for tool in self.__external_tools:
                if tool.stop_after == 'loadgen':
                    _INF('%s Stopping %s tool after "loadgen"' %(self.id,tool.id))
                    tool.shutdown()

            if self.run_postexec:
                time.sleep(5.0)
                for tool in self.__external_tools:
                    if tool.start_before == 'postexec':
                        _INF('%s Starting %s tool before "postexec"' %(self.id,tool.id))
                        tool.start_execution()

                _INF('%s Starting postexec' % self.id)
                self.start_phase('postexec')
                _INF('%s Wait until the end of postexec' % self.id)

                self.wait_BAT_thread_end()
            else:
                _INF('%s Skipping postexec' % self.id)
                self.stop_BATs()

            if self.__CPS_scheduler:
                self.__CPS_scheduler.shutdown()

            for tool in self.__external_tools:
                if tool.stop_after == 'postexec':
                    _INF('%s Stopping %s tool after "postexec"' %(self.id,tool.id))
                    tool.shutdown()

        else:
            run_error = '%s Problem during BAT start' % self.id
            _ERR(run_error)
            self.release(BatError(run_error))

    def stop_BATs(self):
        if not self.execution_with_traffic:
            return

        for bat in self.rtc_data.BAT_instances:
            bat.stop()

        traffic_running = False
        while traffic_running:
            time.sleep(float(10))
            traffic_running = False
            for bat in self.rtc_data.BAT_instances:
                if bat.is_running:
                    traffic_running = True
                    break

        self.wait_BAT_thread_end(60.0)

    def wait_BAT_thread_end(self, timeout=None):

        for bat in self.rtc_data.BAT_instances:
            if bat.is_alive():
                _INF('%s Waitting for %s thread to finish' % (self.id, bat.id))
                bat.join(timeout)
                _INF('%s Thread %s has finished' % (self.id, bat.id))

        self.error_monitor.shutdown()

    def run(self):

        if self.config['enable']:
            _INF('')
            _INF('Start %s phase' % self.id )

            self.__Memory_monitor.start_monitoring()
            _DEB('Start memory monitoring for %s phase' % self.id )

            try:
                if self.execution_with_traffic:
                    _DEB('execution_with_traffic for %s phase' % self.id )
                    try:
                        for bat in self.rtc_data.BAT_instances:
                            bat.start()
                            time.sleep(float(self.time_between_bat_instances))
                            traffic_running = True

                        if self.config['configuration']['manual_control']:
                            while traffic_running:
                                time.sleep(float(10))
                                traffic_running = False
                                for bat in self.rtc_data.BAT_instances:
                                    if bat.execution_state == 'failed':
                                        for bat in self.rtc_data.BAT_instances:
                                            bat.stop()
                                        traffic_running = False
                                        break

                                    if bat.is_running:
                                        traffic_running = True

                            self.wait_BAT_thread_end(20.0)

                        else:
                            self.telnet_control()

                    except KeyboardInterrupt:
                        _INF('%s Traffic stopped by user!' % self.id)
                        if not self.config['configuration']['manual_control']:
                            self.__Action_handler.shutdown()
                            if self.__Action_handler.is_alive():
                                self.__Action_handler.join(5.0)

                            self.__Diaproxy_handler.shutdown()
                            if self.__Diaproxy_handler.is_alive():
                                self.__Diaproxy_handler.join(5.0)

                            self.load_monitor.shutdown()
                            if self.load_monitor.is_alive():
                                self.load_monitor.join(5.0)

                            self.alarm_monitor.shutdown()
                            if self.alarm_monitor.is_alive():
                                self.alarm_monitor.join(5.0)

                            if self.__CPS_scheduler:
                                self.__CPS_scheduler.shutdown()
                                if self.alarm_monitor.is_alive():
                                    self.alarm_monitor.join(5.0)

                            for tool in self.__external_tools:
                                _INF('%s Stopping %s tool after "postexec"' %(self.id,tool.id))
                                tool.shutdown()

                        self.stop_BATs()

                    if self.rtc_data.exit_test_case:
                        _WRN('%s Exit from Test case order has been received' % self.id)
                        self.__Memory_monitor.shutdown()
                        if self.__Memory_monitor.is_alive():
                            _INF('%s Waiting for for Memory monitor shutdown 5 seconds.' % self.id)
                            self.__Memory_monitor.join(5.0)
                        raise KeyboardInterrupt

                    if self.wait_pmf_counters and not self.rtc_data.exit_test_case:
                        try:
                            _INF('%s Waiting for pmf counters 300 seconds. Press ctrl-c to stop' % self.id)
                            time.sleep(float(300))

                        except KeyboardInterrupt:
                            _INF('%s Wait stopped by user!' % self.id)

                elif self.__Action_handler.id == 'FakeActionHandler':
                    _DEB('execution FakeActionHandler NO traffic for %s phase' % self.id )
                    try:
                        _INF('%s Waiting for user. Press ctrl-c to continue' % self.id)
                        signal.pause()

                    except KeyboardInterrupt:
                        _INF('%s Wait stopped by user!' % self.id)

                else:
                    _DEB('execution with NO traffic for %s phase' % self.id )
                    self.start_monitor_alarm()
                    self.start_Action_handler()
                    self.wait_for_action_handler = True
                    try:
                        while self.wait_for_action_handler:
                            time.sleep(float(1))

                        if self.__Action_handler.is_alive():
                            self.__Action_handler.join(5.0)

                        self.alarm_monitor.shutdown()
                        if self.alarm_monitor.is_alive():
                            self.alarm_monitor.join(5.0)
                    except KeyboardInterrupt:
                        _INF('%s Wait for Action Handler stopped by user!' % self.id)
                        self.__Action_handler.shutdown()
                        if self.__Action_handler.is_alive():
                            self.__Action_handler.join(5.0)

                        self.alarm_monitor.shutdown()
                        if self.alarm_monitor.is_alive():
                            self.alarm_monitor.join(5.0)

                    if self.rtc_data.exit_test_case:
                        _WRN('%s Exit from Test case order has been received' % self.id)
                        self.__Memory_monitor.shutdown()
                        if self.__Memory_monitor.is_alive():
                            _INF('%s Waiting for for Memory monitor shutdown 5 seconds.' % self.id)
                            self.__Memory_monitor.join(5.0)
                        raise KeyboardInterrupt

                self.__Memory_monitor.shutdown()
                if self.__Memory_monitor.is_alive():
                    _INF('%s Waiting for for Memory monitor shutdown 5 seconds.' % self.id)
                    self.__Memory_monitor.join(5.0)

            except ExecutionRunError, e:
                _ERR('EXECUTION %s' % str(e))
                self.release(e)

