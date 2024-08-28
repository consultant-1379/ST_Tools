#!/usr/bin/env python
#

import sys
import os
CWD = os.getcwd()
import os.path
import time
import shutil
import hashlib
import tempfile
import socket
HOSTNAME = socket.gethostname()
import traceback
import argparse
import re
import copy

import ntpath
import signal
import textwrap
from datetime import datetime

import hss_utils.st_command as st_command
import hss_utils.connection as connection
import hss_utils.node
import hss_utils.node.cba

import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning

def quit_gracefully(*args):
    raise KeyboardInterrupt("Signal handler")

class ClissError(Exception):
    def __init__(self, error_code):
        self.__err = error_code

    def __str__(self):
        return 'Cliss error: %s' % self.__err

class ClissConditionCheckFailed(Exception):
    def __init__(self, error_code):
        self.__err = error_code

    def __str__(self):
        return 'Cliss condition check failed: %s' % self.__err

class clissConnection(object):
    def __init__(self, node, user):

        self.__host = node.config['host']
        self.__user = user
        self.__node = node
        self.__connection = None


    def connect(self):
        if self.__connection is None:
            self.__connection = self.__node.start_CBACliss(self.__host, identity=self.__user, user=self.__user)

    def disconnect(self):
        if self.__connection is not None:
            self.__node.release_connection(identity=self.__user)
            self.__connection = None

    @property
    def conId(self):
        return self.__user

    def update_parameters(self, parameters):

        self.connect()
        cmd = 'configure'
        self.run_command(cmd)

        for parameter in parameters:
            clissDn = parameter['clissDn']
            data = parameter['data']
            try:
                child_key = parameter['child']['keyname']
                child_list = parameter['child']['keyvalue']
                if len(child_list) == 0:
                    child_list = self.search(clissDn,child_key, disconnect=False)

                for child in child_list:
                    self.modify('%s,%s=%s' % (clissDn,child_key,child),data)
            except KeyError:
                self.modify(clissDn,data)

        cmd = 'commit'
        self.run_command(cmd)

        self.disconnect()

    def run_command(self,cmd):
        _INF('%s' % cmd)
        answer = self.__node.run_command(cmd, identity = self.conId, full_answer=True)
        if 'ERROR' in answer:
            raise ClissError(st_command.clear_ansi(answer))

        return answer

    def modify(self,clissDn,data):
        cmd = '%s' % clissDn
        self.run_command(cmd)

        for parameter in data:
            cmd = '%s=%s' % (parameter['name'],parameter['value']) 
            self.run_command(cmd)

    def search(self,clissDn, attr, disconnect=True):
        self.connect()
        value = []
        cmd = 'show -v %s' % clissDn
        answer = self.run_command(cmd)
        data = self.__node.fill_from_cliss_info([attr], answer)
        if not len(data[attr]):
            raise ClissError('%s not found' % attr)

        value = data[attr]

        if disconnect:
            self.disconnect()
        return value




class TestCaseError(Exception):
    def __init__(self, error_code):
        self.__err = error_code

    def __str__(self):
        return 'Test Case error: %s' % self.__err

class TestCaseConfigurationError(Exception):
    def __init__(self, error_code='HSS_rtc not found'):
        self.__err = error_code

    def __str__(self):
        return '%s' % self.__err


class AlarmLogHandler(hss_utils.node.cba.AlarmLogEventHandlerBaseCBA):
    def __init__(self, access_config):
        hss_utils.node.cba.AlarmLogEventHandlerBaseCBA.__init__(self, access_config)

    def log_event(self, event_info):
        _INF('%s' % event_info)


