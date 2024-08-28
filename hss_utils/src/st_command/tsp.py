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
import threading
import Queue
import pexpect
import xml.etree.ElementTree as ET
import glob
import shutil

import e3utils.log as logging
_DEB = logging.internal_debug
_WRN = logging.warning
_ERR = logging.error
_INF = logging.info

import hss_utils.connection
import hss_utils.connection.session
import hss_utils.connection.monitor
from . import ExecutionTimeout
from . import NotFound
from . import CommandFailure
from . import WrongParameter
from . import create_connection_summary
from . import DYNAMIC_PROCESSES

PROC_REL_STARTED = 1
PROC_REL_OK = 2
PROC_REL_FAILED = 3
PLAN_REC_STARTED = 4
PLAN_REC_OK = 5
PLAN_REC_FAILED = 6
BACKUP_STARTED = 16
BACKUP_OK = 17
BACKUP_FAILED = 18
ENABLE_PROC_STARTED = 28
ENABLE_PROC_OK = 29
ENABLE_PROC_FAILED = 30
DISABLE_PROC_STARTED = 31
DISABLE_PROC_OK = 32
DISABLE_PROC_FAILED = 33
REACT_BACKUP_STARTED = 34
REACT_BACKUP_OK = 35
REACT_BACKUP_FAILED = 36

NOTIFICATIONS = {
    PROC_REL_STARTED:   'Processor Reload Started',
    PROC_REL_OK:        'Processor Reload Finished Successfully',
    PROC_REL_FAILED:    'Processor Reload Failed',
    PLAN_REC_STARTED:   'Planned Reconfiguration Started',
    PLAN_REC_OK:        'Planned Reconfiguration Finished Successfully',
    PROC_REL_FAILED:    'Planned Reconfiguration Failed',
    BACKUP_STARTED:     'Backup started',
    BACKUP_OK:          'Backup Finished Successfully',
    BACKUP_FAILED:      'Backup Failed',
    ENABLE_PROC_STARTED:'Enable Processor Started',
    ENABLE_PROC_OK:     'Enable Processor Finished Successfully',
    ENABLE_PROC_FAILED: 'Enable Processor Failed',
    DISABLE_PROC_STARTED:'Disable Processor Started',
    DISABLE_PROC_OK:    'Disable Processor Finished Successfully',
    DISABLE_PROC_FAILED:'Disable Processor Failed',
    REACT_BACKUP_STARTED:'Reactivation Of Backup Started',
    REACT_BACKUP_OK:    'Reactivation Of Backup Done OK',
    REACT_BACKUP_FAILED:'Reactivation Of Backup Failed'
}

def get_notification_message(notification):
    try:
        return NOTIFICATIONS[notification]
    except KeyError:
        return 'Unkowm notification'

def run_TSP_get_time(user_config, node):

    cmd = 'date +%F" "%R:%S'
    answer = node.run_command(cmd)
    if len(answer) > 0:
        print answer[0]

def TSP_set_loadreg_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('LOADLEVEL',
                        help='Load regulation level to be set')

    return (parser)

def run_TSP_set_loadreg(user_config, node):

    node.start_TelorbCLI(identity ='cli')
    for processor in node.payload:
        cmd = '/CLI/Processors/setloadregulationlevel %s %s' % (processor,user_config.LOADLEVEL)
        node.run_command(cmd, identity = 'cli', answer = {'Load regulation level set for the given processor' :''}, timeout = 5.0)

def TSP_check_upgrade_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('UPGRADEPACKAGE',
                        help='Upgrade package used as filter')

    return (parser)

def run_TSP_check_upgrade(user_config, node):

    node.start_TelorbCLI(identity ='cli')
    cmd = '/CLI/Upgrades/list'
    answer = node.run_command(cmd, identity = 'cli', timeout = 5.0)
    if user_config.UPGRADEPACKAGE not in ' '.join(answer):
        raise NotFound('%s upgrade package not found' % user_config.UPGRADEPACKAGE)

def run_TSP_check_autobackup_upgrade_off(user_config, node):

    node.start_TelorbCLI(identity ='cli')
    cmd = '/CLI/Upgrades/list'
    answer = node.run_command(cmd, identity = 'cli', timeout = 5.0)
    for line in answer:
        if 'Autobackup is' in line and 'on' in line:
            raise CommandFailure('Autobackup is on')

def TSP_set_autobackup_upgrade_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('STATE',
                        help='State to be set. Allowed values are: on / off')

    return (parser)

def run_TSP_set_autobackup_upgrade(user_config, node):

    if user_config.STATE not in ['on', 'off']:
        raise WrongParameter('%s is not a valid state. Allowed values are: on / off' % user_config.STATE)

    node.start_TelorbCLI(identity ='cli')
    cmd = '/CLI/Upgrades/autobackup %s' % ('-y' if user_config.STATE == 'on' else '-n')
    node.run_command(cmd, identity = 'cli', timeout = 5.0)


def TSP_check_loadreg_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('LOADREGULATIONLEVEL',
                        help='Load regulation level used as filter')

    return (parser)

def run_TSP_check_loadreg(user_config, node):

    node.start_TelorbCLI(identity ='cli')
    for processor in node.payload:
        cmd = '/CLI/Processors/getprocessorinfo %s' % processor
        answer = node.run_command(cmd, identity = 'cli', timeout = 5.0)
        regex = re.compile(r'Load Regulation level: (\d+)')
        for line in answer:
            searchObj = regex.match(line)
            if searchObj and user_config.LOADREGULATIONLEVEL != searchObj.group(1):
                raise CommandFailure('Processor %s has a different level %s' % (processor, searchObj.group(1)))

