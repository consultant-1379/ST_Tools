#!/usr/bin/env python
#

import time
import sys
import traceback
import pexpect
import re
import threading
import Queue
import getpass
import socket
from datetime import datetime
import pprint
import copy
import numpy as np
from collections import deque

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

class FakeComponent(object):
    def __init__(self, id = 'FakeMonitor'):
        self.__id = id

    @property
    def id(self):
        return self.__id

    @property
    def user_config(self):
        return None

    @property
    def force_exit(self):
        return True

    def activate_force_exit(self):
        pass

    @property
    def host(self):
        return None

    @property
    def phase_path(self):
        return None

    @property
    def online(self):
        return False

    def start_monitoring(self,phase=None):
        pass

    def stop_monitoring(self):
        pass

    def shutdown(self):
        pass

    def is_alive(self):
        return False

    def join(self, time):
        pass


class Monitor(threading.Thread):
    def __init__(self, id, config, user_config, phase_path):
        threading.Thread.__init__(self)

        self.__user_config = user_config
        self.__host = user_config.NODE
        self.__phase_path = phase_path
        self.__id = id
        self.__running = False
        self.__userid = getpass.getuser()
        self.__hostname = socket.gethostname()
        self.__connection = None
        self.__force_exit = False


    @property
    def user_config(self):
        return self.__user_config

    @property
    def force_exit(self):
        return self.__force_exit

    def activate_force_exit(self):
        self.__force_exit = True

    @property
    def host(self):
        return self.__host

    @property
    def phase_path(self):
        return self.__phase_path

    @property
    def id(self):
        return self.__id 

    @property
    def online(self):
        return self.__running


    def start_monitoring(self):
        if not self.online and self.monitor_data['enable']:
            config = {'host':self.__hostname, 'user' : self.__userid}
            try:
                self.__connection = hss_utils.node.gentraf.GenTraf(config, allow_x11_forwarding = True)
                self.__connection.working_dir = '%s' % os.getcwd()
                cmd = self.cmd
                _INF('%s executing %s' % (self.__id, cmd))
                self.__connection.run_command_async(cmd, answer={'Starting Monitoring': ''}, timeout = 10.0)
                _INF('%s started' % self.__id)
                self.__running = True

            except KeyboardInterrupt:
                _WRN('%s Cancelled by user' % self.__id)

            except Exception, e:
                _ERR('%s Cannot start MONITOR: %s' % (self.__id,str(e)))
            self.start()

    def shutdown(self):
        if self.__running:
            _INF('%s shutdown received' % self.__id)
            if self.__connection is None:
                self.__running = False
                return
            if self.online:
                self.__connection.stop_command_async()
            self.__connection.release()
        self.__running = False


    def run(self):
        #self.start_monitoring()
        while self.online:
            if self.force_exit:
                return
            time.sleep(float(3.0))
        _INF('%s end of thread execution' % self.id)


class Memory_Monitor(Monitor):
    def __init__(self, executor, config, user_config, phase_path):
        Monitor.__init__(self, 'MEMORY_MONITOR', config, user_config, phase_path)

        self.monitor_data = config['configuration']['monitor_memory']
        self.executor = executor

    @property
    def cmd(self):
        cmd = 'CBA_memory_monitor --node %s --user %s -k --set-working-path %s --log-path %s' % (self.host,
                                                                                                 self.user_config.user,
                                                                                                 self.phase_path,
                                                                                                 self.phase_path)

        cpu_load_enabled = self.monitor_data.get('cpu_load_enabled',False)
        if isinstance(cpu_load_enabled,str) or isinstance(cpu_load_enabled,unicode):
            cpu_load_enabled = self.executor.rtc_data.get_macro_value(cpu_load_enabled)
            cpu_load_enabled = (cpu_load_enabled == 'true')

        if cpu_load_enabled:
            cmd += ' --cpu-load'

        try:
            sampling_time = self.monitor_data['sampling_time']
            cmd += ' -t %s' % sampling_time
        except KeyError:
            pass

        try:
            refresh_time = self.monitor_data['refresh_time']
            cmd += ' -r %s' % refresh_time
        except KeyError:
            pass

        try:
            processors = self.monitor_data['processors']
            if processors != '':
                cmd += ' -p %s' % processors
        except KeyError:
            pass

        try:
            real_time_enabled = self.monitor_data['real_time_enabled']
            if not real_time_enabled or self.user_config.disable_graph:
                cmd += ' -s'
        except KeyError:
            cmd += ' -s' if self.user_config.disable_graph else ''

        return cmd



