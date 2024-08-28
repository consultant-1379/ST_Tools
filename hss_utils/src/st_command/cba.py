#!/usr/bin/env python
#

import sys
import os
CWD = os.getcwd()
import os.path
import time
import traceback
import argparse
import re
import xml.etree.ElementTree as ET
import glob
import shutil
import socket
import copy
from datetime import datetime, timedelta

import e3utils.log as logging
_DEB = logging.internal_debug
_WRN = logging.warning
_ERR = logging.error
_INF = logging.info

import hss_utils.node.cba
import hss_utils.connection as connection
import hss_utils.node.gentraf
from . import ExecutionTimeout
from . import NotFound
from . import CommandFailure
from . import WrongParameter

from . import create_connection_summary
from . import DYNAMIC_PROCESSES
from . import execute_cmd, clear_ansi, validate_ip

def CBA_get_connection_by_port_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('PORT',
                        help='Port used as filter')

    command_params.add_argument('--proc',nargs='+',
                      action='store', default=None,
                      help='Processor list used as filter',
                      dest='processor')

    command_params.add_argument('--summary',
                      action='store_true', default=False,
                      help='Print the number of connections ordered by status',
                      dest='summary')
    return (parser)

def run_CBA_get_connection_by_port(user_config, node):

    processors = []
    allowed_processor = node.payload
    if  user_config.processor is None:
        processors = node.payload
    else:
        for processor in user_config.processor:
            if processor in allowed_processor:
                processors.append(processor)
            else:
                raise WrongParameter('%s is not a valid processor. Allowed values are: %s' % (processor, ' '.join(allowed_processor)))

    for  processor in sorted(processors):
        node.extend_connection(str(processor), processor)
        cmd = 'netstat -an | grep ":%s " ' % user_config.PORT
        print('\n%s' % processor)
        if user_config.summary:
            create_connection_summary((node.run_command(cmd, identity = str(processor))))
        else:
            print('\n'.join(node.run_command(cmd, identity = str(processor))))

def run_CBA_check_ExtDb_connections(user_config, node):

    max_connections = int(node.configured_ExtDb_connections)
    faulty_connections = ''

    for processor in sorted(node.payload):
        counter = 0
        node.extend_connection(str(processor), processor)
        cmd = 'netstat -an| grep -e ":389 " -e ":636 "'
        info = node.run_command(cmd, identity = str(processor))
        for line in info:
            if len (line.split()) > 4:
                status = line.split()[5]
                if status == 'ESTABLISHED':
                    counter += 1

        if counter != max_connections:
            faulty_connections += ' %s' % processor

        print('%s %s (%s)' % (processor, counter, max_connections))

    if faulty_connections != '':
        raise CommandFailure('Fail in processors: %s' % faulty_connections)

def CBA_check_Http_connections_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--sum-pl-con',
                      action='store_true', default=False,
                      help='The value read from maxOutgoingConnections applies to all PLs together instead of a single one',
                      dest='sum_pl_con')
    return (parser)

def run_CBA_check_Http_connections(user_config, node):

    max_connections = int(node.configured_Http_connections)
    if max_connections != -2:
        uri_list = node.configured_Http_uris
    else:
        _DEB('HTTP Server1.1 configuration not defined ')
        uri_list = []
    _DEB('URI LIST: %s' % uri_list)

    max2_connections = int(node.configured_Http2_connections)
    if max2_connections != -2:
        uri2_list = node.configured_Http2_uris
    else:
        _DEB('HTTP Server2.0 configuration not defined ')
        uri2_list = []
    _DEB('URI2 LIST: %s' % uri2_list)

    faulty_connections = ''
    total_counter = 0

    for processor in sorted(node.payload):
        counter = 0
        counter2 = 0
        node.extend_connection(str(processor), processor)
        # Counting connections for HTTP Server1.1
        for uri in uri_list:
            cmd = 'netstat -an | grep "%s " ' % uri
            info = node.run_command(cmd, identity = str(processor))
            for line in info:
                if len (line.split()) > 4:
                    status = line.split()[5]
                    if status == 'ESTABLISHED':
                        counter += 1
            _DEB('After checking %s  the counter is %d ' % (uri, counter))

        # Counting connections for HTTP Server2.0 if defined
        for uri in uri2_list:
            cmd = 'netstat -an | grep "%s " ' % uri
            info = node.run_command(cmd, identity = str(processor))
            for line in info:
                if len (line.split()) > 4:
                    status = line.split()[5]
                    if status == 'ESTABLISHED':
                        counter2 += 1
            _DEB('After checking %s  the counter is %d ' % (uri, counter2))

        if max_connections != -2:
            if not user_config.sum_pl_con and  counter != max_connections:
                faulty_connections += ' %s' % processor
                _DEB('FAULTY CONNECTION HTTP1: counter=%d  max_connections=%d in processor %s' % (counter, max_connections, processor))
            total_counter += counter

        if max2_connections != -2:
            if not user_config.sum_pl_con and  counter2 != max2_connections:
                faulty_connections += ' %s' % processor
                _DEB('FAULTY CONNECTION HTTP2: counter=%d  max_connections=%d in processor %s' % (counter2, max2_connections, processor))

        if uri2_list and uri_list:
            print('%s    HTTP %s (%s)   HTTP2 %s (%s)' % (processor, counter,  max_connections, counter2, max2_connections))
        else:
            if uri_list:
                print('%s    HTTP %s (%s)' % (processor,counter,  max_connections))
            if uri2_list:
                print('%s    HTTP2 %s (%s)' % (processor,counter2,  max2_connections))

    if user_config.sum_pl_con and total_counter != max_connections:
        raise CommandFailure('Total connection (%s) does not match maxOutgoingConnections (%s)' % (total_counter, max_connections))

    if not user_config.sum_pl_con and  faulty_connections != '':
        raise CommandFailure('Fail in processors: %s' % faulty_connections)


def CBA_check_time_wait_connections_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--port-con',
                      action='store', default='389',
                      help='Port to check the connections with TIME_WAIT status. By default is "%(default)s"',
                      dest='port_con')

    command_params.add_argument('--min-value',
                      action='store', default='1',
                      help='Minimum value of number of connections with TIME_WAIT status to be considered valid. By default is "%(default)s"',
                      dest='min_value')

    command_params.add_argument('--max-value',
                      action='store', default='99',
                      help='Maximum value of number of connections with TIME_WAIT status to be considered valid. By default is "%(default)s" ',
                      dest='max_value')
    return (parser)

def run_CBA_check_time_wait_connections(user_config, node):

    faulty_connections = ''
    pls_counter = 0

    if int(user_config.min_value) < 0:
        raise WrongParameter('--min-value parameter must be equal to 0 or greater ')
    if int(user_config.max_value) < 0:
        raise WrongParameter('--max-value parameter must be equal to 0 or greater ')
    if int(user_config.min_value) > int(user_config.max_value):
        raise WrongParameter('--max-value parameter must be equal to --min-value parameter or greater ')

    for processor in sorted(node.payload):
        counter = 0
        node.extend_connection(str(processor), processor)
        cmd = 'netstat -an | grep ":%s " ' % user_config.port_con
        info = node.run_command(cmd, identity = str(processor))
        for line in info:
            if len (line.split()) > 4:
                status = line.split()[5]
                if status == 'TIME_WAIT':
                    counter += 1

        if counter != 0:
            pls_counter += 1
            if (counter < int(user_config.min_value) or counter > int(user_config.max_value)):
                faulty_connections += ' %s' % processor
            print('%s    %s    (%s-%s)' % (processor, counter,  user_config.min_value, user_config.max_value))
        else:
            print('%s    %s' % (processor, counter))

    if pls_counter == 0:
        if int(user_config.max_value) > 0:
            raise CommandFailure('No PLs with several TIME_WAIT connections')

    if pls_counter >1:
        raise CommandFailure('More than one PL (%s) with several TIME_WAIT connections' % pls_counter)

    if faulty_connections != '':
        raise CommandFailure('Fail in processors: %s' % faulty_connections)


def run_CBA_datetime(user_config, node):
    print(node.datetime)



def CBA_get_active_SC_for_COM_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-6',
                        default=False, action='store_true',
                        dest='ipv6',
                        help='Select IPv6')
    return (parser)



def run_CBA_get_active_SC_for_COM(user_config, node):

    host, ip = node.get_primary_sc(user_config.ipv6)
    print('%s   %s' % (host,ip))


def run_CBA_get_active_SC_for_DRBD(user_config, node):

    cmd = 'hostname'
    hostanme = node.run_command(cmd)[0]
    cmd = 'drbdadm status'
    role = node.run_command(cmd)[0]
    if 'Primary' in role:
        print(hostanme)
    else:
        print('%s' % ('SC-1' if hostanme == 'SC-2' else 'SC-2'))


def run_CBA_get_PL(user_config, node):

    print('\n'.join(node.payload))

def CBA_clean_app_logs_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-f','--force',
                      action='store_true', default=False,
                      help='Empty files that are being used.',
                      dest='force')

    return (parser)

def run_CBA_clean_app_logs(user_config, node):

    node.conId_for_log='main'
    logs_to_clean = node.logs_to_clean(node.applogs_path)
    if len(logs_to_clean) > 0:
        node.run_command('cd %s' % node.applogs_path)
        cmd = 'rm %s' % ' '.join(logs_to_clean)
        node.run_command(cmd,identity=node.conId_for_log)

    for log_file in logs_to_clean:
        print('Cleaned file %s' % log_file)

    print('Done!')


def run_CBA_clean_pmf_logs(user_config, node):

    cmd = 'rm -f -v /storage/no-backup/com-apr9010443/PerformanceManagementReportFiles/*.xml.gz'
    node.run_command(cmd)
    cmd = 'rm -f -v /storage/no-backup/com-apr9010443/PerformanceManagementReportFiles/*.xml'
    node.run_command(cmd)

def run_CBA_clean_console_logs(user_config, node):

    cmd = 'clurun.sh -c clear_logs'
    node.run_command(cmd)

def run_CBA_clean_capsule_dumps(user_config, node):

    cmd = 'rm /cluster/dumps/*'
    node.run_command(cmd)

    cmd = 'rm /cluster/storage/no-backup/cdclsv/dumps/*'
    node.run_command(cmd)

def run_CBA_list_capsule_dumps(user_config, node):

    cmd = 'ls /cluster/dumps/*'
    answer = node.run_command(cmd)
    if 'No such file or directory' in '\n'.join(answer):
        print('There is not dumps in /cluster/dumps/')
    else:
        print('\n'.join(answer))

    cmd = 'ls /cluster/storage/no-backup/cdclsv/dumps/*'
    answer = node.run_command(cmd)
    if 'No such file or directory' in '\n'.join(answer):
        print('There is not dumps in /cluster/storage/no-backup/cdclsv/dumps/')
    else:
        print('\n'.join(answer))

def run_CBA_clean_alarms(user_config, node):

    node.force_primary_controller()
    logs = node.logs_to_clean(node.alarm_path)
    if logs:
        clean_logs(node, node.alarm_path, logs)

def run_CBA_clean_alerts(user_config, node):

    node.force_primary_controller()
    logs = node.logs_to_clean(node.alert_path)
    if logs:
        clean_logs(node, node.alert_path, logs)

def clean_logs(node, path, logs):
    config = node.config
    try:
        config['user'] = 'com-emergency'
        config['password'] = node.get_user_credential('com-emergency')
        node.create_connection(config=config, session_type=node.session_type,identity='com-emergency', force_open=True)
        conId = 'com-emergency'

    except hss_utils.connection.Unauthorized:
        conId = 'main'

    cmd = 'cd %s' % path
    node.run_command(cmd, identity=conId)
    cmd = 'rm -f %s' % (' '.join(logs))
    node.run_command(cmd, identity=conId)


