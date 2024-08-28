#!/usr/bin/env python
#

import sys
import os
import os.path
import time
import filecmp
import signal
import re
from datetime import datetime
from numpy import mean, absolute, std

import hss_utils.st_command as st_command
import hss_utils.connection as connection

import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning

from HSS_rtc_lib.shared import *
from . import bat_instance
from . import steps
from . import phases
from . import SkipPhase
from . import ExitRtc
from . import StopTestCaseOnFail

def traffic_type(traffic):
    if traffic == 'ESM':
        return 'EPC'
    elif traffic == 'ISMSDA':
        return 'IMS'
    else:
        return traffic


class CHECK(phases.Phase):

    def __init__(self, config , user_config, rtc_data):

        phases.Phase.__init__(self, config , 'CHECK', user_config, rtc_data)
 
    def run(self):
        if self.config['enable']:
            _INF('')
            _INF('Start %s phase' % self.id )
            if not os.path.exists(self.working_path):
                os.makedirs(self.working_path)

            for step in self.config['steps']:
                if self.rtc_data.exit_test_case:
                    _WRN('%s Exit from Test case order has been received' % self.id)
                    break

                try:
                    enable = step["enable"]
                    if isinstance(enable,str) or isinstance(enable,unicode):
                        enable = self.rtc_data.get_macro_value(enable)
                        enable = (enable == 'true')
                except KeyError:
                    _WRN('Missing "enable" field in step definition')
                    continue

                if enable:
                    action = steps.Step(step, self.user_config, self.id, self.working_path,self.rtc_data)
                    if action.step_type == 'external':
                        _INF('')
                        action.run()
                        _INF('')
                        result = (action.returncode == 0)
                        error_info = action.error_info
                        if action.add_to_summary:
                            info_type = 'error' if action.returncode else 'info'
                            self.summary.add_to_report(info_type,'')
                            self.summary.add_to_report(info_type,'CHECK User step:  %s' % action.id)
                            self.summary.add_to_report(info_type,'            cmd:  %s' % action.cmd)
                            self.summary.add_to_report(info_type,'         output:')
                            if action.stdout:
                                for line in action.stdout.splitlines():
                                    self.summary.add_to_report(info_type,'                  %s' % line)
                            else:
                                self.summary.add_to_report(info_type,'                  No info provided in stdout by user step')
                            self.summary.add_to_report(info_type,'')

                    else:
                        result,error_info = eval('self.%s' % action.run())

                    if not result:
                        if action.add_to_verdict or action.stop_on_fail or action.exit_rtc_on_fail or action.report_not_valid:
                            self.rtc_data.update_verdict(result,error_info=error_info,repeat=action.repeat)

                        if action.report_not_valid:
                            self.rtc_data.set_test_suite_execution_status('FAILED')

                        if action.exit_rtc_on_fail:
                            raise ExitRtc('configured in %s at CHECK phase' % step['id'])

                        if action.stop_on_fail:
                            raise StopTestCaseOnFail('configured in %s at CHECK phase' % step['id'])

                        if action.skip_phase_on_fail:
                            raise SkipPhase('configured in %s at CHECK phase' % step['id'])

    def compare_output_files(self, step, slogan):
        result = True
        error_info = ''
        file_in_pre = os.path.join(self.rtc_data.root_path, 'PRE', '%s.data' % step)
        file_in_post = os.path.join(self.rtc_data.root_path, 'POST', '%s.data' % step)

        try:
            if filecmp.cmp(file_in_pre, file_in_post):
                self.summary.add_to_report('info','Check %-*s:  SUCCESS' % (30, slogan))
                result = True
            else:
                self.summary.add_to_report('error','Check %-*s:  FAILED %s and %s are not equal' % (30, slogan, file_in_pre, file_in_post))
                result = False
                error_info = 'CHECK %s: %s and %s are not equal'  % (step, file_in_pre, file_in_post)

        except Exception, e:
            self.summary.add_to_report('warning','Check %-*s:  UNDEFINED Check that %s and %s exist' % (30, slogan, file_in_pre, file_in_post))
            result = False
            error_info = 'CHECK %s: %s '  % (step, str(e))

        return result,error_info


    def check_list_processes(self,gap_processes=""):
        gap_processes = gap_processes.split()
        _DEB ('Check list processes with "%s" as processes to ignore' % gap_processes)
        result = True
        error_info = ''
        slogan = 'list_processes'
        try:
            with open(os.path.join(self.rtc_data.root_path, 'PRE', 'get_processes_list.data')) as f:
                list_processes_pre = f.readlines()
            list_processes_pre = [x.strip() for x in list_processes_pre]

        except IOError as e:
            error_info = 'Check %-*s:  FAILED %s ' % (30, slogan, str(e))
            self.summary.add_to_report('error',error_info)
            return False,error_info

        try:
            with open(os.path.join(self.rtc_data.root_path, 'POST', 'get_processes_list.data')) as f:
                list_processes_post = f.readlines()
            list_processes_post = [x.strip() for x in list_processes_post]

        except IOError as e:
            error_info = 'Check %-*s:  FAILED %s ' % (30, slogan, str(e))
            self.summary.add_to_report('error',error_info)
            return False,error_info

        real_gap = st_command.diff_list(list_processes_pre, list_processes_post)
        real_gap = [x for x in real_gap if x]
        faulty_processes = st_command.diff_list(real_gap, gap_processes)
        if faulty_processes:
            error_info = 'Check %-*s:  FAILED %s ' % ((30, slogan, ' '.join(faulty_processes)))
            self.summary.add_to_report('error',error_info)
            result = False

        if result:
            self.summary.add_to_report('info','Check %-*s:  SUCCESS' % (30, slogan))

        return result,error_info


    def check_pods_restarts(self):
        result = True
        restarts = {}
        error_info = ''
        slogan = 'pods_restart'
        try:
            with open(os.path.join(self.rtc_data.root_path, 'PRE', 'get_pods_info.data')) as f:
                pods_info_pre = f.readlines()

        except IOError as e:
            error_info = 'Check %-*s:  FAILED %s ' % (30, slogan, str(e))
            self.summary.add_to_report('error',error_info)
            return False,error_info

        try:
            with open(os.path.join(self.rtc_data.root_path, 'POST', 'get_pods_info.data')) as f:
                pods_info_post = f.readlines()

        except IOError as e:
            error_info = 'Check %-*s:  FAILED %s ' % (30, slogan, str(e))
            self.summary.add_to_report('error',error_info)
            return False,error_info

        for pod in pods_info_pre:
            pod = pod.split()
            if len(pod) > 4:
                restarts.update({pod[1]:{'value_pre':pod[4],'value_post':''}})

        for pod in pods_info_post:
            pod = pod.split()
            if len(pod) > 4:
                try:
                    restarts[pod[1]]['value_post'] = pod[4]
                except KeyError:
                    restarts.update({pod[1]:{'value_post':pod[4],'value_pre':''}})

        error_info = ''
        report_success = True

        for key, value in restarts.iteritems():
            if value['value_post'] != value['value_pre']:
                report_success = False
                break

        if report_success:
            self.summary.add_to_report('info','Check %-*s:  SUCCESS' % (30, slogan))
            return result,error_info


        error_info = 'Check %-*s:  FAILED'% (30, slogan)
        self.summary.add_to_report('error',error_info)

        self.summary.add_to_report('error','%-*s%-*s Delta Restarts '% (39, ' ',60,'Pod'))

        keys = st_command.sorted_nicely(restarts.keys())

        for key in keys:
            value = restarts[key]
            if value['value_pre'] == '':
                self.summary.add_to_report('error','%-*s %-*s MISSING in PRE' % (38,' ',60,key))
                continue

            if value['value_post'] == '':
                self.summary.add_to_report('error','%-*s %-*s MISSING in POST' % (38,' ',60,key))
                continue

            if value['value_post'] != value['value_pre']:
                data = int(value['value_post']) - int(value['value_pre'])
                self.summary.add_to_report('error','%-*s %-*s %s' % (38,' ',60,key,data))


        self.summary.add_to_report('info','')
        return result,error_info


    def check_free_memory(self):
        result = True
        error_info = ''
        memory_info = {}

        slogan = 'free_memory'
        try:
            with open(os.path.join(self.rtc_data.root_path, 'PRE', 'get_free_memory.data')) as f:
                info = f.readlines()
        except IOError as e:
            error_info = 'Check %-*s:  FAILED %s ' % (30, slogan, str(e))
            self.summary.add_to_report('error',error_info)
            return False,error_info

        try:
            for line in info:
                if 'MEMORY' in line:
                    continue
                memory_info.update({line.split()[0]:{'value_pre':float(line.split()[1]),'value_post':float(0)}})
        except Exception as e:
            error_info = 'Check %-*s:  FAILED %s ' % (30, slogan, str(e))
            self.summary.add_to_report('error',error_info)
            return False,error_info

        try:
            with open(os.path.join(self.rtc_data.root_path, 'POST', 'get_free_memory.data')) as f:
                info = f.readlines()
        except IOError as e:
            error_info = 'Check %-*s:  FAILED %s ' % (30, slogan, str(e))
            self.summary.add_to_report('error',error_info)
            return False,error_info

        try:
            for line in info:
                if 'MEMORY' in line:
                    continue
                try:
                    memory_info[line.split()[0]]['value_post'] = float(line.split()[1])
                except KeyError:
                    memory_info.update({line.split()[0]:{'value_post':float(line.split()[1]),'value_pre':float(0)}})

        except Exception as e:
            error_info = 'Check %-*s:  FAILED %s ' % (30, slogan, str(e))
            self.summary.add_to_report('error',error_info)
            return False,error_info

        error_info = ''
        report_success = True
        for key, value in memory_info.iteritems():
            if value['value_post'] != value['value_pre']:
                report_success = False
                break

        if report_success:
            self.summary.add_to_report('info','Check %-*s:  SUCCESS' % (30, slogan))
            return result,error_info


        error_info = 'Check %-*s:  FAILED'% (30, slogan)
        self.summary.add_to_report('error',error_info)

        self.summary.add_to_report('error','%-*sProc.\tDecrement %%'% (39, ' '))

        keys = st_command.sorted_nicely(memory_info.keys())

        for key in keys:
            value = memory_info[key]
            if value['value_pre'] == 0.0:
                self.summary.add_to_report('error','%-*s %s\tMISSING in PRE' % (38,' ',key))
                continue

            if value['value_post'] == 0.0:
                self.summary.add_to_report('error','%-*s %s\tMISSING in POST' % (38,' ',key))
                continue

            if value['value_post'] != value['value_pre']:
                data = float(((value['value_pre'] - value['value_post']) / value['value_pre']) * 100)
                self.summary.add_to_report('error','%-*s %s\t%.2f' % (38,' ',key, data))


        self.summary.add_to_report('info','')
        return result,error_info



    def find_traffic_log_dir(self):
        cmd = 'find  %s -name "*.txt" | grep --color=never "stats_-Measure"' % os.path.join(self.rtc_data.root_path, 'EXECUTION')
        stdout_value, stderr_value, returncode = st_command.execute_cmd(cmd,stdout= True,stderr = True)

        if returncode == 0:
            traffic_folders = []
            for line in stdout_value.split('\n')[:-1]:
                traffic_type = os.path.basename(line).split('.')[0]
                traffic_folders.append((traffic_type, os.path.dirname(line)))

            return traffic_folders

    def check_traffic_result(self, max_error_rate=0.1):
        result = True
        error_info = ''
        bat_instances = self.find_traffic_log_dir()
        if bat_instances is not None:
            for index, instance in enumerate(bat_instances):
                self.summary.add_to_report('info', ' ')
                self.summary.add_to_report('info', 'Check BAT Instance %s' % (index +1))
                tmp_result = self.check_bat_instance_result(instance, max_error_rate)
                result &= tmp_result
                if not tmp_result:
                    (traffic, logdir) = instance
                    error_info += 'CHECK traffic_result: %s error rate higher than %s.;' % (logdir.split('/')[-1],max_error_rate)

        return result, error_info


    def check_bat_instance_result(self, (traffic, logdir),max_error_rate):
        cmd = 'grep run_titansim_HSS_BAT %s/HSSBatTitanSim_*.log' % logdir
        stdout_value, stderr_value, returncode = st_command.execute_cmd(cmd,stdout= True,stderr = True)

        if len(stdout_value.split('\n'))> 2:
            _DEB('executin cmd %s result %s ' % (cmd, repr(stdout_value)))
            self.summary.add_to_report('error','   Traffic result can not analyzed')
            self.summary.add_to_report('error','   It seems that there are logs for 2 or more run_titansim_HSS_BAT instances in %s' % logdir)

            return False

        self.summary.add_to_report('info', '   Traffic Type:    %s' % traffic_type(traffic))
        self.summary.add_to_report('info', '   Log Directory:   %s' % logdir)

        if returncode == 0:
            position = stdout_value.find('run_titansim_HSS_BAT')
            command = stdout_value[position:-2]
            self.summary.add_to_report('info', '   Command:         %s' % command)

            if ('.log:') in stdout_value:
                position = stdout_value.find('.log:')
                stdout_value = stdout_value[position+5:]

            timestamp = st_command.clear_ansi(stdout_value).split('<')[1].split('>')[0]
            self.summary.add_to_report('info', '   Started at:      %s' % timestamp)


        cmd = 'cat %s/*traffic_result.data' % logdir
        stdout_value, stderr_value, returncode = st_command.execute_cmd(cmd,stdout= True,stderr = True)

        self.summary.add_to_report('info','')

        self.summary.add_to_report('info', '   Error Rate:')
        ind_found = False
        phase = None
        result = True
        for line in stdout_value.split('\n')[:-1]:
            if 'ErrorRate' in line:
                rate = float(line.strip().split()[0][1:])
                if rate > float(max_error_rate):
                    result &= False
                    self.summary.add_to_report('info','')
                    self.summary.add_to_report('error', '      %s' % line[1:])
                    self.summary.add_to_report('info','')
                else:
                    self.summary.add_to_report('info','')
                    self.summary.add_to_report('info', '      %s' % line[1:])
                    self.summary.add_to_report('info','')

                phase = line.split()[3]

            elif len(line) and phase is not None:
                rate = float(line.strip().split()[0][1:])
                if rate >= 1.0:
                    self.summary.add_to_report('error', '   %s' % line[1:])

        self.summary.add_to_report('info','')
        cmd = 'grep NEXP %s/*.data' % logdir
        stdout_value, stderr_value, returncode = st_command.execute_cmd(cmd,stdout= True,stderr = True)

        if returncode == 0:
            nexp_found = False
            for line in stdout_value.split('\n')[:-1]:
                if ':' not in line:
                    continue

                searchObj = re.findall(r'\D(\d+)\D',line.split(':')[1])
                if len(searchObj):
                    rate = int(searchObj[0])
                    if rate:
                        if  not nexp_found:
                            result &= False
                            self.summary.add_to_report('error', '   NEXP Outgoing Req.:   FAILED')
                            nexp_found = True

                        self.summary.add_to_report('error', '       %s' % '  '.join(line.split()[:-1]))

            if not nexp_found:
                self.summary.add_to_report('info', '   NEXP Outgoing Req.:   SUCCESS' )

        else:
            self.summary.add_to_report('info', '   NEXP Outgoing Req.:   UNDEFINED. Data file not found')

        return result

    def get_latency_data_info(self):
        file_list = []
        sample_data = {}
        cmd = 'find %s -name "latency*.data"' % self.rtc_data.root_path
        stdout_value, stderr_value, returncode = st_command.execute_cmd(cmd,stdout= True,stderr = True)

        if returncode == 0:
            for line in stdout_value.split('\n')[:-1]:
                file_list.append(line)
            for element in file_list:
                key = element.split('_')[-1].split('.')[0]
                if int(key) in self.rtc_data.faulty_latency_reports:
                    _DEB ('%s Latency sample %s discarded' % (self.id, key))
                    continue
                try:
                    sample_data[key]['data_file'] += [element]
                except KeyError:
                    sample_data.update({key:{'data_file':[element]}})

            return sample_data

    def check_epm(self,id='EPM',tolerance=2):
        current_epm = {'id':id}
        self.summary.add_to_report('info','')
        self.summary.add_to_report('info', 'EPM report')
        self.summary.add_to_report('info','')
        if not self.rtc_data.epm_enabled:
            self.summary.add_to_report('error', '   Latency not enabled in diaproxy_reports json file field')
            return False, 'CHECK EPM: Latency not enabled in diaproxy_reports json file field'

        result = True
        error_info = ''
        cmd_code_latency = {}
        faulty_samples = []
        sample_data = self.get_latency_data_info()
        if len(sample_data) != self.rtc_data.epm_samples:
            error_info = '  Only %s of %s required samples'% (len(sample_data),self.rtc_data.epm_samples )
            self.summary.add_to_report('error', error_info)
            return False, 'CHECK EPM:%s' % error_info

        for key, value in sample_data.iteritems():
            lines = []
            for data_file in value['data_file']:
                lines += [line.rstrip('\n') for line in open(data_file)]
            time_start = None
            time_stop = None
            tps = 0
            counter = 0
            period = 0
            for line in lines:
                if line == '':
                    continue
                if line.split()[0] in ['SessionId']:
                    continue

                if line.split()[0] == 'Start':
                    timestamp =' '.join(line.split()[3:])
                    time_start = datetime.strptime(timestamp,"%a %b %d %H:%M:%S %Y")
                    continue

                if line.split()[0] == 'Stop':
                    timestamp =' '.join(line.split()[3:])
                    time_stop = datetime.strptime(timestamp,"%a %b %d %H:%M:%S %Y")
                    period = (time_stop-time_start).total_seconds()
                    if period:
                        tps += counter/period
                    counter = 0
                    continue

                if len(line.split()) != 3:
                    continue

                counter += 1
                try:
                    cmd_code = line.split()[1]
                    latency = float(line.split()[2])
                    cmd_code_latency[cmd_code].append(latency)
                except KeyError:
                    cmd_code_latency.update({cmd_code:[latency]})

            if period and tps:
                value.update({'tps':int(tps)})
            else:
                faulty_samples.append(key)

        for k in faulty_samples:
            sample_data.pop(k, None)

        single_tps = []
        samples_ok = []
        data_files = []
        for key, value in sample_data.iteritems():
            samples_ok.append(key)
            data_files += value['data_file']
            single_tps.append(int(value['tps']))

        self.summary.add_to_report('info','   Latency samples used')
        for data_file in data_files:
            self.summary.add_to_report('info','       %s' % data_file)

        self.summary.add_to_report('info','')
        self.summary.add_to_report('info','   Latency samples discarded')
        for sample in sorted(self.rtc_data.faulty_latency_reports):
            self.summary.add_to_report('info','       latency_*_%s.data' % sample)

        ref_name, ref_data = self.rtc_data.get_last_epm(identity=id)

        if single_tps:
            self.summary.add_to_report('info','')
            self.summary.add_to_report('info', '   Current Measurements')
            self.summary.add_to_report('info','')
            tps_average = float(sum(single_tps))/len(single_tps)
            performance = tps_average/float(self.rtc_data.nof_payloads)/float(self.rtc_data.epm['target_load'])
            current_epm.update({'single_tps':single_tps,'tps_average':tps_average,'performance':performance})

            if self.rtc_data.epm['target_load'] != -1:
                self.summary.add_to_report('info', '    (A) Target Load              : %s '% self.rtc_data.epm['target_load'])
                self.summary.add_to_report('info', '    (B) Number of Payloads       : %s '% self.rtc_data.nof_payloads)
            self.summary.add_to_report('info', '        Diameter TPS list        : %s '% '  '.join(str(e) for e in single_tps))
            self.summary.add_to_report('info', '    (C) Diameter TPS average     : %.2f '% tps_average)
            if self.rtc_data.epm['target_load'] != -1:
                self.summary.add_to_report('info', '        Performance  C/B/A       : %.2f '% performance)


            if ref_data:
                self.summary.add_to_report('info','')
                self.summary.add_to_report('info', '   Comparison with reference %s' % ref_name)
                self.summary.add_to_report('info','')
                delta = float(tps_average-ref_data['tps_average']) * 100 / float(ref_data['tps_average'])
                self.summary.add_to_report('info', '        TPS average Ref. value   : %.2f'% ref_data['tps_average'])

                if self.rtc_data.epm['target_load'] != -1:
                    if abs(delta) > float(tolerance):
                        result = False
                        self.summary.add_to_report('error', '        TPS Delta                : %.2f '% delta)
                        error_info = 'CHECK EPM:  TPS Delta  %.2f higher than %.2f'% (delta, tolerance)
                    else:
                        self.summary.add_to_report('info', '        TPS Delta                : %.2f '% delta)

                    delta = float(performance-ref_data['performance']) * 100 / float(ref_data['performance'])
                    self.summary.add_to_report('info', '        Performance Ref. value   : %.2f'% ref_data['performance'])

                    if abs(delta) > float(tolerance):
                        result = False
                        self.summary.add_to_report('error', '        Performance Delta        : %.2f '% delta)
                        error_info = 'CHECK EPM:  Performance Delta  %.2f higher than %.2f'% (delta, tolerance)
                    else:
                        self.summary.add_to_report('info', '        Performance Delta        : %.2f '% delta)

            self.summary.add_to_report('info','')

        if cmd_code_latency:
            self.summary.add_to_report('info','')
            self.summary.add_to_report('info', '   Latency report')
            self.summary.add_to_report('info','')
            if ref_data is None:
                prev_avg = ''
                prev_std_desv = ''
                prev_avg_desv = ''
            else:
                prev_avg =      '   Avg Ref.(%s)' % ref_data['target_load']
                prev_std_desv = '   Std Dev Ref.(%s)' % ref_data['target_load']
                prev_avg_desv = '   Avg Dev Ref.(%s)' % ref_data['target_load']

            self.summary.add_to_report('info', '       Cmd code   Avg Current(%s)%s   Std Dev Current(%s)%s   Avg Dev Current(%s)%s' % (self.rtc_data.epm['target_load'],
                                                                                                                                        prev_avg,
                                                                                                                                        self.rtc_data.epm['target_load'],
                                                                                                                                        prev_std_desv,
                                                                                                                                        self.rtc_data.epm['target_load'],
                                                                                                                                        prev_avg_desv))

            latency = {}
            for key, value in cmd_code_latency.iteritems():
                avg = mean(value)
                std_desv = std(value)
                avg_desv = mean(absolute(value - avg)) 

                latency.update({key:{'avg':avg}})
                latency[key].update({'std_desv':std_desv})
                latency[key].update({'avg_desv':avg_desv})
                if ref_data is None:
                    prev_avg = ''
                    prev_std_desv = ''
                    prev_avg_desv = ''
                else:
                    prev_avg =      ' %+*.2f ms' % (12, ref_data['latency'][key]['avg'])
                    prev_std_desv = ' %+*.2f ms' % (16, ref_data['latency'][key]['std_desv'])
                    prev_avg_desv = ' %+*.2f ms' % (16, ref_data['latency'][key]['avg_desv'])

                self.summary.add_to_report('info', '%14s   %+*.2f ms%s   %+*.2f ms%s   %+*.2f ms%s' % (key, 14, avg, prev_avg,
                                                                                                                18, std_desv, prev_std_desv,
                                                                                                                18, avg_desv, prev_avg_desv))

            current_epm.update({'latency':latency})

        self.rtc_data.update_epm(current_epm)
        return result, error_info

    def check_load_stability(self):
        if self.rtc_data.scenario_load_monitor is None:
            self.summary.add_to_report('error', '')
            self.summary.add_to_report('error', 'monitor_load not enabled in json file')
            self.summary.add_to_report('error', '')
            return False, 'CHECK load_stability: monitor_load not enabled in json file'

        result = True
        error_info = ''
        registers = self.rtc_data.scenario_load_monitor.failed_registers()
        self.summary.add_to_report('info','')
        if registers:
            result = False
            error_info = 'CHECK load_stability: %s registers are NOT STABLE' % len(registers)
            self.summary.add_to_report('error', '')
            self.summary.add_to_report('error', 'Load Stability  FAILED')
            for register in registers:
                self.summary.add_to_report('error', '\t%s' % register)
            self.summary.add_to_report('error', '')
        else:
            self.summary.add_to_report('info','')
            self.summary.add_to_report('info', 'Load Stability  SUCCESS')
            self.summary.add_to_report('info','')

        return result, error_info 


    def check_scenario_error_rate(self):
        if self.rtc_data.scenario_error_rate_monitor is None:
            self.summary.add_to_report('error', '')
            self.summary.add_to_report('error', 'monitor_error not enabled in json file')
            self.summary.add_to_report('error', '')
            return False, 'CHECK scenario_error_rate: monitor_error not enabled in json file'

        result = True
        error_info = ''
        registers = self.rtc_data.scenario_error_rate_monitor.failed_registers()
        self.summary.add_to_report('info','')
        if registers:
            result = False
            error_info = 'CHECK scenario_error_rate: %s registers are higher than limit' % len(registers)
            self.summary.add_to_report('error', '')
            self.summary.add_to_report('error', 'Scenario Error rate   FAILED')
            for register in registers:
                self.summary.add_to_report('error', '\t%s' % register)
            self.summary.add_to_report('error', '')
        else:
            self.summary.add_to_report('info','')
            self.summary.add_to_report('info', 'Scenario Error rate   SUCCESS')
            self.summary.add_to_report('info','')

        return result, error_info 