def TSP_check_dbn_mem_alarm_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('DBNMEMALARMLEVEL',
                        help='DBN memory alarm level used as filter')

    return (parser)

def run_TSP_check_dbn_mem_alarm(user_config, node):

    node.start_TelorbCLI(identity ='cli')
    for processor in node.payload:
        cmd = '/CLI/Processors/getprocessorinfo %s' % processor
        answer = node.run_command(cmd, identity = 'cli', timeout = 5.0)
        regex = re.compile(r'DBN Memory Alarm level: (\d+)')
        for line in answer:
            searchObj = regex.match(line)
            if searchObj and user_config.DBNMEMALARMLEVEL != searchObj.group(1):
                raise CommandFailure('Processor %s has a different level %s' % (processor, searchObj.group(1)))


def TSP_check_mem_alarm_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('MEMALARMLEVEL',
                        help='Memory alarm level used as filter')

    return (parser)

def run_TSP_check_mem_alarm(user_config, node):

    node.start_TelorbCLI(identity ='cli')
    for processor in node.payload:
        cmd = '/CLI/Processors/getprocessorinfo %s' % processor
        answer = node.run_command(cmd, identity = 'cli', timeout = 5.0)
        regex = re.compile(r'Memory Alarm level: (\d+)')
        for line in answer:
            searchObj = regex.match(line)
            if searchObj and user_config.MEMALARMLEVEL != searchObj.group(1):
                raise CommandFailure('Processor %s has a different level %s' % (processor, searchObj.group(1)))

def TSP_set_mem_alarm_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('MEMALARMLEVEL',
                        help='DBN mem alarm level to be set')

    return (parser)

def run_TSP_set_mem_alarm(user_config, node):

    node.start_TelorbCLI(identity ='cli')
    for processor in node.payload:
        cmd = '/CLI/Processors/setmemoryalarmlevel %s %s' % (processor,user_config.MEMALARMLEVEL)
        node.run_command(cmd, identity = 'cli', answer = {'Memory alarm level set' :''}, timeout = 5.0)


def TSP_set_dbn_mem_alarm_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('DBNMEMALARMLEVEL',
                        help='DBN mem alarm level to be set')

    return (parser)

def run_TSP_set_dbn_mem_alarm(user_config, node):

    node.start_TelorbCLI(identity ='cli')
    for processor in node.payload:
        cmd = '/CLI/Processors/setDBNmemoryalarmlevel %s %s' % (processor,user_config.DBNMEMALARMLEVEL)
        node.run_command(cmd, identity = 'cli', answer = {'DBN memory alarm level set' :''}, timeout = 5.0)

def TSP_set_dbn_share_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('DBNSHARELEVEL',
                        help='DBN share level to be set')

    return (parser)

def run_TSP_set_dbn_share(user_config, node):

    node.start_TelorbCLI(identity ='cli')
    for processor in node.payload:
        cmd = '/CLI/Processors/setDBNmemoryshare %s %s' % (processor,user_config.DBNSHARELEVEL)
        node.run_command(cmd, identity = 'cli', answer = {'DBN memory share set' :''}, timeout = 5.0)

def TSP_wait_for_nofication_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('TIMEOUT',
                        help='Max time waiting for')
    command_params.add_argument('NOTIFICATION', nargs='+',
                        help='Notification [Notification....[Notification]]')

    command_params.add_argument('-l', '--loader',
                      action='store', default=None,
                      help='Specific loader to be used as monitor',
                      dest='loader')
    return (parser)


def run_TSP_wait_for_nofication(user_config, node):

    node.create_monitor(monitor_type=hss_utils.connection.monitor.TspNotificationMonitor,
                        identity='notification', processor=user_config.loader)

    TSP_wait_for_nofication(node, user_config.NOTIFICATION, user_config.TIMEOUT)


def TSP_wait_for_nofication(node, wait_for_list=[], exit_on_list=[], monitorId='notification', timeout=-1):

    while True:
        now = time.time()

        event = node.wait_event(identity=monitorId, timeout=float(timeout))
        if event is not None:
            _DEB('Received notification: %s' % repr(event))
            notification = int(str.strip((event.split(':')[1])))

            if notification in wait_for_list:
                _DEB('Expected Notification: %s' % get_notification_message(notification))
                wait_for_list.remove(notification)

            elif notification in exit_on_list:
                raise CommandFailure('Exit after Notification: %s' % get_notification_message(notification))

            else:
                _DEB('Unexpected Notification: %s' % get_notification_message(notification))

            if len(wait_for_list) == 0:
                break

        timeout -= time.time() - now
        if timeout < 0:
            raise ExecutionTimeout('Timeout waiting for notification')

def TSP_check_alarm_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('FILTER', nargs='*',
                        help='"FIELD_NAME":"TEXT" ["FIELD_NAME":"TEXT"....["FIELD_NAME":"TEXT"]]')

    command_params.add_argument('-x','--exclude',nargs='*',
                      action='store', default='',
                      help='Substring included in Probable Cause used as exclusion filter',
                      dest='exclude')

    command_params.add_argument('-p', '--print',
                      action='store_true', default=False,
                      help='Print alarms matching filters',
                      dest='display')

    return (parser)