def CBA_get_node_status_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-x','--exclude',
                      action='store', nargs='*',default=[],
                      choices=['app', 'csiass', 'comp', 'sg', 'si', 'siass', 'su', 'pm'],
                      help='Set specific checks to be excluded',
                      dest='exclude')

    return (parser)

def run_CBA_get_node_status(user_config, node):

    allowed_checks=['app', 'csiass', 'comp', 'sg', 'si', 'siass', 'su', 'pm']
    cmd = 'cmw-status node'
    for check in allowed_checks:
        if check not in user_config.exclude:
            cmd += ' %s' % check

    answer = node.run_command(cmd)
    print('\n'.join(answer))

def run_CBA_get_last_pl_reboot(user_config, node):

    processors = ['SC-1', 'SC-2'] + node.processors

    for  processor in sorted(processors):
        node.extend_connection(str(processor), processor)
        cmd = 'who -b'
        answer = node.run_command(cmd, identity=str(processor))
        if len(answer):
            print('%s %s' % (answer[0], processor))

def CBA_get_free_memory_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--cpu_load',
                      default=False, action='store_true',
                      help='Store also cpu info in this path. By default is "%(default)s"',
                      dest='cpu_load')
    command_params.add_argument('-o','--output_path',
                      action='store', default='/tmp',
                      help='Store full memory info and/or cpu info in this path. By default is "%(default)s"',
                      dest='output_path')

    return (parser)



# Calculation from
# https://cc-jira.rnd.ki.sw.ericsson.se/browse/CC-12300

def run_CBA_get_free_memory(user_config, node):
    processors = ['SC-1', 'SC-2'] + node.processors

    try:
        if not os.path.exists(user_config.output_path):
            os.makedirs(user_config.output_path)
    except Exception as e:
        raise CommandFailure('%s' % e)

    try:
        with open("%s" % os.path.join(user_config.output_path,'memory_full_info.txt') , "w") as text_file:
            if user_config.cpu_load:
                print('PROCESSOR  MEMORY   CPU')
            else:
                print('PROCESSOR  MEMORY')
            for  processor in sorted(processors):
                node.extend_connection(str(processor), processor)

                cmd = 'cat /proc/meminfo'
                answer = node.run_command(cmd, identity=str(processor))
                total = 0
                free = 0
                porcentage = 0
                if len(answer):
                    text_file.write('\n%s\n%s\n' % (processor, '\n'.join(answer)))
                    for line in answer:
                        if 'MemTotal' in line:
                            total += int (line.split()[1])
                        if 'SwapTotal' in line:
                            total += int (line.split()[1])
                        if 'MemFree' in line:
                            free += int (line.split()[1])
                        if 'Cached' in line:
                            free += int (line.split()[1])
                        if 'Buffers' in line:
                            free += int (line.split()[1])
                        if 'SwapFree' in line:
                            free += int (line.split()[1])
                        if 'SReclaimable' in line:
                            free += int (line.split()[1])
                        if 'Shmem' in line:
                            free -= int (line.split()[1])
                    percentage = (float(free) *100 ) / float(total)

                if user_config.cpu_load:
                    cmd = 'sar 1 1'
                    answer = node.run_command(cmd, identity=str(processor))
                    cpu_load = 0
                    if len(answer):
                        text_file.write('\n%s\n%s\n' % (processor, '\n'.join(answer)))
                        for line in answer:
                            if 'Average' in line:
                                cpu_idle = line.split()[7]
                                cpu_load = 100 - float(cpu_idle)
                    print('%-*s    %.2f    %.2f' % (7,processor, percentage,cpu_load))
                else:
                    print('%-*s    %.2f' % (7,processor, percentage))

    except IOError as e:
        raise CommandFailure('%s' % e)


def run_CBA_get_cpu_load(user_config, node):
    processors = ['SC-1', 'SC-2'] + node.processors

    try:
        if not os.path.exists(user_config.output_path):
            os.makedirs(user_config.output_path)
    except Exception as e:
        raise CommandFailure('%s' % e)


    except IOError as e:
        raise CommandFailure('%s' % e)


def CBA_find_process_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('PROCESS',
                        help='Process to find')

    command_params.add_argument('-p',
                      action='store_true', default=False,
                      help='Prints the number of ocurrences.',
                      dest='number')

    return (parser)


def run_CBA_find_process(user_config, node):

    payload = node.payload
    node.extend_connection('payload', payload[0])
    cmd = 'clurun.sh ps'

    lines = node.run_command(cmd, identity = 'payload')
    counter = 0
    processor = ''
    for line in lines:
        searchObj = re.search(r'\[(.+?)\]',line)
        if searchObj:
            if processor != '' and counter != 0:
                print('%s%s' % ('%s\t'% counter if user_config.number else '', processor[1:-1]))
            processor = searchObj.group()
            counter = 0
        elif str(user_config.PROCESS) in line:
            counter += 1

    if counter != 0:
        print('%s%s' % ('%s\t'% counter if user_config.number else '', processor[1:-1]))

def CBA_find_dynamic_process_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-l', '--list',
                      action='store_true', default=False,
                      help='Print the list of supportted dynamic processes.',
                      dest='list')
    command_params.add_argument('-p', '--processor',
                      action='store', default=None,
                      help='Processor used as filter',
                      dest='processor')

    return (parser)


def run_CBA_find_dynamic_process(user_config, node):

    if user_config.list:
        print('\n'.join(DYNAMIC_PROCESSES))
        return

    payload = node.payload
    node.extend_connection('payload', payload[0])
    cmd = 'clurun.sh ps'
    processes = ' '.join(node.run_command(cmd, identity = 'payload'))
    dynamic_process_found = False
    for process in DYNAMIC_PROCESSES:
        counter = processes.count(process)
        if counter > 0:
            dynamic_process_found = True
            print('%-*s    %s' % (8, counter, process))

    if dynamic_process_found:
        raise CommandFailure('Dynamic processes found')
    else:
        print('')

def run_CBA_find_all_processes(user_config, node):

    payload = node.payload
    for pl in sorted(payload):
        cmd = 'clurun.sh -n %s -c ps | grep HSS_' % pl
        answer = node.run_command(cmd)
        print(pl)
        print('\n'.join(answer))

def run_CBA_list_processes(user_config, node):
    processes = []
    payload = node.payload
    for pl in sorted(payload):
        cmd = 'clurun.sh -n %s -c ps | grep HSS_' % pl
        answer = node.run_command(cmd)
        for line in answer:
            process = line.split()[-1]

            if process not in processes:
                processes.append(process)

    print('\n'.join(sorted(processes)))

def CBA_get_traffic_info_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-t','--traffic_type',
                        default = 'IMS',choices = ['IMS', 'EPC'],
                        dest='trafic_type',
                        help='Traffic type used as filter. Allowed values IMS | EPC')
    command_params.add_argument('-s','--specific',nargs='+',default=None,
                        choices = ['hss_version', 'dia_tcp', 'dia_sctp','soap','soap_ldap','oam','radius','extdb','udm','udmClient','udmHttp2Client',
                                   'vector_supplier','controller','HSS-MapSriForLcs','ownGTAddress','radiusClient','HSS-EsmIsActive',
                                   'HSS-CommonAuthenticationVectorSupplier'],
                        action='store',
                        help='Specify value',
                        dest='specific')
    command_params.add_argument('-6',
                        default=False, action='store_true',
                        dest='ipv6',
                        help='Select IPv6')
    return (parser)


def run_CBA_get_traffic_info(user_config, node):

    if not user_config.specific:
        user_config.specific = ['hss_version', 'dia_tcp', 'dia_sctp','soap','soap_ldap','oam','radius','extdb','udm','udmClient',
                                   'vector_supplier','controller','HSS-MapSriForLcs','ownGTAddress','radiusClient','HSS-EsmIsActive',
                                   'HSS-CommonAuthenticationVectorSupplier','udmHttp2Client']

    answer = node.get_traffic_info(traffic_type=user_config.trafic_type, info=user_config.specific, IPv6=user_config.ipv6)

    keys = list(answer.keys())
    keys.sort()
    for key in keys:
        if key in user_config.specific:
            print('%s=%s' % (key, answer[key]))

def CBA_check_active_backup_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('BACKUPNAME',
                        help='Backup name used as filter')

    return (parser)


def run_CBA_check_active_backup(user_config, node):
    backup = node.active_backup
    if user_config.BACKUPNAME != backup:
        raise CommandFailure('The active backup is %s instead of %s' % (backup, user_config.BACKUPNAME))


def run_CBA_get_active_backup(user_config, node):
    print(node.active_backup)



def CBA_check_latest_backup_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('BACKUPNAME',
                        help='Backup name used as filter')

    return (parser)


def run_CBA_check_latest_backup(user_config, node):
    backup = node.latest_backup
    if user_config.BACKUPNAME != backup:
        raise CommandFailure('The latest backup is %s instead of %s' % (backup, user_config.BACKUPNAME))

def run_CBA_get_latest_backup(user_config, node):
    print(node.latest_backup)

def CBA_check_last_restored_backup_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('BACKUPNAME',
                        help='Backup name used as filter')

    return (parser)


def run_CBA_check_last_restored_backup(user_config, node):
    backup = node.last_restored_backup
    if user_config.BACKUPNAME != backup:
        raise CommandFailure('The last restored backup is %s instead of %s' % (backup, user_config.BACKUPNAME))

def run_CBA_get_last_restored_backup(user_config, node):
    print(node.last_restored_backup)

def CBA_create_backup_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('BACKUPNAME',
                        help='Backup name. If value is AUTO, the name will be HSSFE<release>_<vector_supplier>')

    command_params.add_argument('-t',
                      action='store', default=600,
                      help='Max time in sec waiting for backup creation. By default is "%(default)s" seconds',
                      dest='max_time')

    return (parser)


def run_CBA_create_backup(user_config, node):
    if user_config.BACKUPNAME == 'AUTO':
        vector =  node.get_traffic_info(info=['vector_supplier']).get('vector_supplier','NOT_FOUND')
        user_config.BACKUPNAME = 'HSSFE%s_%s' % (node.hss_release.replace('.','_'), vector)

    timeout = float(user_config.max_time)
    cmd = 'createBackup %s' % user_config.BACKUPNAME
    answer = node.run_backup_cmd(cmd)
    if 'command failed' in answer:
        raise CommandFailure('%s' % answer.replace('\r\n',' '))

    while True:
        now = time.time()
        time.sleep(float(5))

        info = node.backup_info(['state', 'result', 'resultInfo','timeActionStarted','timeActionCompleted'])
        _DEB('State %s   result %s    resultInfo %s' % (info['state'], info['result'], info['resultInfo']))
        if info['state'] in [['FINISHED'],['CANCELLED']]:
            break
        timeout -= time.time() - now
        if timeout < 0:
            raise ExecutionTimeout('Timeout waiting for backup creation')

    if info['result'] != ['SUCCESS']:
        raise CommandFailure('Creation of %s backup failed: %s' % (user_config.BACKUPNAME, info['resultInfo'][0]))

    _DEB('timeActionStarted: %s    timeActionCompleted: %s' % (info['timeActionStarted'][0],info['timeActionCompleted'][0]))
    started=time.mktime(time.strptime(info['timeActionStarted'][0],"%Y-%m-%dT%H:%M:%S"))
    stopped=time.mktime(time.strptime(info['timeActionCompleted'][0],"%Y-%m-%dT%H:%M:%S"))
    print('Create Backup Time:    %s' % str(stopped-started))


def CBA_check_backup_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('BACKUPNAME',
                        help='Backup name used as filter')

    return (parser)

def run_CBA_check_backup(user_config, node):
    info = node.backup_info(['BrmBackup'])
    if user_config.BACKUPNAME not in info['BrmBackup']:
        raise CommandFailure('%s backup not found' % user_config.BACKUPNAME)


