#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import Queue
import ntpath
import re
import os
import socket
import ipaddress
from ipaddress import IPv4Address, IPv6Address
import getpass
try:
    import paramiko
    _PARAMIKO_AVAILABLE_ = True
except Exception as e:
    _PARAMIKO_AVAILABLE_ = False
    pass



import hss_utils.connection
import hss_utils.connection.session
import hss_utils.connection.ssh
import hss_utils.st_command
from hss_utils.st_command import CommandFailure, ExecutionTimeout, real_path, clear_ansi
from . import Node

import e3utils.log as logging
_DEB = logging.internal_debug
_WRN = logging.warning
_ERR = logging.error
_INF = logging.info

IBD_CREDENTIAL_PATH='~/.ssh'
ANS_CREDENTIAL_PATH='~/.kubeconfig'

NODE_INFO_HEADERS=['NAME','STATUS','ROLES','AGE','VERSION','INTERNAL-IP','EXTERNAL-IP','OS-IMAGE','KERNEL-VERSION','CONTAINER-RUNTIME']
POD_INFO_HEADERS=['NAMESPACE','NAME','READY','STATUS','RESTARTS','AGE','IP','NODE','NOMINATED NODE','READINESS GATES']

ALARM_HANDLER_PORT = 5005


DIA_SERVICES={'Cx':'eric-stm-diameter-traffic-tcp',
              'Sh':'eric-stm-diameter-traffic-tcp',
              #'S6a':'eric-stm-diameter-server-traffic',
              'S6a':'eric-stm-diameter-traffic-sctp'}

PM_SERVICE = 'eric-pm-bulk-reporter'