def run_TSP_check_alarm(user_config, node):
    alarm_filters = {}
    output = []
    for field in user_config.FILTER:
        name = field[:field.find(':')]
        value = field[field.find(':') + 1 :]
        alarm_filters.update({name:value})

    node.start_TelorbCLI(identity ='cli')
    cmd = '/CLI/AlarmsAndNotifications/printalarms'
    alarms = node.run_command(cmd, identity ='cli')

    regex = re.compile(r'ALARM (\d+):')
    for alarm in alarms:
        searchObj = regex.match(alarm)
        if searchObj:
            cmd = '/CLI/AlarmsAndNotifications/printalarms -d %s' % searchObj.group(1)
            answer = node.run_command(cmd, identity ='cli')

            skip = False
            for line in answer:
                if 'Probable Cause' in line:
                    for exlude in user_config.exclude:
                        if exlude in line:
                            skip = True
                            break;
            if skip:
                continue

            full_answer = ' '.join(answer)
            found = True
            for key, value in alarm_filters.iteritems():
                if key not in full_answer or value not in full_answer:
                    found = False
                    break
            if found:
                output += answer

    if len(output) == 0:
        print 'No alarms'
        #raise NotFound('There is not alarm matching the filter criteria')

    if user_config.display:
        for line in output:
            print line


def TSP_wait_for_alarm_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('TIMEOUT',
                        help='Max time waiting for')
    command_params.add_argument('ALARM',
                        help='Substring include in the alarm message')

    command_params.add_argument('-t',
                      action='store', default='',
                      help='Type of alarm used as filter. Default not filetr is used. Allowed values are: Minor | Warning | Major | Critical | CLEARED',
                      dest='type')

    return (parser)


def run_TSP_wait_for_alarm(user_config, node):


    if user_config.type not in ['', 'Minor', 'Warning', 'Major', 'Critical', 'CLEARED']:
        raise WrongParameter('%s is not a valid alarm type. Allowed values are: Minor | Warning | Major | Critical | CLEARED' % user_config.type)

    timeout = float(user_config.TIMEOUT)
    node.create_monitor(monitor_type = hss_utils.connection.monitor.TspAlarmMonitor, identity = 'alarm')

    while True:
        now = time.time()

        alarm = node.wait_event(identity = 'alarm', timeout=timeout)
        if alarm is not None:
            _DEB('Received alarm: %s' % repr(alarm))
            if user_config.ALARM in alarm and user_config.type in alarm:
                _DEB('Expected Alarm: %s' % alarm)
                break
            else:
                _DEB('Unexpected Alarm: %s' % alarm)

        timeout -= time.time() - now
        if timeout < 0:
            raise ExecutionTimeout('Timeout waiting for alarm')


def TSP_check_backup_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('BACKUPNAME',
                        help='Backup name used as filter')

    return (parser)

def run_TSP_check_backup(user_config, node):
    cmd = 't-util /CLI/Backups/list'
    backups = node.run_command(cmd)

    for backup in backups:
        if backup.startswith('(A)'):
            backup = backup[3:]

        if user_config.BACKUPNAME == backup.strip():
            return

    raise NotFound('%s backup does not exist' % user_config.BACKUPNAME)

def TSP_get_backup_size_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('BACKUPNAME',
                        help='Backup name used as filter')

    return (parser)

def run_TSP_get_backup_size(user_config, node):

    if not node.file_exist('/opt/telorb/axe/loadingGroup01_1/backups/%s' % user_config.BACKUPNAME):
        raise NotFound('%s backup does not exist' % user_config.BACKUPNAME)

    cmd = 'du -ks /opt/telorb/axe/loadingGroup01_1/backups/%s | cut -f1' % user_config.BACKUPNAME
    answer = node.run_command(cmd)
    if len(answer) > 0:
        print answer[0]

def run_TSP_get_active_backup(user_config, node):

    cmd = 't-util /CLI/Backups/list'
    backups = node.run_command(cmd)

    for backup in backups:
        if backup.startswith('(A)'):
            print backup[3:]
            return

    raise CommandFailure('Active backup not found')

def TSP_create_backup_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('BACKUPNAME',
                        help='Backup name used as filter')

    command_params.add_argument('-t',
                      action='store', default=60,
                      help='Max time in sec waiting for backup creation.',
                      dest='max_time')

    return (parser)


def run_TSP_create_backup(user_config, node):

    timeout = float(user_config.max_time)
    node.create_monitor(monitor_type = hss_utils.connection.monitor.TspNotificationMonitor, identity = 'notification')

    cmd = 't-util /CLI/Backups/create %s' % user_config.BACKUPNAME
    answer = node.run_command(cmd)

    if 'Backup has been ordered' not in ' '.join(answer):
        raise CommandFailure('Create %s backup failed' % user_config.BACKUPNAME)

    started = time.time()
    TSP_wait_for_nofication(node,
                            wait_for_list=[BACKUP_STARTED,BACKUP_OK],
                            exit_on_list=[BACKUP_FAILED],
                            timeout=user_config.max_time)

    print 'Backup Time:    %s' % str(time.time()-started)


def TSP_activate_backup_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('BACKUPNAME',
                        help='Backup name used as filter')

    command_params.add_argument('-t',
                      action='store', default=60,
                      help='Max time in sec waiting for backup activation.',
                      dest='max_time')

    return (parser)

def run_TSP_activate_backup(user_config, node):

    node.create_monitor(monitor_type = hss_utils.connection.monitor.TspNotificationMonitor, identity = 'notification')

    cmd = 't-util /CLI/Backups/activate %s' % user_config.BACKUPNAME
    node.run_command(cmd)

    TSP_wait_for_nofication(node,
                            wait_for_list=[REACT_BACKUP_STARTED, REACT_BACKUP_OK],
                            exit_on_list=[REACT_BACKUP_FAILED],
                            timeout=user_config.max_time)