def CBA_check_scheduled_backups_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-d', '--deleted',
                      action='store_true', default=False,
                      help='Optional. Check also the backups deleted',
                      dest='check_deleted')
    command_params.add_argument('--from',
                      action='store', default=None,
                      help='Optional. Initial date of the logs to analyze. Value shall be in format "Y-m-dTH:M:S"',
                      dest='from_time')
    command_params.add_argument('--to',
                      action='store', default=None,
                      help='Optional. Ending date of the logs to analyze. Value shall be in format "Y-m-dTH:M:S"',
                      dest='to_time')

    return (parser)

def run_CBA_check_scheduled_backups(user_config, node):
    list_backup_dates = []
    if user_config.from_time:
        try:
            init_date = datetime.strptime(user_config.from_time, '%Y-%m-%dT%H:%M:%S')
        except Exception as e:
            error = '--from %s not valid. Value shall be in format "Y-m-dTH:M:S"' % user_config.from_time
            _ERR(error)
            raise WrongParameter(error)
    else:
        init_date = datetime.strptime('2010-7-10T22:55:56', '%Y-%m-%dT%H:%M:%S')

    if user_config.to_time:
        try:
            last_date = datetime.strptime(user_config.to_time, '%Y-%m-%dT%H:%M:%S')
        except Exception as e:
            error = '--to %s not valid. Value shall be in format "Y-m-dTH:M:S"' % user_config.to_time
            _ERR(error)
            raise WrongParameter(error)
    else:
        last_date = datetime.now()

    _DEB('Initial date to check: %s' % init_date)
    _DEB('Last date to check: %s' % last_date)
    create_pattern = 'create backup BACKUP_'
    backup_failure = False
    host, ip = node.get_primary_sc()
    cmd = 'grep "%s" `ls -rt /var/log/%s/messages* ` ' % (create_pattern, host)
    answer = node.run_command(cmd)
    for line in answer:
        _DEB('line to check: %s' % line)
        info_backup = line.split(':',1)[1]
        date_backup = info_backup.split('.')[0]

        operation_date = datetime.strptime(date_backup, '%Y-%m-%dT%H:%M:%S')
        if operation_date >= init_date and operation_date <= last_date:
            if date_backup in list_backup_dates:
                _DEB('Backup operation with date %s already analyzed' % date_backup)
            else:
                _DEB('Backup operation found with date %s ' % date_backup)
                list_backup_dates.append(date_backup)
                oper_backup = info_backup.split('script:')[1]
                oper_info = oper_backup.split(':')[0]
                result_info = oper_backup.split(':')[1]
                if not 'SUCCESS' in result_info:
                    backup_failure = True
                    _DEB('result info ERROR: %s' % result_info)
                print('%s    %s    %s' % (date_backup, oper_info, result_info))

        else:
            _DEB('Operation done out of period for checking: %s' % info_backup)

    if user_config.check_deleted:
        list_backup_dates = []
        delete_pattern = 'delete backup BACKUP_'
        cmd = 'grep "%s" `ls -rt /var/log/%s/messages* ` ' % (delete_pattern, host)
        answer = node.run_command(cmd)
        for line in answer:
            _DEB('line to check: %s' % line)
            info_backup = line.split(':',1)[1]
            date_backup = info_backup.split('.')[0]
            operation_date = datetime.strptime(date_backup, '%Y-%m-%dT%H:%M:%S')
            if operation_date >= init_date and operation_date <= last_date:
                if date_backup in list_backup_dates:
                    _DEB('Delete Backup operation with date %s already analyzed' % date_backup)
                else:
                    _DEB('Delete Backup operation found with date %s ' % date_backup)
                    oper_backup = info_backup.split('script:')[1]
                    oper_info = oper_backup.split(':')[0]
                    result_info = oper_backup.split(':')[1]
                    if not 'SUCCESS' in result_info:
                        backup_failure = True
                        _DEB('result info ERROR: %s' % result_info)
                    print('%s    %s    %s' % (date_backup, oper_info, result_info))

            else:
                _DEB('Operation done out of period for checking: %s' % info_backup)

    if backup_failure:
        raise CommandFailure('Some backup operations were not SUCCESS')


def CBA_delete_backup_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('BACKUPNAME',
                        help='Backup name used as filter')

    command_params.add_argument('-t',
                      action='store', default=600,
                      help='Max time in sec waiting for backup deletion. By default is "%(default)s" seconds',
                      dest='max_time')

    return (parser)


def run_CBA_delete_backup(user_config, node):
    timeout = float(user_config.max_time)
    cmd = 'deleteBackup %s' % user_config.BACKUPNAME
    answer = node.run_backup_cmd(cmd)
    if 'command failed' in answer:
        raise CommandFailure('%s' % answer.replace('\r\n',' '))

    while True:
        now = time.time()
        time.sleep(float(5))

        info = node.backup_info(['state', 'result', 'resultInfo','timeActionStarted','timeActionCompleted'])
        _DEB('State %s   result %s    resultInfo %s' % (info['state'], info['result'], info['resultInfo']))
        if info['state'] in [['FINISHED'],['CANCELLED']]:
            break
        timeout -= time.time() - now
        if timeout < 0:
            raise ExecutionTimeout('Timeout waiting for backup deletion')

    if info['result'] != ['SUCCESS']:
        raise CommandFailure('Delete of %s backup failed: %s' % (user_config.BACKUPNAME, info['resultInfo'][0]))

    _DEB('timeActionStarted: %s    timeActionCompleted: %s' % (info['timeActionStarted'][0],info['timeActionCompleted'][0]))
    started=time.mktime(time.strptime(info['timeActionStarted'][0],"%Y-%m-%dT%H:%M:%S"))
    stopped=time.mktime(time.strptime(info['timeActionCompleted'][0],"%Y-%m-%dT%H:%M:%S"))
    print('Delete Backup Time:    %s' % str(stopped-started))


def CBA_run_command_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('COMMAND',action='store',
                      help='Command to be executed. It shall be quoted')

    command_params.add_argument('--file',
                      action='store', default=None,
                      help='Store the output in an specific file instead of showing it in console',
                      dest='file')

    command_params.add_argument('-t',
                      action='store', default=120, type=int,
                      help='Max time in sec waiting for command execution. By default is "%(default)s"',
                      dest='max_time')
    return (parser)

def run_CBA_run_command(user_config, node):

    answer = node.run_command(user_config.COMMAND, timeout=float(user_config.max_time), full_answer=True)
    if user_config.file is None:
        print(answer)
    else:
        if not os.path.exists(os.path.dirname(user_config.file)):
            os.makedirs(os.path.dirname(user_config.file))
            os.chmod(os.path.dirname(user_config.file), 0o777)
        with open(user_config.file,'a') as fd:
            fd.write(answer)

def CBA_run_PL_command_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('COMMAND',action='store',nargs='+',
                      help='List of command to be executed. Every single command shall be quoted')

    command_params.add_argument('-p', '--processors',nargs='+',
                      action='store', default=None,
                      help='List of processors where to execute the cmmands. By default all the PLs will be used',
                      dest='processors')

    command_params.add_argument('--file',
                      action='store', default=None,
                      help='Store the output in specific file instead of showing it in console. Processor name will be added as suffix',
                      dest='file')

    command_params.add_argument('-t',
                      action='store', default=120, type=int,
                      help='Max time in sec waiting for command execution. By default is "%(default)s"',
                      dest='max_time')
    return (parser)

def run_CBA_run_PL_command(user_config, node):

    processors=[]
    allowed_processor = node.processors

    if user_config.processors is None:
        processors = allowed_processor
    else:
        for processor in user_config.processors:
            if processor in allowed_processor:
                processors.append(processor)
            else:
                raise WrongParameter('%s is not a valid processor. Allowed values are: %s' % (processor, ' '.join(allowed_processor)))

    for processor in sorted(processors):
        identity = '%s' % (str(processor))
        node.extend_connection(identity, processor,user='root')

        answer = node.run_command('date', identity, timeout=float(user_config.max_time), full_answer=True)
        for command in user_config.COMMAND:
            answer += '\nExecuting: "%s" in %s\n' % (command, processor)
            answer = answer + '\n' + node.run_command(command, identity, timeout=float(user_config.max_time), full_answer=True)
            if user_config.file is None:
                print(answer)
            else:
                file_name = '%s.%s' % (user_config.file, processor)
                if os.path.dirname(user_config.file):
                    if not os.path.exists(os.path.dirname(user_config.file)):
                        os.makedirs(os.path.dirname(user_config.file))
                        os.chmod(os.path.dirname(user_config.file), 0o777)
                with open(file_name,'a') as fd:
                    fd.write(answer)
            answer = ''

def CBA_run_cliss_command_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('CMD',action='store',
                      help='Cliss command to be executed')

    command_params.add_argument('--cliss_user',
                      action='store', default='hssadministrator',
                      choices=['hssadministrator','ericssonhsssupport','SystemAdministrator','com-emergency','root'],
                      help='Cliss user to be used. By default is "%(default)s"',
                      dest='cliss_user')

    command_params.add_argument('--configure',
                      action='store_true', default=False,
                      help='To indicate if the command will modify the configuration. Then a "configure" a "commit" commands will be executed to apply the update.',
                      dest='cliss_conf')

    command_params.add_argument('--file',
                      action='store', default=None,
                      help='Store the output in an specific file instead of showing it in console',
                      dest='file')

    return (parser)

def run_CBA_run_cliss_command(user_config, node):

    answer = node.run_cliss_command(user_config.CMD, user_config.cliss_user, user_config.cliss_conf)
    if user_config.file is None:
        print(answer)
    else:
        try:
            if not os.path.exists(os.path.dirname(user_config.file)):
                _DEB('Saving file %s' % user_config.file)
                os.makedirs(os.path.dirname(user_config.file))
                os.chmod(os.path.dirname(user_config.file), 0o777)
            with open(user_config.file,'a') as fd:
                fd.write(answer)
        except Exception as e:
            raise CommandFailure('Error creating output file: %s' % e)


def CBA_download_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('FROM',action='store',
                      help='Absolute path of remote file to download')

    command_params.add_argument('TO', action='store',
                      help='Absolute path where downloaded file will be stored')

    return (parser)

def run_CBA_download(user_config, node):

    if not os.path.exists(os.path.dirname(user_config.TO)):
        os.makedirs(os.path.dirname(user_config.TO))
        os.chmod(os.path.dirname(user_config.TO), 0o777)

    node.download(user_config.FROM, user_config.TO)



def CBA_find_and_download_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('FROM',action='store',nargs='+',
                      help='List of wilcarded expresions including the absolute path for selecting files.')

    command_params.add_argument('--to', 
                      help='Absolute path where to download files.',
                      default=None, action='store',
                      dest='to')

    command_params.add_argument('--skip-download',
                      help='List files but not download',
                      action='store_true', default=False,
                      dest='skip_download')

    command_params.add_argument('--skip-print',
                      help='Do not print the files to be downloaded',
                      action='store_true', default=False,
                      dest='skip_print')

    command_params.add_argument('--empty',
                      help='Allow empty files',
                      action='store_true', default=False,
                      dest='empty')

    command_params.add_argument('--pack',
                      help='Name for the tgz file created when packing',
                      action='store', default=None,
                      dest='pack')

    time_params = parser.add_argument_group('Slot time configuration')

    time_params.add_argument('--from-mtime',
                      action='store', default=None,
                      help='Set the start modification-time for files selection. Value shall be in format "Y-m-dTH:M:S"',
                      dest='from_time')

    time_params.add_argument('--to-mtime',
                      action='store', default=None,
                      help='Set the last modification-time for files selection. Value shall be in format "Y-m-dTH:M:S"',
                      dest='to_time')

    return (parser)

