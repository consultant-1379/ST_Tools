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
from datetime import datetime
import copy
import pprint
import numpy as np
from collections import deque

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

from . import ExecutionConfigurationError
from . import ExecutionStartError
from . import ExecutionRunError


class Scheduler_Base(threading.Thread):
    def __init__(self, id, executor, config , user_config, phase_path):

        if not executor.execution_with_traffic:
            configuration_error = '%s not allowed in a scenario without traffic' % id
            raise ExecutionConfigurationError(configuration_error)

        threading.Thread.__init__(self)

        self.executor = executor
        self.user_config = user_config
        try:
            self.display_info = config['configuration']['display_cps']
        except KeyError:
            self.display_info = None

        self.answers = Queue.Queue()
        self.__data ={}
        self.__phase = 'preexec'
        self.__id = id
        self.__running = False
        self.__data_file = os.path.join(phase_path,'CPS_%s.data' % executor.rtc_data.id)
        self.gnuplot_file = os.path.join(phase_path,'CPS_gnuplot_%s.cmd' % executor.rtc_data.id)
        self.gnuplot_loop = os.path.join(phase_path,'loop_forever.cmd')
        self.gif_file = os.path.join(phase_path,'CPS_%s.gif' % executor.rtc_data.id)
        self.__start_time = None
        self.__refresh_time = 5
        self.gnuplot_running = False
        self.__cps_scheduling = False
        self.__logfilename = os.path.join(phase_path, '%s.log' % self.id.lower())
        self.__logfile = open(self.__logfilename, "w")
        self.__force_exit = False
        self.__disable_graph = user_config.disable_graph
        self.__telnet_connection_errors = 0


    @property
    def force_exit(self):
        return self.__force_exit

    def activate_force_exit(self):
        self.__force_exit = True

    @property
    def logfile(self):
        return self.__logfile

    @logfile.setter
    def logfile(self, logfile):
        self.__logfile = logfile

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
    def data(self):
        return self.__data

    @property
    def cps_scheduling(self):
        return self.__cps_scheduling 

    @cps_scheduling.setter
    def cps_scheduling(self, cps_scheduling):
        self.__cps_scheduling = cps_scheduling

    @property
    def running(self):
        return self.__running 

    @running.setter
    def running(self, running):
        self.__running = running

    @property
    def start_time(self):
        return self.__start_time

    @start_time.setter
    def start_time(self, start_time):
        self.__start_time = start_time

    @property
    def graph_enabled(self):
        return not self.__disable_graph

    @property
    def cps_display(self):
        if self.display_info is None:
            return False
        return self.__cps_scheduling and self.display_info['enable']

    def create_gnuplot_file(self, gif = False, final_version = False):
        if final_version:
            gif = False

        output_gnuplot = '''set term %s
set title "%s" noenhanced%s 
set ylabel "CPS"
set datafile separator ","
set xdata time
set timefmt "%%Y-%%m-%%d %%H:%%M:%%S"
set format x "%%m-%%d %%H:%%M:%%S"
set xtics rotate by -45
set key outside
set grid layerdefault
set border 3
plot''' % (('gif' if gif else 'x11 font "arial,15,italic"'),
           self.executor.rtc_data.id,
           (('\nset output "%s"' % self.gif_file) if gif else ''))
        column = 2
        color = range(2,124)
        for bat in self.data.keys():
            output_gnuplot += ' "%s" using 1:%s title "Target-%s" noenhanced with lines lt %s,' % ((os.path.basename(self.data_file) if final_version else self.data_file),
                                                                                     column, bat, color[column])
            column += 1
            output_gnuplot += ' "%s" using 1:%s title "Current-%s" noenhanced with lines lt %s,' % ((os.path.basename(self.data_file) if final_version else self.data_file),
                                                                                     column, bat, color[column])
            column += 1

        return output_gnuplot[:-1]

    def init_data_file(self):
        timestamp = '%s' % datetime.now()
        output_data = '%s' % timestamp[:-7]
        for bat in self.data.keys():
            output_data += ',0,0'
        with open(self.data_file, 'w') as file:
            file.write('%s\n' % output_data)


    def handle_gnuplot(self, gif = False):
        output_gnuplot = self.create_gnuplot_file(gif=gif)

        if not gif:
            output_gnuplot += '\nload "%s"\n' % self.gnuplot_loop

            with open(self.gnuplot_loop, 'w') as file:
                file.write('pause %s;replot;reread;' % self.display_info['refresh_time'])

        with open(self.gnuplot_file, 'w') as file:
            file.write(output_gnuplot)

        stdout, stderr, returncode = st_command.execute_cmd('chmod 755 %s %s' % (self.gnuplot_file, self.gnuplot_loop) ,stderr = True)

        try:
            if gif:
                if self.display_info['real_time_enabled'] and self.graph_enabled:
                    cmd = 'ps -eaf | grep "gnuplot -noraise %s" | grep -v "grep" | awk \'{print $2}\' | xargs kill -9' % self.gnuplot_file
                    _INF('%s executing %s' % (self.id,cmd))
                    stdout, stderr, returncode = st_command.execute_cmd(cmd ,stderr = True)
                    self.gnuplot_running = False
                    if returncode:
                        return

                cmd = 'gnuplot %s > /dev/null 2>&1' % self.gnuplot_file
                _INF('%s executing %s' % (self.id,cmd))
                os.system(cmd)

                with open(self.gnuplot_file, 'w') as file:
                    file.write(self.create_gnuplot_file(gif=False, final_version=True))

                stdout, stderr, returncode = st_command.execute_cmd('chmod 755 %s' % self.gnuplot_file ,stderr = True)

            elif self.display_info['real_time_enabled'] and self.graph_enabled:
                cmd = 'gnuplot -noraise %s > /dev/null 2>&1 &' % self.gnuplot_file
                _INF('%s executing %s' % (self.id,cmd))
                os.system(cmd)
                self.gnuplot_running = True

        except Exception, e:
            self.log_event('warning', '%s Problem starting gnuplot: %s' % (self.id, str(e)), True)


    @property
    def id(self):
        return self.__id

    @property
    def phase(self):
        return self.__phase

    @phase.setter
    def phase(self, phase):
        self.__phase = phase

    @property
    def online(self):
        return self.__running

    @property
    def data_file(self):
        return    self.__data_file

    def start_phase(self, phase, bat):
        self.__phase = phase
        try:
            self.data[bat[0].id]['last_time'] = 0
            self.refresh(bat)

        except KeyError, e:
            return

    def refresh(self,bat_to_refresh=[]):
        if not self.cps_scheduling:
            return

        if not bat_to_refresh:
            return

        not_pending_slots = True
        for bat in bat_to_refresh:
            now = time.time()
            try:
                id = self.data[bat.id]
                if len(id[self.phase]):
                    if id['last_time']== 0:
                        if self.set_target_cps(bat,id[self.phase][0]['value']):
                            _INF( '%s Set initial %s cps in %s for %s' % (self.id, id[self.phase][0]['value'], self.phase, bat.id))
                            id['last_time'] = time.time()
                            id['target'] = id[self.phase][0]['value']
                            not_pending_slots = False
                        else:
                            run_error = '%s Problem setting cps' % self.id
                            self.log_event('error', run_error, True)
                            self.shutdown()
                            raise ExecutionRunError(run_error)

                    elif id[self.phase][0]['time'] == -1:
                        not_pending_slots = False

                    elif id[self.phase][0]['time'] < now - id['last_time']:
                        id[self.phase].pop(0)
                        if len(id[self.phase]):
                            if self.set_target_cps(bat,id[self.phase][0]['value']):
                                _INF( '%s Set %s cps in %s after %s seconds for %s' % (self.id, id[self.phase][0]['value'], self.phase, int(now - id['last_time']), bat.id))
                                id['last_time'] = time.time()
                                id['target'] = id[self.phase][0]['value']
                                not_pending_slots = False
                            else:
                                run_error = '%s Problem setting cps' % self.id
                                self.log_event('error', run_error, True)
                                self.shutdown()
                                raise ExecutionRunError(run_error)
                    else:
                        not_pending_slots = False

            except KeyError, e:
                return

        if not_pending_slots and self.phase == 'loadgen':
            self.executor.request_stop_phase()

    def run_ttcn_cli_command(self, cmd, cli):
        answer = None
        try:
            cli.requests.put_nowait((cmd, self.answers))
            try:
                answer = self.answers.get(True, timeout=10.0)
            except Queue.Empty:
                self.log_event('warning', '%s No answer received from %s' % (self.id, cli.id), True)
                return False

            return answer
        except Exception, e:
            action = '%s(%s)' % (cmd['action'],','.join(cmd['args']))
            self.log_event('warning', '%s Problem executing "%s" in %s:  %s' % (self.id, action, cli.id, str(e)), True)


    def set_target_cps(self, bat, value):
        if bat.execution_state != 'running':
            return

        cmd ={'action':'set_value','args':["'targetCps'",'%s' % value]}
        return self.run_ttcn_cli_command(cmd, bat.monitor)

    def get_current_cps(self, bat):
        cmd ={'action':'get_value','args':["'currentCps'"]}
        return self.run_ttcn_cli_command(cmd, bat.monitor)

    def read_current_cps(self):
        for bat in self.executor.rtc_data.BAT_instances:
            try:
                if self.data[bat.id]['enable'] and bat.execution_state == 'running':
                    value = self.get_current_cps(bat)
                    if not value:
                        self.log_event('warning', '%s problem reading cps' % self.id, True)
                        self.__telnet_connection_errors += 1
                        if self.__telnet_connection_errors > 3:
                            run_error = '%s Too much problems (%s) reading cps' % (self.id, self.__telnet_connection_errors)
                            self.log_event('error', run_error, True)
                            self.shutdown()
                    else:
                        self.__telnet_connection_errors = 0
                        self.data[bat.id]['current'] += [int(float(value))]
                        self.data[bat.id]['last_current'] = int(float(value))
            except Exception, e:
                continue

    def update_data_file(self):
        total = 0
        timestamp = '%s' % datetime.now()
        output ='%s' % timestamp[:-7]
        for bat in self.data.keys():
            total = 0
            for index in range(len(self.data[bat]['current'])):
                total += int(self.data[bat]['current'][index])

            if len(self.data[bat]['current']):
                output += ',%s,%s  ' % (self.data[bat]['target'], total/len(self.data[bat]['current']))
            else:
                output += ',%s,0  ' % (self.data[bat]['target'])

            self.data[bat]['current'] = []

        output += ' \n'

        with open(self.data_file, 'a') as file:
            file.write(output)

    def shutdown(self):
        if self.online:
            self.log_event('info', '%s shutdown received' % self.id, True)
            self.__running = False
            if self.cps_display:
                self.handle_gnuplot(gif=True)
                self.gnuplot_running = False

        if self.logfile is not None:
            self.logfile.close()
            self.logfile = None


    def start_execution(self):
        if self.cps_display:
            self.start()

    def run(self):
        self.log_event('info', '%s start thread execution for reading current cps' % self.id, True)
        scans = 0
        self.init_data_file()
        self.handle_gnuplot()
        self.__running = True
        self.__start_time = time.time()
        while (self.online):
            if self.force_exit:
                return

            time.sleep(float(self.display_info['sampling_time']))
            self.read_current_cps()
            scans += 1
            if scans > self.display_info['samples']:
                self.update_data_file()
                scans = 0

        self.log_event('info', '%s end of thread execution' % self.id, True)