def TSP_get_connection_by_port_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('PORT',
                        help='Port used as filter')

    command_params.add_argument('--proc',
                      action='store', default=None,
                      help='Specific Processor used as filter',
                      dest='processor')

    command_params.add_argument('--summary',
                      action='store_true', default=False,
                      help='Print the number of connections ordered by status',
                      dest='summary')

    return (parser)

def run_TSP_get_connection_by_port(user_config, node):

    processors = []
    if  user_config.processor is None:
        processors = node.payload
    else:
        processors.append(user_config.processor)

    for  processor in processors:
        node.extend_connection(str(processor), processor)   
        cmd = 'eptutil /processors/%s/net/util/netstat | grep ".%s " ' % (processor, user_config.PORT)
        print '\n%s' % processor
        if user_config.summary:
            create_connection_summary(node.run_command(cmd))
        else:
            print '\n'.join(node.run_command(cmd))

def TSP_get_IPconnection_processors_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('HOST',
                        help='Specific Host IP or WHOLE_TABLE')

    return (parser)

def run_TSP_get_IPconnection_processors(user_config, node):

    for  processor in node.cluster:
        cmd = "eptutil /processors/%s/net/vip/connection_table | sed \"s/\([TCP|UDP|SCTP|Proto]\)/%s:\\1/\"" % (processor, processor)
        info = node.run_command(cmd)

        cmd = "eptutil /processors/%s/net/socket_register/published_sockets |sed \"s/^800 [|]\([\.0-9]*\) *[|]132  [|]\([0-9]*\) *[|][0-9]* -> \(.*\)$/%s:SCTP \\1:\\2 XXX.XXX.XXX.XXX:YYYY->\\3/g\"" % (processor, processor)
        info += node.run_command(cmd)

        for line in info:
            if line.startswith('Proc'):
                if user_config.HOST == 'WHOLE_TABLE':
                    print line
                elif user_config.HOST in line:
                    print processor
                    break

def TSP_get_vip_FE_processors_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-n',
                      action='store_true', default=False,
                      help='Show network interfaces for Front-End processors',
                      dest='show_interfaces')

    return (parser)

def run_TSP_get_vip_FE_processors(user_config, node):
    get_processors(node, 'network_interfaces', user_config.show_interfaces)

def run_TSP_get_dicos(user_config, node):
    get_processors(node, 'payload')

def run_TSP_get_linux(user_config, node):
    get_processors(node, 'linux')

def run_TSP_get_loaders(user_config, node):
    get_processors(node, 'loader')

def run_TSP_get_processors(user_config, node):
    get_processors(node, 'processors')

def run_TSP_get_cluster_processors(user_config, node):
    get_processors(node, 'cluster')

def get_processors(node, proc_type, show_interfaces = False):
    if proc_type in ['payload', 'controller', 'loader', 'linux','network_interfaces','cluster', 'processors']:
        for processor in eval('node.%s' % proc_type):
            if proc_type == 'network_interfaces':
                processor = processor.split(':')
                print '%s%s' % (processor[0],':%s' % processor[1] if show_interfaces else '')
            else:
                print processor


def run_TSP_clean_app_logs(user_config, node):

    cmd = 'cat /opt/mirror/tsp/applog/applog.cfg'
    info = node.run_command(cmd)

    applog_prefix_list = []
    for line in info:
        line = line.split(':')
        if len(line) > 0:
            applog_prefix_list.append(line[0])

    current_io = node.run_command('hostname')[0]
    node.extend_connection('root_primary_io', current_io, user='root',password='rootroot')

    for applog_prefix in applog_prefix_list:
        if applog_prefix != '':
            cmd = 'truncate -s 0  /opt/mirror/tsp/applog/applog.%s*' % applog_prefix
            node.run_command(cmd, identity ='root_primary_io')


    for proc in node.linux:
        identity = '%s' % proc
        node.extend_connection(identity, proc, user='telorb',password='telorb', session_type=hss_utils.connection.session.StandardLinux)
        node.run_command('su', identity =identity, answer = {'Password:': 'rootroot'})
        if not node.file_exist('/usr/sbin/mysqld', identity = identity):
            _DEB('%s Not needed to delete row in mysql' % identity)
            continue

        for applog_prefix in applog_prefix_list:
            if applog_prefix != '':
                cmd = 'mysql -umysql -pmysql -hplatform-vip  -D logging -e "delete from %s"' % applog_prefix
                node.run_command(cmd, identity =identity)

    cmd = 'ps -fe | grep -i "/usr/sbin/dicosapplog -c" | grep -v grep | awk \'{print $2}\''
    process_to_kill = node.run_command(cmd)
    if len (process_to_kill):
        cmd = 'kill %s' % process_to_kill[0]
        node.run_command(cmd, identity ='root_primary_io')

    for proc in node.linux:
        identity = '%s' % proc
        if not node.file_exist('/opt/telorb/etc/rc.d/init.d/dbwriter', identity = identity):
            _DEB('%s Not needed to stop dbwriter' % identity)
            continue


        cmd = '/opt/telorb/etc/rc.d/init.d/dbwriter stop'
        node.run_command(cmd, identity = identity)


def run_TSP_clean_pmf_logs(user_config, node):

    cmd = 'find /opt/telorb/axe/tsp/NM/PMF/reporterLogs -type f -exec rm -f {} \;'
    node.run_command(cmd, timeout=300)


def TSP_start_profiler_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('PROCESSOR',
                        help='Dicos processor')

    return (parser)