class LoadMonitor(threading.Thread):
    def __init__(self, executor, config, phase_path):
        threading.Thread.__init__(self)

        self.__id = 'LOAD_MONITOR'
        self.executor = executor
        if not self.executor.execution_with_traffic:
            configuration_error = '%s not allowed in a scenario without traffic' % self.__id
            raise ExecutionConfigurationError(configuration_error)

        self.__running = False
        self.__hostname = None
        self.__port = None
        self.__ready = False
        self.__target_load_reached = False
        self.__last_not_stable_time = 0
        self.__current_load = 0
        self.__reading_error = 0
        self.__max_reading_error = 3
        self.__enable_monitoring = True
        self.__default_sampling_time = 3
        self.__default_transition = 10
        self.__slot = {}
        self.__slots = []
        self.__load_db = []
        self.__mutex = st_command.QLock()
        self.__load_samples = None
        self.__allow_usage = False
        self.__logfilename = os.path.join(phase_path, '%s.log' % self.id.lower())
        self.__logfile = open(self.__logfilename, "w")
        self.__force_exit = False

        try:
            if config['monitor_load']['enable']:
                if not isinstance(config['monitor_load']['slots'],list):
                    reference = config['monitor_load']['slots']
                    slots = self.executor.rtc_data.get_load_monitor_slots_from_reference(reference)
                    if not slots:
                        configuration_error = 'Monitor load slots for %s not found' % reference
                        raise ExecutionConfigurationError(configuration_error)

                    config['monitor_load']['slots'] = slots
                    _INF('%s Using traffic reference %s' % (self.id, reference))

                self.__slots = config['monitor_load']['slots']
                self.__allow_usage = True
                self.executor.rtc_data.scenario_load_monitor = self

        except KeyError:
            pass


    @property
    def force_exit(self):
        return self.__force_exit

    def activate_force_exit(self):
        self.__force_exit = True


    @property
    def logfile(self):
        return self.__logfile

    @property
    def id(self):
        return self.__id 

    @property
    def slot(self):
        return self.__slot

    @property
    def slots(self):
        return self.__slots

    @property
    def allow_usage(self):
        return self.__allow_usage

    @property
    def load(self):
        return self.__current_load

    @property
    def load_status(self):
        if not self.ready:
            run_error = '%s Not ready. One loadplotter must be UP&RUNNING' % self.id
            self.log_event('',run_error, True)
            raise ExecutionRunError(run_error)
        try:
            return self.__load_db[-1]['state']
        except Exception:
            return 'UNDEFINED'

    @property
    def online(self):
        return self.__running

    @property
    def hostname(self):
        return self.__hostname

    @property
    def port(self):
        return self.__port

    @property
    def ready(self):
        return self.__ready

    @property
    def min_load(self):
        return self.target_load - self.tolerance

    @property
    def max_load(self):
        return self.target_load + self.tolerance

    @property
    def tolerance(self):
        return 5

    @property
    def variance(self):
        return int(self.slot['variance'])

    @property
    def target_load(self):
        if self.__slot:
            return int(self.slot['target_load'])

        return 0

    @property
    def sampling_time(self):
        try:
            return self.slot['sampling_time']
        except KeyError:
            return self.__default_sampling_time

    @property
    def transition(self):
        try:
            return self.slot['transition']
        except KeyError:
            return self.__default_transition

    @property
    def is_enabled(self):
        return self.__enable_monitoring

    def enable(self):
        self.log_event('info', '%s enable monitoring' % self.__id, True)
        self.__enable_monitoring = True

    def disable(self):
        self.log_event('info', '%s disable monitoring' % self.__id, True)
        self.__enable_monitoring = False

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

    def shutdown(self):
        if self.__running:
            self.log_event('info','%s shutdown received' % self.__id , True)
            now = time.time()
            if now - self.__last_not_stable_time < float(int(self.transition)):
                self.log_event('info', '%s Removing last not stable status due to end of loadgen phase.' % (self.id), True)
                self.__load_db[-1]['check'] = False

        self.__enable_monitoring = False
        self.__running = False
        self.log_final_report()
        if self.logfile is not None:
            self.logfile.close()
            self.__logfile = None

    def start_monitoring(self):
        if not self.allow_usage:
            self.log_event('info', '%s Usage not allowed. Not configured.' % self.id, True)
        elif not self.ready:
            run_error = '%s Not ready. One loadplotter must be UP&RUNNING' % self.id
            self.log_event('',run_error, True)
            raise ExecutionRunError(run_error)
        else:
            self.start()

    def send_command(self, cmd):
        #self.log_event('info', '%s sending udp cmd: "%s" to %s:%s' % (self.id, cmd, self.hostname, self.port), True)
        answer = st_command.send_udp_command(cmd, self.hostname, self.port, timeout=10.0)
        #self.log_event('info', '%s answer: %s' % (self.id, answer), True)
        return answer

    def configure(self, loadplotter=None):
        if loadplotter:
            self.__hostname = loadplotter.split(':')[0]
            self.__port = int(loadplotter.split(':')[1])
            answer = self.send_command('getstatus')
            if answer != 'READY':
                self.log_event('error', '%s is not ready.' % self.id, True)
                return
            self.__ready = True

    @property
    def load_in_range(self):
        return self.__current_load >= self.min_load and self.__current_load <= self.max_load

    @property
    def load_stable(self):
        return np.var(self.__load_samples) <= self.variance

    @property
    def load_media(self):
        total = 0
        for sample in self.__load_samples:
            total += int(sample)
        if self.__load_samples:
            return total / len(self.__load_samples)

    def check_load_stability(self):
        self.__mutex.acquire()
        if self.__target_load_reached:
            self.__load_samples.append(self.__current_load)
            self.__current_load = self.load_media

            timestamp = '%s' % datetime.now()

            if self.load_in_range and self.load_stable:
                if self.load_status != 'STABLE':
                    self.__load_db.append({'state':'STABLE','check':self.is_enabled,'reason':'','timestamp':timestamp[:-7]})
                    self.log_event('info', '%s load %s STABLE in range %s-%s.' % (self.id, self.__current_load, self.min_load, self.max_load ), True)

            else:
                if self.load_status != 'NOT STABLE':
                    self.__last_not_stable_time = time.time()
                    info_type = 'error' if self.is_enabled else 'warning'
                    if self.load_stable:
                        self.__load_db.append({'state':'NOT STABLE','check':self.is_enabled,
                                               'reason':'load %s out of range %s-%s.' % (self.__current_load, self.min_load, self.max_load),
                                               'timestamp':timestamp[:-7]})
                        self.log_event(info_type, '%s load %s out of range %s-%s.' % (self.id, self.__current_load, self.min_load, self.max_load ), True)
                    else:
                        self.__load_db.append({'state':'NOT STABLE','check':self.is_enabled,
                                               'reason':'variance %s higher than %s' % (np.var(self.__load_samples), self.variance),
                                               'timestamp':timestamp[:-7]})
                        self.log_event(info_type, '%s variance %s higher than %s' % (self.id, np.var(self.__load_samples), self.variance), True)


        elif self.load_in_range:
            self.__target_load_reached = True

        self.__mutex.release()

    def failed_registers(self):
        registers = []
        for register in self.__load_db:
            if register['state'] == 'NOT STABLE' and register['check']:
                info = '%s  NOT STABLE: %s' % (register['timestamp'],register['reason'])
                registers.append(info)

        return registers

    def log_final_report(self):
        info = ''
        for register in self.__load_db:
            info += '\n\t%s  State: %s' % (register['timestamp'],register['state'])
            if register['state'] == 'NOT STABLE':
                info += '  Reason: %-*s %s' % (30, register['reason'],('' if register['check'] else 'Discarded'))

        if info:
            self.log_event('', '%s Final Report:\n%s' % (self.id, info), True)

    def reconfigure(self, slots):
        self.__mutex.acquire()
        self.__slots = copy.deepcopy(slots)
        self.__slot = {}
        self.log_event('info', '%s Reconfigured' % self.id, True)
        pprint.pprint(self.__slots)
        self.__mutex.release()

    def set_new_slot(self, now):
        try:
            self.__slot = self.__slots.pop(0)
            self.__load_samples = deque(15*[self.target_load], 15)
            self.__target_load_reached = False
            self.__slot.update({'pending_time':self.__slot['time'],'last_check':now})
            self.log_event('info', '%s new load slot with range %s-%s.' % (self.id, self.min_load, self.max_load ), True)
            timestamp = '%s' % datetime.now()
            self.__load_db.append({'state':'NEW SLOT','check':self.is_enabled,'reason':'','timestamp':timestamp[:-7]})
        except IndexError:
            self.shutdown()

    def update_slot(self):
        self.__mutex.acquire()
        now = time.time()
        if self.slot:
            if self.slot['time'] == -1:
                self.slot['time'] = -2
                self.log_event('info', '%s Keep load slot with range %s-%s until the end of loadgen.' % (self.id, self.min_load, self.max_load ), True)

            elif self.slot['time'] != -2:
                if self.slot['last_check']:
                    self.slot['pending_time'] -= now - self.slot['last_check']
                    if self.slot['pending_time'] < float(int(self.transition)):
                        self.__target_load_reached = False

                    if self.slot['pending_time'] < 0:
                        self.set_new_slot(now)
        else:
            self.set_new_slot(now)

        self.slot['last_check'] = now
        self.__mutex.release()

    def run(self):

        self.log_event('info', '%s start thread execution' % self.id, True)
        self.__running = True
        self.update_slot()

        while self.online:
            if self.force_exit:
                return
            time.sleep(float(self.sampling_time))
            value = self.send_command('getload 0')
            if value is None:
                self.log_event('warning', 'Timeout reading load from loadplotter', True)
                self.__reading_error += 1
                if self.__reading_error > self.__max_reading_error:
                    self.log_event('error', '%s Too many readings errors' % self.id, True)
                    self.shutdown()
                self.log_event('warning', '%s readings errors %s' % (self.id, self.__reading_error), True)
                continue

            try:
                self.__current_load = int(value.split('.')[0])
                self.update_slot()
                self.check_load_stability()
            except Exception, e:
                self.log_event('', 'Exception %s' % (str(e)), True)
                self.__reading_error += 1
                if self.__reading_error > self.__max_reading_error:
                    self.log_event('error', '%s Too many readings errors' % self.id, True)
                    self.shutdown()
                self.log_event('warning', '%s readings errors %s' % (self.id, self.__reading_error), True)

        self.log_event('info', '%s end of thread execution' % self.id, True)

