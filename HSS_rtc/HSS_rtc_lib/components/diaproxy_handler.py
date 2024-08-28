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
from . import ExecutionStartError
from . import ExecutionRunError


class DiaproxyHandler(threading.Thread):
    def __init__(self, executor, config, phase_path):
        threading.Thread.__init__(self)

        self.__id = 'DIAPROXY_HANDLER'
        self.__running = False
        self.executor = executor
        self.__latency = {}
        self.__result_codes = {}
        self.__diaproxys = []
        self.__force_exit = False

        if not self.executor.execution_with_traffic:
            configuration_error = '%s not allowed in a scenario without traffic' % self.__id
            raise ExecutionConfigurationError(configuration_error)

        for key in config['diaproxy_reports'].keys():
            try:
                if key == 'latency' and config['diaproxy_reports'][key]['enable']:
                    if self.executor.load_monitor.id == 'FakeMonitor' and config['diaproxy_reports'][key]['only_when_load_stable']:
                        configuration_error = 'Monitor load is mandatory when using DiaProxy latency reports and load stable is required'
                        raise ExecutionConfigurationError(configuration_error)

                    self.__latency = config['diaproxy_reports'][key]
                    pending_samples = config['diaproxy_reports'][key]['samples']
                    self.__latency.update({'last_action_time':0, 'time_for_next_action':30,'next_action':'start',
                                                'sample_index':-1,'pending_samples':pending_samples})

                    if not isinstance(self.__latency['target_load'],int):
                        load = self.executor.rtc_data.get_load_monitor_target_from_reference(self.__latency['target_load'])
                        if load == -1 and self.__latency['only_when_load_stable']:
                            configuration_error = 'Diaproxy reports latency target load for %s not found' % self.__latency['target_load']
                            raise ExecutionConfigurationError(configuration_error)

                        self.__latency['target_load'] = load
                        _INF('%s Diaproxy reports latency target load %s' % (self.id, load))
            except KeyError, e:
                continue

            try:
                if key == 'result_codes' and config['diaproxy_reports'][key]['enable']:
                    self.__result_codes = config['diaproxy_reports'][key]
                    self.__result_codes.update({'running':False})
            except KeyError, e:
                continue


        self.__logfilename = os.path.join(phase_path, '%s.log' % self.__id.lower())
        self.__logfile = open(self.__logfilename, "w")

    @property
    def force_exit(self):
        return self.__force_exit

    def activate_force_exit(self):
        self.__force_exit = True

    @property
    def id(self):
        return self.__id 

    @property
    def target_load(self):
        return self.__latency['target_load'] 

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

    def check_dependencies(self):
        pass

    def read_tps_counters(self):
        cmd = 'get_and_reset_result_code_counter'
        tps_counters = {}
        for diaproxy in self.__diaproxys:
            self.log_event('info', '%s sending udp cmd: "%s" to %s' % (self.id, cmd, diaproxy), True)
            answer = st_command.send_udp_command(cmd, diaproxy.split(':')[0], int(diaproxy.split(':')[1]), timeout=4.0)
            if answer is None:
                self.log_event('warning', '%s no answer from %s' % (self.id, diaproxy), True)
                return {}
            self.log_event('', '%s answer: %s' % (self.id, answer), True)
            for counter in answer.split():
                key = counter.split('=')[0]
                value = counter.split('=')[1]
                try:
                    tps_counters[key] += int(value)
                except KeyError:
                    tps_counters.update({key:int(value)})

        return tps_counters

    def check_connections_up(self):
        cmd = 'check_connections_up'
        for diaproxy in self.__diaproxys:
            self.log_event('info', '%s sending udp cmd: "%s" to %s' % (self.id, cmd, diaproxy), True)
            answer = st_command.send_udp_command(cmd, diaproxy.split(':')[0], int(diaproxy.split(':')[1]), timeout=4.0)
            if answer is None:
                return False
            self.log_event('info', '%s answer: %s' % (self.id, answer), True)
            if 'SUCCESS' not in answer:
                return False

        return True

    @property
    def online(self):
        return self.__running

    def stop_result_codes_report(self):
        if self.__result_codes['running']:
            self.send_report_cmd('result_codes','stop')
            cmd = 'stop_report result_codes'
            self.__result_codes['running'] = False

    def send_report_cmd(self, report, order):
        cmd = '%s_report %s' % (order, report)
        for diaproxy in self.__diaproxys:
            self.log_event('info', '%s sending udp cmd: "%s" to %s' % (self.id, cmd, diaproxy), True)
            answer = st_command.send_udp_command(cmd, diaproxy.split(':')[0], int(diaproxy.split(':')[1]), timeout=4.0)
            self.log_event('', '%s answer: %s' % (self.id, answer), True)

    def shutdown(self):
        if self.__running:
            self.log_event('info', '%s shutdown received' % self.__id, True)
            if self.__result_codes:
                self.stop_result_codes_report()

            if self.__latency:
                if self.__latency['next_action'] == 'stop':
                    self.send_report_cmd('latency', 'stop')
                    self.log_event('info', '%s Sample %s is faulty' % (self.id, self.__latency['sample_index']), True)
                    self.executor.rtc_data.add_faulty_latency_report(self.__latency['sample_index'])

        self.__running = False
        if self.logfile is not None:
            self.logfile.close()
            self.__logfile = None

    def configure(self, diaproxys=[]):
        self.__diaproxys = diaproxys
        for diaproxy in self.__diaproxys:
            if self.__latency:
                cmd = 'enable_report latency latency'
                self.log_event('info', '%s sending udp cmd: "%s" to %s' % (self.id, cmd, diaproxy), True)
                answer = st_command.send_udp_command(cmd, diaproxy.split(':')[0], int(diaproxy.split(':')[1]), timeout=4.0)
                self.log_event('', '%s answer: %s' % (self.id, answer), True)
            if self.__result_codes:
                cmd = 'enable_report result_codes result_codes'
                self.log_event('info', '%s sending udp cmd: "%s" to %s' % (self.id, cmd, diaproxy), True)
                answer = st_command.send_udp_command(cmd, diaproxy.split(':')[0], int(diaproxy.split(':')[1]), timeout=4.0)
                self.log_event('', '%s answer: %s' % (self.id, answer), True)


    def start_handling(self):
        if not self.__result_codes and not self.__latency:
            self.log_event('info', '%s Not configured.' % self.id, True)
            return
        if not self.__diaproxys:
            self.log_event('error', '%s DiaProxys not found.' % self.id, True)
            return

        self.start()

    @property
    def is_load_stable(self):
        if self.__latency['only_when_load_stable']:
            return  (self.executor.load_monitor.load_status == 'STABLE' and self.executor.load_monitor.target_load == int(self.__latency['target_load']))

        return True

    @property
    def is_load_not_stable(self):
        if self.__latency['only_when_load_stable']:
            return  (self.executor.load_monitor.load_status == 'NOT STABLE')

        return False

    def run(self):

        self.log_event('info', '%s start thread execution' % self.id, True)
        self.__running = True
        if self.__result_codes:
            self.send_report_cmd('result_codes', 'start')
            self.__result_codes['running'] = True

        if self.__latency:
            self.__latency['last_action_time'] = time.time()
            if self.__latency['only_when_load_stable']:
                self.executor.rtc_data.update_epm({'target_load':float(self.target_load)/100})
            else:
                self.executor.rtc_data.update_epm({'target_load':float(-1)})

            wait_time = float(self.__latency.get('wait_before_start', 0))
            if wait_time > 0:
                self.log_event('info', '%s Waiting %s seconds before start' % (self.id, wait_time), True)
                time.sleep(wait_time) 

            while (self.online):
                if self.force_exit:
                    return
                time.sleep(1.0)

                if self.__latency['pending_samples'] > 0:
                    self.__latency['time_for_next_action'] -= time.time() - self.__latency['last_action_time']
                    if self.is_load_stable:
                        if self.__latency['time_for_next_action'] < 0:
                            if self.__latency['next_action'] == 'start':
                                self.__latency['sample_index'] += 1
                            self.send_report_cmd('latency', self.__latency['next_action'])

                            self.__latency['last_action_time'] = time.time()
                            if self.__latency['next_action'] == 'start':
                                self.__latency['time_for_next_action'] = self.__latency['time']
                                self.__latency['next_action'] = 'stop'
                            elif self.__latency['next_action'] == 'stop':
                                self.__latency['pending_samples'] -= 1
                                self.__latency['time_for_next_action'] = self.__latency['wait']
                                self.__latency['next_action'] = 'start'
                        else:
                            self.__latency['last_action_time'] = time.time()

                    elif self.is_load_not_stable and self.__latency['next_action'] == 'stop':
                        self.send_report_cmd('latency', 'stop')

                        self.log_event('info', '%s Sample %s is faulty' % (self.id, self.__latency['sample_index']), True)
                        self.executor.rtc_data.add_faulty_latency_report(self.__latency['sample_index'])
                        self.__latency['last_action_time'] = time.time()
                        self.__latency['time_for_next_action'] = self.__latency['wait']
                        self.__latency['next_action'] = 'start'

                elif self.__latency['stop_loadgen_when_finish']:
                    self.executor.request_stop_phase()
