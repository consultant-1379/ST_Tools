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
import random
import json
import ast
from shutil import copyfile
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

import hss_utils.rosetta
import hss_utils.rosetta.services
import hss_utils.node.cloud
from . import ExecutionTimeout
from . import NotFound
from . import CommandFailure
from . import WrongParameter
from . import ip2int
from . import is_ip_in_net
from . import real_path
from . import execute_cmd, clear_ansi


def run_CLOUD_test(user_config, node):

    #print node.get_nodes_info()

    #print node.get_node_external_ip()
    #print node.get_node_internal_ip()
    
    
    #print node.nodes
    #print node.workers
    #print node.masters


    #print '\n'.join(node.get_pod_by_state(state=['Evicted'],exclude=False))

    #print '\n'.join(node.get_pod_by_state(state=[],exclude=True))

    #print node.get_nodes_ip()

    #print node.get_nodes_status()

    #print '\n'.join(node.find_containers_down())

    #print node.all_nodes_ready

    #cmd = "kubectl get pods -o go-template --template '{{range .items}}{{.metadata.name}}{{\"\\n\"}}{{end}}' -n ccsm"
    #print node.run_command(cmd)

    #cmd = "kubectl get po -n ccsm eric-udm-udrwatcher-5694779dfb-n45qv -o json"
    #answer = node.run_command(cmd,full_answer=True)
    #print answer
    #d = json.loads(answer)
    #import pprint as pp
    #pp.pprint(d)
    #print d['metadata']['labels']['app']

    #cmd = "kubectl get nodes -o jsonpath='{ $.items[0].status.addresses[?(@.type==\"InternalIP\")].address }'"
    #host = node.run_command(cmd,full_answer=True).strip()

    #cmd = "kubectl get svc -n ccsm eric-fh-alarm-handler -o json"
    #d = json.loads(node.run_command(cmd,full_answer=True))

    #import pprint as pp
    #pp.pprint(d)

    #cmd = "kubectl get svc -n ccsm eric-fh-alarm-handler -o jsonpath={.spec.ports[0].%s}" %('port' if d['spec']['type'] =='ClusterIP' else 'nodePort')
    #print cmd
    #port = node.run_command(cmd,full_answer=True).strip()

    #cmd = "wget -O post_alarms.txt http://%s:%s/ah/api/v0.2/alarms?outputFormat=SeveritySummary" % (host, port)
    #print cmd
    ##wget -O post_alarms.txt http://${HOST}:${PORT}/ah/api/v0.2/alarms?outputFormat=SeveritySummary

#ecemit@seliius23270:~/trabajo/trafico$ kubectl -n ccsm exec -it <eric-fh-alarm-handler_pod_name> -- curl  http://eric-fh-alarm-handler:5005/ah/api/v0/alarms?outputFormat=SeveritySummary
#-bash: eric-fh-alarm-handler_pod_name: No such file or directory
#ecemit@seliius23270:~/trabajo/trafico$ kubectl -n ccsm get po | grep handler
#eric-fh-alarm-handler-68889b5f79-6srdp                 1/1     Running     1          6d23h
#eric-fh-alarm-handler-68889b5f79-9rf6v                 1/1     Running     1          6d23h
#ecemit@seliius23270:~/trabajo/trafico$ kubectl -n ccsm exec -it eric-fh-alarm-handler-68889b5f79-6srdp -- curl  http://eric-fh-alarm-handler:5005/ah/api/v0/alarms?outputFormat=SeveritySummary


    #cmd = 'kubectl -n ccsm exec -it %s  -- curl  http://eric-fh-alarm-handler:%s/ah/api/v0/alarms?outputFormat=SeveritySummary' % (node.alarm_handler_pod,
                                                                                                                                   #hss_utils.node.cloud.ALARM_HANDLER_PORT)
    #answer = node.run_command(cmd,full_answer=True)
    #print answer
                                                                                                                                   
    #print node.get_dia_info()
    
    #print node.pods_for_logging
    

    last_file = node.list_counters()[-1]
    last_date_file = datetime.strptime(last_file.split('+')[0], 'A%Y%m%d.%H%M')
    current_date_file = last_date_file
    _DEB('Current %s' % current_date_file)
    while not last_date_file > current_date_file:
        time.sleep(5.0)
        last_file = node.list_counters()[-1]
        last_date_file = datetime.strptime(last_file.split('+')[0], 'A%Y%m%d.%H%M')
        _DEB('Last %s' % last_date_file)


    pass

def CLOUD_run_command_parser():
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