class CBA_TestCaseBase(object):
    def __init__(self, access_config,stand_alone=False):

        if not stand_alone:
            self.check_HSS_rtc_running()
        self.__stand_alone = stand_alone
        self.__id = 'BASE_TEST_CASE'
        self.__access_config = access_config
        self.__alarm_filters = []
        self.__node = None
        self.__channel = None
        self.__alarm_monitor = AlarmLogHandler(self.__access_config)
        self.__processor_DIA_CFG ={}
        self.__configured_ExtDb_connections = -1
        self.__expected_alarms_list = []
        self.__first_error = None
        self.__AandA_changed = False
        self.__use_root_access = True


    def check_HSS_rtc_running(self):
        answer = st_command.send_udp_command('who_are_you', HOSTNAME, 5000, timeout=4.0)
        if answer is None or 'HSS_rtc' not in answer:
            raise TestCaseConfigurationError()

    def send_test_case_info(self, info):
        if self.__stand_alone:
            return
        answer = st_command.send_udp_command('add_info_to_summary %s' % info, HOSTNAME, 5000, timeout=4.0)
        if not answer:
            _WRN('No answer received for "add_info_to_summary %s"' % info)
        elif answer != 'OK':
            _WRN('Answer received for add_info_to_summary: "%s"' % answer)


    def wait_scenario_stable(self, timeout):
        timeout = float(timeout)
        started = time.time()
        while True:
            now = time.time()
            cmd = 'start_scenario_stable_check'
            answer = st_command.send_udp_command(cmd, HOSTNAME, 5000, timeout=10.0)
            if answer is None:
                raise TestCaseError('No answer from HSS_rtc for "%s"' % cmd)

            if 'NOT CONFIGURED' in answer:
                _INF('scenario stability check not configured')
                return

            time.sleep(float(60))
            cmd = 'stop_scenario_stable_check'
            answer = st_command.send_udp_command(cmd, HOSTNAME, 5000, timeout=4.0)
            if answer is None:
                raise TestCaseError('No answer from HSS_rtc for "%s"' % cmd)

            _INF('Answer from HSS_rtc for "%s": %s'% (cmd, answer))
            if 'OK' in answer:
                 return

            timeout -= time.time() - now
            if timeout < float(0):
                raise TestCaseError('Timeout waiting for scenario STABLE')


    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, id):
        self.__id = id

    @property
    def first_error(self):
        return self.__first_error

    @first_error.setter
    def first_error(self, first_error):
        if self.__first_error is None:
            self.__first_error = first_error

    @property
    def node(self):
        return self.__node

    @property
    def processor_DIA_CFG(self):
        return self.__processor_DIA_CFG

    @property
    def alarm_monitor(self):
        return self.__alarm_monitor

    @property
    def alarm_filters(self):
        return self.__alarm_filters

    @property
    def allowed_alarm_filters(self):
        return ['activeSeverity','eventType','lastEventTime','source',
                'specificProblem','additionalText','originalAdditionalText']

    def connect_to_node(self, force_primary=True):
        self.__node = hss_utils.node.cba.Cba(config = self.__access_config, force_primary=force_primary)
        self.__channel = self.__node.get_channel()

    def change_connection_to_node(self,access_config, open_connection=True):
        self.release_node()
        self.__access_config = access_config
        self.__node = hss_utils.node.cba.Cba(config = self.__access_config)
        self.__channel = self.__node.get_channel()
        if open_connection:
            self.connect_to_node()

    @property
    def channel(self):
        return self.__channel

    @property
    def sync_expression(self):
        return self.node.get_sync_expression()

    def release_node(self):
        self.node.release()

    def download(self,source, destination, identity= 'main', timeout = None):
        return self.node.download(source, destination, identity, timeout)

    def upload(self,source, destination, identity= 'main', timeout = None):
        return self.node.upload(source, destination, identity, timeout)

    @property
    def AandA_enabled(self):
        return self.node.is_AandA_enabled()

    @property
    def use_root_access(self):
        return self.__use_root_access

    @property
    def AandA_changed(self):
        return self.__AandA_changed

    def disable_AandA(self):
        self.node.disable_AandA()
        self.node.release_connection(identity='cliss_emergency')
        time.sleep(30.0)
        self.__AandA_changed = True
        self.__use_root_access = True

    def enable_AandA(self):
        self.node.enable_AandA()
        self.node.release_connection(identity='cliss_emergency')
        time.sleep(30.0)
        self.__AandA_changed = False
        self.__use_root_access = False

    def start_alarm_monitoring(self):
        self.alarm_monitor.start_handling()

    def stop_alarm_monitoring(self):
        self.alarm_monitor.shutdown()

    def quit_test_case(self,exit_code,message=''):

        if self.node is not None:
            try:
                self.node.release()
            except OSError as e:
                _WRN('Problem during release node: %s' % str(e))

        if self.alarm_monitor is not None:
            self.alarm_monitor.shutdown()

    def controller_state_info(self):
        return '\n\tSC-1\t%s\n\tSC-2\t%s' % (self.controller_state('SC-1'), self.controller_state('SC-2'))

    def display_controllers_state(self):
        _INF('%s' % self.controller_state_info())

    def controller_state(self,controller):
        try:
            state = self.node.controller_state()
        except st_command.CommandFailure as e:
            ## This exception will be raise when both SCs are locked
            ## In such a case we get the stated with the processor_state function
            _DEB('%s controller exception: %s' % (controller, e))
            _DEB('Getting controller %s state via processor state' % controller)
            return self.node.processor_state(controller)
        if controller in list(state.keys()):
            return state[controller]
        else:
            return self.node.processor_state(controller)


    def display_controllers_drbd_state(self):
        _INF('\n%s' % self.controller_drbd_state())

    def controller_drbd_state(self):
        return self.node.controller_drbd_state()

    def map_info(self, mpv):
        return self.node.get_map_info(mpv)

    def change_OwnGTAddress(self,mpv,OwnGTAddress):
        return self.node.change_OwnGTAddress(mpv,OwnGTAddress)


    @property
    def payloads(self):
        return self.node.payload

    @property
    def processors(self):
        return self.node.processors

    @property
    def all_processors(self):
        return self.node.all_processors

    def processor_uuid(self, processor):
        return self.node.processor_uuid(processor)

    def all_processors_state_info(self):
        info = ''
        procs_state_data = self.node.all_processors_state()
        for key, value in list(procs_state_data.items()):
            info += '\n\t%s\t%s' % (key, value)
        return info

    def processors_state_info(self):
        info = ''
        for processor in self.processors:
            info += '\n\t%s\t%s' % (processor, self.processor_state(processor))
        return info

    def processor_state(self, processor):
        return self.node.processor_state(processor)

    def display_processors_state(self):
        _INF('%s' % self.processors_state_info())

    def display_all_processors_state(self):
        _INF('%s' % self.all_processors_state_info())

    def display_processors_vms(self, list_vms):
        info_node_vm = '\nNODE \tVIRTUAL MACHINE\n---- \t----------------'
        processors = self.node.all_processors
        for processor in processors:
            node_uuid = self.node.processor_uuid(processor)
            vm = list_vms[node_uuid]
            info_node_vm = info_node_vm + '\n' + '%s \t%s' % (processor, vm)
        _INF('%s' % info_node_vm)

    def lock_processor(self, processor):
        return self.node.lock_processor(processor)

    def unlock_processor(self, processor):
        return self.node.unlock_processor(processor)

    def nbi_lock_processor(self, processor,nbi_node,timeout):
        return self.node.nbi_lock_processor(processor,nbi_node,timeout)

    def nbi_unlock_processor(self, processor,nbi_node,timeout):
        return self.node.nbi_unlock_processor(processor,nbi_node,timeout)

    def reboot_processor(self, processor):
        if not self.node.check_available_connection(processor):
            self.node.extend_connection(identity = processor, host = processor)
        try:
            self.node.run_command_async('reboot', identity = processor,
                                    answer = {'closed':''})
            _INF('Reboot done')
        except Exception as e:
            _ERR('Reboot falied. Exception: %s' % str(e))

        try:
            self.node.close_connection(identity = processor)
            _INF('Closing connection')
        except Exception as e:
            _ERR('Closing connection Exception: %s' % e)


    @property
    def configured_ExtDb_connections(self):
        if self.__configured_ExtDb_connections == -1:
            self.__configured_ExtDb_connections = int(self.node.configured_ExtDb_connections)
        return self.__configured_ExtDb_connections

    def display_alarm_filter(self):

        filters_info =''
        for alarm_filter in self.alarm_filters:
            filters_info += '\n\t'
            for key, value in list(alarm_filter.items()):
                filters_info += '    %s : %s' %(key, value)

        _INF ('Expected alarms %s' % filters_info)

    def clean_alarm_filters(self):
        self.__alarm_filters = []

    def add_alarm_filters(self, alarm_filters = []):
        for alarm_filter in alarm_filters:
            for key, value in list(alarm_filter.items()):
                if key not in self.allowed_alarm_filters:
                    error_info = '%s not allowed as alarm filter key.' % key
                    error_info += ' Allowed values:\n\t%s' % (error_info, '\n\t'.join(self.allowed_alarm_filters))
                    raise TestCaseError(error_info)

                if value == '':
                    error_info = '%s shall be a non empty string' % value
                    raise TestCaseError(error_info)

            self.__alarm_filters += [alarm_filter]

    def create_alarms_filter_diameter_connection_up(self,stacks = [], transport_list = ['1','2']):
        alarms_filters = []
        for stack in stacks:
            #dia_cons = self.get_dia_con_up(stack)
            dia_cons=[]

            NeighbourNodes = self.__node.get_dia_container_peer_nodes(stackid, disconnect=False)
            for NeighbourNode in NeighbourNodes:
                DIA_CFG_Conns = self.__node.get_dia_container_peer_node_conns(stackid, NeighbourNode, disconnect=False)

                for DIA_CFG_Conn in DIA_CFG_Conns:
                    con_data = self.__node.get_dia_container_peer_node_conn_info(stackid, NeighbourNode, DIA_CFG_Conn, info=['linkStatus','transportLayerType'], disconnect=False)
                    if con_data['linkStatus'][0] == 'Up'and con_data['transportLayerType'][0] in transport_list:
                        dia_cons += [DIA_CFG_Conn]


            for con_data in dia_cons:
                peer_id = con_data.split('\\23')[1]
                alarms_filters += [{'source':peer_id,'specificProblem':'Diameter Link Failure'}]

            self.__alarm_filters += alarms_filters


    def create_alarms_filter_processor_diameter_connection_up(self,stacks = ['SM','ESM','ISMSDA'], processor=None):
        alarms_filters = []
        processor_DIA_CFG = self.find_diameter_connection_up(stacks = stacks)

        try:
            dia_cons = processor_DIA_CFG[processor]
            for con_data in dia_cons:
                peer_id = con_data.split('\\23')[1]
                alarms_filters += [{'source':peer_id,'specificProblem':'Diameter Link Failure'}]
        except KeyError:
            _INF('Not diameter connections found for %s in stacks %s' % (processor, ' '.join(stacks)))
            return

        self.__alarm_filters += alarms_filters


    def create_alarms_filter_specific_diameter_connection_up(self,processor, stackid, conid, info=['linkStatus','processorName','transportLayerType']):
        alarms_filters = []
        #connections = self.get_dia_con_info(stackid, conid, info)
        connection_data=[]
        NeighbourNodes = self.__node.get_dia_container_peer_nodes(stackid, disconnect=False)
        for NeighbourNode in NeighbourNodes:
            DIA_CFG_Conns = self.__node.get_dia_container_peer_node_conns(stackid, NeighbourNode, disconnect=False)
            for DIA_CFG_Conn in DIA_CFG_Conns:
                if conid in DIA_CFG_Conn:
                    con_data = self.__node.get_dia_container_peer_node_conn_info(stackid, NeighbourNode, DIA_CFG_Conn, info, disconnect=False)
                    if con_data['linkStatus'][0] != 'Up':
                        continue
                    con_info = {'con_id':DIA_CFG_Conn}
                    for data in info:
                        try:
                            con_info.update({data:con_data[data][0]})
                        except (KeyError, IndexError):
                            con_info.update({data:None})
                    connection_data += [con_info]

        for connection in connection_data:
            if processor in connection['processorName']:
                alarms_filters += [{'source':'Conn=%s,Stack=HSS_%s,Host=%s' % (connection['con_id'].split('\\23')[-1],stackid, conid),
                                    'specificProblem':'Diameter Link Failure'}]

        self.__alarm_filters += alarms_filters

    def find_diameter_connection_up(self,stacks = ['SM','ESM','ISMSDA']):
        self.__processor_DIA_CFG = {}
        info=['linkStatus','processorName','transportLayerType']

        for stackid in stacks:
            _INF('Finding Diameter connections UP in stack %s' % stackid)
            #connections = self.get_dia_con_info(stackid, info=['processorName'])
            connection_data=[]
            NeighbourNodes = self.__node.get_dia_container_peer_nodes(stackid, disconnect=False)
            for NeighbourNode in NeighbourNodes:
                DIA_CFG_Conns = self.__node.get_dia_container_peer_node_conns(stackid, NeighbourNode, disconnect=False)
                for DIA_CFG_Conn in DIA_CFG_Conns:
                    if 'HSS_' in DIA_CFG_Conn:
                        con_data = self.__node.get_dia_container_peer_node_conn_info(stackid, NeighbourNode, DIA_CFG_Conn, info, disconnect=False)
                        if con_data['linkStatus'][0] != 'Up':
                            continue
                        con_info = {'con_id':DIA_CFG_Conn}
                        for data in info:
                            try:
                                con_info.update({data:con_data[data][0]})
                            except (KeyError, IndexError):
                                con_info.update({data:None})
                        connection_data += [con_info]

            for connection in connection_data:
                try :
                    processor = connection['processorName'].split(',')[0].split('=')[1]
                except IndexError:
                    _WRN('Unexpected processorName: %s  DIA-CFG: %s ' % (connection['processorName'],connection['con_id']))
                    continue
                try:
                    self.__processor_DIA_CFG[processor].append(connection['con_id'])
                except KeyError:
                    self.__processor_DIA_CFG.update({processor:[connection['con_id']]})
        return self.__processor_DIA_CFG


    def display_diameter_connection_up(self):
        for key, value in list(self.processor_DIA_CFG.items()):
            _INF('Diameter connections UP for %s:\n\t%s' %(key, '\n\t'.join(value)))


    def run_stFramework_command(self, cmd, check_result = True):
        _INF('Executing: "%s"' % cmd)
        stdout, stderr, returncode = st_command.execute_cmd('run_command_node %s' % cmd ,stderr = True)

        if not check_result:
            return stdout, stderr, returncode

        if returncode:
            message = st_command.get_stFramework_error_message(stderr)
            error_info = 'cmd "%s" execution FAILED    %s' % (cmd, message)
            raise TestCaseError(error_info)
        else:
            _INF('cmd "%s" execution SUCCESS.\n%s ' % (cmd, stdout.strip()))

    def run_node_command(self,cmd, timeout = None, full_answer = False):
        return self.node.run_command(cmd, timeout = timeout, full_answer = full_answer)

    def run_processor_command(self,cmd, processor, full_answer = False):
        if not self.node.check_available_connection(processor):
            self.node.extend_connection(identity = processor, host = processor)
        return self.node.run_command(cmd, identity = processor, full_answer = full_answer)

    def add_to_expected_alarms_list(self,alarm):
        if alarm not in self.__expected_alarms_list:
            self.__expected_alarms_list += [alarm]

    def check_expected_alarms(self):
        total_result = True
        for alarm_filter in self.alarm_filters:
            result, info = self.check_expected_alarm(alarm_filter)
            total_result &= result

        return total_result

    def check_expected_alarm(self,alarm_filter, display = True):
        alarm, state = self.alarm_monitor.event_state(alarm_filter)

        if state == 'Cleared':
            self.add_to_expected_alarms_list(alarm)
            self.alarm_monitor.remove_event(alarm)
            info = 'Expected alarm has been received and cleared. Filter: %s' % alarm_filter
            _INF(info)
            return True, info
        elif state == 'not found':
            error_info = 'Expected alarm has not been received. Filter: %s' % alarm_filter
            if display:
                _ERR(error_info)
            return False, error_info
        else:
            self.add_to_expected_alarms_list(alarm)
            error_info = 'Expected alarm has not been cleared. Filter: %s' % alarm_filter
            if display:
                _ERR(error_info)
            return False, error_info

    def wait_for_expected_alarms(self, timeout):
        timeout = float(timeout)
        started = time.time()
        while self.alarm_filters:
            now = time.time()
            my_alarm_filters = copy.deepcopy(self.alarm_filters)
            time.sleep(float(10))
            _DEB('Filters of alarms:%s ' % self.alarm_filters)
            for alarm_filter in my_alarm_filters:
                _DEB('Checking for expected alarm to be cleared: %s ' % alarm_filter)
                result, info = self.check_expected_alarm(alarm_filter, display = False)
                if result:
                    self.alarm_filters.remove(alarm_filter)
                    _DEB('Removed expected alarm %s ' % alarm_filter)

            timeout -= time.time() - now
            if timeout < float(0):
                return self.check_expected_alarms()

            if self.alarm_filters:
                _INF('Remaining time waiting for expected alarms to be cleared %s sec.' % timeout)

        return True


    def check_non_cleared_alarms(self):
        info = self.alarm_monitor.not_cleared_events_info()
        if info != '\n':
                error_info = 'Alarms pending to clear: %s' % info
                _WRN(error_info)
                #raise TestCaseError(error_info)
        else:
            _INF('No alarms pending to clear')

    def display_non_expected_alarms(self):
        _INF('No expected alarms:')
        non_expected_alarms = []
        for state in ['New', 'Cleared']:
            alarms = self.alarm_monitor.events_by_state(state)
            for alarm in alarms:
                if alarm not in self.__expected_alarms_list:
                    self.alarm_monitor.show_event(alarm)

    def wait_for_all_ExtDb_connections_up(self, processor, max_time,wait_time=10):
        if not self.node.check_available_connection(processor):
            _DEB('Extending connection for identity %s' % processor)
            self.node.extend_connection(identity = processor, host = processor)

        timeout = float(max_time)
        started = time.time()
        while True:
            now = time.time()
            try:
                counter = 0
                cmd = 'netstat -an | grep -e ":389 " -e ":636 "'
                info = self.node.run_command(cmd, identity = processor)
                for line in info:
                    if len (line.split()) > 4:
                        status = line.split()[5]
                        if status == 'ESTABLISHED':
                            counter += 1

                if counter == self.configured_ExtDb_connections:
                    _INF('ExtDb established connection %s(%s) in %s' %(counter,self.configured_ExtDb_connections,processor  ))
                    break

                _WRN('ExtDb established connection %s(%s) in %s' %(counter,self.configured_ExtDb_connections,processor ))
            except Exception as e:
                _WRN('Problem checking ExtDb established connection in blade %s' % processor)
                _DEB('Exception: %s' % str(e))
                _DEB('configured_ExtDb_connections %s' % self.configured_ExtDb_connections)

            time.sleep(float(wait_time))
            timeout -= time.time() - now
            _INF('Remaining max time %s sec.' % timeout)
            self.node.close_connection(identity = processor)

            if timeout < float(0):
                error_info = 'Timeout. Waiting for more than %s sec.' % max_time
                raise TestCaseError(error_info)

        self.node.close_connection(identity = processor)
        stopped = time.time()
        return stopped-started

    def check_Http_connections_up(self, processor):
        if not self.node.check_available_connection(processor):
            _DEB('Extending connection for identity %s' % processor)
            self.node.extend_connection(identity = processor, host = processor)

        http_num_con = int(self.node.configured_Http_connections)
        http2_num_con = int(self.node.configured_Http2_connections)
        uri_list = self.node.configured_Http_uris
        _DEB('HTTP URI LIST: %s' % uri_list)
        uri2_list = self.node.configured_Http2_uris
        _DEB('HTTP2 URI LIST: %s' % uri2_list)

        try:
            counter = 0
            for uri in uri_list:
                cmd = 'netstat -an | grep "%s " ' % uri
                info = self.node.run_command(cmd, identity = processor)
                for line in info:
                    if len (line.split()) > 4:
                        status = line.split()[5]
                        if status == 'ESTABLISHED':
                            counter += 1
            if counter == http_num_con:
                _INF('HTTP established connections %s(%s) in %s' % (counter,http_num_con,processor))
            else:
                _WRN('HTTP established connection %s(%s) in %s' % (counter,http_num_con,processor ))

            counter = 0
            for uri in uri2_list:
                cmd = 'netstat -an | grep "%s " ' % uri
                info = self.node.run_command(cmd, identity = processor)
                for line in info:
                    if len (line.split()) > 4:
                        status = line.split()[5]
                        if status == 'ESTABLISHED':
                            counter += 1

            if counter == http2_num_con:
                _INF('HTTP2 established connections %s(%s) in %s' % (counter,http2_num_con,processor))
            else:
                _WRN('HTTP2 established connection %s(%s) in %s' % (counter,http2_num_con,processor ))

        except Exception as e:
            _WRN('Problem checking HTTP established connections in blade %s' % processor)
            _DEB('Exception: %s' % str(e))

        self.node.close_connection(identity = processor)


    def wait_for_node_reload(self, max_time, reconnect=True):
        timeout = float(max_time)
        started = time.time()
        if reconnect:
            timeout -= self.reconnect(max_time)

        while True:
            processors = self.processors
            _INF('Reading processors....')
            if processors:
                break
            time.sleep(float(1))

        for processor in self.payloads:
            timeout -= self.wait_for_all_ExtDb_connections_up(processor, timeout, wait_time=1.0)

        stopped = time.time()
        return stopped-started

    def reconnect(self, max_time):
        timeout = max_time
        started = time.time()
        while True:
            now = time.time()
            time.sleep(float(60))
            try:
                self.node.open_connection(identity = 'main')
                if self.node.node_status_OK:
                    stopped = time.time()
                    _INF('Reconnection time:    %s' % str(stopped-started))
                    return stopped-started
                else:
                    _WRN('Status NOK')
                    timeout -= time.time() - now
                    self.node.close_connection(identity = 'main')

            except Exception as e:
                _DEB('Exception: %s' % str(e))
                timeout -= time.time() - now
                _INF('Remaining max time %s sec.' % timeout)

            if timeout < float(0):
                error_info = 'Reconnection timeout. Waiting for more than %s sec.' % max_time
                raise TestCaseError(error_info)


    def reboot_node(self, cmw=False,timeout=180):
        started = time.time()
        try:
            if cmw:
                cmd = 'cmw-cluster-reboot --yes'
            else:
                cmd = 'cluster reboot --all'
            _INF('Executing cmd: %s' % cmd)
            self.node.run_command_async(cmd, answer = {'The system is going down for reboot NOW':''},timeout=timeout)
            stopped = time.time()
            _INF('Reboot time:    %s' % str(stopped-started))
        except Exception as e:
            error_info = 'Reboot failed. Exception: %s' % str(e)
            raise TestCaseError(error_info)

        try:
            self.node.close_connection(identity = 'main')
            _INF('Closing connection')
        except Exception as e:
            error_info = 'Closing connection Exception: %s' % e
            raise TestCaseError(error_info)

        return stopped-started

    def cmw_reboot_sc(self, sc, answer={'The system is going down for reboot NOW':''}, timeout=180):
        started = time.time()
        try:
            cmd = 'cmw-node-reboot %s' % sc
            _INF('Executing cmd: %s' % cmd)
            self.node.run_command_async(cmd, answer=answer, timeout=timeout)
            stopped = time.time()
        except Exception as e:
            error_info = 'Reboot failed. Exception: %s' % str(e)
            raise TestCaseError(error_info)

        try:
            self.node.close_connection(identity = 'main')
            _INF('Closing connection')
        except Exception as e:
            error_info = 'Closing connection Exception: %s' % e
            raise TestCaseError(error_info)

        return stopped-started

    def reload_node(self):
        cmd = 'cdsv-cluster-reload CONFIRM'
        _INF('Executing cmd: %s' % cmd)
        self.node.run_command(cmd)
        try:
            self.node.close_connection(identity = 'main')
            _INF('Closing connection')
        except Exception as e:
            error_info = 'Closing connection Exception: %s' % e
            raise TestCaseError(error_info)
 
        _INF('Reload ordered')

    def close_connection(self, identity = 'main'):
        if self.node is not None:
            self.node.close_connection(identity = identity)

    def manual_backups(self):

        info = self.node.backup_info(['BrmBackup'])
        backup_list = []
        for backup in info['BrmBackup']:
            level = ',BrmBackup=%s' % backup
            info_backup = self.node.backup_info(['creationType'],level)
            if info_backup['creationType'][0] == 'MANUAL':
                backup_list.append(backup)

        return self.max_backups(), backup_list


    def backup_list(self):
        cliss_connection = clissConnection(self.node,
                                                'hssadministrator')

        return cliss_connection.search(hss_utils.node.cba.BACKUP_CLISS_DN,
                                              'BrmBackup')

    def max_backups(self):

        cliss_connection = clissConnection(self.node,
                                                'hssadministrator')

        clissDn = '%s,BrmBackupHousekeeping=SYSTEM_DATA' % hss_utils.node.cba.BACKUP_CLISS_DN
        max_backups = cliss_connection.search(clissDn, 'maxStoredManualBackups')
        return int(max_backups[0])


    def create_backup(self, backup):
        cmd = 'CBA_create_backup --node %s --user %s %s -v' % (self.__access_config['host'], self.__access_config['user'],
                                                                             backup)
        stdout, stderr, returncode = self.run_stFramework_command(cmd, check_result = False)
        if returncode:
            error_info = st_command.get_stFramework_error_message(stderr)
            raise TestCaseError(error_info)

        _INF('cmd "%s" execution SUCCESS.' % cmd)
        _INF('%s' % stdout.strip())
        return stdout.strip()


    def delete_backup(self, backup):
        cmd = 'CBA_delete_backup --node %s --user %s %s -v' % (self.__access_config['host'], self.__access_config['user'],
                                                                             backup)
        stdout, stderr, returncode = self.run_stFramework_command(cmd, check_result = False)
        if returncode:
            error_info = st_command.get_stFramework_error_message(stderr)
            raise TestCaseError(error_info)

        _INF('cmd "%s" execution SUCCESS.' % cmd)
        _INF('%s' % stdout.strip())
        return stdout.strip()

    def restore_backup(self, backup=None):
        cmd = 'CBA_restore_backup --node %s --user %s %s -v' % (self.__access_config['host'], self.__access_config['user'],
                                                                  ('' if backup is None else '-b %s' % backup))
        stdout, stderr, returncode = self.run_stFramework_command(cmd, check_result = False)
        if returncode:
            error_info = st_command.get_stFramework_error_message(stderr)
            raise TestCaseError(error_info)

        _INF('cmd "%s" execution SUCCESS.' % cmd)
        for line in stdout.split('\n'):
            _INF('%s' % line.strip())

        return stdout