class Cloud(Node):

    def __init__(self, eccd_type, config):

        Node.__init__(self)
        if eccd_type not in ['IBD','ANS']:
            raise ValueError('eccd_type %s not allowed' % eccd_type)

        self.__eccd_type = eccd_type
        self.__config = config
        self.__sftp_user = 'pmreadwriter'
        self.__sftp_password = 'WeakPas$worD-1'
        self.__sftp_transport = None
        self.__sftp_client = None

    def release(self):
        if self.__sftp_client: self.__sftp_client.close()
        if self.__sftp_transport: self.__sftp_transport.close()

        Node.release(self)

    @property
    def sftp_client(self):
        if not _PARAMIKO_AVAILABLE_:
            raise CommandFailure('paramiko python library not available')

        if not self.__sftp_client:
            _DEB('sftp server %s:%s' % (self.sftp_host,self.sftp_port))
            _DEB('sftp user=%s  passwd=%s' % (self.__sftp_user,self.__sftp_password))
            ip = ipaddress.ip_address(unicode(self.sftp_host))
            if isinstance(ip,IPv6Address):
                sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                try:
                    sock.connect((self.sftp_host, self.sftp_port))
                except Exception as e:
                    raise CommandFailure('SFTP problem: %s' %  str(e))
                self.__sftp_transport = paramiko.Transport(sock)
            elif isinstance(ip,IPv4Address):
                self.__sftp_transport = paramiko.Transport((self.sftp_host,self.sftp_port))
                try:
                    self.__sftp_transport.connect(None,self.__sftp_user,self.__sftp_password)
                except Exception as e:
                    raise CommandFailure('SFTP problem: %s' %  str(e))

            else:
                raise CommandFailure('Not valid sftp server ip: %s' % ip)

            self.__sftp_client = paramiko.SFTPClient.from_transport(self.__sftp_transport)

        return self.__sftp_client


    def list_counters(self):
        return self.sftp_client.listdir('/PerformanceManagementReportFiles')

    def get_conuter(self, name, dest):
        self.sftp_client.get(os.path.join('/PerformanceManagementReportFiles', name),dest)

    @property
    def last_counter(self):
        last_file = 'A20000101.1200+0000'
        for file in sorted(self.list_counters(), reverse=True):
            if file.endswith('xml.gz'):
                last_file = file
                break
        return last_file

    @property
    def config(self):
        return self.__config

    @property
    def credential_file(self):
        return self.config['credential_file']

    @property
    def eccd_type(self):
        return self.__eccd_type


    def get_nodes_info(self):
        cmd = 'kubectl get nodes -o wide'
        return self.run_command(cmd,full_answer=True)

    @property
    def nodes(self):
        return self.get_nodes()

    @property
    def workers(self):
        return self.get_nodes(role=['worker','node'])

    @property
    def payload(self):
        return self.get_nodes(role=['worker','node'])

    @property
    def masters(self):
        return self.get_nodes(role=['master'])

    def get_nodes(self,role=['worker','node','master']):
        info = self.get_nodes_info()
        nodes = []
        for line in info.splitlines()[1:]:
            node = line.split()
            if node[NODE_INFO_HEADERS.index('ROLES')] in role:
                nodes.append(node[NODE_INFO_HEADERS.index('NAME')])

        return nodes

    def get_nodes_specific_info(self, fields=NODE_INFO_HEADERS[1:]):
        if not set(fields) <= set(NODE_INFO_HEADERS):
            raise CommandFailure('Wrong info requested')

        info = self.get_nodes_info()
        data = {}
        for line in info.splitlines()[1:]:
            specific = {}
            node = line.split()
            for field in fields:
                specific.update({field:node[NODE_INFO_HEADERS.index(field)]})
            data.update({node[NODE_INFO_HEADERS.index('NAME')]:specific})

        return data

    def get_nodes_ip(self):
        return self.get_nodes_specific_info(fields=['EXTERNAL-IP','INTERNAL-IP'])

    def get_nodes_status(self):
        info = self.get_nodes_specific_info(fields=['STATUS'])
        data = ''
        for node, value in info.iteritems():
            data +="%s\t%s\n" % (node,value['STATUS'])
        return data

    @property
    def all_nodes_ready(self):
        info = self.get_nodes_specific_info(fields=['STATUS'])
        for node, value in info.iteritems():
            if value['STATUS'] != 'Ready':
                return False
        return True

    def get_nodes_not_ready(self):
        nodes=[]
        info = self.get_nodes_specific_info(fields=['STATUS'])
        for node, value in info.iteritems():
            if value['STATUS'] != 'Ready':
                nodes.append(node)
        return nodes

    def get_pods_info(self, namespace=None):
        pods = []
        cmd = 'kubectl get pod %s -o wide' % ('-n %s' % namespace if namespace else '--all-namespaces')
        pods = self.run_command(cmd,full_answer=False)
        if pods:
            pods = pods[1:]

        return pods

    def get_pod_by_state(self,state=[],exclude=False, namespace=None):
        info = self.get_pods_info(namespace=namespace)
        pods=[]
        for line in info:
            pod = line.split()
            if exclude:
                if pod[POD_INFO_HEADERS.index('STATUS')] not in state:
                    pods.append('%s.%s' % (pod[POD_INFO_HEADERS.index('NAMESPACE')], pod[POD_INFO_HEADERS.index('NAME')]))
            else:
                if pod[POD_INFO_HEADERS.index('STATUS')] in state:
                    pods.append('%s.%s' % (pod[POD_INFO_HEADERS.index('NAMESPACE')], pod[POD_INFO_HEADERS.index('NAME')]))

        return pods

    def get_pod_in_node(self,node, namespace=None):
        info = self.get_pods_info(namespace=namespace)
        pods=[]
        for line in info:
            pod = line.split()
            if pod[POD_INFO_HEADERS.index('NODE')] == node:
                pods.append('%s.%s' % (pod[POD_INFO_HEADERS.index('NAMESPACE')], pod[POD_INFO_HEADERS.index('NAME')]))

        return pods


    @property
    def alarm_handler_pod(self):
        cmd = 'kubectl get po --all-namespaces | grep alarm-handler'
        answer = self.run_command(cmd,full_answer=False)
        if answer:
            return answer[0].split()[1]

    @property
    def default_namespace(self):
        return self.get_service_namespace('eric-hssepc-diameter')


    @property
    def pods_for_logging(self):
        cmd = "kubectl get pods -n %s | grep -vE 'Evicted|Completed|ausf-st|udrsim|testrunner|job|eric-cm|eric-data|eric-fh|eric-odca|eric-pm' " % self.default_namespace 
        info = self.run_command(cmd)
        pods=[]
        for line in info:
            if 'NAME' in line:
                continue
            pods.append(line.split()[0])

        return pods

    def get_service_namespace(self, svc):
        cmd = 'kubectl get svc --all-namespaces | grep %s' % svc
        answer = self.run_command(cmd,full_answer=False)
        if answer:
            return answer[0].split()[0]


    def find_containers_down(self, namespace=None):
        info = self.get_pods_info(namespace=namespace)
        containers=[]
        for line in info:
            pod = line.split()
            if pod[POD_INFO_HEADERS.index('STATUS')] == 'Completed':
                continue
            if pod[POD_INFO_HEADERS.index('READY')].split('/')[0] != pod[POD_INFO_HEADERS.index('READY')].split('/')[1]:
                containers.append('%s.%s' % (pod[POD_INFO_HEADERS.index('NAMESPACE')], pod[POD_INFO_HEADERS.index('NAME')]))

        return containers

    @property
    def first_worker_ip(self):
        host_not_ready = self.get_nodes_not_ready()
        nodes_ip = self.get_nodes_ip()
        for host in self.workers:
            if host not in host_not_ready:
                return nodes_ip[host]['INTERNAL-IP']


    def get_service_port(self, service, nodePort=True):
        port = -1
        namespace = self.get_service_namespace(service)
        if namespace:
            cmd = 'kubectl -n %s get svc %s -o jsonpath={.spec.ports[0].%s}' %  (namespace, service, ('nodePort' if nodePort else 'port'))
            port = self.run_command(cmd,full_answer=True).strip()
        return port

    def get_extdb_ip(self):
        cmd = 'kubectl -n %s describe deploy eric-hss-ldapproxy | grep -i LDAPENDPOINT' % self.default_namespace
        answer = self.run_command(cmd,full_answer=True)

        extdb_ip = None
        regex = re.compile(r"LDAPENDPOINT:[ \t]+ldap://(.+):\d+")
        for line in answer.splitlines():
            res = regex.match(clear_ansi(line.strip()))
            if res:
                address = res.group(1)
                if address.startswith('['):
                    address = address[1:-1]
                ip = ipaddress.ip_address(unicode(address))

                if isinstance(ip,IPv4Address) or isinstance(ip,IPv6Address):
                    extdb_ip = '%s' % ip
                    break

        return extdb_ip


    def get_traffic_info(self, appid, info =[], IPv6 = False):
        if len(info) == 0:
            info = ['dia_tcp', 'dia_sctp', 'dia_port','extdb','soap','soap_port']

        _DEB('Getting traffic info for %s type' % appid)
        traffic_info = {}
        data = self.get_dia_info()
        if 'dia_tcp' in info:
            traffic_info['dia_tcp'] = data[appid]['ip'] if appid else ' Missing appid parameter'
        if 'dia_sctp' in info:
            traffic_info['dia_sctp'] = data[appid]['ip'] if appid else ' Missing appid parameter'
        if 'dia_port' in info:
            traffic_info['dia_port'] = data[appid]['port'] if appid else ' Missing appid parameter'
        if 'extdb' in info:
            traffic_info['extdb'] = self.get_extdb_ip()
        if 'soap' in info:
            traffic_info['soap'] = self.get_soap_ip()
        if 'soap_port' in info:
            traffic_info['soap_port'] = self.get_soap_port()

        return traffic_info

    def print_alarm_info(self, info_alarm):
        try:
            additionalInformation = info_alarm['additionalInformation']['text']
        except (IndexError,KeyError) as e:
            additionalInformation = 'No additionalInformation'

        try:
            return '\n%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s' % (info_alarm['alarmName'],info_alarm['severity'],
                                                                info_alarm['eventTime'],info_alarm['serviceName'],
                                                                info_alarm['description'],additionalInformation,
                                                                info_alarm.get('faultyResource','No faultyResource'))
        except (IndexError,KeyError) as e:
            raise e