def run_CLOUD_run_command(user_config, node):
    answer = node.run_command(user_config.COMMAND, timeout=float(user_config.max_time), full_answer=True)
    if user_config.file is None:
        print answer
    else:
        if not os.path.exists(os.path.dirname(user_config.file)):
            os.makedirs(os.path.dirname(user_config.file))
            os.chmod(os.path.dirname(user_config.file), 0o777)
        with open(user_config.file,'a') as fd:
            fd.write(answer)


def run_CLOUD_datetime(user_config, node):
    print node.datetime


def run_CLOUD_get_nodes(user_config, node):
    cmd = 'kubectl get nodes -o wide'
    answer = node.run_command(cmd,full_answer=True)

    print answer


def run_CLOUD_nodes_info(user_config, node):
    cmd = 'kubectl describe node'
    answer = node.run_command(cmd,full_answer=True)

    print answer

def run_CLOUD_deployments_info(user_config, node):
    cmd = 'kubectl describe deploy --all-namespaces'
    answer = node.run_command(cmd,full_answer=True)

    print answer


def run_CLOUD_pods_info(user_config, node):
    cmd = 'kubectl get po --all-namespaces -o wide | sort --reverse --key 5 --numeric'
    answer = node.run_command(cmd,full_answer=True)

    print answer


def run_CLOUD_services_info(user_config, node):
    cmd = 'kubectl get svc --all-namespaces'
    answer = node.run_command(cmd,full_answer=True)

    print answer


def run_CLOUD_events_info(user_config, node):
    cmd = "kubectl --all-namespaces=true get events -o custom-columns=TYPE:.type,REASON:.reason,OBJECT:.metadata.name,"
    cmd += "CREATIONTIME:.metadata.creationTimestamp,MESSAGE:message"
    answer = node.run_command(cmd,full_answer=True)

    print answer


def run_CLOUD_nof_pods_per_node(user_config, node):
    for host in node.nodes:
        print '%s\t%s' % (host, len(node.get_pod_in_node(host)))


def run_CLOUD_total_nof_pods(user_config, node):
    print len(node.get_pods_info())


def run_CLOUD_node_resources(user_config, node):
    cmd = "kubectl top nodes"
    answer = node.run_command(cmd,full_answer=True)

    print answer


def run_CLOUD_replica(user_config, node):
    cmd = "kubectl get rs -n %s" % node.default_namespace
    answer = node.run_command(cmd,full_answer=True)

    print answer


def run_CLOUD_software_installed(user_config, node):
    cmd = "helm list -A"
    answer = node.run_command(cmd,full_answer=True)

    print answer


def run_CLOUD_helm_version(user_config, node):
    cmd = "helm version"
    answer = node.run_command(cmd,full_answer=True)

    print answer

def run_CLOUD_ccd_version(user_config, node):
    workers = node.workers
    if not workers:
        raise CommandFailure('Worker not found')

    cmd = "kubectl -n %s get nodes %s -o jsonpath={.metadata.labels.ccd/version}" % (node.default_namespace, workers[0])
    answer = node.run_command(cmd,full_answer=True)

    print answer

def run_CLOUD_kubectl_version(user_config, node):
    cmd = "kubectl version"
    answer = node.run_command(cmd,full_answer=True)

    print answer


def run_CLOUD_check_all_pods_running(user_config, node):
    pods = node.get_pod_by_state(state=['Completed','Running'],exclude=True)

    if pods:
        raise CommandFailure('Error Pods not running: %s' % ' , '.join(pods))


def run_CLOUD_check_all_containers_started(user_config, node):
    containers = node.find_containers_down()

    if containers:
        raise CommandFailure('Error faulty containers: %s' % ' , '.join(containers))


def run_CLOUD_check_all_nodes_ready(user_config, node):
    nodes = node.get_nodes_not_ready()

    if nodes:
        raise CommandFailure('Error Nodes not ready: %s' % ' , '.join(nodes))


def CLOUD_get_all_containers_logs_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--path',
                      action='store', default=CWD,
                      help='Full path where to store logs file. Default is "%(default)s"',
                      dest='path')

    command_params.add_argument('--since',
                      action='store', default=0, type=int,
                      help='Set the logging period to be saved.',
                      dest='since')

    command_params.add_argument('--since-time',
                      action='store', default=None,
                      help='Set the starting log time to be saved.  Value shall be in format "Y-m-dTH:M:S"',
                      dest='since_time')
    return (parser)