def run_TSP_start_profiler(user_config, node):

    if user_config.PROCESSOR not in node.payload:
        raise WrongParameter('%s is not a valid Dicos processor. Allowed values are: %s' % (user_config.PROCESSOR, ' '.join(node.payload)))

    node.start_Telnet_Payload(user_config.PROCESSOR, identity ='telnet_payload')
    cmd = '/profiler/start'
    answer = node.run_command(cmd, identity = 'telnet_payload')
    for line in answer:
        if 'Profiling already started' in line:
            raise CommandFailure('Profiling already started in %s' % user_config.PROCESSOR)


def TSP_stop_profiler_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('PROCESSOR',
                        help='Dicos processor')

    return (parser)

def run_TSP_stop_profiler(user_config, node):

    if user_config.PROCESSOR not in node.payload:
        raise WrongParameter('%s is not a valid Dicos processor. Allowed values are: %s' % (user_config.PROCESSOR, ' '.join(node.payload)))

    node.start_Telnet_Payload(user_config.PROCESSOR, identity ='telnet_payload')
    cmd = '/profiler/stop'
    answer = node.run_command(cmd, identity = 'telnet_payload')
    for line in answer:
        if 'No profiling started' in line:
            raise CommandFailure('No profiling started in %s' % user_config.PROCESSOR)

def TSP_disable_proc_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('PROCESSOR',
                        help='Cluster processor')

    command_params.add_argument('-t',
                      action='store', default=120,
                      help='Max time in sec waiting for disabling processor.',
                      dest='max_time')

    return (parser)

def run_TSP_disable_proc(user_config, node):

    if user_config.PROCESSOR not in node.cluster:
        raise WrongParameter('%s is not a valid cluster processor or it is already disabled. Allowed values are: %s' % (user_config.PROCESSOR, ' '.join(node.cluster)))

    loader = None
    if node.is_primary_loader(user_config.PROCESSOR):
        for processor in node.loader:
            if processor != user_config.PROCESSOR:
                loader = processor
                break

        if loader is None:
           raise CommandFailure('%s is the unique loader available' % user_config.PROCESSOR)

        node.start_TelorbCLI(identity ='cli', force_primary = False, processor = loader)
        node.create_monitor(monitor_type = hss_utils.connection.monitor.TspNotificationMonitor,
                            identity = 'notification', force_primary = False, processor = loader)
    else:
        node.start_TelorbCLI(identity ='cli')
        node.create_monitor(monitor_type = hss_utils.connection.monitor.TspNotificationMonitor, identity = 'notification', start = True)

    cmd = '/CLI/Processors/disable %s' % user_config.PROCESSOR
    answer = node.run_command(cmd, identity = 'cli')

    if 'ordered' not in ' '.join(answer):
        raise CommandFailure('Disable Processor %s failed' % user_config.PROCESSOR)

    started = time.time()
    TSP_wait_for_nofication(node,
                            wait_for_list=[DISABLE_PROC_STARTED, DISABLE_PROC_OK],
                            exit_on_list=[DISABLE_PROC_FAILED],
                            timeout=user_config.max_time)

    print 'Disable Time:    %s' % str(time.time()-started)

def TSP_reload_processor_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('PROCESSOR',
                        help='Cluster processor')

    command_params.add_argument('-o',
                      action='store_true', default=False,
                      help='Just reload. Do not wait for notifications.',
                      dest='omit')

    command_params.add_argument('-t',
                      action='store', default=120,
                      help='Max time in sec waiting for disabling processor.',
                      dest='max_time')

    return (parser)

def run_TSP_reload_processor(user_config, node):

    if user_config.PROCESSOR not in node.cluster:
        raise WrongParameter('%s is not a valid cluster processor or it is already disabled. Allowed values are: %s' % (user_config.PROCESSOR, ' '.join(node.cluster)))

    loader = None
    if node.is_primary_loader(user_config.PROCESSOR):
        for processor in node.loader:
            if processor != user_config.PROCESSOR:
                loader = processor
                break

        if loader is None:
           raise CommandFailure('%s is the unique loader available' % user_config.PROCESSOR)

        node.start_TelorbCLI(identity ='cli', force_primary = False, processor = loader)
        if not user_config.omit:
            node.create_monitor(monitor_type = hss_utils.connection.monitor.TspNotificationMonitor,
                                             identity = 'notification', force_primary = False,
                                             processor = loader, start = True)
    else:
        node.start_TelorbCLI(identity ='cli')
        if not user_config.omit:
            node.create_monitor(monitor_type = hss_utils.connection.monitor.TspNotificationMonitor,
                                             identity = 'notification', start = True)

    cmd = '/CLI/Processors/reload %s' % user_config.PROCESSOR
    answer = node.run_command(cmd, identity = 'cli')

    if 'ordered' not in ' '.join(answer):
        raise CommandFailure('Reload Processor %s failed' % user_config.PROCESSOR)

    if user_config.omit:
        return

    started = time.time()
    TSP_wait_for_nofication(node,
                            wait_for_list=[PROC_REL_STARTED, PROC_REL_OK, PLAN_REC_STARTED, PLAN_REC_OK],
                            exit_on_list=[PROC_REL_FAILED, PLAN_REC_FAILED],
                            timeout=user_config.max_time)

    print 'Reload Time:    %s' % str(time.time()-started)


def TSP_enable_proc_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('PROCESSOR',
                        help='Cluster processor')

    command_params.add_argument('-t',
                      action='store', default=120,
                      help='Max time in sec waiting for enabling processor.',
                      dest='max_time')

    return (parser)