class ErrorMonitor(threading.Thread):
    def __init__(self, executor, config, phase_path):
        threading.Thread.__init__(self)

        self.__id = 'ERROR_MONITOR'
        self.__config = config
        self.executor = executor
        if not self.executor.execution_with_traffic:
            configuration_error = '%s not allowed in a scenario without traffic' % self.__id
            raise ExecutionConfigurationError(configuration_error)

        self.__running = False
        self.__monitoring = False
        self.__enable = {}
        self.__phase = 'preexec'
        self.__error_rate = 0.1
        self.__error_db = []
        self.__logfilename = os.path.join(phase_path, '%s.log' % self.id.lower())
        self.__logfile = open(self.__logfilename, "w")
        self.__force_exit = False

        try:
            if config['monitor_error']['enable']:
                self.__enable = config['monitor_error']['enable']
                self.__running = True
                self.executor.rtc_data.scenario_error_rate_monitor = self
        except KeyError, e:
            pass


    @property
    def force_exit(self):
        return self.__force_exit

    def activate_force_exit(self):
        self.__force_exit = True

    @property
    def logfile(self):
        return self.__logfile

    @property
    def id(self):
        return self.__id 

    @property
    def phase(self):
        return self.__phase

    @property
    def running(self):
        return self.__running

    @property
    def monitoring(self):
        return self.__monitoring

    @property
    def enabled(self):
        try:
            return self.__enable[self.phase]
        except KeyError, e:
            return False

    @property
    def default_error_rate(self):
        try:
            return self.__config['monitor_error']['default_error_rate']
        except KeyError, e:
            return 0.1

    @property
    def error_rate(self):
        return self.__error_rate

    @error_rate.setter
    def error_rate(self, error_rate=None):
        if error_rate is None:
            self.__error_rate = self.default_error_rate
        else:
            self.__error_rate = error_rate

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

    def shutdown(self):
        if self.running:
            self.log_event('info','%s shutdown received' % self.__id , True)

            if self.monitoring:
                self.stop_monitoring()

            self.log_final_report()

            self.log_event('info', '%s shutdown proccessed' % self.id, True)

        self.__running = False
        if self.logfile is not None:
            self.logfile.close()
            self.__logfile = None

    def start_monitoring(self, phase, error_rate=None):
        if not self.running:
            self.log_event('info', '%s Usage not allowed. Not configured.' % self.id, True)
        else:
            self.__phase = phase
            if self.enabled:
                self.error_rate = error_rate
                self.error_db_open_register()
                self.log_event('info', '%s Open new error register in %s phase ' % (self.id, phase), True)
                for bat_instance in self.executor.rtc_data.BAT_instances:
                    bat_instance.error_db_open_register(phase=phase)
                self.__monitoring = True


    def stop_monitoring(self):
        error_rate = -1
        if not self.running:
            self.log_event('info', '%s Usage not allowed. Not configured.' % self.id, True)
        else:
            if self.monitoring:
                for bat_instance in self.executor.rtc_data.BAT_instances:
                    bat_instance.error_db_close_register()

                self.error_db_close_register()
                self.log_report()
                self.log_event('info', '%s Close error register in %s phase with Scenario error rate: %.2f' % (self.id, self.phase, self.last_error_rate), True)
                error_rate = self.last_error_rate
            self.__monitoring = False

        return error_rate

    def tps_error_rate(self):
        data = self.executor.diaproxy_handler.read_tps_counters()
        self.log_event('info', '%s TPS data: %s' % (self.id, data), True)
        executed = 0
        failed = 0
        for counter, value in data.iteritems():
            if counter == 'request':
                continue
            elif counter in ['success','other']:
                executed += value
            else:
                executed += value
                failed += value

        if executed:
            _DEB('%s TPS executed: %d' % (self.id, executed))
            return float (failed * 100) / float(executed)

        _DEB('%s NO TPS executed: %d' % (self.id, executed))
        return float(executed)

    @property
    def last_error_rate(self):
        try:
            return self.__error_db[-1]['error_rate']
        except (KeyError, IndexError):
            return -1

    def log_report(self, index=-1):
        for bat_instance in self.executor.rtc_data.BAT_instances:
            register = bat_instance.error_db_read_register(register=index)
            if register is None:
                _WRN('%s No error data available for %s' % (self.id, bat_instance.id))
                continue
            info = '%s error rate from %s to %s '% (bat_instance.id, register['start'],register['stop'])
            if register['executed'] > 0:
                rate = (float(register['errors']) *100) / float(register['executed'])
            else:
                rate = 0
            info += '\n\tExecuted    :%s\n\tErrors      :%s\n\tError Rate  :%.2f' % (register['executed'],
                                                                                    register['errors'],
                                                                                    rate)

            self.log_event('', '%s %s' % (self.id, info), True)

    def log_final_report(self, index=-1):
        info = ''
        for register in self.__error_db:
            info += '\n\tStarted: %s  Stopped: %s  Phase: %s' % (register['start'],register['stop'],register['phase'])
            info += '\tError rate: %.2f  Max Error rate: %.2f  %s' % (register['error_rate'],
                                                                      register['max_error_rate'],
                                                                      ('' if register['check'] else 'Discarded') )


        self.log_event('', '%s Final Report:\n%s' % (self.id, info), True)

    def failed_registers(self):
        registers = []
        for register in self.__error_db:
            if register['error_rate'] > register['max_error_rate'] and register['check']:
                info = 'Started: %s  Stopped: %s  Phase: %s' % (register['start'],
                                                                register['stop'],
                                                                register['phase'])

                info += '\tError rate: %.2f  Max Error rate: %.2f' % (register['error_rate'],
                                                                      register['max_error_rate'] )

                registers.append(info)

        return registers

    def error_db_open_register(self):
        timestamp = '%s' % datetime.now()
        self.__error_db.append({'start':timestamp[:-7],'phase':self.__phase,'stop':'',
                                'executed':0,'errors':0,'error_rate':-1,
                                'max_error_rate':self.error_rate,
                                'check':True})


    def error_db_close_register(self):
        if self.__error_db:
            timestamp = '%s' % datetime.now()
            self.__error_db[-1]['stop'] = timestamp[:-7]
            for bat_instance in self.executor.rtc_data.BAT_instances:
                executed, errors = bat_instance.error_db_read_register_counters()
                self.__error_db[-1]['executed'] += executed
                self.__error_db[-1]['errors'] += errors

            if self.__error_db[-1]['executed']:
                self.__error_db[-1]['error_rate'] = (float(self.__error_db[-1]['errors']) *100) / float(self.__error_db[-1]['executed'])
            else:
                self.log_event('warning', '%s Last counter for executed traffic cases is 0\n' % (self.id), True)
                self.__error_db[-1]['error_rate'] = 0.0


    def skip_check_last_register(self):
        if self.__error_db:
            self.__error_db[-1]['check'] = False


