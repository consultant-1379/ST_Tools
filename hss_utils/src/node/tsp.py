#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import re
import time
from distutils.spawn import find_executable

import hss_utils.connection.monitor
import hss_utils.connection.session
import hss_utils.connection.ssh

from hss_utils.st_command import ldap_search
from hss_utils.st_command import remove_quottes
from . import Node
import ipaddress
from ipaddress import IPv4Address, IPv6Address

import e3utils.log as logging
_DEB = logging.internal_debug
_WRN = logging.warning
_ERR = logging.error
_INF = logging.info

LDAP_DATA = {

     'EXTDB_EPC' : {'user' :'administratorName=jambala,nodeName=',
                    'pass' :'Pokemon1',
                    'base' :'HSS-EsmExtDbConfigurationName=HSS-EsmExtDbConfiguration,HSS-EsmConfigurationContainerName=HSS-EsmConfigurationContainer,applicationName=HSS_ESM,nodeName=',
                    'attr': 'HSS-EsmExtDbConfigUrlList'},
     'EXTDB_IMS' : {'user' :'administratorName=jambala,nodeName=',
                    'pass' :'Pokemon1',
                    'base' :'HSS-ExtDbConfigName=HSS-ExtDbConfig,HSS-ConfigurationContainerName=HSS-ConfigurationContainer,applicationName=HSS,nodeName=',
                    'attr': 'HSS-ExtDbConfigUrlList'},
     'VECTOR_SUPPLIER_EPC' : {'user' :'administratorName=HSS-EsmEricsson-Administrator,nodeName=',
                              'pass' :'Txvf123',
                              'base' :'HSS-EsmInstallationSupportName=HSS-EsmInstallationSupport,HSS-EsmServicesSupportContainerName=HSS-EsmServicesSupportContainer,HSS-EsmConfigurationContainerName=HSS-EsmConfigurationContainer,applicationName=HSS_ESM,nodeName=',
                              'attr': 'HSS-EsmAuthenticationVectorSupplier'},
     'VECTOR_SUPPLIER_IMS' : {'user' :'administratorName=HSS-Ericsson-Administrator,nodeName=',
                              'pass' :'Txvf123',
                              'base' :'HSS-InstallationSupportName=HSS-InstallationSupport,HSS-ServicesSupportContainerName=HSS-ServicesSupportContainer,HSS-ConfigurationContainerName=HSS-ConfigurationContainer,applicationName=HSS,nodeName=',
                              'attr': 'HSS-AuthenticationVectorSupplier'},
     'RADIUS' : {'user' :'administratorName=jambala,nodeName=',
                 'pass' :'Pokemon1',
                 'base' :'RAD-ApplicationName=SLF,applicationName=RADIUS,nodeName=',
                 'attr': 'RAD-IpAddress'},
     'DIA_TCP' : {'user' :'administratorName=jambala,nodeName=',
                   'pass' :'Pokemon1',
                   'base' :'stackId=SLF,stackContainerId=SLF,applicationName=DIA,nodeName=',
                   'attr': 'ipAddressesList'},
      'SEC_DIA_TCP' : {'user' :'administratorName=jambala,nodeName=',
                   'pass' :'Pokemon1',
                   'base' :'localVIPNetRedStackId=SLF,stackId=SLF,stackContainerId=SLF,applicationName=DIA,nodeName=',
                   'attr': 'zone2TcpAddressList'},
      'DIA_SCTP' : {'user' :'administratorName=jambala,nodeName=',
                   'pass' :'Pokemon1',
                   'base' :'stackId=SLF,stackContainerId=SLF,applicationName=DIA,nodeName=',
                   'attr': 'sctpAddressesList'},
      'SEC_DIA_SCTP' : {'user' :'administratorName=jambala,nodeName=',
                   'pass' :'Pokemon1',
                   'base' :'localVIPNetRedStackId=SLF,stackId=SLF,stackContainerId=SLF,applicationName=DIA,nodeName=',
                   'attr': 'zone2SctpAddressList'},
     'MAPSRIFORLCS':{'user' :'administratorName=HSS-Ericsson-Administrator,nodeName=',
                   'pass' :'Txvf123',
                   'base' :'HSS-InstallationSupportName=HSS-InstallationSupport,HSS-ServicesSupportContainerName=HSS-ServicesSupportContainer,HSS-ConfigurationContainerName=HSS-ConfigurationContainer,applicationName=HSS,nodeName=',
                   'attr': 'HSS-MapSriForLcs'}
     }
 