def run_CLOUD_get_all_containers_logs(user_config, node):
    path = real_path(user_config.path)
    if not os.path.exists(path):
        os.makedirs(path)

    start_from = ''
    if user_config.since:
        start_from = ' --since=%ss ' % user_config.since
    elif user_config.since_time:
        start_from = ' --since-time=%sZ' % user_config.since_time

    for pod in node.pods_for_logging:
        cmd = "kubectl logs %s -n %s --timestamps=true %s --all-containers=true | grep -iE 'error|warning'" % (pod,
                                                                                                                 node.default_namespace,
                                                                                                                 start_from)
        answer = node.run_command(cmd,full_answer=True)
        with open(os.path.join(path,'all_containers_%s.log' % pod ), "w") as text_file:
            text_file.write(answer)


def CLOUD_get_pods_logs_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--path',
                      action='store', default=CWD,
                      help='Full path where to store logs file. Default is "%(default)s"',
                      dest='path')

    command_params.add_argument('--since',
                      action='store', default=0, type=int,
                      help='Set the logging period to be saved.',
                      dest='since')

    command_params.add_argument('--since-time',
                      action='store', default=None,
                      help='Set the starting log time to be saved',
                      dest='since_time')
    return (parser)


def run_CLOUD_get_pods_logs(user_config, node):
    path = real_path(user_config.path)
    if not os.path.exists(path):
        os.makedirs(path)

    start_from = ''
    if user_config.since:
        start_from = ' --since=%ss ' % user_config.since
    elif user_config.since_time:
        start_from = ' --since-time=%sZ' % user_config.since_time

    for pod in node.pods_for_logging:
        cmd = "kubectl get po -n %s %s -o jsonpath={.spec.containers[0].name}" % (node.default_namespace, pod)
        container = node.run_command(cmd,full_answer=True).strip()
        cmd = "kubectl logs %s -n %s --timestamps=true %s %s | grep -iE 'error|warning'" % (pod, 
                                                                                            node.default_namespace,
                                                                                            start_from, 
                                                                                            container)
        answer = node.run_command(cmd,full_answer=True)
        with open(os.path.join(path,'logs_%s.log' % pod ), "w") as text_file:
            text_file.write(answer)

def CLOUD_check_alarms_parser():
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

    command_params.add_argument('--since-time',
                      action='store', default=None,
                      help='Set the starting time for filtering alarms. Value shall be in format "Y-m-dTH:M:S"',
                      dest='since_time')

    command_params.add_argument('--last-time',
                      action='store', default=None,
                      help='Set the last time for filtering alarms. Value shall be in format "Y-m-dTH:M:S"',
                      dest='last_time')

    return (parser)

def run_CLOUD_check_alarms(user_config, node):

    if user_config.since_time:
        try:
            user_config.offset_date = datetime.strptime(user_config.since_time, '%Y-%m-%dT%H:%M:%S')
        except Exception as e:
            error = '--since-time %s not valid. Value shall be in format "Y-m-dTH:M:S"' % user_config.since_time
            raise WrongParameter(error)
    else:
        user_config.offset_date = datetime.strptime('2010-7-10T22:55:56', '%Y-%m-%dT%H:%M:%S')

    if user_config.last_time:
        try:
            user_config.last_date = datetime.strptime(user_config.last_time, '%Y-%m-%dT%H:%M:%S')
        except Exception as e:
            error = '--to-time %s not valid. Value shall be in format "Y-m-dTH:M:S"' % user_config.last_time
            raise WrongParameter(error)
    else:
        user_config.last_date = datetime.now()


    alarm_handler_pod = node.alarm_handler_pod
    if not alarm_handler_pod:
        raise CommandFailure('Alarm handler not found')

    if user_config.summary:
        cmd = 'kubectl -n %s exec -it %s  -c eric-fh-alarm-handler -- curl  http://eric-fh-alarm-handler:%s/ah/api/v0/alarms?outputFormat=SeveritySummary' % (node.default_namespace,
                                                                                                                                     alarm_handler_pod,
                                                                                                                                     hss_utils.node.cloud.ALARM_HANDLER_PORT)
        answer = node.run_command(cmd,full_answer=True)
        info = json.loads(answer)
        for key in sorted(info.keys()):
            print '%-*s %s' % (20,key, info[key] )

        return

    cmd = 'kubectl -n %s exec -it %s -c eric-fh-alarm-handler -- curl  http://eric-fh-alarm-handler:%s/ah/api/v0/alarms?outputFormat=FullAlarmList' % (node.default_namespace,
                                                                                                                                node.alarm_handler_pod,
                                                                                                                                hss_utils.node.cloud.ALARM_HANDLER_PORT)
    answer = node.run_command(cmd,full_answer=True)
    info = json.loads(answer)

    alarm_list = []
    for alarm in info:
        try:
            alarm_date = datetime.strptime(alarm['eventTime'].split('.')[0], '%Y-%m-%dT%H:%M:%S')
        except Exception as e:
            _DEB('%s eventTime not valid: %s' % (alarm['eventTime'],str(e)))
            continue

        if alarm_date >= user_config.offset_date and alarm_date <= user_config.last_date:
            if user_config.severity in [None, alarm['severity']]:
                if user_config.filter in alarm['description'] and user_config.source in alarm['serviceName']:
                    skip = False
                    for exlude in user_config.exclude:
                        if exlude in alarm['description']:
                            skip = True
                            break;
                    if skip:
                        continue

                    alarm_list.append(node.print_alarm_info(alarm))

    if len(alarm_list):
        print '\n'.join(alarm_list)
        print '\n'
    else:
        print '\nNo alarms'