def run_CBA_find_and_download(user_config, node):

    if not user_config.skip_download and not user_config.to:
        raise WrongParameter('--to is required for downloading files')

    if user_config.skip_download and user_config.pack:
        raise WrongParameter('--skip-download and --pack not allowed together')

    if user_config.skip_download and user_config.skip_print:
        raise WrongParameter('--skip-download and --skip-print not allowed together')

    if user_config.to:
        user_config.to = hss_utils.st_command.real_path(user_config.to)

    if user_config.to and not os.path.exists(os.path.dirname(user_config.to)):
        os.makedirs(os.path.dirname(user_config.to))
        os.chmod(os.path.dirname(user_config.to), 0o777)

    file_list = ''
    for wildcard in user_config.FROM:
        cmd = 'find %s -type f %s' % (wildcard, ('' if user_config.empty else '! -size 0 '))
        if user_config.from_time:
            cmd += '-newermt %s' % user_config.from_time

        if user_config.to_time:
            cmd += '-not -newermt %s' % user_config.to_time

        answer = node.run_command(cmd, full_answer=True)
        if answer.startswith('find: '):
            continue

        file_list += answer

    if not file_list:
        print('No such file or directory')

    for filename in file_list.splitlines():
        if not user_config.skip_print:
            print(filename)

        if user_config.skip_download:
            continue

        elif not user_config.pack:
            node.download(filename, user_config.to)

    if not user_config.pack:
        return

    cmd = 'tar -czvf %s %s' % (user_config.pack, ' '.join(file_list.splitlines()))
    _DEB('Executing: %s' % cmd)
    answer = node.run_command(cmd, full_answer=True)
    _DEB('answer: %s' % answer)
    node.download(user_config.pack, user_config.to)
    cmd = 'rm %s' % user_config.pack
    _DEB('Executing: %s' % cmd)
    answer = node.run_command(cmd, full_answer=True)
    _DEB('answer: %s' % answer)



def CBA_upload_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('FROM',action='store',
                      help='Absolute path of local file to upload')

    command_params.add_argument('TO', action='store',
                      help='Absolute remote path where uploaded file will be stored')

    return (parser)

def run_CBA_upload(user_config, node):

    directory = os.path.dirname(user_config.TO)
    cmd = 'mkdir -p %s' % directory
    node.run_command(cmd)
    node.upload(user_config.FROM, user_config.TO)


def CBA_export_backup_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('BACKUPNAME',
                        help='Backup name used as filter')

    command_params.add_argument('LOCATION',
                        help='Absolute path for storing the backup')

    command_params.add_argument('-u','--unique',
                      action='store_true', default=False,
                      help='Execute only if there is not a backup with the same name in the LOCATION',
                      dest='unique')
    command_params.add_argument('-t',
                      action='store', default=600,
                      help='Max time in sec waiting for backup export. By default is "%(default)s" seconds',
                      dest='max_time')

    return (parser)


def run_CBA_export_backup(user_config, node):

    if user_config.unique:
        access_config = {'host':socket.gethostname(),
                        'port':22,
                        'user':'hss_st',
                        'password':'hss_st'}
        gentraf = hss_utils.node.gentraf.GenTraf(config = access_config)
        cmd = 'ls -ltr %s_SYSTEM_*.tar.gz' % os.path.join(user_config.LOCATION, user_config.BACKUPNAME)
        answer = gentraf.run_command(cmd, full_answer=True)
        if 'No such file or directory' not in answer:
            for backup in answer.splitlines():
                cmd = 'rm -f %s' % clear_ansi(backup.split()[-1])
                gentraf.run_command(cmd)

    if not os.path.exists(user_config.LOCATION):
        os.makedirs(user_config.LOCATION)
        os.chmod(user_config.LOCATION, 0o777)


    access_config = {'host':socket.gethostname(),
                    'port':22,
                    'user':'hss_st',
                    'password':'hss_st'}
    gentraf = hss_utils.node.gentraf.GenTraf(config = access_config)
    try:
        dest_host = gentraf.get_ip_address_nic('bond0.100')[0]
    except Exception as e:
        raise CommandFailure('Problem searching bond0.100 IP: %s' % e)

    gentraf.release()

    info = node.backup_info(['BrmBackup'])
    if user_config.BACKUPNAME not in info['BrmBackup']:
        raise CommandFailure('%s backup does not exist' % user_config.BACKUPNAME)

    level = ',BrmBackup=%s' % user_config.BACKUPNAME
    cmd = 'export --uri "sftp://hss_st@%s%s" --password "hss_st"' % (dest_host, user_config.LOCATION)
    answer = node.run_backup_cmd(cmd, next_level = level)
    if 'command failed' in answer:
        raise CommandFailure('%s' % answer.replace('\r\n',' '))


    timeout = float(user_config.max_time)
    while True:
        now = time.time()
        time.sleep(float(5))

        info = node.backup_info(['state', 'result', 'resultInfo'], next_level = level)
        _DEB('State %s   result %s    resultInfo %s' % (info['state'], info['result'], info['resultInfo']))
        if info['state'] in [['FINISHED'],['CANCELLED']]:
            break
        timeout -= time.time() - now
        if timeout < 0:
            raise ExecutionTimeout('Timeout waiting for action')

    if info['result'] != ['SUCCESS']:
        raise CommandFailure('Export of %s backup failed: %s' % (user_config.BACKUPNAME, info['resultInfo'][0]))


def CBA_import_backup_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('BACKUP',
                        help='Absolute path of the tar.gz file of the backup exported')

    command_params.add_argument('-t',
                      action='store', default=600,
                      help='Max time in sec waiting for backup import. By default is "%(default)s" seconds',
                      dest='max_time')

    return (parser)


def run_CBA_import_backup(user_config, node):

    access_config = {'host':socket.gethostname(),
                    'port':22,
                    'user':'hss_st',
                    'password':'hss_st'}
    gentraf = hss_utils.node.gentraf.GenTraf(config = access_config)
    try:
        dest_host = gentraf.get_ip_address_nic('bond0.100')[0]
    except Exception as e:
        raise CommandFailure('Problem searching bond0.100 IP: %s' % e)

    if os.path.isfile(user_config.BACKUP):
        backup = user_config.BACKUP
    else:
        cmd = 'ls -ltr %s_SYSTEM_*.tar.gz' % user_config.BACKUP
        answer = gentraf.run_command(cmd)
        if answer:
            backup = clear_ansi(answer[-1].split()[-1])
        else:
            raise CommandFailure('Backup not found in %s' % user_config.BACKUP)

    cmd = 'importBackup --uri "sftp://hss_st@%s%s" --password "hss_st"' % (dest_host, backup)

    answer = node.run_backup_cmd(cmd)
    if 'command failed' in answer or 'ERROR' in answer:
        raise CommandFailure('%s' % answer.replace('\r\n',' '))

    timeout = float(user_config.max_time)
    while True:
        now = time.time()
        time.sleep(float(5))

        info = node.backup_info(['state', 'result', 'resultInfo'])
        _DEB('State %s   result %s    resultInfo %s' % (info['state'], info['result'], info['resultInfo']))
        if info['state'] in [['FINISHED'],['CANCELLED']]:
            break
        timeout -= time.time() - now
        if timeout < 0:
            raise ExecutionTimeout('Timeout waiting for action')

    if info['result'] != ['SUCCESS']:
        raise CommandFailure('Import of %s backup failed: %s' % (user_config.BACKUP, info['resultInfo'][0]))



def CBA_restore_backup_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-b','--backupname',
                      action='store', default=None,
                      help='Backup name to be restored. Default is the last used (created or restored)',
                      dest='BACKUPNAME')

    command_params.add_argument('-t',
                      action='store', default=900,
                      help='Max time in sec waiting for backup restore. By default is "%(default)s" seconds',
                      dest='max_time')

    command_params.add_argument('-s', '--skip-reload',
                      action='store_true', default=False,
                      help='Do not wait for system reload.',
                      dest='skip_reload')

    return (parser)



def run_CBA_restore_backup(user_config, node):

    if user_config.BACKUPNAME is None:
        user_config.BACKUPNAME = node.active_backup
    else:
        info = node.backup_info(['BrmBackup'])
        if user_config.BACKUPNAME not in info['BrmBackup']:
            raise CommandFailure('%s backup does not exist' % user_config.BACKUPNAME)

    level = ',BrmBackup=%s' % user_config.BACKUPNAME
    cmd = 'restore'
    answer = node.run_backup_cmd(cmd, next_level = level)
    if 'command failed' in answer:
        raise CommandFailure('%s' % answer.replace('\r\n',' '))

    timeout = float(user_config.max_time)
    ssh_server_available = True
    while ssh_server_available:
        now = time.time()
        time.sleep(float(30))

        try:
            info = node.backup_info(['state', 'result', 'resultInfo','timeActionStarted','timeActionCompleted'], next_level = level)
            _DEB('State %s   result %s    resultInfo %s' % (info['state'], info['result'], info['resultInfo']))

            if info['state'] in [['FINISHED'],['CANCELLED']]:
                break

            timeout -= time.time() - now
            _DEB('timeout %s' % timeout)
            node.close_connection(identity = 'cliss_hssadministrator')
        except Exception as e:
            _DEB('Cabinet reload is on going: %s' % e)
            ssh_server_available = False

        if timeout < float(0):
            raise ExecutionTimeout('Timeout waiting for backup restore')

    if info['result'] != ['SUCCESS'] and info['state'] in [['FINISHED'],['CANCELLED']]:
        raise CommandFailure('Restore %s backup failed: %s' % (user_config.BACKUPNAME, info['resultInfo'][0]))

    _DEB('timeActionStarted: %s    timeActionCompleted: %s' % (info['timeActionStarted'][0],info['timeActionCompleted'][0]))
    started=time.mktime(time.strptime(info['timeActionStarted'][0],"%Y-%m-%dT%H:%M:%S"))
    stopped=time.mktime(time.strptime(info['timeActionCompleted'][0],"%Y-%m-%dT%H:%M:%S"))
    print('Restore Backup Time:   %s' % str(stopped-started))

    node.release_connection(identity = 'cliss_hssadministrator')

    if user_config.skip_reload:
        return

    _DEB('Wait for connection broken')
    started = None
    while True:
        try:
            if node.node_status_OK:
                time.sleep(float(1))
            else:
                started = time.time()
                break

        except Exception as e:
            _DEB('Connection broken. Exception: %s' % e)
            started = time.time()
            break

    _DEB('Wait for cabinet reload')
    while True:
        now = time.time()
        time.sleep(float(5))

        try:
            if node.node_status_OK:
                break
        except Exception as e:
            _DEB('Exception: %s' % e)
        timeout -= time.time() - now
        _DEB('timeout %s' % timeout)
        if timeout < float(0):
            raise ExecutionTimeout('Timeout waiting for backup restore')

    stopped = time.time()
    _DEB('Reload Time:    %s' % str(stopped-started))
    print('Reload Time:           %s' % str(stopped-started))

def run_CBA_check_status(user_config, node):
    return node.node_status_OK


def CBA_schedule_backup_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--period',
                      action='store', default=6,
                      help='Scheduler period in hours. By default is "%(default)s" hours',
                      dest='period')

    command_params.add_argument('--stop',
                      action='store', default=48,
                      help='Time in hours for stopping the scheduler. By default is "%(default)s" hours',
                      dest='stop')

    command_params.add_argument('--name',
                      action='store', default='LongStability',
                      help='Name of the scheduler event. By default is "%(default)s"',
                      dest='name')

    return (parser)