class AlarmMonitor(hss_utils.node.cba.AlarmMonitorBaseCBA):
    def __init__(self, config, user_config, phase_path):

	access_config = {'host':user_config.NODE,
                          'port':user_config.port,
                          'user':user_config.user}

	hss_utils.node.cba.AlarmMonitorBaseCBA.__init__(self, access_config)
	self.__user_config = user_config
	self.__access_config = access_config
        self.__host = user_config.NODE
        self.__phase_path = phase_path
        self.__display = False
        self.__allow_usage = False
        self.__logfile = None
        self.__logfilename = os.path.join(phase_path, '%s.log' % self.id.lower())
        try:
            if config['monitor_alarm']['enable']:
                self.sampling_time = config['monitor_alarm']['sampling_time']
                self.__display = config['monitor_alarm']['display']
                self.__allow_usage = True
        except KeyError, e:
            _DEB(str(e))
            pass

    @property
    def logfile(self):
        return self.__logfile

    @property
    def allow_usage(self):
        return self.__allow_usage

    @property
    def phase_path(self):
        return self.__phase_path

    def start_monitoring(self):
        if not self.allow_usage:
            _INF('%s Usage not allowed. Not configured.' % self.id)
            return

        if not self.online:
            try:
                self.connection = hss_utils.node.cba.Cba(config = self.__access_config)
                _INF('%s started' % self.id)
                self.running = True

            except KeyboardInterrupt:
                _WRN('%s Cancelled by user' % self.id)

            except Exception, e:
                _ERR('%s Cannot start: %s' % (self.id,str(e)))

        if self.logfile is None:
            self.__logfile = open(self.__logfilename, "w")

        self.start()

    def shutdown(self):
        _INF('%s shutdown received' % self.id )
        if self.connection is None:
            self.running = False
            return
        try:
            self.running = False
            time.sleep(float(self.sampling_time) + 1)
        except KeyboardInterrupt:
            _WRN('%s Cancelled by user' % self.id)
        self.connection.release()
        self.connection = None
        if self.logfile is not None:
            self.logfile.close()


    def log_event(self, event_info):
        timestamp = '%s: ' % datetime.now()
        info = '%s%s' % (timestamp, event_info)
        self.logfile.write('%s\n' % info)

        if self.__display:
            print '%s' % info