BOOT_SRVIP = '127.0.0.1'
SITEDB_PORT = '920'

class Tsp(Node):

    def __init__(self, config={}, force_primary = True):

        Node.__init__(self)

        if 'host' not in config.keys():
            raise ValueError('host missing')
        if 'port' not in config.keys():
            config['port'] = '22'
        if 'user' not in config.keys():
            config['user'] = 'telorb'
        if 'password' not in config.keys():
            config['password'] = 'telorb'

        self.__config = config
        self.__session_type=hss_utils.connection.session.EprtSetup

        self.__cluster = []
        self.__payload = []
        self.__controller = []
        self.__loader = []
        self.__linux = []
        self.__network_interfaces = []
        self.__processor_roles = {}
        self.__processor_ip = {}
        self.__traffic_info = {}
        self.__vipo = None

        self.create_connection(config=self.config, session_type=hss_utils.connection.session.EprtSetup)
        self.set_default_connection()

        if force_primary:
            self.force_primary_controller()

    @property
    def config(self):
        return self.__config

    @property
    def session_type(self):
        return self.__session_type

    @property
    def vipo(self):
        if  self.__vipo is None:
            cmd = 't-util /CLI/IPconfiguration/clusternetwork/detailedlist platform-vip'
            for line in self.run_command(cmd):
                if 'prefix' in line:
                    self.__vipo = line.split()[1].split('/')[0]

        return self.__vipo


    def force_primary_controller(self):
        if not self.is_primary:
            Node.extend_connection(self, identity = 'primary_controller',config={'host':'other_io', 'user':'telorb', 'password':'telorb'}, session_type=hss_utils.connection.session.EprtSetup)
            self.set_default_connection('primary_controller')

    def extend_connection(self, identity, host, port = '22', user='telorb',password='telorb', session_type=hss_utils.connection.session.EprtSetup, parent = 'main'):
        config = {'host':host, 'port':port,'user':user,'password': password}

        return Node.extend_connection(self, identity,config=config, session_type=session_type, parent=parent)


    def start_TelorbCLI(self, identity ='cli', force_primary = True, processor = None, port = None):
        new_connection = self.create_connection(config=self.config, session_type=hss_utils.connection.session.TelorbCLI, identity = identity)

        if force_primary:
            for loader in self.loader:
                if self.is_primary_loader(loader):
                    break
            port = 8000 + self.loader.index(loader)
            new_connection.set_CLI_server(loader, port)

        else:
            if processor is None:
                port = 8000
                processor = self.loader[0]
            elif port is None:
                port = 8000 + self.loader.index(processor)

            new_connection.set_CLI_server(processor, port)

        return new_connection

    def is_primary_loader(self, processor):
        if processor not in self.loader:
            return False
        cmd = 't-util /processors/%s/qtil/bin/ps | grep PSM-master' % processor
        return 'PSM-master' in  '\n'.join(self.run_command(cmd))


    def start_Telnet_Payload(self, payload, port = 8100, identity ='telnet_payload'):
        new_connection = self.create_connection(config=self.config, session_type=hss_utils.connection.session.TelorbCLI, identity = identity)
        new_connection.set_CLI_server(payload, port)
        new_connection.set_sync_expression('U-Qtil>')
        return new_connection


    def create_monitor(self, monitor_type, identity = 'monitor', force_primary = True, processor = None, port = None, start = True, extra_info = False):
        monitor =  Node.create_monitor(self, config=self.config, monitor_type = monitor_type, identity = identity)

        if force_primary:
            for loader in self.loader:
                if self.is_primary_loader(loader):
                    break
            port = 8000 + self.loader.index(loader)
            monitor.set_CLI_server(loader, port)

        else:
            if processor is None:
                port = 8000
                processor = self.loader[0]
            elif port is None:
                port = 8000 + self.loader.index(processor)

            monitor.set_CLI_server(processor, port)

        if extra_info:
            monitor.enable_extra_info()

        if start:
            self.start_monitor(identity)

        return monitor

    @property
    def is_primary(self):
        cmd = 'cat /proc/drbd | grep Connected | cut -f1 -d"/" | cut -f4 -d":"'
        answer = self.run_command(cmd)
        return 'Primary' in answer

    @property
    def network_interfaces(self):
        if len(self.__network_interfaces) == 0:
            cmd = 't-util /CLI/VipOspf/listvipospfinstance'
            for line in self.run_command(cmd):

                if 'Processor:' in line:
                    line =line.strip()
                    processor=line.split(':')[1]
                if 'Interface:' in line:
                    line =line.strip()
                    interface=line.split(':')[1]
		    self.__network_interfaces.append('%s:%s' % (processor.strip(),interface.strip()))

	return self.__network_interfaces

    @property
    def processor_roles(self):
        if len(self.__processor_roles) == 0:
            cmd = 'getboard summary'
            for line in self.run_command(cmd):
                if 'Proc_' in line:
                    if line.split()[2] == 'TP':
                        self.__processor_roles.update({line.split()[0]: line.split()[3]})

                    if line.split()[2] == 'IO':
                        self.__processor_roles.update({line.split()[0]: 'IO'})

        return self.__processor_roles
		
    @property
    def processors(self):
        processor_roles = self.processor_roles
        return processor_roles.keys()


    @property
    def processor_ip(self):
        if len(self.__processor_ip) == 0:
            for processor  in self.processor_roles.iterkeys():
                self.__processor_ip.update({processor: ''.join(self.__get_address(processor))})    
            for processor in self.controller:
                self.__processor_ip.update({processor: ''.join(self.__get_address(processor))})   

        return self.__processor_ip

    def get_address(self, processor):
        return self.processor_ip[processor]

    def __get_address(self, processor):
        cmd = 'sitedbclient --server-url=%s:%s  --print-nl query Processors THE Processor name=%s Network name=internal-0 addrs' % (BOOT_SRVIP,SITEDB_PORT, processor )
        return self.run_command(cmd)

    @property
    def cluster(self):
        if len(self.__cluster) == 0:
            cmd = 't-util ls /processors | sort -n'
            for line in self.run_command(cmd):
                if 'Proc_' in line:
                    self.__cluster.append(line.split('/')[0])

        return self.__cluster

    @property
    def payload(self):
        payload = []
        for processor in self.cluster: 
            if self.procsessor_is_type(processor,['PAYLOAD','SS7_BE,SCTP_FE','SCTP_FE,SS7_BE']):
                payload.append(processor)

        return payload
		
    @property
    def controller(self):
        if len(self.__controller) == 0:            
            cmd = 'getboard name -t IO'
            answer = self.run_command(cmd)
            if len(answer) > 0:
                self.__controller = answer[0].split(',')

        return self.__controller

    @property
    def loader(self):
        if len(self.__loader) == 0:
            for processor in self.processors:
                if self.procsessor_is_type(processor,['CM']):
                    self.__loader.append(processor)

        return self.__loader

    @property
    def linux(self):
        if len(self.__linux) == 0:
            for processor in self.cluster:
                if self.procsessor_is_type(processor,['OAM']):
                    self.__linux.append(processor)

        return self.__linux

    def procsessor_is_type(self, processor,proc_type):
        return self.processor_roles[processor] in proc_type


    def network_info(self):
        cmd = 'ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -l telorb %s "ip addr"' % self.linux[0]

        result = self.run_command(cmd, answer={'Password:': 'telorb'})
        return parsers.linuxcommands.ip_addr('\n'.join(result))


    def find_process(self, processor, process):

        identity ='telnet_%s' % processor
        self.start_Telnet_Payload(processor, identity = identity)
        cmd = 'ps'
        answer = self.run_command(cmd, identity = identity)
        return ' '.join(answer).count(process)

    def find_all_processes(self, processor):

        identity ='telnet_%s' % processor
        self.start_Telnet_Payload(processor, identity = identity)
        cmd = 'ps'
        answer = self.run_command(cmd, identity = identity)
        return ' '.join(answer)

    @property
    def primary_loader(self):

        for processor in self.loader:
            if self.is_primary_loader(processor):
                return processor

        return None

    def ldap_search(self,ldap_data, host, port=7323, nodename = 'jambala'):
        return ldap_search(host,port=port,
                            dn='%s%s' % (LDAP_DATA[ldap_data]['user'], nodename),
                            passwd='%s' % LDAP_DATA[ldap_data]['pass'],
                            base='%s%s' % (LDAP_DATA[ldap_data]['base'], nodename),
                            attribute='%s' % LDAP_DATA[ldap_data]['attr'])

    def get_GeoRed_info(self):
        self.start_TelorbCLI(identity ='cli')
        cmd = '/CLI/NetRed/RemoteZone/listremotezones'
        answer = self.run_command(cmd, identity = 'cli', timeout = 5.0)
        if 'Command not found' in ' '.join(answer):
            return 0, False

        geoRedZone = 1 if answer[1] == '2' else 2

        cmd = '/CLI/NetRed/RemoteZone/getrelativemode %s' % answer[1]
        answer = self.run_command(cmd, identity = 'cli', timeout = 5.0)

        if 'Netshared relative' in ' '.join(answer):
            geoRedActive = geoRedZone == 1
        else:
            geoRedActive = 'Down' not in ' '.join(answer)

        return geoRedZone, geoRedActive

    def get_traffic_info(self, traffic_type = 'IMS', info ={}, nodename = 'jambala', zone = 1, host_is_oam=True, IPv6 = False ):
        if len(info) == 0:
            info = ['hss_version', 'dia_tcp', 'dia_sctp','oam','radius','extdb',
                    'vector_supplier','controller','HSS-MapSriForLcs']

        if host_is_oam:
            oam_ip= self.config['host']
        else:
            oam_ip= self.vipo

        #if len(self.__traffic_info) == 0:
            #self.__traffic_info = {'hss_version':'', 'dia_tcp':'', 'dia_sctp':'','oam':oam_ip,'radius':'','extdb':'',
                                   #'vector_supplier' : '','controller': '','HSS-MapSriForLcs':False}
        traffic_info = {}
        for data in info:
            if data == 'oam':
                traffic_info.update({'oam':oam_ip})
            elif data == 'HSS-MapSriForLcs':
                traffic_info.update({'HSS-MapSriForLcs':False})
            else:
                traffic_info.update({data:''})


        if 'vector_supplier' in info:
            if traffic_type == 'IMS':
                data = self.ldap_search('VECTOR_SUPPLIER_IMS', oam_ip, nodename = nodename)
            else:
                data = self.ldap_search('VECTOR_SUPPLIER_EPC', oam_ip, nodename = nodename)

            if data is not None:
                traffic_info['vector_supplier'] = remove_quottes(data[0])

        if 'extdb' in info:
            dn = 'EXTDB_IMS' if traffic_type == 'IMS' else 'EXTDB_EPC'
            data = self.ldap_search(dn, oam_ip, nodename = nodename)

            #traffic_info['extdb'] = None
            if data is not None:
                #ext_db_url = data[0].replace('0:ldap://','')
                #traffic_info['extdb'] = ext_db_url.split(':')[0]

                regex = re.compile(r"\d+:ldap://(.+):\d+\$.+")
                for url in data:
                    res = regex.match(url)
                    if res:
                        address = res.group(1)
                        if address.startswith('['):
                            address = address[1:-1]
                        ip = ipaddress.ip_address(unicode(address))
                        #if isinstance(ip,IPv6Address if IPv6 else IPv4Address):
                        if isinstance(ip,IPv4Address):
                            traffic_info['extdb'] = '%s' % ip
                            break


        if traffic_type == 'IMS' and 'radius' in info:
            data = self.ldap_search('RADIUS', oam_ip, nodename = nodename)
            if data is not None:
                traffic_info['radius'] = data[zone-1][2:]

        if zone == 2:

            if 'dia_tcp' in info:
                data = self.ldap_search('SEC_DIA_TCP', oam_ip, nodename = nodename)
                if data is not None:
                    #traffic_info['dia_tcp'] = data[0][2:]
                    for address in data:
                        ip = ipaddress.ip_address(unicode(address[2:]))
                        if isinstance(ip,IPv6Address if IPv6 else IPv4Address):
                            traffic_info['dia_tcp'] = address[2:]
                            break

            if 'dia_sctp' in info:
                data = self.ldap_search('SEC_DIA_SCTP', oam_ip, nodename = nodename)
                if data is not None:
                    #traffic_info['dia_sctp'] = data[0][2:]
                    for address in data:
                        ip = ipaddress.ip_address(unicode(address[2:]))
                        if isinstance(ip,IPv6Address if IPv6 else IPv4Address):
                            traffic_info['dia_sctp'] = address[2:]
                            break

        else:

            if 'dia_tcp' in info:
                data = self.ldap_search('DIA_TCP', oam_ip, nodename = nodename)
                if data is not None:
                    #traffic_info['dia_tcp'] = data[0][2:]
                    for address in data:
                        ip = ipaddress.ip_address(unicode(address[2:]))
                        if isinstance(ip,IPv6Address if IPv6 else IPv4Address):
                            traffic_info['dia_tcp'] = address[2:]
                            break

            if 'dia_sctp' in info:
                data = self.ldap_search('DIA_SCTP', oam_ip, nodename = nodename)
                if data is not None:
                    #traffic_info['dia_sctp'] = data[0][2:]
                    for address in data:
                        ip = ipaddress.ip_address(unicode(address[2:]))
                        if isinstance(ip,IPv6Address if IPv6 else IPv4Address):
                            traffic_info['dia_sctp'] = address[2:]
                            break

        if 'HSS-MapSriForLcs' in info:
            data = self.ldap_search('MAPSRIFORLCS', oam_ip, nodename = nodename)
            if data is None:
                traffic_info['HSS-MapSriForLcs'] = False
            else:
                traffic_info['HSS-MapSriForLcs'] = (data[0] == 'TRUE')

        if 'controller' in info:
            if not host_is_oam:
                traffic_info['controller'] = self.config['host']
            else:
                config={'host': self.config['host'],
                    'port': '31310',
                    'user':'jambala' ,
                    'password': 'Pokemon1'}

                self.create_connection(config=config, identity = 'vipoam', session_type=hss_utils.connection.session.JambalaCLI)
                new_connection=self.connection(identity='vipoam')
                new_connection.set_sync_expression('\[ok\]')
                cmd = 'show configuration Node TspTransport TspIpInterfaces TspIpInterface tspIpNetwork external-0'
                answer = self.run_command(cmd, identity = 'vipoam')
                for line in answer:
                    if 'TspIpInterface ' in line:
                        controller = line.split()[1]
                        config={'host': controller,
                        'port': '22',
                        'user':'telorb' ,
                        'password': 'telorb'}
                        identity = '%s' % controller
                        self.create_connection(config=config, identity = identity,session_type=hss_utils.connection.session.StandardLinux)
                        self.set_default_connection(identity = identity)
                        if self.is_primary:
                            traffic_info['controller']= controller

        if 'hss_version' in info:
            config={'host': traffic_info['controller'],
                    'port': '22',
                    'user':'telorb' ,
                    'password': 'telorb'}

            self.start_TelorbCLI(identity ='cli', force_primary = False)
            cmd = '/env/getenv HSS_VERSION'
            answer = self.run_command(cmd, identity = 'cli')
            if len(answer):
                traffic_info['hss_version'] = (answer[1].split(' '))[0]

        return traffic_info


    def start_healthcheck(self, output):
        cmd = 'HssHealthCheck -all --no-formatting -r %s' % output
        result = self.run_command(cmd, 
                                  answer={'TSP Username': 'telorb','TSP Password':'telorb','LDAP Username': 'jambala','LDAP Password':'Pokemon1'},
                                  timeout=300)


    def wait_until_cabinet_available(self, timeout=120):

        config={'host': self.vipo,
                'port': '31310',
                'user':'jambala' ,
                'password': 'Pokemon1'}

        timeout = float(int(timeout))
        started = time.time()
        ssh_server_not_available = True
        while ssh_server_not_available:
            now = time.time()
            time.sleep(float(10))

            try:
                self.create_connection(config=config, identity = 'vipoam', session_type=hss_utils.connection.session.JambalaCLI)
                new_connection=self.connection(identity='vipoam')
                new_connection.set_sync_expression('\[ok\]')
                cmd = 'show configuration Node TspTransport TspIpInterfaces TspIpInterface tspIpNetwork external-0'
                self.run_command(cmd, identity = 'vipoam')
                ssh_server_not_available = False

            except Exception as e:
                _DEB('Cabinet reload is on going: %s' % str(e))
                timeout -= time.time() - now
                if timeout < float(0):
                    return False

        return True