def run_CBA_schedule_backup(user_config, node):

    cmd = 'configure'
    level = ',BrmBackupScheduler=SYSTEM_DATA'
    answer = node.run_backup_cmd(cmd, next_level = level)
    _DEB('%s' % answer)
    if 'ERROR' in answer:
        raise CommandFailure('%s' % answer)

    cmd = 'BrmPeriodicEvent=%s' % user_config.name
    answer = node.run_backup_cmd(cmd, next_level = level)
    _DEB('%s' % answer)
    if 'ERROR' in answer:
        raise CommandFailure('%s' % answer)

    cmd = 'hours=%s' % user_config.period
    level = ',BrmBackupScheduler=SYSTEM_DATA,BrmPeriodicEvent=%s' % user_config.name
    answer = node.run_backup_cmd(cmd, next_level = level)
    _DEB('%s' % answer)
    if 'ERROR' in answer:
        raise CommandFailure('%s' % answer)

    #start = datetime.today() 
    #cmd = 'startTime=%s' % start.strftime("%Y-%m-%dT%H:%M:%S")
    #answer = node.run_backup_cmd(cmd, next_level = level)
    #_DEB('%s' % answer)
    #if 'ERROR' in answer:
        #raise CommandFailure('%s' % answer)

    stop = datetime.today() + timedelta(hours=int(user_config.stop))
    cmd = 'stopTime=%s' % stop.strftime("%Y-%m-%dT%H:%M:%S")
    answer = node.run_backup_cmd(cmd, next_level = level)
    _DEB('%s' % answer)
    if 'ERROR' in answer:
        raise CommandFailure('%s' % answer)

    cmd = 'commit'
    answer = node.run_backup_cmd(cmd, next_level = level)
    _DEB('%s' % answer)
    if 'ERROR' in answer:
        raise CommandFailure('%s' % answer)


def CBA_remove_schedule_backup_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--name',
                      action='store', default='LongStability',
                      help='Name of the scheduler event to be removed. By default is "%(default)s"',
                      dest='name')

    return (parser)


def run_CBA_remove_schedule_backup(user_config, node):

    cmd = 'configure'
    level = ',BrmBackupScheduler=SYSTEM_DATA'
    answer = node.run_backup_cmd(cmd, next_level = level)
    if 'ERROR' in answer:
        raise CommandFailure('%s' % answer)

    cmd = 'no BrmPeriodicEvent=%s' % user_config.name
    answer = node.run_backup_cmd(cmd, next_level = level)
    if 'ERROR' in answer:
        raise CommandFailure('%s' % answer)

    cmd = 'commit'
    answer = node.run_backup_cmd(cmd, next_level = level)
    if 'ERROR' in answer:
        raise CommandFailure('%s' % answer)



def run_CBA_list_backup(user_config, node):

    info = node.backup_info(['BrmBackup'])
    backup_list = []
    manual_backups = 0
    for backup in info['BrmBackup']:
        level = ',BrmBackup=%s' % backup
        info_backup = node.backup_info(['creationType', 'creationTime', 'status'],level)
        if info_backup['creationType'][0] == 'MANUAL':
            manual_backups += 1
        backup_list.append( '%s\t%s\t%s\t%s' % (info_backup['creationTime'][0],info_backup['status'][0],info_backup['creationType'][0], backup))

    backup_list.sort()
    print('\n'.join(backup_list))

    level = ',BrmBackupHousekeeping=SYSTEM_DATA'
    max_backups = node.backup_info(['maxStoredManualBackups'],level)
    print('\nWarning: %s new backups can be manually created' % (int(max_backups['maxStoredManualBackups'][0]) - manual_backups))


def CBA_check_alarms_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-s','--severity',
                      action='store', default=None,
                      help='Field used as filter',
                      dest='severity')

    command_params.add_argument('-f','--filter',
                      action='store', default='',
                      help='Substring included in specificProblem description used as filter',
                      dest='filter')

    command_params.add_argument('--source',
                      action='store', default='',
                      help='Substring included in source used as filter',
                      dest='source')

    command_params.add_argument('-x','--exclude',nargs='*',
                      action='store', default='',
                      help='Substring included in specific Problem description used as exclusion filter',
                      dest='exclude')

    command_params.add_argument('--summary',
                      action='store_true', default=False,
                      help='Display type alarms counters',
                      dest='summary')

    command_params.add_argument('--list',
                      action='store_true', default=False,
                      help='Return the list of alarms',
                      dest='list')

    command_params.add_argument('--specific',
                      action='store', default=None,
                      help='Print alarm info for an specific alarm',
                      dest='specific')

    return (parser)


def run_CBA_check_alarms(user_config, node):

    if user_config.summary:
        info = node.alarm_info(['sumCritical','sumMajor','sumMinor','sumWarning','totalActive'])
        print('Critical     %s' % info['sumCritical'][0])
        print('Major        %s' % info['sumMajor'][0])
        print('Minor        %s' % info['sumMinor'][0])
        print('Warning      %s' % info['sumWarning'][0])
        print('totalActive  %s' % info['totalActive'][0])

    info = node.alarm_info(['FmAlarm'])
    if user_config.list:
        print('\n'.join(info['FmAlarm']))
        return

    if user_config.specific is not None:
        if user_config.specific in info['FmAlarm']:
            data = node.get_alarm_info(user_config.specific)
            if data:
                print(node.print_alarm_info(user_config.specific, data))
        return

    alarm_list = []
    for alarm in info['FmAlarm']:
        info_alarm = node.get_alarm_info(alarm)
        if not info_alarm:
            continue
        if user_config.severity in [None, info_alarm['activeSeverity'][0]]:
            if user_config.filter in info_alarm['specificProblem'][0] and user_config.source in info_alarm['source'][0]:
                skip = False
                for exlude in user_config.exclude:
                    if exlude in info_alarm['specificProblem'][0]:
                        skip = True
                        break;
                if skip:
                    continue

                alarm_list.append(node.print_alarm_info(alarm,info_alarm))

    if len(alarm_list):
        print('\n'.join(alarm_list))
    else:
        print('\nNo alarms')


def CBA_get_licenses_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--no_granted',
                      action='store_true', default=False,
                      help='Select only no granted licenses',
                      dest='no_granted')
    return (parser)

def run_CBA_get_licenses(user_config, node):

    print('\nFeature Licenses:')
    print('\n\t%s' % '\n\t'.join(node.find_licenses(user_config.no_granted)))

    print('\nCapacity Licenses:')
    print('\n\t%s' % '\n\t'.join(node.find_capacity_licenses()))

def run_CBA_grant_licenses(user_config, node):

    node.grant_licenses()


def run_CBA_check_all_licenses_granted(user_config, node):

    node.check_all_licenses_granted()


def CBA_NBI_check_alarms_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-s','--severity',
                      action='store', default=None,
                      help='Field used as filter',
                      dest='severity')

    command_params.add_argument('-f','--filter',
                      action='store', default='',
                      help='Substring included in specificProblem description used as filter',
                      dest='filter')

    command_params.add_argument('-x','--exclude',nargs='*',
                      action='store', default='',
                      help='List of Substrings included in specific Problem description alarm field used as exclusion filter',
                      dest='exclude')

    command_params.add_argument('--xsource',nargs='*',
                      action='store', default='',
                      help='List of Substrings included in source alarm field used as exclusion filter',
                      dest='xsource')

    return (parser)

def run_CBA_NBI_check_alarms(user_config, node):

    if user_config.filter == '':
        info = node.nbi_alarm_info(['sumCritical','sumMajor','sumMinor','sumWarning','totalActive'])
        print('Critical     %s' % info['sumCritical'][0])
        print('Major        %s' % info['sumMajor'][0])
        print('Minor        %s' % info['sumMinor'][0])
        print('Warning      %s' % info['sumWarning'][0])
        print('totalActive  %s' % info['totalActive'][0])

    info = node.nbi_alarm_info(['FmAlarm'])
    alarm_list = []
    for alarm in info['FmAlarm']:
        level = ',FmAlarm=%s' % alarm
        info_alarm = node.nbi_alarm_info(['activeSeverity', 'eventType',
                                          'lastEventTime','source',
                                          'specificProblem', 'additionalText',
                                          'originalAdditionalText']
                                          ,level)

        if user_config.severity in [None, info_alarm['activeSeverity'][0]]:

            if user_config.filter in info_alarm['specificProblem'][0]:
                skip = False
                for exlude in user_config.exclude:
                    if exlude in info_alarm['specificProblem'][0]:
                        skip = True
                        break;
                if skip:
                    continue

                skip = False
                for exlude in user_config.xsource:
                    if exlude in info_alarm['source'][0]:
                        skip = True
                        break;
                if skip:
                    continue

                alarm_list.append( 'FmAlarm:%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s' % (alarm,info_alarm['activeSeverity'][0],info_alarm['eventType'][0],
                                                                        info_alarm['lastEventTime'][0],info_alarm['source'][0],
                                                                        info_alarm['specificProblem'][0],info_alarm['additionalText'][0],
                                                                        info_alarm['originalAdditionalText'][0]))

    if len(alarm_list):
        print('\n'.join(alarm_list))

    else:
        print('\nNo alarms')


def CBA_health_check_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-o','--output_path',
                      action='store', default=None,
                      help='Collect result info and store it in this path',
                      dest='output_path')
    command_params.add_argument('-t',
                action='store', default=600,
                help='Max time in sec waiting for health check execution. By default is "%(default)s" seconds',
                dest='max_time')


    return (parser)


def run_CBA_health_check(user_config, node):

    timeout = float(user_config.max_time)
    node.start_healthcheck()
    time.sleep(float(10))

    while True:
        now = time.time()
        time.sleep(float(5))
        info = node.healthcheck_info(['lastReportFileName','localFileStorePath','state','result','resultInfo','status'])
        if info['state'][0] == 'FINISHED':
            break
        timeout -= time.time() - now
        if timeout < 0:
            raise ExecutionTimeout('Timeout waiting for health check execution')


    if info['result'][0] != 'SUCCESS':
        raise CommandFailure('Health Check error: %s' % info['resultInfo'][0])

    if user_config.output_path is not None:
        files_to_download = os.path.join(info['localFileStorePath'][0],info['lastReportFileName'][0])
        node.download('%s*' % files_to_download, user_config.output_path)

    if info['status'][0] == 'NOT_HEALTHY':
        raise CommandFailure('Health Check status is NOT HEALTHY')


def CBA_diacc_collect_info_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-o','--output_path',
                      action='store', default='.',
                      help='Collect C-Diameter info will be stored in this path',
                      dest='output_path')

    command_params.add_argument('-t',
                      action='store', default=300,
                      help='Max time in sec waiting for command execution.',
                      dest='max_time')

    return (parser)


def run_CBA_diacc_collect_info(user_config, node):

    # Executing the script to collect the info from just one of the Payloads
    payload = node.payload
    node.extend_connection('payload', payload[0])
    cmd = 'cd /cluster'
    node.run_command(cmd, identity = 'payload')
    node.run_command(cmd)
    cmd = '/opt/diacc/bin/diacc-collect-info.sh '
    answer = node.run_command(cmd, timeout=float(user_config.max_time), identity = 'payload')

    if 'Unable to create' in ' '.join(answer):
        raise CommandFailure('Unable to create archive')

    if 'Generating collected troubleshooting data archive' in ' '.join(answer):
        for line in answer:
            if 'data archive into' in line:
                log_file = line.split("into ",1)[1]

        node.download('%s' % log_file, user_config.output_path)
        cmd = 'rm %s' % log_file
        node.run_command(cmd)
    else:
        raise CommandFailure('Error when collecting diacc info: %s' % (' '.join(answer)))


def CBA_cmw_collect_info_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-o','--output_path',
                      action='store', default='.',
                      help='Collect result info will be stored in this path',
                      dest='output_path')

    command_params.add_argument('-s','--file_suffix',
                      action='store', default='',
                      help='Used for building output file name',
                      dest='file_suffix')

    command_params.add_argument('-t',
                      action='store', default=300,
                      help='Max time in sec waiting for command execution.',
                      dest='max_time')


    return (parser)