class CloudANS(Cloud):

    def __init__(self, config={}):

        if 'credential_file' not in config.keys():
            raise ValueError('kubeconfig credential file missing')
        config['host'] = socket.gethostname()
        config['port'] = '22'
        config['user'] = getpass.getuser()

        Cloud.__init__(self, eccd_type='ANS', config=config)

        self.__session_type=hss_utils.connection.session.StandardLinux
        self.create_connection()
        self.set_default_connection()
        self.__sftp_port=-1

    @property
    def sftp_host(self):
        return self.first_worker_ip

    @property
    def sftp_port(self):
        try:
            self.__sftp_port = int(self.get_service_port(PM_SERVICE))
        except ValueError as e:
            if 'Unable to connect to the server' in str(e):
                raise hss_utils.connection.Unauthorized(str(e))

            _DEB('Problem reading sftp port: %s' % str(e))

        return self.__sftp_port


    def create_connection(self):
        Cloud.create_connection(self,config=self.config, session_type=self.__session_type)

    def run_command(self, cmd, identity = None, answer = {}, timeout = None, full_answer = False):
        Cloud.run_command(self,'export KUBECONFIG=%s' % self.credential_file, full_answer = True)
        return Cloud.run_command(self, cmd, identity = identity, answer = answer, timeout = timeout, full_answer = full_answer)

    @property
    def datetime(self):
        cmd = 'kubectl get po --all-namespaces -o wide | grep %s' % PM_SERVICE
        answer = self.run_command(cmd,full_answer=True)
        po = answer.split()[1]

        cmd = 'kubectl -n %s exec %s -- date +"%%Y-%%m-%%dT%%H:%%M:%%S"' %(self.default_namespace, po)
        answer = self.run_command(cmd)
        return answer[-1]

    def get_dia_info(self):
        data = {}
        ip = self.first_worker_ip
        for stack, service in DIA_SERVICES.iteritems():
            port = self.get_service_port(service)
            data.update({stack :{'ip':ip, 'port':port}})

        return data

    def get_soap_port(self):
        return self.get_service_port('eric-ingressgw-epc-soap-traffic' , nodePort=True)

    def get_soap_ip(self):
        return self.first_worker_ip