def run_CLOUD_get_alarms(user_config, node):
    alarm_handler_pod = node.alarm_handler_pod
    if not alarm_handler_pod:
        raise CommandFailure('Alarm handler not found')
    cmd = 'kubectl -n %s exec -it %s  -c eric-fh-alarm-handler -- curl  http://eric-fh-alarm-handler:%s/ah/api/v0/alarms?outputFormat=SeveritySummary' % (node.default_namespace,
                                                                                                                                 alarm_handler_pod,
                                                                                                                                 hss_utils.node.cloud.ALARM_HANDLER_PORT)
    answer = node.run_command(cmd,full_answer=True)
    if 'Error from server' in answer:
        raise CommandFailure(answer)

    try:
        info = json.loads(answer)
    except ValueError:
        raise CommandFailure('No alarm found. Wrong json returned by "%s"' % repr(cmd))

    for key in sorted(info.keys()):
        print '%-*s %s' % (20,key, info[key] )

def CLOUD_get_diameter_info_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--appid', default=None,nargs='*',
                      action='store', choices=hss_utils.node.cloud.DIA_SERVICES.keys(),
                      help='Specific Diameter application name. By default all of them will be displayed',
                      dest='appid')

    return (parser)

def run_CLOUD_get_diameter_info(user_config, node):
    if not user_config.appid:
        user_config.appid = hss_utils.node.cloud.DIA_SERVICES.keys()
    info = node.get_dia_info()
    for appid in user_config.appid:
        print '%s\t%s : %s' % (appid, info[appid]['ip'], info[appid]['port'])



def CLOUD_get_traffic_info_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--appid', default=None,
                      action='store', choices=hss_utils.node.cloud.DIA_SERVICES.keys(),
                      help='Specific Diameter application name.',
                      dest='appid')

    command_params.add_argument('-s','--specific',nargs='+',default=None,
                        choices = ['dia_tcp', 'dia_sctp','dia_port','extdb','soap','soap_port'],
                        action='store',
                        help='Specify value',
                        dest='specific')
    return (parser)


def run_CLOUD_get_traffic_info(user_config, node):

    if user_config.specific is None:
        user_config.specific = ['dia_tcp', 'dia_sctp','dia_port','extdb','soap','soap_port']

    answer = node.get_traffic_info(user_config.appid, info=user_config.specific)

    keys = answer.keys()
    keys.sort()
    for key in keys:
        if key in user_config.specific:
            print '%s=%s' % (key, answer[key])





def CLOUD_delete_evicted_pods_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--namespace',
                      action='store', default=None,
                      help='Only pods in the namespace. By default all namespaces will be used',
                      dest='namespace')
    return (parser)


def run_CLOUD_delete_evicted_pods(user_config, node):

    pods = node.get_pod_by_state(state=['Evicted'],exclude=False, namespace=user_config.namespace)
    for pod in pods:
        pod = pod.split('.')
        cmd = 'kubectl -n %s delete po %s ' % (pod[0], pod[1])
        answer = node.run_command(cmd)




def CLOUD_wait_next_pm_counters_update_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--timer',
                      action='store', default=10,type=int,
                      help='Waiting time between checks. By default is "%(default)s"',
                      dest='timer')
    command_params.add_argument('--max-time',
                      action='store', default=1800,type=int,
                      help='Max time in sec waiting for. By default is "%(default)s" seconds',
                      dest='max_time')

    return (parser)