def run_CBA_cmw_collect_info(user_config, node):

    cmd = 'cd /cluster'
    node.run_command(cmd)
    cmd = 'export CMW_COLLECTLOG_TEMPDIR=/var/log'
    node.run_command(cmd)
    cmd = 'cmw-collect-info cmw-collect-%s' %  user_config.file_suffix
    answer = node.run_command(cmd, timeout=float(user_config.max_time))

    if 'Unable to create archive' in ' '.join(answer):
        raise CommandFailure('Unable to create archive')

    if 'Logs archived' in ' '.join(answer):
        node.download('/cluster/cmw-collect-%s.tar.gz' % user_config.file_suffix, user_config.output_path)
        cmd = 'rm /cluster/cmw-collect-%s.tar.gz' % user_config.file_suffix
        node.run_command(cmd)
    else:
        raise CommandFailure('Error when collecting info: %s' % (' '.join(answer)))

def CBA_collect_logs_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-o','--output_path',
                      action='store', default='.',
                      help='Collect result info will be stored in this path',
                      dest='output_path')

    command_params.add_argument('-s','--file_suffix',
                      action='store', default='',
                      help='Used for building output file name',
                      dest='file_suffix')

    command_params.add_argument('-t',
                      action='store', default=300,
                      help='Max time in sec waiting for every single collection data.',
                      dest='max_time')

    command_params.add_argument('--collect_console',
                      action='store_true', default=False,
                      help='Enable console log collect.',
                      dest='collect_console')

    command_params.add_argument('--log_type',
                      action='store', default='ALL',
                      choices=['alarms','alerts','applogs','ALL'],
                      help='Select one single type of logs to be collected.',
                      dest='log_type')

    return (parser)


def run_CBA_collect_logs(user_config, node):

    node.force_primary_controller()
    if user_config.collect_console:
        logdump ='logdump_fake'
        cmd = 'cdclsv-pack'
        answer = node.run_command(cmd, full_answer=True)
        for word in answer.split():
            if 'logdump' in word:
                logdump = word

        timeout = user_config.max_time
        applogs_dir='/storage/no-backup/cdclsv/dumps/%s.tgz' % logdump
        while True:
            now = time.time()
            time.sleep(float(5))

            cmd = 'ls %s' % applogs_dir
            answer = node.run_command(cmd, full_answer=True)
            if 'No such file or directory' not in answer:
                break
            timeout -= time.time() - now
            if timeout < 0:
                raise ExecutionTimeout('Timeout waiting for cdclsv-pack execution')

        node.download('%s*' % applogs_dir, user_config.output_path)
        cmd = 'rm %s*' % applogs_dir
        node.run_command(cmd)

    if user_config.log_type == 'ALL':
        log_types = ['alarms','alerts','applogs']
        _DEB('Collecting logs for ALL types')
    else:
        log_types = [user_config.log_type]
        _DEB('Collecting logs for type %s' % user_config.log_type)

    if 'applogs' in log_types:
        cmd = 'cd %s' % node.applogs_path
        node.run_command(cmd)
        tar_file = 'applog_%s.tgz' % user_config.file_suffix
        cmd = 'tar zcvf %s *.log' % tar_file
        node.run_command(cmd, timeout=float(user_config.max_time))

        node.download('%s/%s' % (node.applogs_path, tar_file), user_config.output_path)
        cmd = 'rm %s/%s' % (node.applogs_path, tar_file)
        node.run_command(cmd)

    if 'alarms' in log_types or 'alerts' in log_types:
        config = copy.deepcopy(node.config)
        try:
            config['user'] = 'com-emergency'
            config['password'] = node.get_user_credential('com-emergency')
            node.create_connection(config=config, session_type=hss_utils.connection.session.StandardLinux,identity='com-emergency', force_open=True)
            conId = 'com-emergency'
        except hss_utils.connection.Unauthorized:
            conId = 'main'

    if 'alarms' in log_types:
        cmd = 'cd %s' % node.alarm_path
        node.run_command(cmd, identity=conId)
        tar_file = 'FmAlarmLog_%s.tgz' % user_config.file_suffix
        cmd = 'tar zcvf %s *.log' % tar_file
        node.run_command(cmd, identity=conId, timeout=float(user_config.max_time))
        node.download('%s/%s' % (node.alarm_path,tar_file), user_config.output_path, identity=conId)
        cmd = 'rm -f %s/%s' % (node.alarm_path,tar_file)
        node.run_command(cmd, identity=conId)

    if 'alerts' in log_types:
        cmd = 'cd %s' % node.alert_path
        node.run_command(cmd, identity=conId)
        tar_file = 'FmAlertLog_%s.tgz' % user_config.file_suffix
        cmd = 'tar zcvf %s *.log' % tar_file
        node.run_command(cmd, identity=conId, timeout=float(user_config.max_time))
        node.download('%s/%s' % (node.alert_path,tar_file), user_config.output_path, identity=conId)
        cmd = 'rm -f %s/%s' % (node.alert_path,tar_file)
        node.run_command(cmd, identity=conId)


cba_gauge_counters = ['TotalNumberOfApplicationServersStored'
  ]

def CBA_pmf_counter_sum_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--dir',
                      action='store', default=None,
                      help='Specify the full path of the directory with the compressed files (.xml.gz) to process. If not defined, the files will be downloaded from the environment.',
                      dest='dir_files')
    command_params.add_argument('-o', '--output',
                      action='store', default=None,
                      help='Specify the full path of output file. By default info is displayed in console',
                      dest='output_file')

    return (parser)

def run_CBA_pmf_counter_sum(user_config, node):

    main_path = '/storage/no-backup/com-apr9010443/PerformanceManagementReportFiles'
    if user_config.dir_files is None:
        working_directory = '/opt/hss/CBA_pmf_counters_sum_%s' % os.getpid()
        if not os.path.exists(working_directory):
            os.makedirs(working_directory)
        try:
            node.download('%s/*.xml.gz' % main_path, working_directory)
        except IOError:
            os.rmdir(working_directory)
            raise CommandFailure('PMF counters not found')
    else:
        working_directory = user_config.dir_files
        if not os.path.exists(working_directory):
            raise CommandFailure('Directory PMF counters does not exist')



    _DEB('Uncompressing files from %s directory' % working_directory)
    cmd = 'gzip -d %s/*.xml.gz' % working_directory
    stdout_value, returncode = execute_cmd(cmd)
    if returncode:
        raise CommandFailure('Error executing: %s' % cmd)

    total_counter={}
    max_len_of_counter_name = 0
    _DEB('Analyzing XML files. It may take a while ...')
    file_list= sorted(glob.glob("%s/*.xml" % working_directory))
    for element in file_list:
        partial_counter = {}

        tree = ET.parse(element)
        root = tree.getroot()
        for md in root.findall('{http://www.3gpp.org/ftp/specs/archive/32_series/32.435#measCollec}measData'):

            for mi in md.findall('{http://www.3gpp.org/ftp/specs/archive/32_series/32.435#measCollec}measInfo'): 
                prefix = ''
                name = mi.attrib['measInfoId']
                if 'DiaNode' in mi.attrib['measInfoId']:
                    prefix = 'DiaNode.'
                if 'DiaPeer' in mi.attrib['measInfoId']:
                    prefix = mi.attrib['measInfoId'] + '.'

                measType_dict = {}
                for measType in mi.findall('{http://www.3gpp.org/ftp/specs/archive/32_series/32.435#measCollec}measType'):
                    measType_name = prefix + measType.text
                    measType_dict.update({measType.attrib['p']: measType_name})

                for measValue in mi.findall('{http://www.3gpp.org/ftp/specs/archive/32_series/32.435#measCollec}measValue'):
                    if '$' in measValue.attrib['measObjLdn']:
                        continue
                    for r in measValue.findall('{http://www.3gpp.org/ftp/specs/archive/32_series/32.435#measCollec}r'):
                        key = r.attrib['p']
                        try:
                            if measType_dict[key].startswith ('VS.'):
                                continue
                            if measType_dict[key] in cba_gauge_counters:
                                partial_counter[measType_dict[key]] = int(r.text)
                            else:
                                partial_counter[measType_dict[key]] += int(r.text)
                        except KeyError:
                            partial_counter.update({measType_dict[key]:int(r.text)})

        for key, value in list(partial_counter.items()):
            try:
                if key in cba_gauge_counters:
                    total_counter[key] = value
                else:
                    total_counter[key] += value
            except KeyError:
                total_counter.update({key:value})
                if len(key) > max_len_of_counter_name:
                    max_len_of_counter_name = len(key)


    if user_config.output_file is None:
        for key in sorted(total_counter):
            print('%-*s  %s' % (max_len_of_counter_name, key, total_counter[key]))
    else:
        try:
            log_dir = os.path.dirname(user_config.output_file)
            if log_dir != '':
                if not os.path.exists(log_dir):
                    os.makedirs(log_dir)
            with open(user_config.output_file, "w") as text_file:
                for key in sorted(total_counter):
                    text_file.write("%-*s  %s\n" % (max_len_of_counter_name, key, total_counter[key]))

        except Exception as e:
            raise CommandFailure('Error creating output file: %s' % e)

    if user_config.dir_files is None:
        shutil.rmtree(working_directory)
    else: # We compress again the files to let the files as they were before the execution
        cmd = 'gzip %s/*.xml' % working_directory
        stdout_value, returncode = execute_cmd(cmd)
        if returncode:
            raise CommandFailure('Error executing: %s' % cmd)

def CBA_check_pmf_counter_update_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-t', '--traffic',
                      action='store', default='BOTH',
                      choices = ['IMS', 'EPC', 'BOTH'],
                      help='Specify the traffic type for selecting the counters to be checked. By default is "BOTH"',
                      dest='traffic')

    return (parser)