class Scheduler(Scheduler_Base):
    def __init__(self, executor, config , user_config, phase_path):

        Scheduler_Base.__init__(self,'SCHEDULER',executor, config , user_config, phase_path) 

        if not isinstance(config['instances'],dict):
            reference = config['instances']
            instances = executor.rtc_data.get_bat_instances_from_reference(reference)
            if not instances:
                configuration_error = 'BAT instances configuration for %s not found' % reference
                self.release(ExecutionConfigurationError(configuration_error))

            config['instances'] = instances
            _INF('%s Using traffic reference %s' % (self.id, reference))



        for key in config['instances'].keys():
            try:
                if config['instances'][key]['enable'] and config['instances'][key]['cps_scheduler']['enable']:
                    aux_config = config['instances'][key]['cps_scheduler']
                    aux_config.update({'last_time':0,'current':[],'target':0})
                    self.data.update({key:aux_config})
                    self.cps_scheduling = True

            except KeyError, e:
                continue


class EC_Scheduler(Scheduler_Base):
    def __init__(self, executor, config , user_config, phase_path):

        Scheduler_Base.__init__(self,'CAPACITY_HANDLER',executor, config , user_config, phase_path)
        self.__config = config
        self.__period = -1
        self.__max_error_rate = -1
        self.__traffic_slots = []
        self.__traffic_ref = {}
        self.__last_time = 0
        self.__EC_candidate = -1
        self.__EC_candidate_found = False
        self.__EC_load = None
        self.__update_load_monitor = False
        self.__load_samples = []
        self.__period_load = []
        self.__max_load = 0
        self.__max_load_variance = 0
        self.__current_load_variance = 0
        self.__DC_load_measure_enable = False
        self.__validation_time = -1
        self.__PL_for_DC = None
        self.__rump_up = True
        self.__bat_instances_pending_to_start = None
        self.__fsm_status = 'initial'
        self.__Traffic_config = {'instances':{},'slots':[]}
        self.__nof_steps = 0

        if self.executor.error_monitor.id == 'FakeMonitor':
            configuration_error = 'Monitor error is mandatory when using capacity handler'
            raise ExecutionConfigurationError(configuration_error)

        if self.executor.diaproxy_handler.id == 'FakeDiaproxyHandler':
            configuration_error = 'Diaproxy Handler is mandatory when using capacity handler'
            raise ExecutionConfigurationError(configuration_error)

        try:
            if config['configuration']['Capacity_handler']['enable']:
                try:
                    self.__period = config['configuration']['Capacity_handler']['configuration']['period']
                    self.__max_load = config['configuration']['Capacity_handler']['configuration']['max_load']
                    self.__max_error_rate = config['configuration']['Capacity_handler']['configuration']['error_rate']
                    self.__max_load_variance = config['configuration']['Capacity_handler']['configuration']['load_variance']
                    self.__DC_load_measure_enable = config['configuration']['Capacity_handler']['configuration']['type'] == 'DC'
                    self.__traffic_slots = config['configuration']['Capacity_handler']['run_traffic']['traffic_slots']
                    self.__traffic_ref = config['configuration']['Capacity_handler']['create_traffic_ref']
                    self.__update_load_monitor = config['configuration']['Capacity_handler']['run_traffic']['update_load_monitor']
                except KeyError as e:
                    configuration_error = 'Missing %s Capacity_handler parameter in json file' % str(e)
                    raise ExecutionConfigurationError(configuration_error)

                try:
                    self.__validation_time = config['configuration']['Capacity_handler']['configuration']['validation_time']
                except KeyError:
                    pass

        except KeyError as e:
            return

        except Exception as e:
            configuration_error = 'CAPACITY_HANDLER Error parsing json file: %s' % str(e)
            raise ExecutionConfigurationError(configuration_error)

        if self.load_validation_enabled and self.executor.load_monitor.id == 'FakeMonitor':
            configuration_error = 'Monitor load is mandatory when using capacity handler'
            raise ExecutionConfigurationError(configuration_error)

        self.delete_reference()

        for key in config['instances'].keys():
            try:
                if config['instances'][key]['enable'] and config['instances'][key]['cps_scheduler']['enable']:
                    self.__Traffic_config['instances'].update({key:copy.deepcopy(config['instances'][key])})
                    aux_config = config['instances'][key]['cps_scheduler']
                    try:
                        initial = config['instances'][key]['cps_scheduler']['loadgen']['initial']
                        delta_up = config['instances'][key]['cps_scheduler']['loadgen']['delta_up']
                        delta_down = config['instances'][key]['cps_scheduler']['loadgen']['delta_down']
                    except Exception, e:
                        configuration_error = 'Missing cps_scheduler->loadgen->%s  for %s in json file' % (str(e),key)
                        raise ExecutionConfigurationError(configuration_error)

                    aux_config.update({'last_time':0,'current':[],'last_current':0,'target':0,'used_target':[]})
                    self.data.update({key:aux_config})

            except KeyError, e:
                continue

        self.cps_scheduling = True

    @property
    def load_media(self):
        total = 0
        if self.__load_samples:
            for sample in self.__load_samples:
                total += int(sample)
            _DEB('%s load media had a total:%d' % (self.id, int(total)))
            return total / len(self.__load_samples)

        _DEB('%s NOT load samples: %s' % (self.id, self.__load_samples))
        return 0

    def purge_load_samples(self, media):
        for index in range(len(self.__load_samples)):
            if self.rump_up:
                if self.__load_samples[index] >= media:
                    self.__load_samples = self.__load_samples[index:]
                    _DEB('%s load samples rump_up: %s' % (self.id, self.__load_samples))
                    break
            else:
                if self.__load_samples[index] <= media:
                    self.__load_samples = self.__load_samples[index:]
                    _DEB('%s load samples NOT rump_up: %s' % (self.id, self.__load_samples))
                    break

    @property
    def load_stable(self):
        media = self.load_media
        if media:
            if self.__fsm_status != 'validate':
                self.purge_load_samples(media)
                media = self.load_media
            self.__period_load.append(media)
            _DEB('%s period load with media %.2f is:%s' % (self.id, float(media), self.__period_load))
            self.__current_load_variance = np.var(self.__load_samples)
            _DEB('%s load is stable if current load variace %.2f is grater than max load variance %.2f' % (self.id, self.__current_load_variance, self.max_load_variance))
            return self.current_load_variance <= self.max_load_variance

        self.__period_load.append(-1)
        _DEB('%s Load NOT stable. Period load is:%s' % (self.id, self.__period_load))
        return False

    @property
    def update_load_monitor(self):
        return self.__update_load_monitor

    @property
    def max_load_variance(self):
        return float(self.__max_load_variance)

    @property
    def current_load_variance(self):
        return float(self.__current_load_variance)

    @property
    def max_load(self):
        return float(self.__max_load)

    @property
    def load_validation_enabled(self):
        return (self.__max_load != -1)

    @property
    def traffic_ref(self):
        return self.__traffic_ref

    @property
    def rump_up(self):
        return self.__rump_up

    def shutdown(self):
        if self.online:
            self.log_event('info', '%s shutdown received' % self.id, True)
            self.running = False
            if self.cps_display:
                self.handle_gnuplot(gif=True)
                self.gnuplot_running = False

            if self.__PL_for_DC is not None:
                self.unlock_PL()

        self.log_event('', '%s Scheduling info:\n%s' % (self.id, self.scheduling_info()))
        if self.logfile is not None:
            self.logfile.close()
            self.logfile = None


    def scheduling_info(self):
        info = ''
        for count in range(0,self.__nof_steps):
            info +='\n\tLoad: %s' % (self.__period_load[count] if self.load_validation_enabled else '-1')

            for bat in self.data.keys():
                info += '\t%s cps:%s' % (bat, self.data[bat]['used_target'][count])
        _DEB('%s scheduling_info:%s' % (self.id, info))
        return '%s\n' % info

    def slot_factor(self, slot):
        factor = slot['factor']
        if isinstance(factor,str) or isinstance(factor,unicode):
            factor = self.executor.rtc_data.get_macro_value(factor)

        try:
            return float(factor)
        except Exception as e:
            run_error = '%s Factor value not valid: %s' % (self.id, factor)
            raise ExecutionRunError(run_error)

    def build_cps_table(self):
        for bat in self.data.keys():
            self.data[bat]['loadgen'] = []
            if len(self.data[bat]['used_target']) > 1:
                for slot in self.__traffic_slots:
                    cps = int(float(self.slot_factor(slot)) * self.data[bat]['used_target'][-1])
                    self.data[bat]['loadgen'].append({'time':slot['time'],
                                                      'value':cps})
                    self.data[bat]['last_time'] = 0
                    self.data[bat]['current'] = []
                    self.data[bat]['target'] = 0

    def reconfigure_load_monitor(self):
        if self.__EC_load is not None and self.update_load_monitor:
            slots=[]
            for slot in self.__traffic_slots:
                target_load = float(self.slot_factor(slot) * self.__EC_load)
                slots.append({"target_load":target_load,
                              "time":slot['time'],"variance":self.max_load_variance,"transition":10})

            self.executor.load_monitor.reconfigure(slots)

    def delete_reference(self):
        for reference in self.traffic_ref:
            self.executor.rtc_data.delete_reference(reference['id'])


    def create_reference(self):
        for reference in self.traffic_ref:
            for bat in self.data.keys():
                cps_target = self.data[bat]['used_target'][-1]
                loadgen = []

                for slot in reference['slots']:
                    cps = int(float(self.slot_factor(slot)) * cps_target)
                    loadgen.append({'value':cps,'time':slot['time']})

                self.__Traffic_config['instances'][bat]['cps_scheduler']['loadgen'] = loadgen

            slots=[]
            reference_value = -1
            if self.load_validation_enabled:
                for slot in reference['slots']:
                    target_load = float(self.slot_factor(slot) * self.__EC_load)
                    slots.append({"target_load":target_load,
                                "time":slot['time'],"variance":self.max_load_variance,"transition":10})

            self.__Traffic_config['slots'] = slots
            if self.load_validation_enabled:
                reference_value = int(self.__EC_load * reference.get('target_load_factor', 1))
                add_info = ''
                for slot in reference['slots']:
                    add_info += '\ttime=%s:factor=%s' % (slot['time'],self.slot_factor(slot))
                self.log_event('info', '%s Traffic reference created %s\n%s' % (self.id,reference['id'],add_info), True)

            self.executor.rtc_data.update_reference(self.__Traffic_config, reference['id'], reference_value)




    def lock_PL(self, timeout=60.0):
        try:
            unlocked_pl = self.executor.rtc_data.cabinet.payload
        except Exception , e:
            run_error = '%s problem finding a PL to be locked: %s   ' % (self.id, str(e))
            raise ExecutionRunError(run_error)

        if unlocked_pl:
            try:
                self.executor.rtc_data.cabinet.lock_processor(unlocked_pl[0])
                self.log_event('info', '%s %s locking' % (self.id,unlocked_pl[0]), True)
                self.__PL_for_DC = unlocked_pl[0]
                max_time = timeout
                while True:
                    now = time.time()
                    time.sleep(5.0)
                    if self.executor.diaproxy_handler.check_connections_up():
                        self.log_event('info', '%s All DiaProxy connection UP after locking %s ' % (self.id, self.__PL_for_DC), True)
                        break

                    max_time -= (time.time() - now)
                    if max_time < 0:
                        run_error = '%s Time waiting for DiaProxy (%s sec) connection UP after locking %s expired' % (self.id, timeout, self.__PL_for_DC)
                        self.log_event('error', run_error, True)
                        raise ExecutionRunError(run_error)

                time.sleep(90.0)
                self.log_event('info', '%s %s has been locked' % (self.id,unlocked_pl[0]), True)
                return

            except Exception , e:
                run_error = '%s Problem locking  %s : %s' % (self.id, unlocked_pl[0],str(e))
                self.log_event('error', run_error, True)

        else:
            run_error = '%s not found a PL to be locked   ' % self.id

        raise ExecutionRunError(run_error)

    def unlock_PL(self):
        if self.__PL_for_DC is None:
            self.log_event('warning', '%s There is not a PL to be unlocked   ' % self.id, True)
            return
        try:
            self.executor.rtc_data.cabinet.unlock_processor(self.__PL_for_DC)
            self.log_event('info', '%s %s unlocking' % (self.id, self.__PL_for_DC), True)
            self.__PL_for_DC = None
            self.log_event('info', '%s PL has been unlocked' % (self.id), True)
            return
        except Exception , e:
            run_error = 'error', '%s Problem unlocking  %s : %s' % (self.id,
                                                                    self.__PL_for_DC,
                                                                    str(e))
            self.log_event('error', run_error, True)

    def start_phase(self, phase, bat):
        self.phase = phase
        if self.phase in ['preexec','postexec']:
            Scheduler_Base.start_phase(self,phase, bat)
            return


        if self.load_validation_enabled:
            self.executor.load_monitor.disable()
        if self.__DC_load_measure_enable and self.__PL_for_DC is None:
            self.lock_PL()

        if self.__bat_instances_pending_to_start is None:
            self.__bat_instances_pending_to_start = len(self.executor.rtc_data.BAT_instances)

        self.__bat_instances_pending_to_start -= 1

        if self.__bat_instances_pending_to_start == 0:
            self.refresh(self.executor.rtc_data.BAT_instances)
            self.__bat_instances_pending_to_start = None

    def refresh(self,bat_to_refresh):
        if not self.cps_scheduling:
            return

        if not bat_to_refresh:
            return

        if self.phase in ['preexec','postexec'] or self.__fsm_status == 'finished':
            Scheduler_Base.refresh(self,bat_to_refresh)
            return

        now = time.time()
        if self.__last_time == 0:
            self.__last_time = now
            self.__nof_steps += 1
            for bat_instance in bat_to_refresh:
                try:
                    bat_data = self.data[bat_instance.id]
                    if self.set_target_cps(bat_instance,bat_data['loadgen']['initial']):
                        self.log_event('info',  '%s Set initial %s cps in %s for %s' % (self.id, 
                                                                                        bat_data['loadgen']['initial'],
                                                                                        'loadgen',
                                                                                        bat_instance.id), True)
                        bat_data['target'] = bat_data['loadgen']['initial']
                        bat_data['used_target'].append(bat_data['loadgen']['initial'])
                        self.__load_samples = []
                        self.__fsm_status = 'search'
                    else:
                        run_error = '%s Unable to initialize the Capacity handler: problem setting cps' % self.id
                        self.log_event('error', run_error, True)
                        self.executor.rtc_data.update_verdict(False, error_info=run_error,repeat=True)
                        self.executor.request_stop_phase()
                        self.__fsm_status = 'finished'
                        return
                except KeyError, e:
                    run_error = '%s Unable to initialize the Capacity handler: %s' % (self.id, str(e))
                    self.log_event('error', run_error, True)
                    self.executor.rtc_data.update_verdict(False, error_info=run_error,repeat=True)
                    self.executor.request_stop_phase()
                    self.__fsm_status = 'finished'
                    return

        elif self.__period < now - self.__last_time:
            error_rate = self.executor.error_monitor.stop_monitoring()
            _DEB('%s error rate: %.2f' % (self.id, error_rate))
            self.executor.error_monitor.skip_check_last_register()
            load_stable = self.load_stable if self.load_validation_enabled else True
            tps_error_rate = self.executor.error_monitor.tps_error_rate()
            _DEB('%s TPS error rate: %f' % (self.id, tps_error_rate))
            if self.load_validation_enabled: 
                _DEB('%s Load Validation ENABLED ' % self.id)
                clv = self.current_load_variance
                load_info = 'Load:%s  Variance:%.2f' % (self.__period_load[-1],clv)  
            else:
                load_info = 'Load:%s  Variance:' % self.__period_load[-1]

            _DEB('%s load info: %s' % (self.id, load_info))
            event_message = '%s CPS_error_rate:%.2f  TPS_error_rate:%.2f  %s' % (self.id, float(error_rate), float(tps_error_rate), load_info)
            self.log_event('info', event_message, True) 

            if self.__fsm_status == 'validate':
                if tps_error_rate > self.__max_error_rate or not load_stable:
                    if tps_error_rate > self.__max_error_rate:
                        run_error = '%s Unable to validate DC: tps error rate %.2f is higher than %.2f' % (self.id,
                                                                                        tps_error_rate,
                                                                                        self.__max_error_rate)
                    else:
                        run_error = '%s Unable to validate DC: load is not stable' % self.id

                    self.log_event('error', run_error, True)
                    self.executor.rtc_data.update_verdict(False, error_info=run_error,repeat=True)
                    self.__fsm_status = 'finished'
                    self.executor.request_stop_phase()
                    return

                self.__EC_load = self.__period_load[-1] if self.load_validation_enabled else -1
                self.log_event('info', '%s DC validation finished: tps error rate %.2f is lower than %.2f with DC load %s' % (self.id,
                                                                                            tps_error_rate,
                                                                                            self.__max_error_rate,
                                                                                            self.__EC_load), True)

                self.create_reference()
                self.build_cps_table()
                self.__fsm_status = 'finished'
                self.log_event('info', '%s Scheduling info:\n%s' % (self.id, self.scheduling_info()))
                if  not self.__traffic_slots:
                    self.log_event('info', '%s Request stop phase' % self.id, True)
                    self.executor.request_stop_phase()
                    return

                if self.load_validation_enabled:
                    self.reconfigure_load_monitor()
                    self.executor.load_monitor.enable()

                return


            elif self.__fsm_status == 'search':
                reached_limit = False
                if error_rate > self.__max_error_rate:
                    self.log_event('info', '%s cps error rate %.2f is higher than %.2f' % (self.id,
                                                                                    error_rate,
                                                                                    self.__max_error_rate), True)
                    reached_limit = True
                elif self.load_validation_enabled and self.__period_load[-1] >= self.max_load:
                    self.log_event('info', '%s load %s is higher than %s' % (self.id,
                                                                                self.__period_load[-1],
                                                                                self.max_load), True)
                    reached_limit = True
                elif self.load_validation_enabled and not load_stable:
                    self.log_event('info', '%s load is not stable' % self.id, True)
                    reached_limit = True

                if reached_limit:
                    self.__fsm_status = 'search_down'
                    self.__rump_up = False

                for bat_instance in bat_to_refresh:
                    try:
                        bat_data = self.data[bat_instance.id]
                        if self.__fsm_status == 'search_down':
                            self.__EC_candidate = int(len(bat_data['used_target']) - 2)
                            if self.__EC_candidate < 0:
                                run_error = '%s Unable to find the Capacity. The first step does not match quality criteria' % self.id
                                self.log_event('error', run_error, True)
                                self.executor.rtc_data.update_verdict(False, error_info=run_error,repeat=True)
                                self.executor.request_stop_phase()
                                self.__fsm_status = 'finished'
                                return

                            new_value = bat_data['used_target'][-1] - bat_data['loadgen']['delta_down']
                        else:
                            current_cps = self.data[bat_instance.id]['last_current']
                            if abs(bat_data['target']) > 100 and abs(bat_data['target'] - current_cps) > 0.25 * bat_data['target']:
                                run_error = '%s Unable to find the Capacity. %s could be paused' % (self.id, bat_instance.id)
                                self.log_event('error', run_error, True)
                                self.executor.rtc_data.update_verdict(False, error_info=run_error,repeat=True)
                                self.executor.request_stop_phase()
                                self.__fsm_status = 'finished'
                                return

                            new_value = bat_data['target'] + bat_data['loadgen']['delta_up']

                        if self.set_target_cps(bat_instance,new_value):
                            self.log_event('info',  '%s Set %s cps in loadgen after %s seconds for %s' % (self.id,
                                                                                                        new_value,
                                                                                                        int(now - self.__last_time)
                                                                                                        , bat_instance.id), True)
                            bat_data['target'] = new_value
                            bat_data['used_target'].append(new_value)
                            self.__load_samples = []
                        else:
                            run_error = '%s Unable to find the Capacity: problem setting cps' % self.id
                            self.log_event('error', run_error, True)
                            self.executor.rtc_data.update_verdict(False, error_info=run_error,repeat=True)
                            self.executor.request_stop_phase()
                            self.__fsm_status = 'finished'
                            return
                    except KeyError, e:
                        run_error = '%s Unable to find the Capacity: %s' % (self.id, str(e))
                        self.log_event('error', run_error, True)
                        self.executor.rtc_data.update_verdict(False, error_info=run_error,repeat=True)
                        self.executor.request_stop_phase()
                        self.__fsm_status = 'finished'
                        return

                self.__nof_steps += 1
                self.executor.error_monitor.start_monitoring(phase='loadgen', error_rate=self.__max_error_rate)
                self.__last_time = time.time()

            elif self.__fsm_status == 'search_down':
                load_info = ''
                load_ok = True
                self.__EC_load = -1
                if self.load_validation_enabled:
                    if load_stable and self.__period_load[-1] <= self.max_load:
                        self.__EC_load = self.__period_load[-1]
                        load_info = 'and load %s stable lower than %s' % (self.__EC_load,self.max_load)
                    else:
                        load_ok = False

                if tps_error_rate <= self.__max_error_rate and load_ok:
                    self.log_event('info', '%s tps error rate %.2f is lower or equal than %.2f %s' % (self.id,
                                                                                                      tps_error_rate,
                                                                                                      self.__max_error_rate,
                                                                                                      load_info), True)
                    if self.__DC_load_measure_enable:
                        self.log_event('info', '%s Start validation of DC' % self.id, True)
                        self.unlock_PL()
                        for bat_instance in bat_to_refresh:
                            try:
                                bat_data = self.data[bat_instance.id]
                                new_value = float (0.8 * bat_data['used_target'][-1])
                                if self.set_target_cps(bat_instance,new_value):
                                    self.log_event('info',  '%s Set %s cps (0.8 * %s) in %s for %s' % (self.id, 
                                                                                                    new_value,
                                                                                                    bat_data['used_target'][-1],
                                                                                                    'loadgen',
                                                                                                    bat_instance.id), True)
                                    bat_data['target'] = new_value
                                    bat_data['used_target'].append(new_value)
                                    self.__EC_candidate = len(bat_data['used_target']) -1 
                                else:
                                    run_error = '%s Unable to find the DC: problem setting cps' % self.id
                                    self.log_event('error', run_error, True)
                                    self.executor.rtc_data.update_verdict(False, error_info=run_error,repeat=True)
                                    self.executor.request_stop_phase()
                                    self.__fsm_status = 'finished'
                                    return

                            except KeyError, e:
                                run_error = '%s Unable to find the DC: %s' % (self.id, str(e))
                                self.log_event('error', run_error, True)
                                self.executor.rtc_data.update_verdict(False, error_info=run_error,repeat=True)
                                self.executor.request_stop_phase()
                                self.__fsm_status = 'finished'
                                return

                        self.__nof_steps += 1
                        time.sleep(60.0)
                        self.__load_samples = []
                        self.__fsm_status = 'validate'
                        self.__period = self.__validation_time
                        self.__last_time = time.time()
                        self.executor.error_monitor.start_monitoring(phase='loadgen', error_rate=self.__max_error_rate)
                        return

                    self.create_reference()
                    self.build_cps_table()
                    self.__fsm_status = 'finished'
                    self.log_event('info', '%s Scheduling info:\n%s' % (self.id, self.scheduling_info()))
                    if  not self.__traffic_slots:
                        self.log_event('info', '%s Request stop phase' % self.id, True)
                        self.executor.request_stop_phase()
                        return

                    if self.load_validation_enabled:
                        self.reconfigure_load_monitor()
                        self.executor.load_monitor.enable()
                    self.executor.error_monitor.start_monitoring(phase='loadgen', error_rate=self.__max_error_rate)

                else:
                    for bat_instance in bat_to_refresh:
                        try:
                            bat_data = self.data[bat_instance.id]
                            new_value = bat_data['used_target'][-1] - bat_data['loadgen']['delta_down']
                            if bat_data['used_target'][self.__EC_candidate] > new_value:
                                run_error = '%s Unable to find the Capacity: next CPS value is lower than the latest good value during rump up' % self.id
                                self.log_event('error', run_error, True)
                                self.executor.rtc_data.update_verdict(False, error_info=run_error,repeat=True)
                                self.executor.request_stop_phase()
                                self.__fsm_status = 'finished'
                                return

                            if self.set_target_cps(bat_instance,new_value):
                                self.log_event('info',  '%s Set %s cps in loadgen after %s seconds for %s' % (self.id,
                                                                                                            new_value,
                                                                                                            int(now - self.__last_time)
                                                                                                            , bat_instance.id), True)
                                bat_data['target'] = new_value
                                bat_data['used_target'].append(new_value)
                                self.__load_samples = []
                            else:
                                run_error = '%s Unable to find the Capacity: problem setting cps' % self.id
                                self.log_event('error', run_error, True)
                                self.executor.rtc_data.update_verdict(False, error_info=run_error,repeat=True)
                                self.executor.request_stop_phase()
                                self.__fsm_status = 'finished'
                                return
                        except KeyError, e:
                            run_error = '%s Unable to find the Capacity: %s' % (self.id, str(e))
                            self.log_event('error', run_error, True)
                            self.executor.rtc_data.update_verdict(False, error_info=run_error,repeat=True)
                            self.executor.request_stop_phase()
                            self.__fsm_status = 'finished'
                            return

                    self.__nof_steps += 1
                    self.executor.error_monitor.start_monitoring(phase='loadgen', error_rate=self.__max_error_rate)
                    self.__last_time = time.time()
            else:
                run_error = '%s Unable to find the Capacity: Wrong FSM state %s' % (self.id, self.__fsm_status)
                self.log_event('error', run_error, True)
                self.executor.rtc_data.update_verdict(False, error_info=run_error,repeat=True)
                self.executor.request_stop_phase()
                self.__fsm_status = 'finished'
                return

        elif self.load_validation_enabled:
            self.__EC_load = self.executor.load_monitor.load
            self.__load_samples.append(self.__EC_load)

