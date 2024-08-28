#!/usr/bin/env python
#

import sys
import os
import os.path
from datetime import datetime

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

import hss_utils.node.gentraf
import hss_utils.st_command as st_command
import hss_utils.connection as connection
import hss_utils.node
import hss_utils.node.cba
import hss_utils.node.tsp

import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning

from HSS_rtc_lib.shared import *
from . import ExecutionConfigurationError
from . import ExecutionStartError
from . import ExecutionRunError





class BAT_base(threading.Thread):
    def __init__(self, host, cabinet, config, id, instance, root_path, exec_config, executor, disable_graph=False):

        threading.Thread.__init__(self)

        self.__cabinet = cabinet
        self.__config = config
        self.__executor = executor
        self.__host = host
        self.__disable_graph = disable_graph

        self.__node = None
        self.__id = id
        self.__instance = instance
        self.__channel = None
        self.__exit_code = ''
        self.__need_clean = False
        self.__start_time = None
        self.__stop_time = None
        self.__execution_state = ''
        self.__destination_path = os.path.join(root_path,self.__id)
        self.__path_suffix = time.strftime("%Y%m%d-%H%M%S")
        self.__working_dir = '/opt/hss/%s/%s_%s' % (getpass.getuser(), self.id, self.__path_suffix)
        self.__cli_telnet = None
        self.__cli_display = None
        self.__Diaproxys = []
        self.__Loadplotter = None
        self.__force_exit = False

        self.temp_dir = '/opt/hss/%s/%s_%s/titansim_HSS_BAT' % (getpass.getuser(), self.id, self.__path_suffix)
        self.__stat_file = None
        self.last_stats = {}
        self.__current_stats = {}
        self.__error_template = {}
        self.__error_db_enabled = False
        self.__error_db ={'preexec':[],
                          'loadgen':[],
                          'postexec':[]
                         }

        self.__traffic_phase = 'preexec'

        try:
            self.monitor_error = exec_config['monitor_error']
        except KeyError:
            self.monitor_error = {
                'enable':{'preexec':False,'loadgen':False,'postexec':False},
                'sampling_time':0,
                'display':False
                }


        if not os.path.exists(self.__destination_path):
            os.makedirs(self.__destination_path)

        _DEB('Creating %s in %s' % (self.__id, self.__host))
        access_config = {'host':self.__host} 
        try:
            self.__node = hss_utils.node.gentraf.GenTraf(config = access_config, allow_x11_forwarding = True)
            self.__channel = self.__node.get_channel()
            self.__node.create_connection(config=access_config, session_type=self.__node.session_type,identity='aux')
        except connection.Unauthorized, e: 
            configuration_error = '%s creation problem: %s' % (self.__id, str(e))
            _ERR(configuration_error)
            raise ExecutionConfigurationError(configuration_error)

        except (connection.ConnectionFailed, connection.ConnectionTimeout), e: 
            configuration_error = '%s creation problem: %s' % (self.__id, str(e))
            _ERR(configuration_error)
            raise ExecutionConfigurationError(configuration_error)

        except KeyboardInterrupt:
            _WRN('Cancelled by user')
        except Exception, e:
            configuration_error = '%s creation problem: %s' % (self.__id, str(e))
            _ERR(configuration_error)
            raise ExecutionConfigurationError(configuration_error)

    @property
    def access_params(self):
       if self.executor.user_config.node_type =='CBA':
	 return ('--cliss-user %s ' % self.executor.user_config.user)
       else:
         return ('')

    @property
    def force_exit(self):
        return self.__force_exit

    def activate_force_exit(self):
        self.__force_exit = True

    @property
    def executor(self):
        return self.__executor

    @property
    def monitor_error_rate_file(self):
        return '%s/%s_monitor_error_rate.data' % (self.destination_path, self.id)

    @property
    def total_error_rate_file(self):
        return '%s/%s_total_error_rate.data' % (self.destination_path, self.id)

    @property
    def total_error_rate_gif_file(self):
        return '%s/%s_total_error_rate.gif' % (self.destination_path, self.id)

    @property
    def total_error_rate_gnuplot_file(self):
        return '%s/%s_total_error_rate.cmd' % (self.destination_path, self.id)

    @property
    def traffic_result_file(self):
        return '%s/%s_traffic_result.data' % (self.destination_path, self.id)

    def set_traffic_phase(self, value):
        self.__traffic_phase = value

    @property
    def traffic_phase(self):
        return self.__traffic_phase

    @traffic_phase.setter
    def traffic_phase(self, traffic_phase):
        self.__traffic_phase = traffic_phase

    @property
    def stat_file(self):
        return self.__stat_file

    @property
    def current_stats(self):
        return self.__current_stats

    @property
    def cabinet(self):
        return self.__cabinet

    @property
    def config(self):
        return self.__config

    @property
    def host(self):
        return self.__host

    @property
    def node(self):
        return self.__node

    @node.setter
    def node(self, node):
        self.__node = node

    @property
    def id(self):
        return self.__id

    @property
    def channel(self):
        return self.__channel

    @property
    def need_clean(self):
        return self.__need_clean

    @need_clean.setter
    def need_clean(self, need_clean):
        self.__need_clean = need_clean

    @property
    def execution_state(self):
        return self.__execution_state

    @execution_state.setter
    def execution_state(self, execution_state):
        self.__execution_state = execution_state

    @property
    def start_time(self):
        return self.__start_time

    @start_time.setter
    def start_time(self, start_time):
        self.__start_time = start_time

    @property
    def stop_time(self):
        return self.__stop_time

    @stop_time.setter
    def stop_time(self, stop_time):
        self.__start_time = stop_time

    @property
    def is_running(self):
        return self.exit_code == ''

    @property
    def destination_path(self):
        return self.__destination_path

    @property
    def working_dir(self):
        return self.__working_dir

    @property
    def instance(self):
        return self.__instance

    @property
    def telnet_upper_port(self):
        return self.telnet_lower_port + 99

    @property
    def telnet_lower_port(self):
        return 6000 + 100 * int(self.__instance)

    def free_port(self, lower_port, upper_port,offset=None):

        if offset is not None:
            for port in range(lower_port+offset,lower_port+offset+50):
                if self.node.available_port(port):
                    return port

        candidate = random.randint(lower_port, upper_port)
        tries = 100
        while not self.node.available_port(candidate):
            candidate = random.randint(lower_port, upper_port)
            tries -= 1
            if tries == 0:
                run_error = '%s Cannot get a free port in range %s-%s' % (self.id, lower_port, upper_port)
                _ERR(run_error)
                raise ExecutionRunError(run_error)

        return candidate

    @property
    def cli_telnet(self):
        if self.__cli_telnet is None:
            self.__cli_telnet = self.free_port(self.telnet_lower_port, self.telnet_upper_port,offset=0)

        return self.__cli_telnet

    @property
    def cli_display(self):
        if self.__cli_display is None:
            self.__cli_display = self.free_port(self.telnet_lower_port, self.telnet_upper_port,offset=50)

        return self.__cli_display

    @property
    def telnet_value(self):
        return ':CLI_TELNET:%s :CLI_DISPLAY:%s'% (self.cli_telnet, self.cli_display)

    @property
    def mc_upper_port(self):
        return self.mc_lower_port + 99

    @property
    def mc_lower_port(self):
        return 7000 + 100 * int(self.__instance)

    @property
    def mc_port(self):
        return self.free_port(self.mc_lower_port, self.mc_upper_port)

    @property
    def traffic_type(self):
        param_list = self.config['parameters'].split(' ')
        position = param_list.index('-C')
        return param_list[position + 1]

    @property
    def update_parameters(self):
        return self.executor.rtc_data.macro_translator(self.config['parameters'] + ' -E "%s"' % self.telnet_value)

    @property
    def disable_graph(self):
        return '--disable_graph' if self.__disable_graph else ''

    @property
    def Diaproxys(self):
        return self.__Diaproxys

    def add_diaproxy(self, host, udp_port):
        self.__Diaproxys.append('%s:%s' % (host, udp_port))

    @property
    def Loadplotter(self):
        return self.__Loadplotter

    @Loadplotter.setter
    def Loadplotter(self, loadplotter):
        self.__Loadplotter = loadplotter


    def run(self):
        if self.node is None: 
            return None

        self.node.working_dir = self.working_dir
        self.need_clean= True

        _INF('%s cmd: %s' % (self.id, self.cmd))
        self.start_time = datetime.now()

        max_time_for_start = float(180)
        max_time_for_shutdown = float(120)

        _INF('%s %s' % (self.id, self.execution_state))
        self.channel.write_line(self.cmd)

        if self.execution_state != '':
            run_error = '%s Wrong state %s' % (self.id, self.traffic_phase)
            _ERR(run_error)
            raise ExecutionRunError(run_error)

        self.execution_state = 'starting'
        sync_expression = self.node.get_connection().sync_expression
        while True:
            if self.force_exit:
                return
            now = time.time()
            try:
                result = self.channel.expect(['Alias sent',
                                            sync_expression,
                                            '\r\n',
                                            'Traffic finished in Manual Mode. Waiting for user to stop execution',
                                            'Main Test case terminated',
                                            'Problem starting MC']
                                            ,timeout=float(self.monitor_error['sampling_time']) if self.monitor_error['sampling_time'] > 0 else 10.0)

                # Alias sent
                if result == 0:
                    if self.execution_state == 'starting':
                        self.start_monitor()
                        self.execution_state = 'running'
                        self.set_stat_file()
                        _INF('%s %s' % (self.id, self.execution_state))
                        continue

                # run_titansim finished
                elif result == 1:
                    if self.execution_state in ['starting','failed' ]:
                        self.execution_state = 'failed'
                        self.__exit_code = 'faulty BAT'
                        _ERR('%s %s' % (self.id, self.execution_state))
                    else:
                        self.execution_state = 'stopped'
                        _INF('%s %s' % (self.id, self.execution_state))
                    break
                elif result == 5:
                    if self.execution_state == 'starting':
                        self.execution_state = 'failed'
                        self.__exit_code = 'Problem starting MC'
                        _ERR('%s %s' % (self.id, self.execution_state))
                    else:
                        self.execution_state = 'stopped'
                        _INF('%s %s' % (self.id, self.execution_state))
                    break
                # info sent by run_titansim 
                elif result == 2:
                    if self.execution_state == 'pending to stop':
                        self.execution_state = 'stopping'
                        _INF('%s %s' % (self.id, self.execution_state))
                        self.stop_traffic()
                        continue

                    elif self.execution_state == 'starting':
                        max_time_for_start -= time.time() - now
                    elif self.execution_state == 'stopping':
                        max_time_for_shutdown -= time.time() - now

                    #if not self.channel.stdout.startswith('debug') and  len(self.channel.stdout) > 4:
                    if ' DEB ' not in self.channel.stdout and not self.channel.stdout.startswith('debug') and  len(self.channel.stdout) > 4:
                        print '%s %s  %s' % (self.id, self.execution_state, self.channel.stdout[1:])
                        if 'UP & RUNNING' in self.channel.stdout[1:]:
                            word_list = self.channel.stdout[1:].split()
                            pos = word_list.index('Diaproxy')
                            info = word_list[pos+1]
                            self.add_diaproxy(info.split(':')[0],info.split(':')[2])
                        if 'LoadPlotter up and running' in self.channel.stdout[1:]:
                            word_list = self.channel.stdout[1:].split()
                            pos = word_list.index('in')
                            info = word_list[pos+1]
                            self.__Loadplotter = word_list[pos+1]


                    continue
                # traffic finished 
                elif result == 3:
                    _INF('%s %s Traffic finished...waiting for counters' % (self.id, self.execution_state))
                    time.sleep(20.0)
                    self.execution_state = 'pending to stop'
                    _INF('%s %s' % (self.id, self.execution_state))
                    continue
                # Main Test case terminated
                elif result == 4:
                    _INF('%s %s Main Test case terminated' % (self.id, self.execution_state))
                    self.execution_state = 'stopping'
                    continue

            except pexpect.TIMEOUT, e:
                if self.execution_state == 'starting':
                    max_time_for_start -= time.time() - now
                    if max_time_for_start < 0:
                        self.execution_state = 'pending to stop'
                    continue

                elif self.execution_state == 'failed':
                    continue

                elif self.execution_state == 'running':
                    self.set_stat_file()
                    fake = self.error_template
                    self.check_result()
                    continue

                elif self.execution_state == 'pending to stop':
                    self.execution_state = 'stopping'
                    _INF('%s %s' % (self.id, self.execution_state))

                    self.stop_traffic()
                    continue

                elif self.execution_state == 'stopping':   
                    max_time_for_shutdown -= time.time() - now
                    if max_time_for_shutdown > 0:
                        continue
                    _WRN('%s %s Max time for stopping expired' % (self.id, self.execution_state))
                    break

                run_error = 'Unhandled timeout %s %s' % (self.id, self.execution_state)
                _ERR(run_error)
                raise ExecutionRunError(run_error)

            except pexpect.EOF, e:
                run_error = 'EOF waiting for %s' % self.id
                _ERR(run_error)
                self.release_monitor()
                raise ExecutionRunError(run_error)

            except KeyboardInterrupt:
                _WRN('User skips wait %s %s' % (self.id, self.execution_state))
                if self.execution_state == 'stopping':
                    max_time_for_shutdown -= time.time() - now
                    if max_time_for_shutdown > 0:
                        continue
                    break
                self.execution_state = 'stopping'
                _INF('%s %s' % (self.id, self.execution_state))

                self.stop_traffic()

                continue

        self.stop_time = datetime.now()
        self.collect_and_clean()
        if self.execution_state != 'failed':
            self.final_result()
            self.generate_result_code_graph()

        self.release()
        _INF('%s end of thread execution in %s state' % (self.id, self.execution_state))

    @property
    def exit_code(self):
        if self.__exit_code == '':

            cmd = 'tail -2 %s/HSSBatTitanSim_*.log' % self.node.working_dir
            try:
                answer = self.node.run_command(cmd, identity='aux')
            except Exception as e:
                _WRN('%s problem executing "%s" %s' % (self.id, cmd, str(e)))
                return self.__exit_code

            if len(answer):
                for line in answer:
                    position = line.find('Exit code')
                    if  position != -1:
                        self.__exit_code = line[position:]
                        self.stop_time = datetime.now()

        return self.__exit_code

    def stop(self):
        if self.node is None: 
            return None

        if self.execution_state in ['starting','running']:
            self.execution_state = 'pending to stop'
            _INF('%s %s' % (self.id, self.execution_state))

    def release_monitor(self):
        pass

    def start_monitor(self):
        pass

    @property
    def error_db_registering(self):
        if self.__error_db[self.traffic_phase]:
            return self.__error_db[self.traffic_phase][-1]['stop'] == ''

        return False

    def error_db_open_register(self, phase = None,timestamp=None):
        if phase is None:
            phase = self.traffic_phase
        if self.monitor_error['enable'][phase]:
            if timestamp is None:
                timestamp = '%s' % datetime.now()
            register ={'start':timestamp[:-7],'stop':'','executed':0,'errors':0}
            self.__error_db[phase].append(register)
            _INF('%s Create a new error rate register at %s' % (self.id, timestamp))

    def error_db_close_register(self,timestamp=None):
        if self.error_db_registering:
            if timestamp is None:
                timestamp = '%s' % datetime.now()
            self.__error_db[self.traffic_phase][-1]['stop'] = timestamp[:-7]
            _INF('%s Close error rate register at %s' % (self.id, timestamp))

    def error_db_update_register(self,executed,errors):
        if self.error_db_registering:
            self.__error_db[self.traffic_phase][-1]['executed'] += executed
            self.__error_db[self.traffic_phase][-1]['errors'] += errors

    def error_db_read_register_counters(self, register=-1):
        executed = 0
        errors = 0
        try:
            if self.__error_db[self.traffic_phase]:
                executed = self.__error_db[self.traffic_phase][register]['executed']
                errors = self.__error_db[self.traffic_phase][register]['errors']
        except KeyError, e:
            _WRN('%s KeyError reading db_read_register_counters: %s' % (self.id, str(e)))
            pass
        return executed, errors

    def error_db_read_register(self, register=-1):
        try:
            if self.__error_db[self.traffic_phase]:
                return self.__error_db[self.traffic_phase][register]
        except KeyError:
            return {}

    def error_db_read_phase_data(self, phase):
        try:
            return self.__error_db[phase]
        except KeyError:
            return []

    def error_db_reset_phase_data(self, phase):
        try:
            self.__error_db[phase] = []
        except KeyError:
            pass

    def error_db_read_db(self):
        try:
            return self.__error_db
        except KeyError:
            return {}

    def collect_and_clean(self):
        if self.need_clean:
            max_tries = 3
            tries = 0
            while self.exit_code == '':
                time.sleep (2.0)
                tries += 1
                if tries >= max_tries:
                    self.__exit_code = 'Success'
                    self.stop_time = datetime.now()
                    break

            self.node.clean_working_dir('%s/' % self.destination_path, backup=['\*'])

            if 'Success' in self.exit_code:
                _INF('%s SUCCESS  %s' % (self.id, self.exit_code))
            else:
                _ERR('%s FAILED   %s' % (self.id, self.exit_code))

        self.need_clean = False
        self.release_monitor()

    def release(self):
        if self.node is None:
            return

        if self.execution_state == 'running':
            self.stop()

        self.node.release()
        self.node = None

    def __str__(self):

        return '%s running on %s' % (self.id, self.host)

    def final_result(self):

        if 'Success' in self.exit_code:
            _INF('SUCCESS   %s %s' % (self.id, self.exit_code))
        else:
            _ERR('FAILED    %s %s' % (self.id, self.exit_code))

    def set_stat_file(self):
        if self.stat_file is None:
            cmd = 'find  %s_LGen_1  -name "*.txt" | grep --color=never "stats_-Measure"' % self.temp_dir
            _INF('%s executing %s' % (self.id, cmd))
            try:
                stdout = self.node.run_command(cmd, identity='aux')
            except Exception as e:
                _WRN('%s problem executing "%s" %s' % (self.id, cmd, str(e)))
                return 

            for line in stdout:
                if 'No such file or directory' in line or line == '""':
                    continue
                if 'stats_-Measure' in line:
                    self.__stat_file = line
                    _INF('%s statistic file %s' % (self.id, self.__stat_file))
                    return

            _WRN('%s statistic file not found' %self.id)

    @property
    def error_template(self):
        if not len(self.__error_template):
            if self.stat_file is None:
                    return self.__error_template

            cmd = 'grep Capture_Started "%s"' % self.stat_file
            try:
                stdout = self.node.run_command(cmd, identity='aux')
            except Exception as e:
                _WRN('%s problem executing "%s" %s' % (self.id, cmd, str(e)))
                return self.__error_template

            for line in stdout:
                if 'Capture_Started' in line:
                    script = line.split('.')[3].split('"')[0]
                    self.__error_template.update({'time' : 0,
                                                  script:{'preexec':{'value':[0,0,0]},
                                                          'loadgen':{'value':[0,0,0]},
                                                          'postexec':{'value':[0,0,0]}}})
        return self.__error_template

    def get_current_stats(self, path = '', local = False):

        if self.stat_file is None:
            return

        if path != '':
            self.__stat_file = os.path.join(path, os.path.basename(self.stat_file))

        if not len(self.error_template):
            return

        cmd = 'tail -%s "%s"' % (((len(self.error_template) -1 ) * 2), self.stat_file)

        if local:
            stdout, stderr, returncode = st_command.execute_cmd(cmd ,stderr = True)
            stdout = stdout.split('\n')
        else:
            try:
                stdout = self.node.run_command(cmd, identity='aux')
            except Exception as e:
                _ERR('%s problem executing "%s" %s' % (self.id, cmd, str(e)))
                self.__current_stats = {}
                return

        if 'cannot open' in ' '.join(stdout):
            _ERR('%s cannot open file %s' % (self.id, self.__stat_file))
            self.__current_stats = {}
            return

        length = len (stdout)

        if 'Capture_Finished' in ' '.join(stdout):
            data = stdout[:length/2]
        else:
            data = stdout[length/2:]
        try:
            phase = self.traffic_phase
            error_sample = self.error_template
            for line in data:
                if len(line) and line.startswith('["Group'):
                    script = line.split('.')[3].split('"')[0]
                    error_sample['time'] = int(line.split(',')[1].split('.')[0])
                    value = line.split(':')[1]
                    error_sample[script]['preexec']['value'] = map(int, value.split()[:3])
                    error_sample[script]['loadgen']['value'] = map(int, value.split()[3:6])
                    error_sample[script]['postexec']['value'] = map(int, value.split()[6:])

                    if error_sample[script]['postexec']['value'][0]:
                        phase = 'postexec'
                    elif phase != 'postexec' and error_sample[script]['loadgen']['value'][0]:
                        phase = 'loadgen'
                    elif phase not in ['postexec','loadgen'] and error_sample[script]['preexec']['value'][0]:
                        phase = 'preexec'

            self.traffic_phase = phase
            self.__current_stats = copy.deepcopy(error_sample)

        except Exception, e:
            _ERR('%s problem parsing file %s %s' % (self.id, self.__stat_file, str(e)))
            self.__current_stats = {}
            return

    def final_result(self):
        output = ''
        message = ''

        self.get_current_stats(path=self.destination_path, local=True)

        for phase in ['preexec', 'loadgen', 'postexec']:
            total_errors = 0
            total_executed = 0

            for key in sorted(self.current_stats.keys()):
                if key == 'time':
                    continue
                errors = self.current_stats[key][phase]['value'][2]
                executed = self.current_stats[key][phase]['value'][0]
                total_errors += errors
                total_executed += executed
                if errors:
                    if executed:
                        percentage = (float(errors) *100) / float(executed)
                    else:
                        percentage = float(0)
                    output += '  %+*.2f %%   %s   (%s/%s)\n' % (20, percentage, key, errors, executed)

            if total_executed:
                total_percentage = (float(total_errors) *100) / float(total_executed)
            else:
                total_percentage = float(0)

            message += '\n\n %+*.2f %%  %-*s  (%s/%s)\n\n' % ( 6, total_percentage, 25,('ErrorRate %s Phase' % phase), total_errors, total_executed) + output
            output =''

        with open(self.traffic_result_file, 'w') as file:
            file.write('%s\n' % message)

        if self.monitor_error['display']:
            print message

        if self.monitor_error['sampling_time']:
            self.create_error_graph()

    def create_gnuplot_file(self, gif = False, final_version=False):
        if final_version:
            gif = False

        return '''set term %s
set title "%s" noenhanced%s
set ylabel "Error Rate"
set datafile separator ","
set xdata time
set timefmt "%%Y-%%m-%%d %%H:%%M:%%S"
set format x "%%m-%%d %%H:%%M:%%S"
set xtics rotate by -45
set key outside
set grid layerdefault
set border 3
plot "%s" using 1:2 title "" with lines lt 2''' % (('gif' if gif else 'x11 font "arial,15,italic"'),
                                                self.id,
                                                ('\nset output "%s"' % self.total_error_rate_gif_file if gif else ''),
                                                (os.path.basename(self.total_error_rate_file) if final_version else  self.total_error_rate_file)) 

    def create_error_graph(self):

        with open(self.total_error_rate_gnuplot_file, 'w') as file:
            file.write(self.create_gnuplot_file(gif=True))
        stdout, stderr, returncode = st_command.execute_cmd('chmod 755 %s' % (self.total_error_rate_gnuplot_file) ,stderr = True)

        cmd = 'gnuplot %s > /dev/null 2>&1' % self.total_error_rate_gnuplot_file
        _INF('%s executing %s' % (self.id,cmd))
        os.system(cmd)

        with open(self.total_error_rate_gnuplot_file, 'w') as file:
            file.write(self.create_gnuplot_file(final_version=True))
        stdout, stderr, returncode = st_command.execute_cmd('chmod 755 %s' % (self.total_error_rate_gnuplot_file) ,stderr = True)

    def check_result(self):

        if self.traffic_phase not in ['preexec','loadgen','postexec']:
            return 

        try:
            if self.monitor_error['enable'][self.traffic_phase]:
                delta_error = self.update_errors_info()
                if delta_error is None:
                    return

                self.handle_error_rate(delta_error)
        except KeyError:
            return

    def update_errors_info(self):
        self.get_current_stats()
        if not len(self.current_stats):
            return

        delta_error={'period_time' : 0,
                     'total_time':0,
                     'preexec':{'scripts':[],'total':{}},
                     'loadgen':{'scripts':[],'total':{}},
                     'postexec':{'scripts':[],'total':{}}
                     }

        if not len(self.current_stats):
            return delta_error

        if self.traffic_phase not in ['preexec','loadgen','postexec']:
            return delta_error

        if not len(self.last_stats):
            self.last_stats = copy.deepcopy(self.error_template)

        total_errors = 0
        total_executed = 0
        for key in self.current_stats.keys():
            if key == 'time':
                continue
            errors = self.current_stats[key][self.traffic_phase]['value'][2] - self.last_stats[key][self.traffic_phase]['value'][2]
            success = self.current_stats[key][self.traffic_phase]['value'][1] - self.last_stats[key][self.traffic_phase]['value'][1]
            executed = errors + success
            total_errors += errors
            total_executed += executed
            if errors:
                percentage = (float(errors) *100) / float(executed)
                try:
                    delta_error[self.traffic_phase]['scripts'] += [{'script':key,'executed':executed,'errors':errors,'percentage':percentage}]
                except KeyError, e:
                    _ERR('%s problem parsing file %s %s' % (self.id, self.stat_file, str(e)))
        try:
            delta_error['total_time'] = self.current_stats['time']
            delta_error['period_time'] = self.current_stats['time'] - self.last_stats['time']
        except KeyError, e:
            _ERR('%s problem parsing file %s %s' % (self.id, self.stat_file, str(e)))

        if delta_error['period_time'] < self.monitor_error['sampling_time']:
            return

        if total_executed:
            percentage = (float(total_errors) *100) / float(total_executed)
            self.error_db_update_register(total_executed,total_errors)
        else:
            percentage = float(0)

        try:
            delta_error[self.traffic_phase]['total'].update({'executed':total_executed,'errors':total_errors,'percentage':percentage})
        except KeyError, e:
            _ERR('%s problem parsing file %s %s' % (self.id, self.stat_file, str(e)))

        self.last_stats = copy.deepcopy(self.current_stats)
        return delta_error

    def handle_error_rate(self, delta_error):
        timestamp = '%s' % datetime.now()
        output_ind = self.handle_ind_error_rate(delta_error)
        output_total = self.handle_total_error_rate(delta_error)

        if len(output_ind):
            message = '''
### Statistics %s   %s  in the last %s seconds : %s
%s
%s
''' % (self.id,self.traffic_phase, delta_error['period_time'],
        timestamp[:-7], 
        output_total,
        output_ind)

            if self.monitor_error['display']:
                print message

            with open(self.monitor_error_rate_file, 'a') as file:
                file.write('%s\n' % message)

    def handle_ind_error_rate(self, delta_error):
        output = ''
        error_found = False
        try:
            script_errors = sorted(delta_error[self.traffic_phase]['scripts'], key=operator.itemgetter('script'))
            for script in script_errors:
                if script['errors']:
                    error_found = True
                    output += '\n        %+*s    %+*.2f %%   %s' % (10,script['errors'],
                                                                     7, script['percentage'],script['script'])
        except KeyError:
            return ''

        if error_found:
            message = '''
    INDIV.  ERRORS   ERROR RATE   SCRIPT NAME
%s
''' % output

            return message

        return ''

    def handle_total_error_rate(self, delta_error):
        output = ''
        message = ''
        try:
            total_errors = delta_error[self.traffic_phase]['total']
            if total_errors['errors']:
                output += '\n        %+*s    %+*.2f %%' % (10,total_errors['errors'],
                                                      7, total_errors['percentage'])
                message= '''
    TOTAL   ERRORS   ERROR RATE
 %s
''' % output

        except KeyError:
            return ''

        timestamp = '%s' % datetime.now()
        with open('%s' % self.total_error_rate_file, 'a') as file:
            file.write('%s,%s\n' % (timestamp[:-7],delta_error[self.traffic_phase]['total']['percentage']))

        return message

    def find_files(self, filename, path = None):
        file_list = []
        cmd = 'find  %s -name "%s"' % ((self.destination_path if path is None else path) , filename)
        _INF('%s executing %s' % (self.id,cmd))

        stdout, stderr, returncode = st_command.execute_cmd(cmd ,stderr = True)
        stdout = stdout.split('\n')
        for line in stdout:
            file_list.append(os.path.basename(line))
        return file_list


    def generate_result_code_graph(self):
        files = self.find_files('result_codes_absolute*')

        for filename in files:
            if filename != '':
                self.create_gif(filename, percentage = False)

        files = self.find_files('result_codes_percentage*')

        for filename in files:
            if filename != '':
                self.create_gif(filename)


    def create_gif(self, full_filename, percentage = True):

        filename = '_'.join(full_filename.split('_')[2:-1])
        output_gnuplot = '''set term gif
set title "%(name)s" noenhanced
set output "%(name)s.gif"
set key outside
set ylabel "%(ylabel)s"
set xlabel "Time (s)"
set grid layerdefault
set border 3
plot "%(fname)s" using 1:2 title "Success" noenhanced with lines lt 2, "%(fname)s" using 1:3 title "UnableToComply" noenhanced with lines lt 7, "%(fname)s" using 1:4 title "TooBusy" noenhanced with lines lt 1, "%(fname)s" using 1:5 title "Other" noenhanced with lines lt 8%(req)s

''' % {'name':filename,
       'fname':full_filename,
       'ylabel':('Result Code (%)' if percentage else 'Result Code - Request'),
       'req':('' if percentage else ', "%s" using 1:6 title "Request" noenhanced with lines lt 3' % full_filename)}

        with open('%s.cmd' % os.path.join(self.destination_path,filename), 'w') as file:
            file.write('%s\n' % output_gnuplot)

        cwd = os.getcwd()
        cmd = 'cd %s;gnuplot %s.cmd;cd %s' % (self.destination_path, filename,cwd)
        _INF('%s executing %s' % (self.id,cmd))
        os.system(cmd)

class BAT(BAT_base):
    def __init__(self, host, cabinet, config , id, instance, root_path, exec_config, executor,disable_graph=False):

        BAT_base.__init__(self, host, cabinet, config , id, instance, root_path, exec_config, executor,disable_graph=disable_graph)

    @property
    def cmd(self):
        return 'run_titansim_HSS_BAT -V %s %s %s --force-tmp %s --mc-port %s --dia-port-offset %s %s' % (self.cabinet,
                                                                                    self.update_parameters,
                                                                                    self.disable_graph,
                                                                                    self.temp_dir,
                                                                                    self.mc_port,
                                                                                    (100 * int(self.instance)),
                                                                                    self.access_params)


    def stop_traffic(self):
        if self.execution_state == 'stopped':
            return
        self.channel.write_line(chr(3))