def run_CBA_check_pmf_counter_update(user_config, node):

    main_path = '/storage/no-backup/com-apr9010443/PerformanceManagementReportFiles'
    working_directory = '/opt/hss/CBA_pmf_counters_sum_%s' % os.getpid()
    if not os.path.exists(working_directory):
        os.makedirs(working_directory)

    cmd = 'ls -ltr %s/*.xml.gz' % main_path
    file_to_download=None
    try:
        answer = node.run_command(cmd)
        for line in reversed(answer):
            if 'xml.gz' in line:
                file_to_download=line
                break

    except Exception as e:
        os.rmdir(working_directory)
        raise CommandFailure('PMF counters not found: %s' % e)

    if file_to_download is None:
        os.rmdir(working_directory)
        raise CommandFailure('PMF counters not found')

    try:
        node.download(clear_ansi(file_to_download.split()[-1]), working_directory)
    except IOError:
        os.rmdir(working_directory)
        raise CommandFailure('PMF counters not found')


    cmd = 'gzip -d %s/*.xml.gz' % working_directory
    stdout_value, returncode = execute_cmd(cmd)
    if returncode:
        raise CommandFailure('Error executing: %s' % cmd)

    total_counter={}
    max_len_of_counter_name = 0
    file_list= sorted(glob.glob("%s/*.xml" % working_directory))
    for element in file_list:
        partial_counter = {}

        tree = ET.parse(element)
        root = tree.getroot()
        for md in root.findall('{http://www.3gpp.org/ftp/specs/archive/32_series/32.435#measCollec}measData'):

            for mi in md.findall('{http://www.3gpp.org/ftp/specs/archive/32_series/32.435#measCollec}measInfo'): 
                measType_dict = {}
                for measType in mi.findall('{http://www.3gpp.org/ftp/specs/archive/32_series/32.435#measCollec}measType'):
                    name = measType.text
                    attr = measType.attrib
                    measType_dict.update({measType.attrib['p']: measType.text})

                for measValue in mi.findall('{http://www.3gpp.org/ftp/specs/archive/32_series/32.435#measCollec}measValue'):
                    for r in measValue.findall('{http://www.3gpp.org/ftp/specs/archive/32_series/32.435#measCollec}r'):
                        key = r.attrib['p']
                        try:
                            if measType_dict[key].startswith ('VS.'):
                                continue
                            if measType_dict[key] in cba_gauge_counters:
                                partial_counter[measType_dict[key]] = int(r.text)
                            else:
                                partial_counter[measType_dict[key]] += int(r.text)
                        except KeyError:
                            partial_counter.update({measType_dict[key]:int(r.text)})

        for key, value in list(partial_counter.items()):
            try:
                if key in cba_gauge_counters:
                    total_counter[key] = value
                else:
                    total_counter[key] += value
            except KeyError:
                total_counter.update({key:value})
                if len(key) > max_len_of_counter_name:
                    max_len_of_counter_name = len(key)

    shutil.rmtree(working_directory)

    try:
        if user_config.traffic == 'BOTH':
            _DEB('EsmExtDbSearchRequests: %s    IsmExtDbSearchRequests: %s' % (total_counter['EsmExtDbSearchRequests'], total_counter['IsmExtDbSearchRequests']))
            if total_counter['EsmExtDbSearchRequests'] <= 0 or total_counter['IsmExtDbSearchRequests'] <= 0:
                raise CommandFailure('Faulty counters: EsmExtDbSearchRequests: %s    IsmExtDbSearchRequests: %s' % (total_counter['EsmExtDbSearchRequests'],
                                                                                                                    total_counter['IsmExtDbSearchRequests']))
        elif user_config.traffic == 'EPC':
            _DEB('EsmExtDbSearchRequests: %s ' % total_counter['EsmExtDbSearchRequests'])
            if total_counter['EsmExtDbSearchRequests'] <= 0:
                raise CommandFailure('Faulty counter: EsmExtDbSearchRequests: %s ' % total_counter['EsmExtDbSearchRequests'])
        else :
            _DEB('IsmExtDbSearchRequests: %s' % (total_counter['IsmExtDbSearchRequests']))
            if total_counter['IsmExtDbSearchRequests'] <= 0:
                raise CommandFailure('Faulty counter: IsmExtDbSearchRequests: %s ' % total_counter['IsmExtDbSearchRequests'])
    except KeyError as e:
        raise CommandFailure('%s counter not found.' % e)


def CBA_SS7_SCTP_release_association_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--inst_id',
                      action='store', default=None,
                      help='Instance ID of the Association. By default it will be done for all.',
                      dest='inst_id')
    command_params.add_argument('--assoc_id',
                      action='store', default=1,
                      help='Association ID that will be released. By default is "%(default)s" ',
                      dest='assoc_id')
    return (parser)

def run_CBA_SS7_SCTP_release_association(user_config, node):

    node.start_CBASignmcli(identity ='signm')

    if user_config.inst_id is None:
        cmd = 'STTA:AssocID=%s;' % user_config.assoc_id
    else:
        cmd = 'STTA:IID=%s,AssocID=%s;' % (user_config.inst_id, user_config.assoc_id)

    output = node.run_command(cmd, identity = 'signm', full_answer=True)
    if 'EXECUTED' not in output:
        raise CommandFailure('%s' % output)

    print(output)

    return

def CBA_SS7_SCTP_info_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--param',
                      action='store', default=None,
                      help='Param to be used to filter the SCTP info. Example: "IID=1"',
                      dest='var')
    return (parser)

def run_CBA_SS7_SCTP_info(user_config, node):

    node.start_CBASignmcli(identity ='signm')

    if user_config.var is None:
        cmd = 'STNFO;'
    else:
        cmd = 'STNFO:%s;' % user_config.var

    sctp_info = node.run_command(cmd, identity = 'signm', full_answer=True)
    if 'EXECUTED' not in sctp_info:
        raise CommandFailure('%s' % sctp_info)

    print(sctp_info)
    return

def CBA_SS7_stack_reset_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-t',
                      action='store', default=30,
                      help='Max time waiting for all processes running again after reset. By default is "%(default)s" seconds',
                      dest='max_time')
    return (parser)

def run_CBA_SS7_stack_reset(user_config, node):

    node.start_CBASignmcli(identity ='signm')
    cmd = 'procr:ALL;'
    processes = node.run_command(cmd, identity = 'signm')
    if 'EXECUTED' not in ' '.join(processes):
        raise CommandFailure('%s' % ' '.join(processes))

    reset_on_going = True
    timeout = float(user_config.max_time)
    while reset_on_going:
        now = time.time()
        time.sleep(float(5))
        cmd = 'procp'
        processes = node.run_command(cmd, identity = 'signm')
        proc_state = {}
        for line in processes:
            if 'procp' in line or 'State' in line:
                continue

            try:
                key = line.split()[-1]
                proc_state[key].append(' '.join(line.split()[:-1]))
            except KeyError:
                proc_state.update({key:[' '.join(line.split()[:-1])]})

        reset_on_going = False
        for key in list(proc_state.keys()):
            if key != 'Running':
                reset_on_going = True
                break

        timeout -= time.time() - now
        if timeout < float(0) and reset_on_going:
            print('Timeout waiting for all processes running again after reset')
            for key in list(proc_state.keys()):
                if key != 'Running':
                    print('Processes in %s state \n\t%s' % (key, '\n\t'.join(proc_state[key])))
            return

def run_CBA_SS7_stack_processes_state(user_config, node):

    node.start_CBASignmcli(identity ='signm')
    cmd = 'procp'
    processes = node.run_command(cmd, identity = 'signm')
    proc_state = {}
    for line in processes:
        if 'procp' in line or 'State' in line:
            continue

        try:
            key = line.split()[-1]
            proc_state[key].append(' '.join(line.split()[:-1]))
        except KeyError:
            proc_state.update({key:[' '.join(line.split()[:-1])]})

    for key in list(proc_state.keys()):
        print('Processes in %s state \n\t%s' % (key, '\n\t'.join(proc_state[key])))

def CBA_envdata_get_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--variable', nargs='*',
                      action='store', default=None,
                      help='Variable to be used',
                      dest='var')

    return (parser)

def run_CBA_envdata_get(user_config, node):

    if user_config.var is None:
        for variable in node.envdata:
            value = node.get_envdata(variable)
            print('%-*s: %s' %(50, variable, value))

    else:
        for variable in user_config.var:
            value = node.get_envdata(variable)
            if value is not None:
                print('%-*s: %s' %(50, variable, value))


def CBA_envdata_set_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('VAR',
                      help='Variable to be used')

    command_params.add_argument('VALUE',
                      help='Value to be set')
    return (parser)

def run_CBA_envdata_set(user_config, node):
    node.set_envdata(user_config.VAR, user_config.VALUE)

def CBA_envdata_unset_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('VAR',
                      help='Variable to be used')
    return (parser)

def run_CBA_envdata_unset(user_config, node):
    if user_config.VAR not in node.envdata:
        raise WrongParameter('%s is not a valid env. data.' % user_config.VAR)

    node.unset_envdata(user_config.VAR)


def CBA_reload_proc_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('PROCESSOR',
                        help='Cluster processor')

    command_params.add_argument('-t',
                      action='store', default=120,
                      help='Max time in sec waiting for reloading the processor. By default is "%(default)s"',
                      dest='max_time')

    return (parser)


def run_CBA_reload_proc(user_config, node):

    processors = ['SC-1', 'SC-2'] + node.processors
    if user_config.PROCESSOR not in processors:
        raise WrongParameter('%s is not a valid processor. Allowed values are: %s' % (user_config.PROCESSOR, ' '.join(processors)))


def CBA_get_FEE_eVIP_elements_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-p', '--processors',nargs='+',
                      action='store', default=None,
                      help='List of processors used as filter',
                      dest='processors')

    command_params.add_argument('--ip',
                        default=False, action='store_true',
                        dest='ip',
                        help='Display additional IP information')

    return (parser)


def run_CBA_get_FEE_eVIP_elements(user_config, node):

    processors=[]
    allowed_processor = node.processors

    if user_config.processors is None:
        processors = allowed_processor
    else:
        for processor in user_config.processors:
            if processor in allowed_processor:
                processors.append(processor)
            else:
                raise WrongParameter('%s is not a valid processor. Allowed values are: %s' % (processor, ' '.join(allowed_processor)))

    for processor in sorted(processors):
        data = node.get_FEE_eVIP(processor, ip_list=user_config.ip)
        if data:
            print('%s \n%s' % (processor,data))
        else:
            print('%s \n' % (processor))


def CBA_unlock_proc_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('PROCESSORS',nargs='+',
                        help='Cluster processors')

    command_params.add_argument('-t',
                      action='store', default=90, type=int,
                      help='Max time in sec waiting for unlocking processor. By default is "%(default)s"',
                      dest='max_time')

    return (parser)


def run_CBA_unlock_proc(user_config, node):

    processors=[]
    allowed_processor = ['SC-1', 'SC-2'] + node.processors
    for processor in user_config.PROCESSORS:
        if processor in allowed_processor:
            processors.append(processor)
        else:
            raise WrongParameter('%s is not a valid processor. Allowed values are: %s' % (processor, ' '.join(allowed_processor)))

    for processor in processors:
        if node.processor_state(processor) == 'UNLOCKED':
            continue

        print('%s\tUnlock Time:    %s' % (processor, node.unlock_processor(processor,user_config.max_time)))


def CBA_lock_proc_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('PROCESSORS',nargs='+',
                        help='Cluster processors')

    command_params.add_argument('-t',
                      action='store', default=90, type=int,
                      help='Max time in sec waiting for locking processor. By default is "%(default)s"',
                      dest='max_time')

    return (parser)


def run_CBA_lock_proc(user_config, node):

    processors=[]
    allowed_processor = ['SC-1', 'SC-2'] + node.processors
    for processor in user_config.PROCESSORS:
        if processor in allowed_processor:
            processors.append(processor)
        else:
            raise WrongParameter('%s is not a valid processor. Allowed values are: %s' % (processor, ' '.join(allowed_processor)))


    for processor in processors:
        if node.processor_state(processor) == 'LOCKED':
            continue

        print('%s\tlock Time:    %s' % (processor, node.lock_processor(processor,user_config.max_time)))

def CBA_proc_status_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('PROCESSORS',nargs='*',
                        help='Cluster processors. If omitted all the processors will be displayed')

    return (parser)


def run_CBA_proc_status(user_config, node):

    processors=[]
    allowed_processor = ['SC-1', 'SC-2'] + node.processors
    if not user_config.PROCESSORS:
        processors = allowed_processor
    else:
        for processor in user_config.PROCESSORS:
            if processor in allowed_processor:
                processors.append(processor)
            else:
                raise WrongParameter('%s is not a valid processor. Allowed values are: %s' % (processor, ' '.join(allowed_processor)))

    for processor in sorted(processors):
        print('%s\t%s' % (processor,node.processor_state(processor)))


def run_CBA_check_AandA_enabled(user_config, node):

    if not node.is_AandA_enabled():
        raise CommandFailure('AandA not enabled')

def run_CBA_enable_AandA(user_config, node):
    node.enable_AandA()

def run_CBA_disable_AandA(user_config, node):
    node.disable_AandA()


def run_CBA_get_repository_list(user_config, node):

    cmd = 'cmw-repository-list'
    answer = node.run_command(cmd)
    if len(answer):
        for line in answer:
            print('%s' % (line))


def CBA_schedule_health_check_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--hcjob',
                      action='store', default='Full',
                      help='Name of the Health Check job where the scheduler event will be created. By default is "%(default)s" ',
                      dest='name_hcjob')
    command_params.add_argument('--period',
                      action='store', default=6,
                      help='Scheduler period in hours. By default is "%(default)s" hours',
                      dest='period')

    command_params.add_argument('--stop',
                      action='store', default=48,
                      help='Time in hours for stopping the scheduler. By default is "%(default)s" hours',
                      dest='stop')

    command_params.add_argument('--scheduler',
                      action='store', default='P_EVENT_TESTCASE',
                      help='Name of the scheduler event. By default is "%(default)s"',
                      dest='name_event')

    return (parser)