def run_CLOUD_wait_next_pm_counters_update(user_config, node):

    counters = node.list_counters()
    if not counters:
        raise CommandFailure('Counters file not found')

    last_file = node.last_counter

    last_date_file = datetime.strptime(last_file.split('+')[0], 'A%Y%m%d.%H%M')
    current_date_file = last_date_file
    _DEB('Current %s' % last_file)
    timeout = float(user_config.max_time)
    while not last_date_file > current_date_file:
        now = time.time()

        time.sleep(float(user_config.timer))
        last_file = node.last_counter
        last_date_file = datetime.strptime(last_file.split('+')[0], 'A%Y%m%d.%H%M')
        _DEB('Last %s' % last_file)
        timeout -= time.time() - now
        if timeout < 0:
            raise ExecutionTimeout('Timeout waiting for counters update')



gauge_counters = ['TotalNumberOfApplicationServersStored'
  ]

def CLOUD_pmf_counter_sum_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('SINCETIME',
                      help='Set the starting time for collecting counters file. Value shall be in format "Y-m-dTH:M:S"')

    command_params.add_argument('-o', '--output',
                      action='store', default=None,
                      help='Specify the full path of output file. By default info is displayed in console',
                      dest='output_file')

    command_params.add_argument('--last-time',
                      action='store', default=None,
                      help='Set the last time for collecting counters file. Value shall be in format "Y-m-dTH:M:S"',
                      dest='last_time')

    command_params.add_argument('--folder',
                      action='store', default=None,
                      help='Specify the full path folder where to save downloaded counters files. Folder must not exist',
                      dest='working_directory')

    command_params.add_argument('--verify-no-counters-with',
                      action='store', default=None, nargs='+',
                      help='List of words that can not be present in counter names.',
                      dest='forbidden')

    return (parser)

def run_CLOUD_pmf_counter_sum(user_config, node):
    try:
        user_config.offset_date = datetime.strptime(user_config.SINCETIME, '%Y-%m-%dT%H:%M:%S')
    except Exception as e:
        raise WrongParameter('SINCETIME %s not valid. Value shall be in format "Y-m-dTH:M"' % user_config.SINCETIME)

    if user_config.last_time:
        try:
            user_config.last_date = datetime.strptime(user_config.last_time, '%Y-%m-%dT%H:%M:%S')
        except Exception as e:
            raise WrongParameter('--last-time %s not valid. Value shall be in format "Y-m-dTH:M"' % user_config.last_time)
    else:
        user_config.last_date = datetime.now()

    if user_config.working_directory:
        user_config.working_directory = real_path(user_config.working_directory)
        user_config.remove_file = False
    else:
        user_config.working_directory = '/opt/hss//CLOUD_pmf_counters_sum_%s' % os.getpid()
        user_config.remove_file = True

    _DEB('working_directory: %s' % user_config.working_directory)

    if os.path.exists(user_config.working_directory):
        raise WrongParameter('--folder %s not valid. The folder must not exist' % user_config.working_directory)

    os.makedirs(user_config.working_directory)

    nof_counter_files = 0
    for counter in node.list_counters():
        try:
            counter_date = datetime.strptime(counter.split('+')[0], 'A%Y%m%d.%H%M')
        except Exception as e:
            _DEB('%s counter file not valid: %s' % (counter,str(e)))
            continue

        if counter_date >= user_config.offset_date and counter_date <= user_config.last_date:
            _DEB('Download %s ' % counter)
            node.get_conuter(counter, os.path.join(user_config.working_directory,counter))
            nof_counter_files += 1

    if nof_counter_files == 0:
        raise CommandFailure('There is not Counter files to analyze')

    cmd = 'gzip -d %s/*.xml.gz' % user_config.working_directory
    stdout_value, returncode = execute_cmd(cmd)
    if returncode:
        raise CommandFailure('Error executing: %s' % cmd)

    total_counter={}
    max_len_of_counter_name = 0
    file_list= sorted(glob.glob("%s/*.xml" % user_config.working_directory))
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
                            if measType_dict[key] in gauge_counters:
                                partial_counter[measType_dict[key]] = int(r.text)
                            elif measType_dict[key].startswith('eric-hss') and measType_dict[key].endswith('ratio'):
                                partial_counter[measType_dict[key]] += int(r.text)
                        except KeyError:
                            try:
                                partial_counter.update({measType_dict[key]:int(r.text)})
                            except ValueError:
                                _WRN('%s counter value is not an integer. Skip' % measType_dict[key])
                                continue



        for key, value in partial_counter.iteritems():
            try:
                if key in gauge_counters:
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


    if user_config.remove_file:
        shutil.rmtree(user_config.working_directory)

    if user_config.forbidden:
        forbidden_found = False
        for counter in total_counter.keys():
            forbidden_found = forbidden_found or any(substring in counter for substring in user_config.forbidden)

        if forbidden_found:
            raise CommandFailure('Found counters with a forbidden word: %s' % ' '.join(user_config.forbidden))