def run_TSP_enable_proc(user_config, node):

    if user_config.PROCESSOR not in node.processors:
        raise WrongParameter('%s is not a valid processor. Allowed values are: %s' % (user_config.PROCESSOR, ' '.join(node.processors)))


    if user_config.PROCESSOR in node.cluster:
        raise WrongParameter('%s is already enabled' % user_config.PROCESSOR)

    node.start_TelorbCLI(identity ='cli')
    node.create_monitor(monitor_type = hss_utils.connection.monitor.TspNotificationMonitor, identity = 'notification', start = True)

    cmd = '/CLI/Processors/enable %s' % user_config.PROCESSOR
    answer = node.run_command(cmd, identity = 'cli')

    if 'ordered' not in ' '.join(answer):
        raise CommandFailure('Enable Processor %s failed' % user_config.PROCESSOR)

    started = time.time()
    TSP_wait_for_nofication(node,
                            wait_for_list=[ENABLE_PROC_STARTED, ENABLE_PROC_OK],
                            exit_on_list=[ENABLE_PROC_FAILED],
                            timeout=user_config.max_time)

    print 'Enable Time:    %s' % str(time.time()-started)


def run_TSP_find_primary_loader(user_config, node):

    print node.primary_loader


def run_TSP_find_DIA_HANDLER_proc(user_config, node):

    for processor in node.payload:
        if node.find_process(processor, 'DIA_PRC_HandlerProcess') > 0:
            print processor


def TSP_find_process_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('PROCESS',
                        help='Process to find')

    command_params.add_argument('-p',
                      action='store_true', default=False,
                      help='Prints the number of ocurrences.',
                      dest='number')

    return (parser)


def run_TSP_find_process(user_config, node):

    for processor in node.payload:
        counter = node.find_process(processor, user_config.PROCESS)
        extra_info = '\t%s\t%s' % (user_config.PROCESS, counter) if user_config.number else ''
        print '%s%s' % (processor, extra_info)

def TSP_is_there_process_on_processor_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('PROCESS',
                        help='Process to find')

    command_params.add_argument('PROCESSOR',
                        help='Process to find')

    command_params.add_argument('-p',
                      action='store_true', default=False,
                      help='Prints the number of ocurrences.',
                      dest='number')

    return (parser)


def run_TSP_is_there_process_on_processor(user_config, node):

    if user_config.PROCESSOR not in node.payload:
        raise WrongParameter('%s is not a valid processor. Allowed values are: %s' % (user_config.PROCESSOR, ' '.join(node.payload)))

    counter = node.find_process(user_config.PROCESSOR, user_config.PROCESS)
    if counter == 0:
        raise CommandFailure('%s is not running in processor %s' % (user_config.PROCESS, user_config.PROCESSOR))

    if user_config.number:
        print counter


def TSP_find_dynamic_process_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-l', '--list',
                      action='store_true', default=False,
                      help='Print the list of supportted dynamic processes.',
                      dest='list')

    command_params.add_argument('-p',
                      action='store_true', default=False,
                      help='Prints the number of ocurrences.',
                      dest='number')

    return (parser)


def run_TSP_find_dynamic_process(user_config, node):

    if user_config.list:
        print '\n'.join(DYNAMIC_PROCESSES)
        return

    dynamic_process_found = False
    for processor in node.payload:
        info = node.find_all_processes(processor)
        for process in DYNAMIC_PROCESSES:
            counter = info.count(process)
            if counter:
                extra_info = '\t%s\t%s' % (process, counter) if user_config.number else ''
                dynamic_process_found = True
                print '%s%s' % (processor, extra_info)

    if dynamic_process_found:
        raise CommandFailure('Dynamic processes found')
    else:
        print ' '


def TSP_get_traffic_info_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-t','--traffic_type',
                        default = 'IMS',choices = ['IMS', 'EPC'],
                        dest='trafic_type',
                        help='Traffic type used as filter. Allowed values IMS | EPC')
    command_params.add_argument('-f', '--force-vipo',
                      action='store_true', default=False,
                      help='Use the node value as vipo',
                      dest='host_is_oam')
    command_params.add_argument('--zone',default = 1,
                        action='store',
                        help='Specify GeoRed zone. Allowed values 1 or 2',
                        dest='zone')
    command_params.add_argument('-s','--specific',nargs='+',default=None,
                        choices = ['hss_version', 'dia_tcp', 'dia_sctp','oam','radius','extdb',
                                   'vector_supplier','controller','HSS-MapSriForLcs'],
                        action='store',
                        help='Specify value',
                        dest='specific')

    command_params.add_argument('-6',
                        default=False, action='store_true',
                        dest='ipv6',
                        help='Select IPv6')
    return (parser)


def run_TSP_get_traffic_info(user_config, node):

    if user_config.specific is None:
        user_config.specific = ['hss_version', 'dia_tcp', 'dia_sctp','oam','radius','extdb',
                                   'vector_supplier','controller','HSS-MapSriForLcs']

    answer = node.get_traffic_info(user_config.trafic_type, user_config.specific, zone=int(user_config.zone), host_is_oam=user_config.host_is_oam, IPv6=user_config.ipv6)

    keys = answer.keys()
    keys.sort()
    for key in keys:
        if key in user_config.specific:
            print '%s=%s' % (key, answer[key])


def TSP_restore_backup_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-b','--backupname',
                      action='store', default=None,
                      help='Backup name to be restored. Default is the active backup',
                      dest='BACKUPNAME')

    command_params.add_argument('-t',
                      action='store', default=1500,
                      help='Max time waiting for. By default is 1500 seconds',
                      dest='timeout')

    return (parser)