def run_CBA_schedule_health_check(user_config, node):

    start = datetime.today() + timedelta(seconds=int(10))
    stop = datetime.today() + timedelta(hours=int(user_config.stop))

    info = node.healthcheck_list_hcjobs(['HcJob'])
    if len(info['HcJob']):
        for key in info:
            if key == 'HcJob':
                hcjob_name = info[key]

        if user_config.name_hcjob not in info[key]:
            raise CommandFailure('HcJob %s not found in the system.' % user_config.name_hcjob )
    else:
        raise CommandFailure('Not HcJobs defined in the system.')

    cmd = 'configure'
    level = ',HcJob=%s,HcJobScheduler=1' % user_config.name_hcjob
    answer = node.run_health_check_cmd(cmd, next_level = level)
    _DEB('%s' % answer)
    if 'ERROR' in answer:
        raise CommandFailure('%s' % answer)

    cmd = 'administrativeState=UNLOCKED'
    answer = node.run_health_check_cmd(cmd, next_level = level)
    _DEB('%s' % answer)
    if 'ERROR' in answer:
        raise CommandFailure('%s' % answer)

    cmd = 'HcPeriodicEvent=%s' % user_config.name_event	
    answer = node.run_health_check_cmd(cmd, next_level = level)
    _DEB('%s' % answer)
    if 'ERROR' in answer:
        raise CommandFailure('%s' % answer)

    cmd = 'hours=%s' % user_config.period
    level = ',HcJob=%s,HcJobScheduler=1,HcPeriodicEvent=%s' % (user_config.name_hcjob,user_config.name_event)
    answer = node.run_health_check_cmd(cmd, next_level = level)
    _DEB('%s' % answer)
    if 'ERROR' in answer:
        raise CommandFailure('%s' % answer)

    cmd = 'startTime=%s' % start.strftime("%Y-%m-%dT%H:%M:%S")
    answer = node.run_health_check_cmd(cmd, next_level = level)
    _DEB('%s' % answer)
    if 'ERROR' in answer:
        raise CommandFailure('%s' % answer)

    cmd = 'stopTime=%s' % stop.strftime("%Y-%m-%dT%H:%M:%S")
    answer = node.run_health_check_cmd(cmd, next_level = level)
    _DEB('%s' % answer)
    if 'ERROR' in answer:
        raise CommandFailure('%s' % answer)

    cmd = 'commit'
    answer = node.run_health_check_cmd(cmd, next_level = level)
    _DEB('%s' % answer)
    if 'ERROR' in answer:
        raise CommandFailure('%s' % answer)


def CBA_remove_schedule_health_check_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--hcjob',
                      action='store', default='Full',
                      help='Name of the Health Check job where the scheduler event will be removed. By default is "%(default)s" ',
                      dest='name_hcjob')
    command_params.add_argument('--scheduler',
                      action='store', default='P_EVENT_TESTCASE',
                      help='Name of the scheduler event to be removed. By default is "%(default)s" ',
                      dest='name_event')

    return (parser)


def run_CBA_remove_schedule_health_check(user_config, node):

    info = node.healthcheck_list_hcjobs(['HcJob'])
    if len(info['HcJob']):
        for key in info:
            if key == 'HcJob':
                hcjob_name = info[key]

        if user_config.name_hcjob not in info[key]:
            raise CommandFailure('HcJob %s not found in the system.' % user_config.name_hcjob )
    else:
        raise CommandFailure('Not HcJobs defined in the system.')

    cmd = 'configure'
    level = ',HcJob=%s,HcJobScheduler=1' % user_config.name_hcjob
    answer = node.run_health_check_cmd(cmd, next_level = level)
    if 'ERROR' in answer:
        raise CommandFailure('%s' % answer)

    cmd = 'administrativeState=LOCKED'
    answer = node.run_health_check_cmd(cmd, next_level = level)
    _DEB('%s' % answer)
    if 'ERROR' in answer:
        raise CommandFailure('%s' % answer)

    cmd = 'no HcPeriodicEvent=%s' % user_config.name_event
    answer = node.run_health_check_cmd(cmd, next_level = level)
    if 'ERROR' in answer:
        raise CommandFailure('%s' % answer)

    cmd = 'commit'
    answer = node.run_health_check_cmd(cmd, next_level = level)
    if 'ERROR' in answer:
        raise CommandFailure('%s' % answer)


def CBA_get_diacc_dump_json_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-o','--output_path',
                      action='store', default='.',
                      help='C-Diameter json files will be stored in this path',
                      dest='output_path')

    return (parser)


def run_CBA_get_diacc_dump_json(user_config, node):

    # Get the dump JSON file from just one of the Payloads
    processor = node.payload[0]
    node.extend_connection(str(processor), processor)
    diacc_json_dir='/cluster/C-Diameter_transport_dump.json'
    cmd = '/opt/diacc/bin/dump_transport_latest.sh >%s' % diacc_json_dir
    node.run_command(cmd, identity = str(processor))

    if not os.path.exists(user_config.output_path):
        os.makedirs(user_config.output_path)
    try:
        node.download(diacc_json_dir, user_config.output_path)
    except IOError:
        raise CommandFailure('JSON file not found')

    cmd = 'rm %s*' % diacc_json_dir
    node.run_command(cmd)


def CBA_sync_ntp_server_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--ntp-server',
                      action='store', default=None,
                      help='ntp_server IP used to syncronize the CBA cluster nodes.',
                      dest='ntp_server')

    return (parser)


def run_CBA_sync_ntp_server(user_config, node):

    if user_config.ntp_server:
        if not validate_ip(user_config.ntp_server):
            raise WrongParameter('Wrong IP adress format for parameter %s ' % user_config.ntp_server)
    else:
        raise WrongParameter('Mandatory parameter ntp_server has been omited.')

    _DEB('Syncronizing CBA cluster with NTP server %s' % user_config.ntp_server)
    processors = node.all_processors
    for processor in sorted(processors):
        if 'SC-' in processor:
            answer = node.sync_processor_ntp_server(processor,user_config.ntp_server)
            time.sleep(float(2))
            print('Processor %s syncronized: %s' % (processor, answer[0]))
    time.sleep(float(5))
    # PLs node syncronized with SCs by restarting ntp service
    for processor in sorted(processors):
        if 'SC-' not in processor:
            answer = node.sync_processor_ntp_restart(processor)
            print('Processor %s syncronized: %s' % (processor, answer[0]))


def run_CBA_check_umask(user_config, node):
    UMASK = "0027"
    umask_ok=1
    processors = node.all_processors
    for processor in processors:
        umask = node.processor_umask(processor)
        if UMASK == umask:
            print('%s: %s   \tOK' % (processor, umask))
        else:
            umask_ok=0
            print('%s: %s   \tNOK' % (processor, umask))
    if not umask_ok:
        error_info = ('UMASK NOK on some of the nodes. Expected value:%s' % UMASK)
        raise CommandFailure(error_info)
    return umask_ok


def CBA_wait_datetime_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--wait-time',
                      action='store', default=None,
                      help='Date to wait until the HSS environment reach that date.',
                      dest='wait_time')

    return (parser)


def run_CBA_wait_datetime(user_config, node):

    if user_config.wait_time is None:
        _DEB('WAIT_TIME not defined. Nothing to wait.')
        n_secs_to_sleep = 0
    else:
        try:
            wait_time = datetime.strptime(user_config.wait_time, '%Y-%m-%dT%H:%M:%S')
        except Exception as e:
            error = '--wait-time %s not valid. Value shall be in format "Y-m-dTH:M:S"' % user_config.wait_time
            raise WrongParameter('%s' % error)

        _DEB('Waiting until datetime %s' % wait_time)

        current_time = datetime.strptime(node.datetime, '%Y-%m-%dT%H:%M:%S')
        _DEB('current datetime %s' % current_time)
        sleep_time = wait_time - current_time
        n_secs_to_sleep = sleep_time.total_seconds()
        if (n_secs_to_sleep > 0):
            _DEB('Sleeping %s seconds' % sleep_time)
            time.sleep(float(n_secs_to_sleep))
        else:
            _WRN('WAIT_TIME date is before current date of the ssytem. Nothing to wait')

    print(node.datetime)


def CBA_get_node_vdicos_vars_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--vars',
                      action='store', nargs='*',default=[],
                      help='Set specific vdicos vars to check. Optional. If not defined, the whole list of variables will be showed.',
                      dest='vdicos_vars')

    return (parser)

def run_CBA_get_node_vdicos_vars(user_config, node):

    cmd = 'vdicos-envdata-list'
    vdicos_var_list = node.run_command(cmd)
    _DEB('Current vdicos vars list: %s ' % vdicos_var_list)
    if user_config.vdicos_vars:
        vars_to_check=user_config.vdicos_vars
        _DEB('vdicos vars list passed as parameter: %s ' % vars_to_check)
    else:
        vars_to_check=vdicos_var_list
        
    info_vdicos_var = {}
    for check in vars_to_check:
        _DEB('Checking vdicos var : %s ' % check)
        if check not in vdicos_var_list:
            error = 'VDicos var %s to check is not in the vdicos vars list: ' % check
            raise WrongParameter('%s' % error)
        else:
            cmd = 'vdicos-envdata-get %s' % check
            answer = node.run_command(cmd)
            info_check = '%s' % answer[0]
            info_vdicos_var[check] = info_check

    for key in sorted(info_vdicos_var.keys()):
        print('%s = %s' % (key, info_vdicos_var[key]))


def CBA_disable_iTCO_watchdog_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('BACKUP_RELEASE',
                      help='Release of the backup to be restored to know if the iTCO watchdog must be disabled or not.')

    return (parser)

def run_CBA_disable_iTCO_watchdog(user_config, node):
    processors=['SC-1', 'SC-2']
    current_releases=['1.31', '1.32', '1.33', '1.34']
    allowed_releases=['1.24', '1.25', '1.26', '1.29', '1.29.1', '1.31', '1.32', '1.33', '1.34']
    backup_release = user_config.BACKUP_RELEASE
    if backup_release not in allowed_releases:
        error = 'Backup release passed as parameter "%s" is not valid. Values allowed: %s' % (backup_release, allowed_releases)
        _ERR(error)
        raise WrongParameter(error)

    itco_watchdog_enabled = True

    if node.is_virtual:
        print('Virtual environment. Only applies for Native environments.')
        return

    cmd = 'cmw-utility immlist -a release managedElementId=1'
    num_release = node.run_command(cmd)[0].split('=')[1]
    _DEB('Current HSS release is: %s ' % num_release)
    if num_release in current_releases and backup_release not in current_releases:
        print('Disabling iTCO watchdog before restoring from HSS release "%s" to HSS release "%s".' % (num_release, backup_release))
        timeout = float(60)
        now = time.time()
        while itco_watchdog_enabled:
            for processor in processors:
                node.disable_itco_watchdog(processor)
            time.sleep(float(5))
            itco_watchdog_enabled = False
            for processor in processors:
                if node.status_itco_watchdog_disabled(processor):
                    print('iTCO watchdog disabled on %s' % processor)
                else:
                    print('iTCO watchdog not disabled on %s yet' % processor)
                    itco_watchdog_enabled = True
            timeout -= time.time() - now
            if timeout < 0:
                raise ExecutionTimeout('Timeout trying to disable iTCO watchdog')
    else:
        print('Not necessary to disable iTCO watchdog before restoring from HSS release "%s" to HSS release "%s".' % (num_release, backup_release))