class ExternalTool(threading.Thread):
    def __init__(self, executor, config, phase_path):
        threading.Thread.__init__(self)

        self.is_running=False
        self.__config = config
        self.executor = executor
        if not self.executor.execution_with_traffic:
            configuration_error = '%s not allowed in a scenario without traffic' % self.id
            raise ExecutionConfigurationError(configuration_error)

        self.__phase_path = phase_path
        self.__force_exit = False
        if self.start_before not in ['preexec','loadgen','postexec']:
            configuration_error = '%s Wrong start_before. Allowed values are : preexec | loadgen | postexec' % self.id
            raise ExecutionConfigurationError(configuration_error)

        if self.stop_after not in ['preexec','loadgen','postexec']:
            configuration_error = '%s Wrong stop_after. Allowed values are : preexec | loadgen | postexec' % self.id
            raise ExecutionConfigurationError(configuration_error)


    @property
    def config(self):
        return self.__config

    @property
    def phase_path(self):
        return self.__phase_path

    @property
    def id(self):
        return self.config.get('id','unknown_tool') 

    @property
    def cmd(self):
        return self.executor.rtc_data.macro_translator(self.config.get('cmd',''))

    @property
    def stop_after(self):
        return self.config.get('stop_after',None) 

    @property
    def start_before(self):
        return self.config.get('start_before',None) 

    def start_execution(self):
        if not self.is_running:
            _INF('%s Execute command: %s' % (self.id, self.cmd))
            self.start()

    def shutdown(self):
        if self.is_running:
            self.stop()

    def activate_force_exit(self):
        if self.is_running:
            self.stop()

    def run(self):
        self.process = subprocess.Popen(self.cmd,
                                        stdout = subprocess.PIPE,
                                        stderr = subprocess.PIPE,
                                        shell=True,
                                        cwd=self.phase_path,
                                        preexec_fn=os.setsid,
                                        executable='/bin/bash')

        self.is_running=True
        self.process.wait()
        self.is_running=False 
        _INF('%s Background command finished: "%s"' % (self.id, self.cmd))



    def stop(self):
        if self.is_alive():
            _INF('%s Stopping background command: "%s"' % (self.id, self.cmd))
            os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            self.join(10.0)