def run_TSP_restore_backup(user_config, node):

    cmd = 't-util /CLI/Backups/list'
    backups = node.run_command(cmd)
    active_backup = None
    for backup in backups:
        if backup.startswith('(A)'):
            active_backup = backup[3:].strip()

    if active_backup is None:
        raise CommandFailure('Problem reading the active backup')

    if user_config.BACKUPNAME is not None:
        if user_config.BACKUPNAME != active_backup:
            node.create_monitor(monitor_type = hss_utils.connection.monitor.TspNotificationMonitor, identity = 'notification')

            cmd = 't-util /CLI/Backups/activate %s' % user_config.BACKUPNAME
            node.run_command(cmd)

            TSP_wait_for_nofication(node,
                                    wait_for_list=[REACT_BACKUP_STARTED, REACT_BACKUP_OK],
                                    exit_on_list=[REACT_BACKUP_FAILED],
                                    timeout=user_config.timeout)

            node.stop_monitor('notification')

    run_TSP_perform_zone_reload(user_config, node)


def TSP_perform_zone_reload_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-t',
                      action='store', default=1500,
                      help='Max time waiting for. By default is 1500 seconds',
                      dest='timeout')
    return (parser)


def run_TSP_perform_zone_reload(user_config, node):

    node.create_monitor(monitor_type = hss_utils.connection.monitor.TspAlarmMonitor,identity = 'alarm')

    node.start_TelorbCLI(identity ='cli')
    cmd = '/CLI/Processors/zonereload'
    node.run_command_async(cmd, identity = 'cli', answer = {'Confirm action ' :';'}, timeout = 15.0)

    node.close_connection(identity = 'cli')

    timeout = float(user_config.timeout)

    while True:
        now = time.time()

        alarm = node.wait_event(identity = 'alarm', timeout=timeout)
        if alarm is not None:
            _DEB('Received alarm: %s' % repr(alarm))
            if 'Zone Reloaded From Backup' in alarm:
                _DEB('Expected Alarm: %s' % alarm)
                break
            else:
                _DEB('Unexpected Alarm: %s' % alarm)

        timeout -= time.time() - now
        if timeout < 0:
            raise ExecutionTimeout('Timeout waiting for alarm')

    node.stop_monitor('alarm')

    if not node.wait_until_cabinet_available(timeout=120):
        raise ExecutionTimeout('Timeout waiting for cabinet available')


def TSP_wait_for_reload_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('TIMEOUT',
                        help='Max time waiting for reload')

    command_params.add_argument('LOADER',
                        help='PrimaryLoader:Port')

    return (parser)


def run_TSP_wait_for_reload(user_config, node):

    loader_host = user_config.LOADER.split(':')[0]
    loader_port = user_config.LOADER.split(':')[1]
    timeout = float(user_config.TIMEOUT)

    node.create_monitor(monitor_type = hss_utils.connection.monitor.TspAlarmMonitor,
                              identity = 'alarm', force_primary = False,
                              processor = loader_host, port = loader_port,
                              start = False, extra_info = False)

    while True:
        now = time.time()

        alarm = node.wait_event(identity = 'alarm', timeout=10.0)
        if alarm is not None:
            _DEB('Received alarm: %s' % repr(alarm))
            if 'Zone Reloaded From Backup' in alarm:
                _DEB('Expected Alarm: %s' % alarm)
                break
            else:
                _DEB('Unexpected Alarm: %s' % alarm)

        timeout -= time.time() - now
        if timeout < 0:
            raise ExecutionTimeout('Timeout waiting for alarm')

def run_TSP_get_GeoRed_info(user_config, node):

    geoRedZone, geoRedActive = node.get_GeoRed_info()
    if geoRedZone == 0:
        raise WrongParameter('Cabinet (%s) is not configured in GeoRed' % user_config.NODE)

    print ('Zone %s %s'% (geoRedZone, ('Active' if geoRedActive else 'Standby')))


def run_TSP_list_capsule_dumps(user_config, node):

    cmd = 'ls -ltr /opt/telorb/axe/tsp/crashcollector/*'
    answer = node.run_command(cmd)
    print '\n'.join(answer)

def run_TSP_get_processors_info(user_config, node):

    node.start_TelorbCLI(identity ='cli')
    for processor in node.payload:
        cmd = '/CLI/Processors/getprocessorinfo %s' % processor
        answer = node.run_command(cmd, identity = 'cli', timeout = 5.0)
        print processor
        for line in answer:
            print '\t%s' % line

def TSP_health_check_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-o','--output_path',
                      action='store', default=None,
                      help='Collect result info and store it in this path',
                      dest='output_path')

    return (parser)


def run_TSP_health_check(user_config, node):

    output = '~/HssHealthCheck/reports/HssHealthCheck_%s.html' % os.getpid()
    node.start_healthcheck(output)

    if user_config.output_path is not None:
        node.download('%s' % output, user_config.output_path)
        cmd = 'rm -f %s' % output
        node.run_command(cmd)

def TSP_collect_logs_parser():
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
                      help='Max time in sec waiting for command.',
                      dest='max_time')


    return (parser)


def run_TSP_collect_logs(user_config, node):

    applogs_path = '/opt/mirror/tsp/applog/'
    cmd = 'cd %s' % applogs_path
    node.run_command(cmd) 
    tar_file = 'applog_%s.tgz' % user_config.file_suffix
    cmd = 'tar zcvf %s applog.*' % tar_file
    node.run_command(cmd, timeout=float(user_config.max_time))    
    node.download('%s/%s' % (applogs_path, tar_file), user_config.output_path)
    cmd = 'pwd'
    node.run_command(cmd)
    cmd = 'rm %s/%s' % (applogs_path, tar_file)
    node.run_command(cmd)