class CloudIBD(Cloud):

    def __init__(self, config={}):

        if 'host' not in config.keys():
            raise ValueError('host missing')
        if 'credential_file' not in config.keys():
            raise ValueError('ssh_key credential file missing')
        if 'port' not in config.keys():
            config['port'] = '22'
        if 'user' not in config.keys():
            config['user'] = 'eccd'

        Cloud.__init__(self, eccd_type='IBD', config=config)

        self.__session_type=hss_utils.connection.session.StandardLinux
        self.create_connection()
        self.set_default_connection()
        self.__sftp_port = -1

    @property
    def sftp_host(self):
        return self.get_service_vip(PM_SERVICE)

    @property
    def sftp_port(self):
        try:
            self.__sftp_port = int(self.get_service_port(PM_SERVICE, nodePort=False))
        except ValueError as e:
            if 'Unable to connect to the server' in str(e):
                raise hss_utils.connection.Unauthorized(str(e))
            _DEB('Problem reading sftp port: %s' % str(e))
            self.__sftp_port = -1

        return self.__sftp_port

    def create_connection(self):
        Cloud.create_connection(self,config=self.config, session_type=self.__session_type,ssh_key=self.credential_file)


    def get_service_vip(self, service):
        namespace = self.get_service_namespace(service)
        if namespace:
            cmd = 'kubectl -n %s get svc %s -o jsonpath={.status.loadBalancer.ingress[0].ip}'%  (namespace, service)
            return self.run_command(cmd,full_answer=True).strip()

    def get_soap_port(self):
        return self.get_service_port('eric-ingressgw-epc-soap-traffic' , nodePort=False)

    def get_soap_ip(self):
        return self.get_service_vip('eric-ingressgw-epc-soap-traffic')

    def get_dia_info(self):
        data = {}
        ip = self.get_service_vip('eric-stm-diameter-traffic-sctp')
        for stack, service in DIA_SERVICES.iteritems():
            port = self.get_service_port(service, nodePort=False)
            data.update({stack :{'ip':ip, 'port':port}})

        return data