tsp_gauge_counters = ['TotalNumberOfSubscribersStored',
'TotalNumberOfUsersStored',
'TotalNumberOfSipPublicIdsStored',
'TotalNumberOfTelPublicIdsStored',
'TotalNumberOfUsersBarred',
'TotalNumberOfPublicIdsBarred',
'TotalNumberOfPsiUsersStored',
'TotalNumberOfPsiSipPublicIdsStored',
'TotalNumberOfPsiTelPublicIdsStored',
'TotalNumberWildcardedPSIsDefined',
'TotalNumberWildcardedPUIsDefined',
'TotalNumberOfPublicIdsRegistered',
'TotalNumberOfUsersRegistered',
'TotalNumberOfPublicIdsUnregistered',
'TotalNumberOfUsersWithPublicIdUnregistered',
'NumberOfPublicIdsRegisteredPerDomain',
'TotalNumberOfPsiUsersUnregistered',
'TotalNumberOfNonceStored',
'HssAvgProvisionedUsers',
'TotalNumberOfEpsSubscribersStored',
'TotalNumberOfEpsUsersStored',
'TotalNumberOfEpsUsersLocated',
'TotalNumberOfEpsUsersPurged',
'TotalNumberOfUsersRegisteredNon3GppIpAccess',
'TotalNumberOfApplicationServersStored',
'TotalNumberOfProvisionedEntries',
'TotalNumberOfPublicIds',
'TotalNumberOfMsisdns',
'TotalNumberOfWildcardedPSIEntries',
'TotalNumberOfImsis',
'TotalNumberOfPrivateIds',
'TotalNumberOfMsisdnRanges',
'TotalNumberOfImsiRanges',
'TotalNumberOfPrivateIdRanges',
'HssSmTotalNumberOfSessionsStored',
'HssSmSihPushNotifRequestsPending',
'tsp.ansitcap.tps',
'tsp.icettcap.tps',
'tsp.mtpl2.link_load_sent ',
'tsp.mtpl2.link_load_received',
'tsp.mtpl2_hssl.link_load_sent',
'tsp.mtpl2_hssl.link_load_received',
'tsp.sctp.assoc_established',
'tsp.sctp.data_received_assoc',
'tsp.sctp.data_sent_assoc',
'tsp.saal_lm.link_load_sent',
'tsp.saal_lm.link_load_received']

def TSP_pmf_counter_sum_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-g', '--groups', nargs='+',
                      action='store', default=[],
                      help='Specify the group(s) of counters to be handled. By dfault all of them will be used',
                      dest='groups')
    command_params.add_argument('-e', '--exclude', nargs='*',
                      action='store', default=[],
                      help='Specify the group(s) of counters to be handled',
                      dest='exclude')
    command_params.add_argument('-l', '--list',
                      action='store_true', default=False,
                      help='List all available groups of counters',
                      dest='listgroups')
    command_params.add_argument('-o', '--output',
                      action='store', default=None,
                      help='Specify the full path of output file. By default info is displayed in console',
                      dest='output_file')

    return (parser)

def run_TSP_pmf_counter_sum(user_config, node):

    main_path = '/opt/telorb/axe/tsp/NM/PMF/reporterLogs'
    cmd = 'find %s -type d -name "*"' % main_path
    groups = node.run_command(cmd)
    allowed_groups = []
    excluded_groups = []

    if  len (user_config.exclude) > 0 and len (user_config.groups) > 0:
        raise WrongParameter('-g and -o are can not be set at the same time')

    for group in groups[1:]:
        allowed_groups.append(os.path.basename(group))

    if user_config.listgroups:
        print '%s' % '\n'.join(allowed_groups)
        return

    working_directory = '/opt/hss/TSP_pmf_counters_sum_%s' % os.getpid()
    if not os.path.exists(working_directory):
        os.makedirs(working_directory)

    if len (user_config.groups) == 0:
        for group in allowed_groups:
            if group not in user_config.exclude:
                folder = '%s/%s' % (main_path, group)
                node.download('%s/*' % folder, working_directory)

    else:
        for user_group in user_config.groups:
            if user_group not in allowed_groups:
                raise WrongParameter('%s is not a valid group. Allowed values are: %s' % (user_group, ' '.join(allowed_groups)))

            folder = '%s/%s' % (main_path, user_group)
            node.download('%s/*' % folder, working_directory)

    file_list= sorted(glob.glob("%s/*" % working_directory))

    total_counter={}
    max_len_of_counter_name = 0
    for element in file_list:
        partial_counter = {}
        tree = ET.parse(element)
        root = tree.getroot()

        for md in root.findall('md'):
            measType_list = []
            for mi in md.findall('mi'): 

                if 'PlatformMeasures' in element:
                    continue

                else:
                    name = mi.find('mt').text
                    counter = 0
                    for mv in mi.findall('mv'):
                        text_counter = mv.find('r').text
                        if text_counter is not None:
                            counter += int(float(text_counter))

                    try:
                        if name in tsp_gauge_counters:
                            partial_counter[name] = counter
                        else:
                            partial_counter[name] += counter
                    except KeyError:
                        partial_counter.update({name:counter})

        for key, value in partial_counter.iteritems():
            try:
                if key in tsp_gauge_counters:
                    total_counter[key] = value
                else:
                    total_counter[key] += value
            except KeyError:
                total_counter.update({key:value})
                if len(key) > max_len_of_counter_name:
                    max_len_of_counter_name = len(key)


    if user_config.output_file is None:
        for key in sorted(total_counter):
            print "%-*s  %s" % (max_len_of_counter_name, key, total_counter[key])
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

    shutil.rmtree(working_directory)
