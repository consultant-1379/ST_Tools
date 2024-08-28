#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import re
import os
import sys
import threading
import time
import pprint
import xml.etree.ElementTree as ET
import copy

import hss_utils.connection.session
import hss_utils.connection.ssh
from hss_utils.st_command import remove_quottes, sorted_nicely, clear_ansi, parse, get_node_credentials
from hss_utils.st_command import CommandFailure, ExecutionTimeout
from . import Node
import ipaddress
from ipaddress import IPv4Address, IPv6Address

import e3utils.log as logging
_DEB = logging.internal_debug
_WRN = logging.warning
_ERR = logging.error
_INF = logging.info

EXTDB_CLISS_DN ='ManagedElement=1,HSS-Function.applicationName=HSS_FUNCTION,HSS-ExtDbFunction.applicationName=HSS_EXTDB'

EXTDB_INSTALL_CLISS_DN ='ManagedElement=1,HSS-Function.applicationName=HSS_FUNCTION,HSS-ExtDbFunction=HSS_EXTDB,\
HSS-ExtDbServicesSupportContainer=HSS-ExtDbServicesSupportContainer,HSS-ExtDbInstallation=HSS-ExtDbInstallation'

VECTOR_SUPPLIER_EPC_CLISS_DN ='ManagedElement=1,HSS-Function=HSS_FUNCTION,HSS-EsmApplication=HSS_ESM,HSS-EsmConfigurationContainer=HSS-EsmConfigurationContainer,\
HSS-EsmServicesSupportContainer=HSS-EsmServicesSupportContainer,HSS-EsmInstallationSupport=HSS-EsmInstallationSupport'

VECTOR_SUPPLIER_IMS_CLISS_DN ='ManagedElement=1,HSS-Function=HSS_FUNCTION,HSS-IsmSdaApplication=HSS_ISMSDA,HSS-ConfigurationContainer=HSS-ConfigurationContainer,\
HSS-ServicesSupportContainer=HSS-ServicesSupportContainer,HSS-InstallationSupport=HSS-InstallationSupport'

MODULE_IMS_CLISS_DN ='ManagedElement=1,HSS-Function=HSS_FUNCTION,HSS-IsmSdaApplication=HSS_ISMSDA'
MODULE_ESM_CLISS_DN ='ManagedElement=1,HSS-Function=HSS_FUNCTION,HSS-EsmApplication.applicationName=HSS_ESM,\
HSS-EsmConfigurationContainer=HSS-EsmConfigurationContainer,HSS-EsmConfigurationData=HSS-EsmConfigurationData'

ARPF_CLISS_DN ='ManagedElement=SELIITHSS00032-L,HSS-Function.applicationName=HSS_FUNCTION,HSS-Common.applicationName=HSS_Common,HSS-CommonConfigurationContainer=HSS-CommonConfigurationContainer,\
HSS-CommonServicesSupportContainer=HSS-CommonServicesSupportContainer,HSS-CommonServicesSupport=HSS-CommonServicesSupport'


RADIUS_CLISS_DN = 'ManagedElement=1,HSS-Function.applicationName=HSS_FUNCTION,RAD-Application.applicationName=RADIUS,RAD-AppInstance.rad-ApplicationName=HSS_SM'

DIA_IMS_CLISS_DN = 'ManagedElement=1,HSS-Function=HSS_FUNCTION,DIA-CFG-Application=DIA,DIA-CFG-StackContainer=HSS_ISMSDA,DIA-CFG-OwnNodeConfig=HSS_ISMSDA'
DIA_EPC_CLISS_DN = 'ManagedElement=1,HSS-Function=HSS_FUNCTION,DIA-CFG-Application=DIA,DIA-CFG-StackContainer=HSS_ESM,DIA-CFG-OwnNodeConfig=HSS_ESM'

DIA_PEER_ISMSDA_CLISS_DN = 'ManagedElement=1,HSS-Function=HSS_FUNCTION,DIA-CFG-Application=DIA,DIA-CFG-StackContainer=HSS_ISMSDA,DIA-CFG-PeerNodeContainer=HSS_ISMSDA'
DIA_PEER_ESM_CLISS_DN = 'ManagedElement=1,HSS-Function=HSS_FUNCTION,DIA-CFG-Application=DIA,DIA-CFG-StackContainer=HSS_ESM,DIA-CFG-PeerNodeContainer=HSS_ESM'
DIA_PEER_SM_CLISS_DN = 'ManagedElement=1,HSS-Function=HSS_FUNCTION,DIA-CFG-Application=DIA,DIA-CFG-StackContainer=HSS_SM,DIA-CFG-PeerNodeContainer=HSS_SM'

MAP_ISMSDA_CLISS_DN = 'ManagedElement=1,HSS-Function=HSS_FUNCTION,MPV-Application=MAP,MPV-AppInstance=ISM-SDA'
MAP_ESM_CLISS_DN = 'ManagedElement=1,HSS-Function=HSS_FUNCTION,MPV-Application=MAP,MPV-AppInstance=HSS_ESM'

BACKUP_CLISS_DN = 'ManagedElement=1,SystemFunctions=1,BrM=1,BrmBackupManager=SYSTEM_DATA'
ALARM_CLISS_DN = 'ManagedElement=1,SystemFunctions=1,Fm=1'

HEALTH_CHECK_DN = 'ManagedElement=1,SystemFunctions=1,HealthCheckM=1'

USER_MNG_DN = 'ManagedElement=1,SystemFunctions=1,SecM=1,UserManagement=1'

NBI_ALARM_CLISS_DN = 'ManagedElement=1,SystemFunctions=1,Fm=1'
NBI_TENANT_CLISS_DN = 'ManagedElement=1,DmxcFunction=1'
NBI_PROC_CLISS_DN = 'ManagedElement=1,Equipment=1'

LICENSE_DN = 'ManagedElement=1,SystemFunctions=1,Lm=1'
UDM_SERVER_CLISS_DN = 'ManagedElement=1,HSS-Function=HSS_FUNCTION,HTTP-Application=HTTP,HTTP-PeerServiceConfig=UDM'
UDM_HTTP2_SERVER_CLISS_DN = 'ManagedElement=1,HSS-Function=HSS_FUNCTION,HTTP-Application=HTTP,HTTP-PeerServiceConfig=UDMHttp2'

ESM_ACTIVE_DN = 'ManagedElement=1,HSS-Function=HSS_FUNCTION,HSS-EsmApplication=HSS_ESM,HSS-EsmLicense=HSS-EsmLicense'
SOAP_SERVER_CLISS_DN = 'ManagedElement=1,Transport=1,Evip=1,EvipAlbs=1,EvipAlb=ln_om_sc,EvipVips=1'
EVIP_FLOWPOLICY_CLISS_DN = 'ManagedElement=1,Transport=1,Evip=1,EvipAlbs=1,EvipAlb=ln_om_sc,EvipFlowPolicies=1'
SOAP_LDAP_SERVER_CLISS_DN = 'ManagedElement=1,Transport=1,Evip=1,EvipAlbs=1,EvipAlb=ln_ldap_sc,EvipFlowPolicies=1,EvipFlowPolicy=ExtDbSoap'

NTP_SERVER_DN = 'ManagedElement=1,SystemFunctions=1,SysM=1,TimeM=1,Ntp=1'
SYS_DN = 'ManagedElement=1,SystemFunctions=1,SysM=1'
CERT_MNG_DN = 'ManagedElement=1,SystemFunctions=1,SecM=1,CertM=1'


CLISS_ACCESS = {
     'DEFAULT' : 'hssadministrator',
     'ESM_ACTIVE' : 'hssadministrator',
     'EXTDB' : 'hssadministrator',
     'EXTDB_INSTALL' : 'ericssonhsssupport',
     'VECTOR_SUPPLIER' : 'ericssonhsssupport',
     'ARPF' : 'ericssonhsssupport',
     'RADIUS' : 'hssadministrator',
     'DIAMETER' : 'hssadministrator',
     'MAP' : 'hssadministrator',
     'BACKUP' : 'hssadministrator',
     'ALARM' : 'hssadministrator',
     'NBI_ALARM' : 'advanced',
     'NBI_TENANT' : 'advanced',
     'NBI_PROC' : 'advanced',
     'HEALTH_CHECK' : 'hssadministrator',
     'USER_MNG' : 'com-emergency',
     'UDM_SERVER': 'hssadministrator',
     'SOAP_SERVER': 'SystemAdministrator',
     'SOAP_LDAP_SERVER': 'SystemAdministrator',
     'USER_LICENSE': 'SystemAdministrator',
     'USER_CERT' : 'com-emergency',
     'USER_NTP': 'SystemAdministrator'
     }

def identation(text_line):
    return len(text_line) - len(text_line.lstrip())

class Cba(Node):

    def __init__(self, config={}, force_primary = False, netconf = False):
        Node.__init__(self)

        self.__USER_CREDENTIALS = get_node_credentials('hss_cba')

        if 'host' not in config.keys():
            raise ValueError('host missing')
        if 'port' not in config.keys():
            config['port'] = '22'
        if 'user' not in config.keys():
            config['user'] = 'com-emergency'

        config['password'] = self.__USER_CREDENTIALS[config['user']]

        self.__config = config
        self.__conId_for_log = None

        if netconf:
            self.__session_type=hss_utils.connection.session.NetconfCBA
        else:
            self.__session_type=hss_utils.connection.session.StandardLinux
            if config['user'] != 'root':
                self.__session_type=hss_utils.connection.session.HardenedLinux

        self.__processors = []
        self.__payloads = []
        self.__envdata = []
        _DEB('Creating connection  with session type %s' % self.session_type)
        con = self.create_connection(config=self.config, session_type=self.session_type)
        if self.__session_type == hss_utils.connection.session.HardenedLinux:
            con.set_root_passw(self.__USER_CREDENTIALS['root'])

        self.set_default_connection()

        if force_primary:
            self.force_primary_controller()

    def get_user_credential(self,user):
        return self.__USER_CREDENTIALS[user]


    @property
    def cli_port(self):
        regex = re.compile(r"<cliPort>(.+)</cliPort>")
        cmd = 'cat  /storage/system/config/com-apr9010443/lib/comp/libcom_sshd_manager.cfg'
        for line in self.run_command(cmd):
            res = regex.match(line.strip())
            if res:
                _DEB('cli_port:%s' % res.group(1))
                return int(res.group(1))

    @property
    def config(self):
        return self.__config

    @property
    def session_type(self):
        return self.__session_type

    def sc_ip(self, sc, IPv6=False):
        cmd = 'cat /cluster/etc/cluster.conf | grep ln_om | grep "ip %s" %s' %(('1' if sc == 'SC-1' else '2'),
                                                                                      (' | grep sc6' if IPv6 else '' ))
        return self.run_command(cmd)[0].split()[-1]

    def force_primary_controller(self):
        _DEB('force_primary_controller()')
        cmd = 'hostname'
        hostname = self.run_command(cmd)[0]
        if not self.sc_is_primary(hostname):
            hostname = '%s' % 'SC-1' if hostname == 'SC-2' else 'SC-2'

        self.__config['host'] = self.sc_ip(hostname)
        self.release_connection('main')

        _DEB('Creating connection  for primary controller %s' % self.__config['host'])
        con = self.create_connection(config=self.config, session_type=self.session_type)
        if self.__session_type == hss_utils.connection.session.HardenedLinux:
            con.set_root_passw(self.__USER_CREDENTIALS['root'])

        self.set_default_connection()

    def get_primary_sc(self, IPv6=False):
        _DEB('get_primary_sc()')
        cmd = 'hostname'
        hostname = self.run_command(cmd)[0]
        if not self.sc_is_primary(hostname):
            hostname = '%s' % 'SC-1' if hostname == 'SC-2' else 'SC-2'
        return (hostname, self.sc_ip(hostname, IPv6=IPv6))

    @property
    def datetime(self):
        cmd = 'date +%Y-%m-%dT%H:%M:%S'
        answer = self.run_command(cmd)
        return answer[-1]


    def extend_connection(self, identity, host, port = '1022', user='root', parent = 'main'):
        _DEB('extend_connection()')
        password = self.__USER_CREDENTIALS[user]
        config = {'host':host, 'port':port,'user':user,'password': password}
        _DEB('Extending connection to user %s and password %s ' % (user,password))
        _DEB('Extending connection to host %s with port %s and identity %s' % (host,port,identity))
        return Node.extend_connection(self, identity, config=config, session_type=hss_utils.connection.session.StandardLinux, parent=parent)

    def upload(self, source, destination, identity = 'main', timeout = None):
        up_user = self.config['user']
        _DEB('Uploading files with user %s and identity %s to directory %s' % (up_user, identity, destination))
        if up_user != 'root':
            up_dir =  self.temporary_path
            _DEB('Creating temporary directory %s' % up_dir)
            cmd = 'mkdir -p %s' % up_dir
            self.run_command(cmd, identity)
            cmd = 'rm %s*' % up_dir
            self.run_command(cmd, identity)
            cmd = 'chmod 777 %s' % up_dir
            self.run_command(cmd, identity)
            temp_destination = up_dir
        else:
            temp_destination = destination

        exit_code = Node.upload(self, source, temp_destination, identity, timeout)
        if up_user != 'root':
            cmd = 'mkdir -p %s; ' % destination
            self.run_command(cmd, identity)
            _DEB('Copying files from temporary directory to final destination %s' % destination)
            cmd = 'cp %s* %s' % (up_dir, destination)
            returncode = self.run_command(cmd, identity)
            local_source = source.split('/')[-1]
            cmd = 'chmod 755 %s/%s' % (destination,local_source)
            returncode = self.run_command(cmd, identity)
            cmd = 'rm -rf %s*' % up_dir
            self.run_command(cmd, identity)

        return exit_code


    def download(self, source, destination, identity = 'main', timeout = None):
        down_user = self.config['user']
        _DEB('Downloading files with user %s and identity %s' % (down_user, identity))
        if down_user != 'root':
            down_dir =  self.temporary_path
            _DEB('Creating temporary directory %s' % down_dir);
            cmd = 'mkdir -p %s' % down_dir
            self.run_command(cmd, identity)
            cmd = 'rm %s*' % down_dir
            self.run_command(cmd, identity)
            cmd = 'chmod 777 %s' % down_dir
            self.run_command(cmd, identity)
            _DEB('Copying files from source %s to temporary directory %s' % (source, down_dir))
            cmd = 'cp %s %s' % (source, down_dir)
            returncode = self.run_command(cmd, identity)
            cmd = 'chmod -R 777 %s*' % down_dir
            self.run_command(cmd, identity)
            temp_source = os.path.join(down_dir, os.path.basename(source))
        else:
            temp_source = source

        _DEB('Downloading files from source %s to destination %s' % (temp_source, destination))
        return Node.download(self, temp_source, destination, identity, timeout)

    def start_CBACliss(self, host, identity ='cliss',port = '122' ,user='hssadministrator'):
        _DEB('start_CBACliss()')
        password = self.__USER_CREDENTIALS[user]
        if self.check_available_connection(identity = identity):
            try:
                _DEB('Using available connection for identity %s' % identity)
                connection = self.get_connection(identity = identity)
                self.run_command('', identity=identity, timeout = 5.0)
                return connection
            except (hss_utils.connection.ConnectionFailedEOF, hss_utils.connection.ConnectionFailedTimeout) as e:
                _DEB('%s connection in wrong state. Recreate it' % identity)
                self.release_connection(identity)

        _DEB('Creating new connection for identity %s' % identity)
        if self.cli_port != 122:
            port = 830

        config = {'host':host,'port':port, 'user':self.__config['user'], 'password':self.__config['password']}
        try:
            if self.is_AandA_enabled() and user != 'root':
                config = {'host':host,'port':port, 'user':user, 'password':password}

            new_connection = self.create_connection(config=config, session_type=hss_utils.connection.session.CBACliss,
                                                    identity = identity, force_open=True, timeout=60.0)
        except hss_utils.connection.Unauthorized:
            try:
                _DEB('%s connection refused for user %s. Trying with com-emergency user.' % (identity, config['user']))
                config['user'] = 'com-emergency'
                password = self.__USER_CREDENTIALS['com-emergency']
                config['password'] = password
                new_connection = self.create_connection(config=config, session_type=hss_utils.connection.session.CBACliss,
                                                        identity = identity, force_open=True, timeout=60.0)

            except hss_utils.connection.Unauthorized:
                _DEB('%s connection refused for user %s. Trying again ...' % (identity, config['user']))
                self.check_user_locked(config['user'])
                new_connection = self.create_connection(config=config, session_type=hss_utils.connection.session.CBACliss, identity = identity, force_open=True, timeout=60.0)

        return new_connection

    def start_CBAClissEmergency(self, identity ='cliss_emergency',port = '22' ,user='com-emergency', parent = 'main'):
        _DEB('start_CBAClissEmergency()')
        password = self.__USER_CREDENTIALS[user]
        cmd = 'hostname'
        hostname = self.run_command(cmd, identity=parent)[0]
        if not self.sc_is_primary(hostname):
            hostname = '%s' % 'SC-1' if hostname == 'SC-2' else 'SC-2'
        config = {'host':hostname,'port':port, 'user':user, 'password':password}
        self.check_user_locked(config['user'])
        _DEB('Extending connection to host %s with port %s and identity %s' % (hostname,port,identity))
        return Node.extend_connection(self, identity,config=config, session_type=hss_utils.connection.session.CBACliss, parent=parent)


    def start_CBANBICliss(self, host, identity ='nbi_cliss',port = '2024' ,user='advanced'):
        password = self.__USER_CREDENTIALS[user]
        config = {'host':host,'port':port, 'user':user, 'password':password}
        _DEB('Extending connection to host %s with port %s and identity %s' % (host,port,identity))
        try:
            new_connection = self.create_connection(config=config, session_type=hss_utils.connection.session.CBANBICliss, identity = identity, force_open=True)
        except hss_utils.connection.Unauthorized:
            config['user'] = self.__config['user']
            config['password'] = self.__config['password']
            new_connection = self.create_connection(config=config, session_type=hss_utils.connection.session.CBACliss, identity = identity, force_open=True)

        return new_connection


    def start_CBASignmcli(self, identity ='signm', parent = 'main'):
        cmd = 'hostname'
        hostname = self.run_command(cmd, identity=parent)[0]
        config = {'host':hostname,'port':'1022', 'user':'root', 'password': self.__USER_CREDENTIALS['root']}
        _DEB('Extending connection to host %s with port %s and identity %s' % (hostname,config['port'],identity))
        new_connection = Node.extend_connection(self, identity = identity, config=config, session_type=hss_utils.connection.session.CBASignmcli)
        return new_connection


    def subnets(self):
        subnets = []
        cmd = 'ip route'
        answer = self.run_command(cmd)
        for line in answer:
            if '/' in line.split()[0]:
                subnets.append(line.split('/')[0])

        return subnets

    def sc_is_primary(self, sc):
        _DEB('sc_is_primary()')
        status = self.controller_state()
        if status:
            try:
                return 'ACTIVE' in status[sc]
            except KeyError:
                return False

        return False

    @property
    def is_primary(self):
        cmd = 'hostname'
        sc = self.run_command(cmd)[0]
        return sc_is_primary(sc)

    @property
    def is_drbd_primary(self):
        cmd = 'hostname'
        hostname = self.run_command(cmd)[0]
        status = self.controller_drbd_state()
        if 'Primary' == status:
            return True
        else:
            return False

    @property
    def hss_release(self):
        cmd = 'immlist -a release managedElementId=1'
        answer = self.run_command(cmd,full_answer=True)
        for line in answer.splitlines():
            if 'release=' in line:
                return line.split('=')[-1]
        raise CommandFailure('"%s" cmd failed' % cmd)
 
    @property
    def payload(self):
        payloads = []
        lines = self.run_command("cmw-status -v node | sed '/SC-/,/OperState/d'")
        unlocked = False
        for line in lines:
            searchObj = re.search(r'PL\-\d+',line)
            if searchObj:
                payload = searchObj.group()
            elif re.search(r'AdminState\=UNLOCKED',line):
                unlocked = True
            elif re.search(r'OperState\=ENABLED',line) and unlocked:
                payloads.append(payload)
                unlocked = False
                payload = None

        return payloads

    @property
    def node_status_OK(self):
        new_connection = self.create_connection(config=self.config, session_type=self.session_type,identity='status')
        if self.session_type == hss_utils.connection.session.HardenedLinux:
            new_connection.set_root_passw(self.__USER_CREDENTIALS['root'])
        try:
            answer = self.run_command('cmw-status app csiass comp node sg si siass su',identity='status', full_answer = True)
            self.release_connection(identity='status')
        except Exception:
            self.release_connection(identity='status')
            return False
        return 'Status OK' in answer

    def processor_umask(self, processor):
        self.extend_connection(processor, processor)
        cmd = 'umask'
        answer = self.run_command(cmd, identity = processor)
        return answer[0]

    def processor_uuid(self, processor):
        self.extend_connection(processor, processor)
        cmd = 'dmidecode | grep UUID'
        answer = self.run_command(cmd, identity = processor)
        data = answer[0]
        uuid = data.split(':')[1]
        uuid = uuid.strip()
        return uuid.lower()

    def processor_date(self, processor, full_date = False):
        self.extend_connection(processor, processor)
        if full_date:
            cmd = 'date +%Y%m%d-%H:%M:%S'
        else:
            cmd = 'date +%Y%m%d'
        answer = self.run_command(cmd, identity = processor)
        return answer[-1]

    def processor_state(self, processor):
        lines = self.run_command("cmw-status -v node", full_answer = True)

        data=parse(lines)
        data=data[data.keys()[0]]
        for key, value in data.iteritems():
            if processor in key:
                if 'DISABLED' in value['OperState']:
                    return 'DISABLED'
                elif 'ENABLED' in value['OperState']:
                    if 'UNLOCKED' in value['AdminState']:
                        return 'UNLOCKED'
                    else:
                        return 'LOCKED'

    def all_processors_state(self):
        lines = self.run_command("cmw-status -v node", full_answer = True)
        data=parse(lines)
        state_data={}
        data=data[data.keys()[0]]
        for key, value in data.iteritems():
            searchObj = re.search(r'PL\-\d+|SC\-\d+',key)
            if searchObj:
                processor = searchObj.group()
            if 'DISABLED' in value['OperState']:
                state_data[processor] = 'DISABLED'
            elif 'ENABLED' in value['OperState']:
                if 'UNLOCKED' in value['AdminState']:
                    state_data[processor] = 'UNLOCKED'
                else:
                    state_data[processor] = 'LOCKED'
        return state_data

    def controller_state(self):
        _DEB('controller_state()')
        result = {}
        lines = self.run_command('cmw-status -v siass | grep -A2 "ComSa\|ERIC-com"', full_answer = True)
        data=parse(lines)

        try:
            data = data['safSISU']
            for key, value in data.iteritems():
                if 'Cmw1' in key or 'SC-1' in key:
                    result.update({'SC-1': value['HAState']})
                if 'Cmw2' in key or 'SC-2' in key:
                    result.update({'SC-2': value['HAState']})
        except KeyError as e:
            _DEB('Problem reading SC status: %s' % str(e))

        if result:
            return result

        raise CommandFailure('SC Status info not available')


    def controller_drbd_state(self):
        answer = self.run_command('drbdadm status', full_answer = True)
        if len(answer):
            return answer
        else:
            _ERR('No answer from command "drbdadm status": %s' % answer)



    @property
    def processors(self):
        if len(self.__payloads) == 0:
            lines = self.run_command("cmw-status -v node | sed '/SC-/,/OperState/d'")
            for line in lines:
                searchObj = re.search(r'PL\-\d+',line)
                if searchObj:
                    payload = searchObj.group()
                elif re.search(r'OperState\=ENABLED',line):
                    self.__payloads.append(payload)
                    payload = None

        return self.__payloads

    @property
    def all_processors(self):
        if len(self.__processors) == 0:
            lines = self.run_command("cmw-status -v node")
            for line in lines:
                searchObj = re.search(r'PL\-\d+|SC\-\d+',line)
                if searchObj:
                    processor = searchObj.group()
                    self.__processors.append(processor)

        return self.__processors

    @property
    def envdata(self):
        if len(self.__envdata) == 0:
            self.__envdata = self.run_command('vdicos-envdata-list')
        return self.__envdata

    def get_envdata(self, var):
        if var in self.envdata:
            return self.run_command('vdicos-envdata-get %s' % var)[0]

    def set_envdata(self, var, value):
        if var in self.envdata:
            self.run_command('vdicos-envdata-set %s %s' % (var, value))

        else:
            self.run_command('vdicos-envdata-create %s' % var)
            self.run_command('vdicos-envdata-set %s %s' % (var, value))

    def unset_envdata(self, var):
        if var in self.envdata:
            self.run_command('vdicos-envdata-unset %s' % var)

    @property
    def applogs_path(self):
        return '/cluster/storage/no-backup/coremw/var/log/saflog/vdicos/applog'

    @property
    def alert_path(self):
        return '/var/filem/nbi_root/AlertLogs'

    @property
    def alarm_path(self):
        return '/var/filem/nbi_root/AlarmLogs'

    @property
    def temporary_path(self):
        user = self.config['user']
        return '/home/%s/upload_download/' % user

    @property
    def certificates_path(self):
        return '/cluster/home/sec/certificates'

    @property
    def conId_for_log(self):
        if self.__conId_for_log is None:
            try:
                config = copy.deepcopy(self.config)
                config['user'] = 'com-emergency'
                config['password'] = self.__USER_CREDENTIALS['com-emergency']
                _DEB('Creating connection Id_for_log for com-emergency')
                self.create_connection(config=config, session_type=hss_utils.connection.session.StandardLinux,identity='com-emergency', force_open=True)
                self.__conId_for_log = 'com-emergency'
            except hss_utils.connection.Unauthorized:
                _DEB('Exception creating connection Id_for_log for com-emergency')
                self.__conId_for_log = 'main'
        _DEB('conId_for_log is %s' % self.__conId_for_log)
        return self.__conId_for_log

    @conId_for_log.setter
    def conId_for_log(self, value):
        self.__conId_for_log = value


    def find_logs(self, path, wildcard='*'):
        cmd = 'ls -Art %s/%s' %(path,wildcard)
        answer = self.run_command(cmd, identity=self.conId_for_log)

        filtered_answer= []
        for line in answer:
            if line.startswith('ls:'):
                _DEB('Line log starts with ls: %s' % line)
                return filtered_answer
            line = line.split('/')[-1]
            filtered_answer.append(clear_ansi(line))

        return filtered_answer

    def get_log_info(self, log):
        cmd = 'cat %s' % log
        return self.run_command(cmd, identity=self.conId_for_log, full_answer=True)

    def logs(self, path, wildcard='*'):
        answer= []
        for line in self.find_logs(path, wildcard=wildcard):
            line = line.split('/')[-1]
            answer.append(clear_ansi(line))

        return answer

    def logs_to_clean(self, path, wildcard='*'):
        logs_to_clean = []
        for log in self.logs(path, wildcard=wildcard):
            m = re.search("\d\d\d", log)
            if m:
                first_underscore_after_name_pos = m.start() - 1
                underscore_counter = log[first_underscore_after_name_pos:].count('_')
                if '.cfg' in log and underscore_counter == 2:
                    logs_to_clean.append(log)
                elif '.log' in log and underscore_counter == 4:
                    logs_to_clean.append(log)

        return logs_to_clean

    def active_log(self, path, wildcard='*.log'):
        log_list = self.logs(path, wildcard=wildcard)
        for log in reversed(log_list):
            underscore_counter = log.count('_')
            if underscore_counter == 2:
                return log

    @property
    def hss_version(self):
        cmd = 'vdicos-envdata-get HSS_VERSION'
        answer = self.run_command(cmd)
        if len(answer):
            return answer[0]

    def enable_AandA(self):
        if self.is_AandA_enabled():
            return

        self.start_CBAClissEmergency(identity ='cliss_emergency')
        cmd = '%s,LdapAuthenticationMethod=1' % USER_MNG_DN
        self.run_command(cmd, identity = 'cliss_emergency', full_answer=True)

        cmd = 'configure'
        self.run_command(cmd, identity = 'cliss_emergency', full_answer=True)

        cmd = 'administrativeState=UNLOCKED'
        self.run_command(cmd, identity = 'cliss_emergency', full_answer=True)

        cmd = '%s,LocalAuthorizationMethod=1' % USER_MNG_DN
        self.run_command(cmd, identity = 'cliss_emergency', full_answer=True)

        cmd = 'administrativeState=UNLOCKED'
        self.run_command(cmd, identity = 'cliss_emergency', full_answer=True)

        cmd = 'commit'
        answer = self.run_command(cmd, identity = 'cliss_emergency', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))

    def disable_AandA(self):
        if not self.is_AandA_enabled():
            return

        self.start_CBAClissEmergency(identity ='cliss_emergency')
        cmd = '%s,LdapAuthenticationMethod=1' % USER_MNG_DN
        self.run_command(cmd, identity = 'cliss_emergency', full_answer=True)

        cmd = 'configure'
        self.run_command(cmd, identity = 'cliss_emergency', full_answer=True)

        cmd = 'administrativeState=LOCKED'
        self.run_command(cmd, identity = 'cliss_emergency', full_answer=True)

        cmd = '%s,LocalAuthorizationMethod=1' % USER_MNG_DN
        self.run_command(cmd, identity = 'cliss_emergency', full_answer=True)

        cmd = 'administrativeState=LOCKED'
        self.run_command(cmd, identity = 'cliss_emergency', full_answer=True)

        cmd = 'commit'
        answer = self.run_command(cmd, identity = 'cliss_emergency', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))


    def check_user_locked_sc(self, user, sc):
        _DEB('check user locked %s in %s' % (user, sc))
        con = self.create_connection(config=self.config, session_type=self.session_type, identity='aux_com')
        if self.session_type == hss_utils.connection.session.HardenedLinux:
            con.set_root_passw(self.__USER_CREDENTIALS['root'])

        cmd = 'ssh %s pam_tally2 --user %s' % (sc, user)
        answer = self.run_command(cmd)
        num_failures = 0
        info = answer[1].split()
        if user in info:
            num_failures=int(info[1])
            _DEB('Num failures for user %s in %s is %d ' % (user, sc, num_failures))

        if num_failures > 4 :
            _DEB('Reseting failures for user %s ' % user)
            cmd = 'ssh %s pam_tally2 --user %s -r' % (sc, user)
            time.sleep(float(0.1))
            answer = self.run_command(cmd)
            cmd = 'ssh %s pam_tally2 --user %s' % (sc, user)
            answer = self.run_command(cmd)
            info = answer[1].split()
            if user in info:
                num_failures=int(info[1])
                _DEB('Num failures after reset for user %s in %s is %d' % (user, sc, num_failures))
        

    def check_user_locked(self, user):
        _DEB('check user locked %s' % user)
        cmd = 'hostname'
        hostname = self.run_command(cmd)[0]
        self.check_user_locked_sc(user, hostname)
        hostname = '%s' % 'SC-1' if hostname == 'SC-2' else 'SC-2'
        self.check_user_locked_sc(user, hostname)


    def is_AandA_enabled(self):
        _DEB('is_AandA_enabled()')
        con = self.create_connection(config=self.config, session_type=self.session_type, identity='aux_com')
        if self.session_type == hss_utils.connection.session.HardenedLinux:
            con.set_root_passw(self.__USER_CREDENTIALS['root'])

        self.start_CBAClissEmergency(identity ='cliss_emergency', parent='aux_com')
        cmd = 'show -v %s,LdapAuthenticationMethod=1' % USER_MNG_DN
        answer = self.run_command(cmd, identity = 'cliss_emergency', full_answer=True)

        data = self.fill_from_cliss_info(['administrativeState'], answer)
        if len(data['administrativeState']):
            if data['administrativeState'][0] == 'LOCKED':
                self.release_connection(identity = 'cliss_emergency')
                self.release_connection(identity = 'aux_com')
                _DEB('is_AandA_enabled False')
                return False

        cmd = 'show -v %s,LocalAuthorizationMethod=1' % USER_MNG_DN
        answer = self.run_command(cmd, identity = 'cliss_emergency', full_answer=True)

        data = self.fill_from_cliss_info(['administrativeState'], answer)
        if len(data['administrativeState']):
            if data['administrativeState'][0] == 'LOCKED':
                self.release_connection(identity = 'cliss_emergency')
                self.release_connection(identity = 'aux_com')
                _DEB('is_AandA_enabled False')
                return False

        self.release_connection(identity = 'cliss_emergency')
        self.release_connection(identity = 'aux_com')
        _DEB('is_AandA_enabled True')
        return True

    def get_traffic_info(self, traffic_type = 'IMS', info =[], IPv6 = False):
        if len(info) == 0:
            info = ['hss_version', 'dia_tcp', 'dia_sctp','soap','soap_ldap','oam','radius','extdb','udm',
                    'udmHttp2Client','vector_supplier','controller','HSS-MapSriForLcs','ownGTAddress',
                    'radiusClient','HSS-EsmIsActive','udmClient','HSS-CommonAuthenticationVectorSupplier']


        _DEB('Getting traffic info for %s type' % traffic_type)
        traffic_info = {}
        for data in info:
            if data == 'oam':
                traffic_info.update({'oam':self.config['host']})
            elif data == 'controller':
                traffic_info.update({'controller': self.config['host']})
            elif data == 'HSS-MapSriForLcs':
                traffic_info.update({'HSS-MapSriForLcs':False})
            elif data == 'EsmIsActive':
                traffic_info.update({'EsmIsActive':False})
            else:
                traffic_info.update({data:''})


        if 'hss_version' in info:
            cmd = 'vdicos-envdata-get HSS_VERSION'
            answer = self.run_command(cmd)
            if len(answer) and 'error' not in answer[0]:
                traffic_info['hss_version'] = answer[0].split(' ')[0]

        if 'dia_tcp' in info or 'dia_sctp' in info:
            _DEB('Getting traffic info with cliss_hssadministrator session')
            self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator')
            cmd = 'show -v %s' % (DIA_IMS_CLISS_DN if traffic_type == 'IMS' else DIA_EPC_CLISS_DN)
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

            data = self.fill_from_cliss_info(['ipAddressesList', 'sctpAddressesList'], answer)
            traffic_info['dia_tcp'] = None
            if 'ipAddressesList' not in data.keys():
                raise CommandFailure('ipAddressesList not found in %s.' % (DIA_IMS_CLISS_DN if traffic_type == 'IMS' else DIA_EPC_CLISS_DN))
            for address in data['ipAddressesList']:
                ip = ipaddress.ip_address(unicode(address[2:]))
                if isinstance(ip,IPv6Address if IPv6 else IPv4Address):
                    traffic_info['dia_tcp'] = address[2:]
                    break

            traffic_info['dia_sctp'] = None
            if 'sctpAddressesList' not in data.keys():
                raise CommandFailure('sctpAddressesList not found in %s.' % (DIA_IMS_CLISS_DN if traffic_type == 'IMS' else DIA_EPC_CLISS_DN))
            for address in data['sctpAddressesList']:
                ip = ipaddress.ip_address(unicode(address[2:]))
                if isinstance(ip,IPv6Address if IPv6 else IPv4Address):
                    traffic_info['dia_sctp'] = address[2:]
                    break

        if traffic_type == 'IMS' and 'radius' in info:
            _DEB('Getting traffic info with cliss_hssadministrator session to get radius info')
            self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator')
            cmd = 'show -v %s' % RADIUS_CLISS_DN
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

            data = self.fill_from_cliss_info(['rad-IpAddress'], answer)
            if 'rad-IpAddress' not in data.keys():
                raise CommandFailure('rad-IpAddress not found in %s.' % RADIUS_CLISS_DN)
            if len(data['rad-IpAddress']):
                traffic_info['radius'] = data['rad-IpAddress'][0][2:]

        if traffic_type == 'IMS' and 'radiusClient' in info:
            _DEB('Getting traffic info with cliss_hssadministrator session to get radiusClient info')
            self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator')
            cmd = 'show -v %s' % RADIUS_CLISS_DN
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

            data = self.fill_from_cliss_info(['RAD-RadiusClient'], answer)
            if 'RAD-RadiusClient' not in data.keys():
                raise CommandFailure('RAD-RadiusClient not found in %s.' % RADIUS_CLISS_DN)

            if len(data['RAD-RadiusClient']):
                traffic_info['radiusClient'] = ' '.join('%s' % x.split(':')[-1] for x in data['RAD-RadiusClient'])

        if 'ownGTAddress' in info:
            _DEB('Getting traffic info with cliss_hssadministrator session to get ownGTAddress info')
            self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator')
            cmd = 'show -v %s' % MAP_ISMSDA_CLISS_DN
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            if 'element not found' not in answer:
                data = self.fill_from_cliss_info(['mpv-OwnGTAddress'], answer)
                if 'mpv-OwnGTAddress' not in data.keys():
                    raise CommandFailure('mpv-OwnGTAddress not found in %s.' % MAP_ISMSDA_CLISS_DN)
                if len(data['mpv-OwnGTAddress']):
                    traffic_info['ownGTAddress'] = data['mpv-OwnGTAddress'][0].split(':')[-1]

        if 'extdb' in info:
            _DEB('Getting traffic info with cliss_hssadministrator session to get extdb info')
            self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator')
            cmd = 'show -v %s' % EXTDB_CLISS_DN
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

            data = self.fill_from_cliss_info(['hss-ExtDbConfigUrlList'], answer)
            if 'hss-ExtDbConfigUrlList' not in data.keys():
                raise CommandFailure('hss-ExtDbConfigUrlList not found in %s.' % EXTDB_CLISS_DN)

            traffic_info['extdb'] = None
            regex = re.compile(r"\d+:ldaps?://(.+):\d+\$.+")
            for url in data['hss-ExtDbConfigUrlList']:
                res = regex.match(url)
                if res:
                    address = res.group(1)
                    if address.startswith('['):
                        address = address[1:-1]
                    ip = ipaddress.ip_address(unicode(address))
                    if isinstance(ip,IPv6Address if IPv6 else IPv4Address):
                        traffic_info['extdb'] = '%s' % ip
                        break


        if 'vector_supplier' in info:
            _DEB('Getting traffic info with cliss_ericssonhsssupport session to get vector_supplier info')
            self.start_CBACliss(self.config['host'], identity = 'cliss_ericssonhsssupport', user = CLISS_ACCESS['VECTOR_SUPPLIER'])
            cmd = 'show -v %s' % (VECTOR_SUPPLIER_IMS_CLISS_DN if traffic_type == 'IMS' else VECTOR_SUPPLIER_EPC_CLISS_DN)
            answer = self.run_command(cmd, identity = 'cliss_ericssonhsssupport', full_answer=True)

            if traffic_type == 'IMS':
                data = self.fill_from_cliss_info(['hss-AuthenticationVectorSupplier'], answer)
                if 'hss-AuthenticationVectorSupplier' not in data.keys():
                    raise CommandFailure('hss-AuthenticationVectorSupplier not found in %s.' % VECTOR_SUPPLIER_IMS_CLISS_DN)
                if len(data['hss-AuthenticationVectorSupplier']):
                    traffic_info['vector_supplier'] = data['hss-AuthenticationVectorSupplier'][0]
            else:
                data = self.fill_from_cliss_info(['hss-EsmAuthenticationVectorSupplier'], answer)
                if 'hss-EsmAuthenticationVectorSupplier' not in data.keys():
                    raise CommandFailure('hss-EsmAuthenticationVectorSupplier not found in %s.' % VECTOR_SUPPLIER_EPC_CLISS_DN)
                if len(data['hss-EsmAuthenticationVectorSupplier']):
                    traffic_info['vector_supplier'] = data['hss-EsmAuthenticationVectorSupplier'][0]

        if 'HSS-MapSriForLcs' in info:
            _DEB('Getting traffic info with cliss_ericssonhsssupport session to get HSS-MapSriForLcs info')
            self.start_CBACliss(self.config['host'], identity = 'cliss_ericssonhsssupport', user = CLISS_ACCESS['VECTOR_SUPPLIER'])
            cmd = 'show -v %s' % VECTOR_SUPPLIER_IMS_CLISS_DN
            answer = self.run_command(cmd, identity = 'cliss_ericssonhsssupport', full_answer=True)
            data = self.fill_from_cliss_info(['hss-MapSriForLcs'], answer)
            if 'hss-MapSriForLcs' not in data.keys():
                raise CommandFailure('hss-MapSriForLcs not found in %s.' % VECTOR_SUPPLIER_IMS_CLISS_DN)
            if len(data['hss-MapSriForLcs']):
                traffic_info['HSS-MapSriForLcs'] = True if data['hss-MapSriForLcs'][0] == 'true' else False

        if 'HSS-CommonAuthenticationVectorSupplier' in info:
            _DEB('Getting traffic info with cliss_ericssonhsssupport session')
            self.start_CBACliss(self.config['host'], identity = 'cliss_ericssonhsssupport', user = CLISS_ACCESS['VECTOR_SUPPLIER'])
            cmd = 'show -v %s' % ARPF_CLISS_DN
            answer = self.run_command(cmd, identity = 'cliss_ericssonhsssupport', full_answer=True)
            data = self.fill_from_cliss_info(['hss-CommonAuthenticationVectorSupplier'], answer)
            if 'hss-CommonAuthenticationVectorSupplier' in data.keys():
                if len(data['hss-CommonAuthenticationVectorSupplier']):
                    traffic_info['HSS-CommonAuthenticationVectorSupplier'] = data['hss-CommonAuthenticationVectorSupplier'][0]

        if 'HSS-EsmIsActive' in info:
            _DEB('Getting traffic info with cliss_hssadministrator session')
            self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator')
            cmd = 'show -v %s' % ESM_ACTIVE_DN
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            data = self.fill_from_cliss_info(['hss-EsmIsActive'], answer)
            if 'hss-EsmIsActive' not in data.keys():
                raise CommandFailure('hss-EsmIsActive not found in %s.' % ESM_ACTIVE_DN)
            if len(data['hss-EsmIsActive']):
                traffic_info['HSS-EsmIsActive'] = True if data['hss-EsmIsActive'][0] == 'true' else False

        if 'udm' in info:
            _DEB('Getting traffic info with cliss_udm session to get udm info')
            try:
                self.start_CBACliss(self.config['host'], identity = 'cliss_udm', user = CLISS_ACCESS['UDM_SERVER'])
                cmd = 'show -v %s%s' % (UDM_SERVER_CLISS_DN, '_ipv6' if IPv6 else '')
                answer = self.run_command(cmd, identity = 'cliss_udm', full_answer=True)
                traffic_info['udm'] = None
                data = self.fill_from_cliss_info(['ipAddress'], answer)
                if 'ipAddress' in list(data.keys()):
                    if len(data['ipAddress']):
                        ip = ipaddress.ip_address(unicode(data['ipAddress'][0]))
                        if isinstance(ip,IPv6Address if IPv6 else IPv4Address):
                            traffic_info['udm'] = data['ipAddress'][0]
                else:
                    _DEB('ipAddress not found in %s.' % UDM_SERVER_CLISS_DN)
                    _DEB('Looking for UDM Http2 server info')
                    cmd = 'show -v %s%s' % (UDM_HTTP2_SERVER_CLISS_DN, '_ipv6' if IPv6 else '')
                    answer = self.run_command(cmd, identity = 'cliss_udm', full_answer=True)
                    data = self.fill_from_cliss_info(['ipAddress'], answer)
                    if 'ipAddress' in list(data.keys()):
                        if len(data['ipAddress']):
                            ip = ipaddress.ip_address(unicode(data['ipAddress'][0]))
                            if isinstance(ip,IPv6Address if IPv6 else IPv4Address):
                                traffic_info['udm'] = data['ipAddress'][0]
                    else:
                        _DEB('ipAddress not found in %s.' % UDM_HTTP2_SERVER_CLISS_DN)
                        _DEB('UDM: ipAddress data:%s'% data)


            except Exception as e:
                _DEB('TBD: Exception when getting UDM info: %s'% e)

        if 'soap' in info:
            _DEB('Getting traffic info with cliss_SystemAdministrator session to get soap info')
            self.start_CBACliss(self.config['host'], identity = 'cliss_SystemAdministrator', user = CLISS_ACCESS['SOAP_SERVER'])
            cmd = 'show -v %s' % SOAP_SERVER_CLISS_DN
            answer = self.run_command(cmd, identity = 'cliss_SystemAdministrator', full_answer=True)
            traffic_info['soap'] = None

            data = self.fill_from_cliss_info(['EvipVip'], answer)

            if 'EvipVip' not in data.keys():
                raise CommandFailure('EvipVip not found in %s.' % SOAP_SERVER_CLISS_DN)

            for address in data['EvipVip']:
                ip = ipaddress.ip_address(unicode(address))
                if isinstance(ip,IPv6Address if IPv6 else IPv4Address):
                    traffic_info['soap'] = address
                    break


        if 'soap_ldap' in info:
            _DEB('Getting traffic info with cliss_SystemAdministrator session to get soap_ldap info')
            self.start_CBACliss(self.config['host'], identity = 'cliss_SystemAdministrator', user = CLISS_ACCESS['SOAP_SERVER'])
            cmd = 'show -v %s' % SOAP_LDAP_SERVER_CLISS_DN
            answer = self.run_command(cmd, identity = 'cliss_SystemAdministrator', full_answer=True)
            traffic_info['soap_ldap'] = None
            if 'ERROR' not in answer:
                data = self.fill_from_cliss_info(['dest'], answer)
                if 'dest' not in data.keys():
                    raise CommandFailure('dest not found in %s.' % SOAP_LDAP_SERVER_CLISS_DN)
                if len(data['dest']):
                    ip = ipaddress.ip_address(unicode(data['dest'][0]))
                    if isinstance(ip,IPv6Address if IPv6 else IPv4Address):
                        traffic_info['soap_ldap'] = data['dest'][0]

        if 'udmClient' in info:
            _DEB('Getting traffic info with cliss_udm session to get udmClient info')
            try:
                self.start_CBACliss(self.config['host'], identity = 'cliss_udm', user = CLISS_ACCESS['UDM_SERVER'])
                cmd = 'show -v %s%s' % (UDM_SERVER_CLISS_DN, '_ipv6' if IPv6 else '')
                answer = self.run_command(cmd, identity = 'cliss_udm', full_answer=True)
                _DEB('ANSWER: %s'% answer)

                traffic_info['udmClient'] = 'None'
                data = self.fill_from_cliss_info(['uriAddressList'], answer)
                if 'uriAddressList' not in data.keys():
                    raise CommandFailure('uriAddressList not found in %s.' % UDM_SERVER_CLISS_DN)

                regex = re.compile(r"\d+:http://(.+):\d+")
                for url in data['uriAddressList']:
                    res = regex.match(url)
                    if res:
                        address = res.group(1)
                        if address.startswith('['):
                            address = address[1:-1]
                        ip = ipaddress.ip_address(unicode(address))
                        if isinstance(ip,IPv6Address if IPv6 else IPv4Address):
                            if traffic_info['udmClient'] == '':
                                traffic_info['udmClient'] = '%s' % url.split('//')[-1]
                            else:
                                traffic_info['udmClient'] = '%s %s' % (traffic_info['udmClient'], url.split('//')[-1])

            except Exception as e:
                _DEB('TBD: Exception when getting UDM info: %s'% e)

        if 'udmHttp2Client' in info:
            _DEB('Getting traffic info with cliss_udm session to get udmHttp2Client info')
            try:
                self.start_CBACliss(self.config['host'], identity = 'cliss_udm', user = CLISS_ACCESS['UDM_SERVER'])
                cmd = 'show -v %s%s' % (UDM_HTTP2_SERVER_CLISS_DN, '_ipv6' if IPv6 else '')
                answer = self.run_command(cmd, identity = 'cliss_udm', full_answer=True)

                traffic_info['udmHttp2Client'] = ''
                data = self.fill_from_cliss_info(['uriAddressList'], answer)
                if 'uriAddressList' not in list(data.keys()):
                    _WRN('uriAddressList not found for UDM HTTP2 in %s.' % UDM_HTTP2_SERVER_CLISS_DN)
                else:
                    regex = re.compile(r"\d+:http://(.+):\d+")
                    for url in data['uriAddressList']:
                        res = regex.match(url)
                        if res:
                            address = res.group(1)
                            if address.startswith('['):
                                address = address[1:-1]
                            if sys.version_info[0] == 2:
                                ip = ipaddress.ip_address(unicode(address))
                            else:
                                ip = ipaddress.ip_address(str(address))
                            if isinstance(ip,IPv6Address if IPv6 else IPv4Address):
                                if traffic_info['udmHttp2Client'] == '':
                                    traffic_info['udmHttp2Client'] = '%s' % url.split('//')[-1].split('$')[0]
                                else:
                                    traffic_info['udmHttp2Client'] = '%s %s' % (traffic_info['udmHttp2Client'], url.split('//')[-1].split('$')[0])

            except Exception as e:
                _DEB('TBD: Exception when getting UDM info: %s'% e)

        return traffic_info

    @property
    def configured_ExtDb_connections(self):

        self.start_CBACliss(self.config['host'], identity = 'cliss_ericssonhsssupport', user = CLISS_ACCESS['EXTDB_INSTALL'])
        cmd = 'show -v %s' % EXTDB_INSTALL_CLISS_DN
        answer = self.run_command(cmd, identity = 'cliss_ericssonhsssupport', full_answer=True)
        _DEB('configured_ExtDb_connections answer %s' % answer)
        self.close_connection(identity = 'cliss_ericssonhsssupport')

        data = self.fill_from_cliss_info(['hss-ExtDbMaxConnections'], answer)
        try:
            if len(data['hss-ExtDbMaxConnections']):
                return data['hss-ExtDbMaxConnections'][0]
        except Exception as e:
            return -1

    @property
    def configured_ExtDb_urls(self):

        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['EXTDB'])
        cmd = 'show -v %s' % EXTDB_CLISS_DN
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        _DEB('configured_ExtDb_urls answer %s' % answer)
        self.close_connection(identity = 'cliss_hssadministrator')

        data = self.fill_from_cliss_info(['hss-ExtDbConfigUrlList'], answer)
        _DEB('configured_ExtDb_urls data %s' % data)
        url_list = []
        try:
            num_urls = len(data['hss-ExtDbConfigUrlList'])
            idx = 0
            while idx < num_urls:
                url = data['hss-ExtDbConfigUrlList'][idx].split('/')[-1].split('$')[0]
                url_list.append(url)
                idx +=1
        except Exception as e:
            return url_list
        return url_list


    @property
    def configured_Http_connections(self):

        self.start_CBACliss(self.config['host'], identity = 'cliss_udm', user = CLISS_ACCESS['UDM_SERVER'])
        cmd = 'show -v %s' % UDM_SERVER_CLISS_DN
        answer = self.run_command(cmd, identity = 'cliss_udm', full_answer=True)
        self.close_connection(identity = 'cliss_udm')
        if 'not found' in answer or 'Invalid value' in answer:
            _DEB('Http_connections not defined:\n%s' % answer)
            return -2

        data = self.fill_from_cliss_info(['maxOutgoingConnections'], answer)
        try:
            if len(data['maxOutgoingConnections']):
                return data['maxOutgoingConnections'][0]
        except Exception as e:
            return -1

    @property
    def configured_Http_uris(self):

        self.start_CBACliss(self.config['host'], identity = 'cliss_udm', user = CLISS_ACCESS['UDM_SERVER'])
        cmd = 'show %s' % UDM_SERVER_CLISS_DN
        answer = self.run_command(cmd, identity = 'cliss_udm', full_answer=True)
        _DEB('configured_Http_uris answer %s' % answer)
        self.close_connection(identity = 'cliss_udm')

        uri_list = []
        if 'ERROR' in answer:
            return uri_list

        data = self.fill_from_cliss_info(['uriAddressList'], answer)
        try:
            num_uris= len(data['uriAddressList'])
            idx = 0
            while idx < num_uris:
                uri = data['uriAddressList'][idx].split('/')[-1]
                uri_list.append(uri)
                idx +=1
        except Exception as e:
            return uri_list
        return uri_list

    @property
    def configured_Http2_connections(self):

        self.start_CBACliss(self.config['host'], identity = 'cliss_udm', user = CLISS_ACCESS['UDM_SERVER'])
        cmd = 'show -v %s' % UDM_HTTP2_SERVER_CLISS_DN
        answer = self.run_command(cmd, identity = 'cliss_udm', full_answer=True)
        self.close_connection(identity = 'cliss_udm')
        if 'not found' in answer:
            _DEB('Http_connections not defined:\n%s' % answer)
            return -2

        data = self.fill_from_cliss_info(['maxOutgoingConnections'], answer)
        try:
            if len(data['maxOutgoingConnections']):
                return data['maxOutgoingConnections'][0]
        except Exception as e:
            return -1

    @property
    def configured_Http2_uris(self):

        self.start_CBACliss(self.config['host'], identity = 'cliss_udm', user = CLISS_ACCESS['UDM_SERVER'])
        cmd = 'show %s' % UDM_HTTP2_SERVER_CLISS_DN
        answer = self.run_command(cmd, identity = 'cliss_udm', full_answer=True)
        _DEB('configured_Http2_uris answer %s' % answer)
        self.close_connection(identity = 'cliss_udm')

        uri_list = []
        if 'ERROR' in answer:
            return uri_list

        data = self.fill_from_cliss_info(['uriAddressList'], answer)
        try:
            num_uris= len(data['uriAddressList'])
            idx = 0
            while idx < num_uris:
                uri = data['uriAddressList'][idx].split('/')[-1].split('$')[0]
                uri_list.append(uri)
                idx +=1
        except Exception as e:
            return uri_list
        return uri_list

    def run_cliss_command(self, cmd, user, configure):
        self.start_CBACliss(self.config['host'], identity = user, user=user)
        if configure:
            cmd = 'configure' % cmd
            answer = self.run_command(cmd, identity = user, full_answer=True)
            cmd = '%s' % cmd
            answer = self.run_command(cmd, identity = user, full_answer=True)
            cmd = 'commit' % cmd
            answer = self.run_command(cmd, identity = user, full_answer=True)
            if 'ERROR' in answer:
                raise CommandFailure(answer.replace('\r\n',';'))
        else:
            cmd = '%s' % cmd
            answer = self.run_command(cmd, identity = user, full_answer=True)
        self.close_connection(identity = user)
        return answer


    def update_licenses(self,licenses):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_LICENSE'])
        cmd = 'show -v %s' % LICENSE_DN
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        data = self.fill_from_cliss_info(['fingerprintUpdateable','fingerprint'], answer)

        try:
            if not len(data['fingerprintUpdateable']):
                raise CommandFailure('fingerprintUpdateable not found.')
            if data['fingerprintUpdateable'][0] == 'false':
                if not len(data['fingerprint']):
                    raise CommandFailure('fingerprint not found.')
                if data['fingerprint'][0] != '01-23-45-67-89-ab-20150101':
                    raise CommandFailure('fingerprint != 01-23-45-67-89-ab-20150101')
            else:
                cmd = 'configure'
                answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
                cmd = '%s,fingerprint="01-23-45-67-89-ab-20150101"' % LICENSE_DN
                answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
                cmd = 'commit'
                answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
                if 'ERROR' in answer:
                    raise CommandFailure(answer.replace('\r\n',';'))

                cmd = 'show -v %s' % LICENSE_DN
                answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
                data = self.fill_from_cliss_info(['fingerprint'], answer)
                if not len(data['fingerprint']):
                    raise CommandFailure('fingerprint not found.')
                if data['fingerprint'][0] != '01-23-45-67-89-ab-20150101':
                    raise CommandFailure('fingerprint != 01-23-45-67-89-ab-20150101')

        except Exception as e:
            raise CommandFailure(str(e))

        cmd = '%s,KeyFileManagement=1' % LICENSE_DN
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'installKeyFile file:///cluster/%s ""' % licenses
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

        timeout = float(300)
        started = time.time()
        while True:
            now = time.time()
            time.sleep(float(5))

            cmd = 'show -v'
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            data = self.fill_from_cliss_info(['state', 'result'], answer)
            _DEB('State %s   result %s' % (data['state'], data['result']))

            if data['state'] == ['FINISHED']:
                break

            timeout -= time.time() - now

            if timeout < float(0):
                raise ExecutionTimeout('Timeout waiting for installKeyFile')

        if data['result'] != ['SUCCESS']:
            raise CommandFailure('installKeyFile failed')

        self.grant_licenses()

    def unlock_traffic_modules(self):
        # Checking IMS Module Administrative Status
        modules_unlocked = 0
        self.start_CBACliss(self.config['host'], identity = 'cliss_modules', user = CLISS_ACCESS['DEFAULT'])
        cmd = '%s' % MODULE_IMS_CLISS_DN
        self.run_command(cmd, identity = 'cliss_modules', full_answer=True)
        cmd = 'show hss-AdministrativeState'
        answer = self.run_command(cmd, identity = 'cliss_modules', full_answer=True)
        if 'Locked' in answer:
            _DEB('IMS Module is "Locked". Setting Administrative State to "Unlocked"')
            cmd = 'configure'
            answer = self.run_command(cmd, identity = 'cliss_modules', full_answer=True)
            cmd = 'hss-AdministrativeState="Unlocked"'
            answer = self.run_command(cmd, identity = 'cliss_modules', full_answer=True)
            cmd = 'commit'
            answer = self.run_command(cmd, identity = 'cliss_modules', full_answer=True)
            if 'ERROR' in answer:
                raise CommandFailure(answer.replace('\r\n',';'))
            modules_unlocked +=1
        else:
            _DEB('IMS Module is not "Locked". Nothing to do.')

        # Checking ESM Module Administrative Status
        self.start_CBACliss(self.config['host'], identity = 'cliss_modules', user = CLISS_ACCESS['DEFAULT'])
        cmd = '%s' % MODULE_ESM_CLISS_DN
        self.run_command(cmd, identity = 'cliss_modules', full_answer=True)
        cmd = 'show hss-EsmAdministrativeState'
        answer = self.run_command(cmd, identity = 'cliss_modules', full_answer=True)
        if 'Locked' in answer:
            _DEB('ESM Module is "Locked". Setting Administrative State to "Unlocked"')
            cmd = 'configure'
            answer = self.run_command(cmd, identity = 'cliss_modules', full_answer=True)
            cmd = 'hss-EsmAdministrativeState="Unlocked"'
            answer = self.run_command(cmd, identity = 'cliss_modules', full_answer=True)
            cmd = 'commit'
            answer = self.run_command(cmd, identity = 'cliss_modules', full_answer=True)
            if 'ERROR' in answer:
                raise CommandFailure(answer.replace('\r\n',';'))
            modules_unlocked +=1
        else:
            _DEB('ESM Module is not "Locked". Nothing to do.')
        return modules_unlocked


    def grant_licenses(self):

        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_LICENSE'])
        cmd = '%s' % LICENSE_DN
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

        cmd = 'publishLicenseInventory'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        time.sleep(10)
        no_granted_licenses = self.find_licenses(no_granted=True)
        if no_granted_licenses:
            raise CommandFailure('There are no granted licenses: %s' % ' '.join(no_granted_licenses))

    def find_licenses(self,no_granted):

        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_LICENSE'])
        cmd = 'show -v %s' % LICENSE_DN
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))
        data = self.fill_from_cliss_info(['FeatureKey'], answer)

        licenses=[]
        for key in data['FeatureKey']:
            cmd = 'show -v %s,FeatureKey=%s' % (LICENSE_DN, key)
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            if 'ERROR' in answer:
                raise CommandFailure(answer.replace('\r\n',';'))
            info = self.fill_from_cliss_info(['granted','keyId'], answer)

            if no_granted:
                if info['granted'][0] != 'true':
                    licenses += info['keyId']
            else:
                licenses += ['%s\t%s' % (info['keyId'][0], 'Granted' if info['granted'][0] == 'true' else 'No granted')]

        return sorted_nicely(licenses)

    def check_all_licenses_granted(self):

        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_LICENSE'])
        cmd = 'show -v %s' % LICENSE_DN
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))
        data = self.fill_from_cliss_info(['FeatureKey'], answer)

        if  not data['FeatureKey']:
            raise CommandFailure('FeatureKeys not found')

        for key in data['FeatureKey']:
            cmd = 'show -v %s,FeatureKey=%s' % (LICENSE_DN, key)
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            if 'ERROR' in answer:
                time.sleep(1.0)
                cmd = 'show -v %s,FeatureKey=%s' % (LICENSE_DN, key)
                answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
                if 'ERROR' in answer:
                    raise CommandFailure(answer.replace('\r\n',';'))
            info = self.fill_from_cliss_info(['granted','keyId'], answer)

            if info['granted'][0] != 'true':
                raise CommandFailure('FeatureKey %s is not granted' % info['keyId'])


    def find_capacity_licenses(self):

        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_LICENSE'])
        cmd = 'show -v %s' % LICENSE_DN
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))
        data = self.fill_from_cliss_info(['CapacityKey'], answer)

        licenses=[]
        for key in data['CapacityKey']:
            cmd = 'show -v %s,CapacityKey=%s' % (LICENSE_DN, key)
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            if 'ERROR' in answer:
                raise CommandFailure(answer.replace('\r\n',';'))
            info = self.fill_from_cliss_info(['keyId'], answer)

            licenses += ['%s' % info['keyId'][0]]

        return sorted_nicely(licenses)

    def start_health_check_handling(self, next_level = ''):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator')
        cmd = HEALTH_CHECK_DN + next_level
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

    def run_health_check_cmd(self,cmd, next_level = ''):
        self.start_health_check_handling(next_level)
        return self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)


    def start_backup_handling(self, next_level = ''):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator')
        cmd = BACKUP_CLISS_DN + next_level
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

    def run_backup_cmd(self,cmd, next_level = ''):
        self.start_backup_handling(next_level)
        return self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

    @property
    def active_backup(self):
        cmd = 'ls -ltr /cluster/brf/backup'
        answer = self.run_command(cmd)
        return clear_ansi(answer[-1].split()[-1])

    @property
    def latest_backup(self):
        cmd = 'ls -ltr /cluster/brf/box/data'
        answer = self.run_command(cmd)
        for line in answer:
            if 'software.latest' in line:
                return line.split('/')[3]

    @property
    def last_restored_backup(self):
        cmd = 'ls -ltr /cluster/brf/box/data'
        answer = self.run_command(cmd)
        for line in answer:
            if 'software.restored' in line:
                return line.split('/')[3]

    def backup_info(self, requested_info = [], next_level = ''):
        self.start_backup_handling(next_level)
        cmd = 'show -v'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        return self.fill_from_cliss_info(requested_info, answer)

    def start_alarm_handling(self, next_level = ''):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator')
        cmd = ALARM_CLISS_DN + next_level
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

    def alarm_info(self, requested_info = [], next_level = ''):
        self.start_alarm_handling(next_level)
        cmd = 'show -v'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        return self.fill_from_cliss_info(requested_info, answer)


    def get_alarm_info(self, alarm):
        level = ',FmAlarm=%s' % alarm
        info_alarm = self.alarm_info(['activeSeverity', 'eventType',
                                        'lastEventTime','source',
                                        'specificProblem', 'additionalText',
                                        'originalAdditionalText']
                                        ,level)
        return info_alarm

    def print_alarm_info(self,alarm,info_alarm):
        try:
            return 'FmAlarm:%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s' % (alarm,info_alarm['activeSeverity'][0],info_alarm['eventType'][0],
                                                                info_alarm['lastEventTime'][0],info_alarm['source'][0],
                                                                info_alarm['specificProblem'][0],info_alarm['additionalText'][0],
                                                                info_alarm['originalAdditionalText'][0])
        except (IndexError,KeyError) as e:
            raise e

    def start_nbi_alarm_handling(self, next_level = ''):
        self.start_CBANBICliss(self.config['host'], identity = 'nbi_cliss')
        cmd = NBI_ALARM_CLISS_DN + next_level
        self.run_command(cmd, identity = 'nbi_cliss', full_answer=True)

    def nbi_alarm_info(self, requested_info = [], next_level = ''):
        self.start_nbi_alarm_handling(next_level)
        cmd = 'show -v'
        answer = self.run_command(cmd, identity = 'nbi_cliss', full_answer=True)
        if next_level == '':
            if 'sumCritical' in answer:
                _DEB('Alarms info gotten correctly')
                return self.fill_from_cliss_info(requested_info, answer)
            _DEB('Error when getting Alarms info. Trying again after 10 secs ')
        else:
            return self.fill_from_cliss_info(requested_info, answer)
        time.sleep(float(10))
        answer = self.run_command(cmd, identity = 'nbi_cliss', full_answer=True)
        if 'sumCritical' in answer:
            return self.fill_from_cliss_info(requested_info, answer)
        err_message = 'Error when getting alarms from NBI'
        raise CommandFailure(err_message)

    def get_nbi_tenant(self, nbi_node):
        subnets = self.subnets()
        self.start_CBANBICliss(nbi_node, identity = 'nbi_cliss')
        cmd = 'show -v %s' % NBI_TENANT_CLISS_DN
        answer = self.run_command(cmd, identity = 'nbi_cliss', full_answer=True)
        Tenants = self.fill_from_cliss_info(['Tenant'], answer)

        for tenant in Tenants['Tenant']:
            cmd = 'show -r %s,Tenant=%s' % (NBI_TENANT_CLISS_DN,self.raw_string(tenant))
            answer = self.run_command(cmd, identity = 'nbi_cliss', full_answer=True)
            SubnetAddrs = self.fill_from_cliss_info(['subnetAddr'], answer)

            for subnetAddr in SubnetAddrs['subnetAddr']:
                if subnetAddr in subnets:
                    return tenant

    def get_nbi_proc_cliss_dn(self, nbi_node, processor):
        tenant = self.get_nbi_tenant(nbi_node)
        _DEB('TENANT=%s for Processor %s' % (tenant,processor))
        self.start_CBANBICliss(nbi_node, identity = 'nbi_cliss')
        cmd = 'show -v %s' % NBI_PROC_CLISS_DN
        answer = self.run_command(cmd, identity = 'nbi_cliss', full_answer=True)
        Shelfs = self.fill_from_cliss_info(['Shelf'], answer)
        for shelf in Shelfs['Shelf']:
            cmd = 'show -v %s,Shelf=%s' % (NBI_PROC_CLISS_DN,shelf)
            answer = self.run_command(cmd, identity = 'nbi_cliss', full_answer=True)
            Slots = self.fill_from_cliss_info(['Slot'], answer)
            for slot in Slots['Slot']:
                cmd = 'show -v %s,Shelf=%s,Slot=%s,Blade=1' % (NBI_PROC_CLISS_DN,shelf,slot)
                answer = self.run_command(cmd, identity = 'nbi_cliss', full_answer=True)
                data = self.fill_from_cliss_info(['userLabel','tenant'], answer)
                if tenant in data['tenant'] and processor in data['userLabel'][0]:
                    _DEB('Processor %s found in Shelf=%s and Slot=%s' % (processor,shelf,slot))
                    return '%s,Shelf=%s,Slot=%s,Blade=1' % (NBI_PROC_CLISS_DN,shelf,slot)

        err_message = 'Processor %s not found in NBI configuration' % processor
        raise CommandFailure(err_message)


    def nbi_lock_processor(self, processor,nbi_node,timeout=60):
        max_time = float(timeout)
        self.start_CBANBICliss(nbi_node, identity = 'nbi_cliss')
        started = time.time()

        cmd = '%s' % self.get_nbi_proc_cliss_dn(nbi_node,processor)
        self.run_command(cmd, identity = 'nbi_cliss', full_answer=True)
        cmd = 'configure'
        self.run_command(cmd, identity = 'nbi_cliss', full_answer=True)
        cmd = 'administrativeState=LOCKED'
        self.run_command(cmd, identity = 'nbi_cliss', full_answer=True)
        cmd = 'commit'
        answer = self.run_command(cmd, identity = 'nbi_cliss', full_answer=True)
        if 'ERROR' in answer:
            _ERR('NBI_LOCK:     Error when locking Processor %s' % processor)
            _ERR('NBI_LOCK:     ANSWER:\n%s' % answer)

            raise CommandFailure(answer.replace('\r\n',';'))
        _DEB('NBI_LOCK:     Processor %s set as LOCKED' % processor)

        if 'SC' in processor:
            self.close_connection()
            time.sleep(float(10))

        max_time -= time.time() - started
        while True:
            now = time.time()
            time.sleep(float(2))
            if self.processor_state(processor) == 'DISABLED':
                _DEB('NBI_LOCK: Processor %s is LOCKED' % processor)
                return str(time.time()-started)

            max_time -= time.time() - now
            if max_time < 0:
                raise RuntimeError('Timeout (%s sec) waiting for locking processor %s' % (timeout, processor))


    def nbi_unlock_processor(self, processor,nbi_node, timeout=300):
        max_time = float(timeout)
        self.start_CBANBICliss(nbi_node, identity = 'nbi_cliss')
        started = time.time()

        cmd = '%s' % self.get_nbi_proc_cliss_dn(nbi_node,processor)
        self.run_command(cmd, identity = 'nbi_cliss', full_answer=True)
        cmd = 'configure'
        self.run_command(cmd, identity = 'nbi_cliss', full_answer=True)
        cmd = 'administrativeState=UNLOCKED'
        self.run_command(cmd, identity = 'nbi_cliss', full_answer=True)
        cmd = 'commit'
        answer = self.run_command(cmd, identity = 'nbi_cliss', full_answer=True)
        if 'ERROR' in answer:
            _ERR('NBI_UNLOCK:     Error when unlocking Processor %s' % processor)
            _ERR('NBI_UNLOCK:     ANSWER:\n%s' % answer)
            raise CommandFailure(answer.replace('\r\n',';'))

        _DEB('NBI_LOCK:     Processor %s set as UNLOCKED' % processor)
        max_time -= time.time() - started
        while True:
            now = time.time()
            time.sleep(float(2))
            if self.processor_state(processor) == 'UNLOCKED':
                _DEB('NBI_UNLOCK:    Processor %s is UNLOCKED' % processor)
                return str(time.time()-started)

            max_time -= time.time() - now
            if max_time < 0:
                raise RuntimeError('Timeout (%s sec) waiting for unlocking processor %s' % (timeout, processor))


    def lock_processor(self, processor,timeout=90):
        started = time.time()
        cmd = 'cmw-node-lock %s' % processor
        answer = self.run_command(cmd, timeout=timeout)
        return str(time.time()-started)

    def unlock_processor(self, processor,timeout=90):
        started = time.time()
        cmd = 'cmw-node-unlock %s' % processor
        answer = self.run_command(cmd, timeout=timeout)
        return str(time.time()-started)

    def get_FEE_eVIP(self, processor,ip_list=False):
        self.extend_connection(processor, processor)
        cmd = 'ip netns list | grep FEE | sort'
        answer = self.run_command(cmd, identity = processor)
        data=''
        for fee in answer:
            data += '%s\n' % fee
            if ip_list:
                eth = 'eth3'
                if 'raddia' in fee:
                    eth = 'eth4'
                elif 'sig' in fee:
                    eth = 'eth5'
                cmd = 'ip netns exec %s ip addr |grep %s' % (fee, eth)
                data += '  %s' % self.run_command(cmd, identity = processor, full_answer=True)

        return data


    def disable_itco_watchdog(self, processor,timeout=10):
        self.extend_connection(processor, processor)
        cmd = 'systemctl stop lde-watchdogd.service'
        self.run_command(cmd, timeout=timeout)
        cmd = 'echo "V" >/dev/watchdog'
        self.run_command(cmd, timeout=timeout)

    def status_itco_watchdog_disabled(self, processor,timeout=10):
        self.extend_connection(processor, processor)
        cmd = 'systemctl status lde-watchdogd.service | grep "Active:"'
        answer = self.run_command(cmd, timeout=timeout)
        if 'inactive' in answer[0]:
            return True
        return False


    @property
    def is_virtual(self):
        cmd = 'dmesg | grep Hypervisor'
        answer = self.run_command(cmd,full_answer=True)
        return len(answer) > 0

    def start_healthcheck(self):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator')
        cmd = HEALTH_CHECK_DN
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'configure'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

        cmd = 'no HcJob=Full'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

        cmd = 'commit'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))

        if self.is_virtual:
            cmd = 'configure'
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            cmd = 'HcRule=HSS_201,administrativeState=LOCKED'
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            cmd = 'HcRule=HSS_107,administrativeState=LOCKED'
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            cmd = 'commit'
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            if 'ERROR' in answer:
                raise CommandFailure(answer.replace('\r\n',';'))

        cmd = 'configure'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

        cmd = 'HcJob=Full'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

        cmd = 'rulesCategories=TROUBLESHOOT'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

        cmd = 'rulesCategories=SHORT'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

        cmd = 'commit'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))

        cmd = 'execute'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)


    def healthcheck_info(self, requested_info = []):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator')
        cmd = HEALTH_CHECK_DN + ',HcJob=Full'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'show -v'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        return self.fill_from_cliss_info(requested_info, answer)

    def healthcheck_list_hcjobs(self, requested_info = []):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator')
        cmd = HEALTH_CHECK_DN
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'show'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        return self.fill_from_cliss_info(requested_info, answer)


    def fill_from_cliss_info(self, to_fill,info=''):
        filled = {}
        if 'ERROR:' not in info:
            data = self.parse_cliss_info(info)
            if len(data):
                for key in to_fill:
                    try:
                        filled.update({key:data[key]})
                    except Exception:
                        filled.update({key: ''})

        return filled

    def parse_cliss_info(self, info):
        data = {}
        for line in info.split('\n'):
            if identation (line) == 0:
                continue
            line = line.replace(' <read-only>','')
            line = line.replace(' <default>','')
            line = line.replace(' <deprecated>','')
            line = line.replace('\r','')

            line = line.lstrip()
            if line.count('=') >= 1 and not line.startswith('"'):
                first_equal_pos = line.index('=')
                key = line[:first_equal_pos]
                value = remove_quottes(line[first_equal_pos + 1:])
                try:
                    data[key].append(value)
                except KeyError:
                    data[key] = [value]

            elif line.startswith('"'):
                value = remove_quottes(line)
                try:
                    data[key].append(value)
                except KeyError:
                    data[key] = [value]

            else:
                key = line

        return data

    def raw_string(self,s):
        if isinstance(s, str):
            s = s.encode('string-escape')
        elif isinstance(s, unicode):
            s = s.encode('unicode-escape')
        return s


    def get_dia_container_peer_nodes(self, stackid, str_filter=None, disconnect=True):
        if stackid == 'ISMSDA':
            cliss_dn = DIA_PEER_ISMSDA_CLISS_DN
        elif stackid == 'ESM':
            cliss_dn = DIA_PEER_ESM_CLISS_DN
        elif stackid == 'SM':
            cliss_dn = DIA_PEER_SM_CLISS_DN
        else:
            raise ValueError('Container value not expected')

        self.start_CBACliss(self.config['host'], 'cliss_hssadministrator')

        cmd = 'show -v %s %s' % (cliss_dn, ('|filter %s' % str_filter if str_filter else '' ))
        answer = self.run_command(cmd, 'cliss_hssadministrator', full_answer=True)
        neighbourNodes = self.fill_from_cliss_info(['DIA-CFG-NeighbourNode'], answer)

        neighbourNodes = neighbourNodes.get('DIA-CFG-NeighbourNode',[])

        if disconnect:
            self.close_connection('cliss_hssadministrator')
        return neighbourNodes


    def get_dia_container_peer_node_info(self, stackid, peer_node, info =[], disconnect=True, IPv6 = False):
        if stackid == 'ISMSDA':
            cliss_dn = DIA_PEER_ISMSDA_CLISS_DN
        elif stackid == 'ESM':
            cliss_dn = DIA_PEER_ESM_CLISS_DN
        elif stackid == 'SM':
            cliss_dn = DIA_PEER_SM_CLISS_DN
        else:
            raise ValueError('Container value not expected')

        if len(info) == 0:
            info = ['connIds','diaVendorId','distributionScheme','dscp','dscpReference',
                    'enabled','firmwareRevision','initiateConnection','ipAddressesList',
                    'isDynamic','isIPv6Supported','nodeId','portNr','productName',
                    'realm','sctpAddressesList','sctpHandlerLogLevel','sctpWouldBlockBufferSize',
                    'supportedAcctAppIds','supportedAuthAppIds','supportedVendorsIds','supportedVendorSpecificApps',
                    'tcpCongestionCeaseLevel','tcpCongestionRaiseLevel','tcpReceiveBufferSize','tcpSendBufferSize',
                    'tcpSocketReceiveBufferSize','tcpSocketSendBufferSize','traceSctpHandler',
                    'transportLayerType','DIA-CFG-Conn']

        peer_node_info = {}

        self.start_CBACliss(self.config['host'], 'cliss_hssadministrator')

        cmd = 'show -v %s,DIA-CFG-NeighbourNode=%s' % (cliss_dn, peer_node)
        answer = self.run_command(cmd, 'cliss_hssadministrator', full_answer=True)
        peer_node_data = self.fill_from_cliss_info(info, answer)
        for param in info:
            peer_node_info[param] = peer_node_data.get(param,[])

        if 'ipAddressesList' in info:
            if 'empty' in peer_node_info['ipAddressesList'][0]:
                peer_node_info['ipAddressesList'] = None
            else:
                for address in peer_node_info['ipAddressesList']:
                    ip = ipaddress.ip_address(unicode(address[2:]))
                    if isinstance(ip,IPv6Address if IPv6 else IPv4Address):
                        peer_node_info['ipAddressesList'] = address[2:]
                        break

        if 'sctpAddressesList' in info:
            if 'empty' in peer_node_info['sctpAddressesList'][0]:
                peer_node_info['sctpAddressesList'] = None
            else:
                for address in peer_node_info['sctpAddressesList']:
                    ip = ipaddress.ip_address(unicode(address[2:]))
                    if isinstance(ip,IPv6Address if IPv6 else IPv4Address):
                        peer_node_info['sctpAddressesList'] = address[2:]
                        break

        if disconnect:
            self.close_connection('cliss_hssadministrator')
        return peer_node_info


    def get_dia_container_peer_node_conns(self, stackid, peer_node, disconnect=True):
        if stackid == 'ISMSDA':
            cliss_dn = DIA_PEER_ISMSDA_CLISS_DN
        elif stackid == 'ESM':
            cliss_dn = DIA_PEER_ESM_CLISS_DN
        elif stackid == 'SM':
            cliss_dn = DIA_PEER_SM_CLISS_DN
        else:
            raise ValueError('Container value not expected')

        self.start_CBACliss(self.config['host'], 'cliss_hssadministrator')

        cmd = 'show -v %s,DIA-CFG-NeighbourNode=%s' % (cliss_dn, peer_node)
        answer = self.run_command(cmd, 'cliss_hssadministrator', full_answer=True)
        neighbourNodeConns = self.fill_from_cliss_info(['DIA-CFG-Conn'], answer)

        neighbourNodeConns = neighbourNodeConns.get('DIA-CFG-Conn',[])

        if disconnect:
            self.close_connection('cliss_hssadministrator')
        return neighbourNodeConns


    def get_dia_container_peer_node_conn_info(self, stackid, peer_node, connId, info =[], disconnect=True, IPv6 = False):
        if stackid == 'ISMSDA':
            cliss_dn = DIA_PEER_ISMSDA_CLISS_DN
        elif stackid == 'ESM':
            cliss_dn = DIA_PEER_ESM_CLISS_DN
        elif stackid == 'SM':
            cliss_dn = DIA_PEER_SM_CLISS_DN
        else:
            raise ValueError('Container value not expected')

        if len(info) == 0:
            info = ['blockReason','connectedAddress','connId','dscp','dscpReference',
                    'enabled','ipAddressesList','linkStatus','portNr','priority',
                    'processorName','sctpAddressesList','sctpHandlerLogLevel',
                    'ss7CpUserId', 'traceSctpHandler','transportLayerType']

        conn_info = {}

        self.start_CBACliss(self.config['host'], 'cliss_hssadministrator')
        cmd = 'show -v %s,DIA-CFG-NeighbourNode=%s,DIA-CFG-Conn=%s' % (cliss_dn, peer_node,connId) 
        answer = self.run_command(cmd, 'cliss_hssadministrator', full_answer=True)
        conn_info = self.fill_from_cliss_info(info, answer)

        if 'ipAddressesList' in info:
            if 'empty' in peer_node_info['ipAddressesList'][0]:
                peer_node_info['ipAddressesList'] = None
            else:
                for address in conn_info['ipAddressesList']:
                    ip = ipaddress.ip_address(unicode(address[2:]))
                    if isinstance(ip,IPv6Address if IPv6 else IPv4Address):
                        conn_info['ipAddressesList'] = address[2:]
                        break

        if 'sctpAddressesList' in info:
            if 'empty' in peer_node_info['ipAddressesList'][0]:
                peer_node_info['ipAddressesList'] = None
            else:
                for address in conn_info['sctpAddressesList']:
                    ip = ipaddress.ip_address(unicode(address[2:]))
                    if isinstance(ip,IPv6Address if IPv6 else IPv4Address):
                        conn_info['sctpAddressesList'] = address[2:]
                        break

        if disconnect:
            self.close_connection('cliss_hssadministrator')
        return conn_info


    def remove_dia_peer_node(self, stackid, dia_peer_node, disconnect=True):

        if stackid == 'ISMSDA':
            cliss_dn = DIA_PEER_ISMSDA_CLISS_DN
        elif stackid == 'ESM':
            cliss_dn = DIA_PEER_ESM_CLISS_DN
        elif stackid == 'SM':
            cliss_dn = DIA_PEER_SM_CLISS_DN
        else:
            raise ValueError('Container value not expected')

        self.start_CBACliss(self.config['host'], 'cliss_hssadministrator')

        cmd = '%s,DIA-CFG-NeighbourNode=%s' % (cliss_dn, dia_peer_node)
        answer = self.run_command(cmd, 'cliss_hssadministrator', full_answer=True)
        cmd = 'configure'
        answer = self.run_command(cmd, 'cliss_hssadministrator', full_answer=True)
        cmd = 'enabled=false'
        answer = self.run_command(cmd, 'cliss_hssadministrator', full_answer=True)
        cmd = 'commit'
        answer = self.run_command(cmd, 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))

        cmd = '%s' % cliss_dn
        answer = self.run_command(cmd, 'cliss_hssadministrator', full_answer=True)
        cmd = 'configure'
        answer = self.run_command(cmd, 'cliss_hssadministrator', full_answer=True)
        cmd = 'no DIA-CFG-NeighbourNode=%s' % dia_peer_node
        answer = self.run_command(cmd, 'cliss_hssadministrator', full_answer=True)
        cmd = 'commit'
        answer = self.run_command(cmd, 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))

        if disconnect:
            self.close_connection('cliss_hssadministrator')


    def get_map_info(self, mpv):
        data={}
        if mpv == 'ISM-SDA':
            cliss_dn = MAP_ISMSDA_CLISS_DN
        elif mpv == 'ESM':
            cliss_dn = MAP_ESM_CLISS_DN
        else:
            return data

        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator')

        cmd = 'show -v %s' % cliss_dn 
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        MPV_Operations = self.fill_from_cliss_info(['MPV-Operation'], answer)
        OwnGTAddress = self.fill_from_cliss_info(['mpv-OwnGTAddress'], answer)
        if not OwnGTAddress:
            return data
        if len(OwnGTAddress['mpv-OwnGTAddress']):
            data.update({'mpv-OwnGTAddress':OwnGTAddress['mpv-OwnGTAddress'][0],'MPV_Operations':[]})
        else:
            return data

        try:
            MPV_Operations = MPV_Operations['MPV-Operation']
        except KeyError:
            self.close_connection(identity = 'cliss_hssadministrator')
            return data

        for MPV_Operation in MPV_Operations:
            cmd = 'show -v %s,MPV-Operation=%s' % (cliss_dn,MPV_Operation)
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            mpv_data = self.fill_from_cliss_info(['mpv-MapTimeGap','mpv-MaxMap','mpv-Timer'], answer)
            data['MPV_Operations'].append({'MPV-Operation':MPV_Operation,
                                            'mpv-MapTimeGap':mpv_data['mpv-MapTimeGap'][0],
                                            'mpv-MaxMap':mpv_data['mpv-MaxMap'][0],
                                            'mpv-Timer':mpv_data['mpv-Timer'][0],})

        self.close_connection(identity = 'cliss_hssadministrator')
        return data

    def change_OwnGTAddress(self,mpv,OwnGTAddress):
        if mpv == 'ISM-SDA':
            cliss_dn = MAP_ISMSDA_CLISS_DN
        elif mpv == 'ESM':
            cliss_dn = MAP_ESM_CLISS_DN
        else:
            return False

        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator')

        cmd = cliss_dn
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

        cmd = 'configure'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

        cmd = 'mpv-OwnGTAddress=%s' % OwnGTAddress
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

        cmd = 'commit'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))

        self.close_connection(identity = 'cliss_hssadministrator')
        return True


    def remove_ntp_server_cliss(self,id_ntp_server):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_NTP'])

        cmd = '%s,NtpServer=%s' % (NTP_SERVER_DN, id_ntp_server)
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

        ntp_server = "NtpServer=%s" % id_ntp_server
        try:
            cmd = '%s' % NTP_SERVER_DN
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            cmd = 'configure'
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            cmd = 'no %s' % ntp_server
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            cmd = 'commit'
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            if 'ERROR' in answer:
                raise CommandFailure(answer.replace('\r\n',';'))

        except Exception as e:
            raise CommandFailure(str(e))


    def add_ntp_server_cliss(self,ntp_server_ip,id_ntp_server):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_NTP'])

        try:
            cmd = '%s' % NTP_SERVER_DN
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            # Adding new NTP Server
            cmd = 'configure'
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            ntp_server = "NtpServer=%s" % id_ntp_server
            cmd = '%s' % ntp_server
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            cmd = 'serverAddress=%s' % ntp_server_ip
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            cmd = 'administrativeState=UNLOCKED'
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            cmd = 'commit'
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            if 'ERROR' in answer:
                raise CommandFailure(answer.replace('\r\n',';'))

        except Exception as e:
            raise CommandFailure(str(e))

    def update_ntp_server_cliss(self,ntp_server_ip,id_ntp_server):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_NTP'])

        try:
            ntp_server = "NtpServer=%s" % id_ntp_server
            cmd = '%s,%s' % (NTP_SERVER_DN,ntp_server)
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            # Replacing IPs
            cmd = 'configure'
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            cmd = 'serverAddress=%s' % ntp_server_ip
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            cmd = 'commit'
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            if 'ERROR' in answer:
                raise CommandFailure(answer.replace('\r\n',';'))

        except Exception as e:
            raise CommandFailure(str(e))

    def get_ntp_servers_info_cliss(self):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_NTP'])

        cmd = 'show -r %s' % NTP_SERVER_DN
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        data = self.fill_from_cliss_info(['NtpServer'], answer)
        ntp_info = {}
        try:
            if len(data['NtpServer']):
                ntp_server_id = data['NtpServer'][0]
                ntp_server = "NtpServer=%s" % ntp_server_id
                cmd = '%s,%s' % (NTP_SERVER_DN,ntp_server)
                self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
                address_data = self.fill_from_cliss_info(['serverAddress'], answer)
                server_ip_0 = address_data['serverAddress'][0]
                ntp_info.update({ntp_server_id:server_ip_0})

                if len(data['NtpServer']) >1:
                    ntp_server_id = data['NtpServer'][1]
                    ntp_server = "NtpServer=%s" % ntp_server_id
                    cmd = '%s,%s' % (NTP_SERVER_DN,ntp_server)
                    self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
                    address_data = self.fill_from_cliss_info(['serverAddress'], answer)
                    server_ip_1 = address_data['serverAddress'][1]
                    ntp_info.update({ntp_server_id:server_ip_1})

        except Exception as e:
            raise CommandFailure(str(e))

        return ntp_info


    def update_ntp_servers_cliss(self,list_ntp_servers):
        num_ntp_servers = len(list_ntp_servers)
        ntp_info = self.get_ntp_servers_info_cliss()
        _DEB('Current NTP configuration %s' % ntp_info)
        num_ntp_ids = len(ntp_info)
        idx_ntp_server=0
        if num_ntp_servers >= num_ntp_ids:
            for id_ntp in sorted(ntp_info.keys()):
                ntp_server = list_ntp_servers[idx_ntp_server]
                _DEB('Updating configuration for NTP server %s with ID %s' % (ntp_server, id_ntp))
                self.update_ntp_server_cliss(ntp_server,id_ntp)
                idx_ntp_server +=1

            if idx_ntp_server == 1 and num_ntp_servers > 1:
                ntp_server = list_ntp_servers[idx_ntp_server]
                new_id_ntp = str(1 + int(id_ntp))
                _DEB('Adding NTP server with ID %s and IP address %s' % (new_id_ntp, ntp_server))
                self.add_ntp_server_cliss(ntp_server, new_id_ntp)
        else: # We only update one NTP server. We have to remove the second one
            for ntp_server in list_ntp_servers:
                ntp_server = list_ntp_servers[idx_ntp_server]
                id_ntp = sorted(ntp_info.keys())[idx_ntp_server]
                _DEB('Updating configuration for NTP server %s with ID %s' % (ntp_server, id_ntp))
                self.update_ntp_server_cliss(ntp_server,id_ntp)
                idx_ntp_server +=1

            if idx_ntp_server == 1 and num_ntp_ids > 1:
                id_ntp = sorted(ntp_info.keys())[idx_ntp_server]
                ip_ntp = ntp_info[id_ntp]
                _DEB('Removing NTP server with ID %s and IP address %s' % (id_ntp,ip_ntp))
                self.remove_ntp_server_cliss(id_ntp)

    def sync_processor_ntp_server(self, processor, ntp_server):
        self.extend_connection(processor, processor)
        timeout = float(120)
        cmd = 'ntpdate -u %s' % ntp_server
        while True:
            now = time.time()
            answer = self.run_command(cmd, identity = processor, full_answer=True)
            _DEB('ntpdate output:%s' % answer)
            if 'step time server' in answer or 'adjust time server' in answer:
                break
            time.sleep(float(5))
            timeout -= time.time() - now
            if timeout < 0:
                raise ExecutionTimeout('Timeout waiting for syncronization processor %s' % processor)

        cmd = 'date'
        return self.run_command(cmd, identity = processor)

    def sync_processor_ntp_restart(self, processor):
        self.extend_connection(processor, processor)
        cmd = 'service ntp restart'
        self.run_command(cmd, identity = processor)
        time.sleep(float(8))
        cmd = 'date'
        return self.run_command(cmd, identity = processor)


    def add_csr_cert_cliss(self, cn_ip):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_CERT'])

        cmd = 'show -r -v %s' % CERT_MNG_DN
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        # Install Node Credential by CSR
        if 'NodeCredential=1' not in answer:
            _DEB('Creating CSR certificate with CN=%s' % cn_ip)
            cmd = '%s' % CERT_MNG_DN
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            cmd = 'configure'
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            cmd = 'NodeCredential=1'
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            cmd = 'subjectName=\"C=SE,O=Ericsson,CN=%s\"' % cn_ip
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            cmd = 'keyInfo=RSA_4096'
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            cmd = 'commit'
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            if 'ERROR' in answer:
                raise CommandFailure(answer.replace('\r\n',';'))

            cmd = 'startOfflineCsrEnrollment --uri HSS.csr'
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            if 'true' not in answer:
                cmd = 'show'
                answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
                if 'URI parameter file already exists' not in answer:
                    _DEB('CSR certificate file already exists')
                else:
                    raise CommandFailure(answer.replace('\r\n',';'))

        else:
            for line in answer.splitlines():
                if 'subjectName=' in line:
                    _INF('CSR certificate already created with\n%s' % line)


    def delete_csr_cert_cliss(self):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_CERT'])

        cmd = CERT_MNG_DN
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        # Removing Node Credential by CSR
        _DEB('Removing CSR certificate')
        cmd = 'configure'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'no NodeCredential=1'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'commit'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))


    def enrollment_info(self, requested_info = []):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_CERT'])
        cmd = CERT_MNG_DN + ',NodeCredential=1'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'show enrollmentProgress'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        return self.fill_from_cliss_info(requested_info, answer)

    def get_tls_protocol(self):
        _DEB('Getting tls_protocol')
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_CERT'])
        cmd = 'show ManagedElement=1,SystemFunctions=1,SecM=1,Tls=1 | filter protocolVersion | filter TLS'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        for line in answer.splitlines():
            if "protocolVersion=" in line:
                tls_protocol = line.split('=')[-1].replace('"','')
                break
        _DEB('tls_protocol: %s' % tls_protocol)
        if tls_protocol == 'TLSv1.2':
            tls_protocol_cmd = 'tls1_2'
        elif tls_protocol == 'TLSv1.1':
            tls_protocol_cmd = 'tls1_1'
        else:
            tls_protocol_cmd = 'tls1'
        return tls_protocol_cmd


    def trusted_cert_info(self, requested_info = []):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_CERT'])
        cmd = CERT_MNG_DN
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'show reportProgress'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        return self.fill_from_cliss_info(requested_info, answer)


    def inst_csr_cert_cliss(self, ip_tg, cert_file, cert_finger_print):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_CERT'])

        cmd = 'show %s' % CERT_MNG_DN
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        # Install Node Credential by CSR
        if 'NodeCredential=1' not in answer:
            err_info='Node Credential should be already created'
            raise CommandFailure(err_info)

        cmd = '%s,NodeCredential=1' % CERT_MNG_DN
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        # sftp is done with hss_st user from the GT to get the cert file
        user_pwd = self.get_user_credential('hss_st')
        cmd = 'installCredentialFromUri --uri sftp://hss_st@%s/%s --uriPassword %s --fingerprint %s' % (ip_tg, cert_file, user_pwd, cert_finger_print)
        _DEB('Executing cmd: %s' % cmd)
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'true' not in answer:
            raise CommandFailure(answer.replace('\r\n',';'))

        timeout = float(60)
        while True:
            now = time.time()
            time.sleep(float(5))
            info = self.enrollment_info(['state','result','resultInfo'])
            if info['state'][0] == 'FINISHED':
                break
            timeout -= time.time() - now
            if timeout < 0:
                raise ExecutionTimeout('Timeout waiting for installCredentialFromUri')

        if info['result'][0] != 'SUCCESS':
            err_message = 'installCredentialFromUri error: %s' % info['resultInfo'][0]
            raise CommandFailure(err_message)


    def inst_trusted_cert_cliss(self, ip_tg, cert_file, cert_finger_print):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_CERT'])

        cmd = CERT_MNG_DN
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

        # Install Trusted Certificate
        user_pwd = self.get_user_credential('hss_st')
        cmd = 'installTrustedCertFromUri --uri sftp://hss_st@%s/%s --uriPassword %s --fingerprint %s' % (ip_tg, cert_file, user_pwd, cert_finger_print)
        _DEB('Executing cmd: %s' % cmd)
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'true' not in answer:
            raise CommandFailure(answer.replace('\r\n',';'))

        timeout = float(60)
        while True:
            now = time.time()
            time.sleep(float(3))
            info = self.trusted_cert_info(['state','result','resultInfo'])
            if info['state'][0] == 'FINISHED':
                break
            timeout -= time.time() - now
            if timeout < 0:
                raise ExecutionTimeout('Timeout waiting for installTrustedCertFromUri')
        if info['result'][0] != 'SUCCESS':
            raise CommandFailure('installTrustedCertFromUri error: %s' % info['resultInfo'][0])


    def delete_trusted_cert_cliss(self):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_CERT'])

        try:
            cmd = CERT_MNG_DN
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

            # Remove Trusted Certificate
            cmd = 'removeTrustedCert --trustedCert "TrustedCertificate=1"'
            _DEB('Executing cmd: %s' % cmd)
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            if 'true' not in answer:
                _WRN('TrustedCertificate did not exist:\n%s' % answer)

        except Exception as e:
            raise CommandFailure(str(e))


    def create_trusted_category_cliss(self):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_CERT'])

        cmd = CERT_MNG_DN
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        # Create Trusted Category with the trustedCertificate
        cmd = 'configure'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'TrustCategory=1'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'trustedCertificates=["%s,TrustedCertificate=1"]' % CERT_MNG_DN
        _DEB('Executing cmd: %s' % cmd)
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))
        cmd = 'commit'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))



    def delete_trusted_category_cliss(self):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_CERT'])

        cmd = CERT_MNG_DN
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        # Create Trusted Category with the trustedCertificate
        cmd = 'configure'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'no TrustCategory=1'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'commit'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))


    def enable_trusted_cert_cliss(self):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_CERT'])

        cmd = CERT_MNG_DN
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        # Enable Trusted Certificate
        cmd = 'configure'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'TrustedCertificate=1'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'managedState=ENABLED'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'commit'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))


    def disable_trusted_cert_cliss(self):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_CERT'])

        cmd = CERT_MNG_DN
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        # Enable Trusted Certificate
        cmd = 'TrustedCertificate=1'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            _WRN('TrustedCertificate does not exist:\n%s' % answer)
        else:
            cmd = 'configure'
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            cmd = 'managedState=DISABLED'
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            cmd = 'commit'
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            if 'ERROR' in answer:
                raise CommandFailure(answer.replace('\r\n',';'))



    def config_cli_tls_cliss(self):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_CERT'])

        cmd = '%s,CliTls=1' % SYS_DN
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        # Configure CLI TLS
        cmd = 'configure'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'nodeCredential=\"%s,NodeCredential=1\"' % CERT_MNG_DN
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'trustCategory=\"%s,TrustCategory=1\"' % CERT_MNG_DN
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'commit'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))

        # Setting teh Administrative State to UNLOCKED
        cmd = 'configure'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'administrativeState=UNLOCKED'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'commit'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))


    def delete_config_cli_tls_cliss(self):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_CERT'])

        cmd = '%s,CliTls=1' % SYS_DN
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        # Setting the Administrative State to LOCKED
        cmd = 'configure'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'administrativeState=LOCKED'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        # Removing CLI TLS configuration
        cmd = 'no nodeCredential=\"%s,NodeCredential=1\"' % CERT_MNG_DN
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'no trustCategory=\"%s,TrustCategory=1\"' % CERT_MNG_DN
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'commit'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))


    def config_netconf_tls_cliss(self):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_CERT'])

        cmd = '%s,NetconfTls=1' % SYS_DN
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        # Configure NETCONF TLS
        cmd = 'configure'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'nodeCredential="%s,NodeCredential=1"' % CERT_MNG_DN
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'trustCategory="%s,TrustCategory=1"' % CERT_MNG_DN
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'commit'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))

        # Setting teh Administrative State to UNLOCKED
        cmd = 'configure'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'administrativeState=UNLOCKED'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'commit'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))


    def delete_config_netconf_tls_cliss(self):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_CERT'])

        cmd = '%s,NetconfTls=1' % SYS_DN
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        # Setting teh Administrative State to LOCKED
        cmd = 'configure'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'administrativeState=LOCKED'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        #  Removing NETCONF TLS Configuration
        cmd = 'no nodeCredential="%s,NodeCredential=1"' % CERT_MNG_DN
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'no trustCategory="%s,TrustCategory=1"' % CERT_MNG_DN
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'commit'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))


    def config_flow_policy_cliss(self,flow_policy_name, flow_dest, flow_port, flow_prot='tcp', flow_pool='SCs_rr'):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_CERT'])

        cmd = EVIP_FLOWPOLICY_CLISS_DN
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        # Configure NETCONF TLS EvipFlowPolicy
        cmd = 'configure'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'EvipFlowPolicy=%s' % flow_policy_name
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'addressFamily="ipv4"'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        # dest is the OAM IP of the HSS environment
        cmd = 'dest="%s"' % flow_dest
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'destPort="%s"' % flow_port
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'protocol="%s"' % flow_prot
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'targetPool="%s"' % flow_pool
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'commit'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))


    def delete_flow_policy_cliss(self,flow_policy_name):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_CERT'])

        cmd = EVIP_FLOWPOLICY_CLISS_DN
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        # Configure NETCONF TLS EvipFlowPolicy
        cmd = 'configure'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'no EvipFlowPolicy=%s' % flow_policy_name
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'commit'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))


    def get_tls_port(self, tls_component):
        tls_config_file = '/cluster/storage/system/config/com-apr9010443/lib/comp/libcom_tlsd_manager.cfg'
        port = ''
        cmd = 'grep %sTlsPort %s' % (tls_component, tls_config_file)
        answer = self.run_command(cmd)
        for line in answer:
            if tls_component in line:
                new_line = re.search('Port>(.*)</', line)
                port = new_line.group(1)
        return port


    def check_scaling_cliss(self):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_MNG'])

        timeout = float(300)
        started = time.time()
        error_message = 'Failed to retrieve all requested information'
        exec_OK = False
        while not exec_OK:
            exec_OK = True
            now = time.time()
            time.sleep(float(5))

            cmd = '%s,CrM=1' % SYS_DN
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            cmd = 'show -m ComputeResourceRole -p instantiationState,operationalState'
            answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            if 'ERROR' in answer:
                if error_message in answer:
                    _WRN('ERROR expected when getting computerResourceRole information. Retrying ...')
                    exec_OK = False
                else:
                    raise CommandFailure(answer.replace('\r\n',';'))

            timeout -= time.time() - now
            if timeout < float(0):
                raise ExecutionTimeout('Timeout waiting for computerResourceRole information')

        return answer


    def scalable_payloads_cliss(self):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_MNG'])

        cmd = '%s,CrM=1' % SYS_DN
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'show Role=role.payload'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))

        return answer

    def scale_in_payloads_cliss(self, list_pl_names):
        self.start_CBACliss(self.config['host'], identity = 'cliss_hssadministrator', user = CLISS_ACCESS['USER_MNG'])

        for pl_name in list_pl_names:
            cmd = '%s,CrM=1,ComputeResourceRole=%s' % (SYS_DN, pl_name)
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            cmd = 'configure'
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
            cmd = 'no provides'
            self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)

        #Only one commit and from the upper level
        cmd = 'up'
        self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        cmd = 'commit'
        answer = self.run_command(cmd, identity = 'cliss_hssadministrator', full_answer=True)
        if 'ERROR' in answer:
            raise CommandFailure(answer.replace('\r\n',';'))


class AlarmMonitorBaseCBA(threading.Thread):
    def __init__(self, access_config):
        threading.Thread.__init__(self)

        self.__id = 'ALARM_MONITOR'
        self.__access_config = access_config
        self.__running = False
        self.__connection = None
        self.__allow_reconnection = True
        self.__max_time_for_reconnection = 300
        self.__last_alarms = []
        self.__current_alarms = []
        self.__alarms = {}
        self.__sampling_time = 1
        self.__force_exit = False

    @property
    def force_exit(self):
        return self.__force_exit

    def activate_force_exit(self):
        self.__force_exit = True

    @property
    def id(self):
        return self.__id

    @property
    def online(self):
        return self.__running

    @property
    def max_time_for_reconnection(self):
        return self.__max_time_for_reconnection

    @max_time_for_reconnection.setter
    def max_time_for_reconnection(self, max_time_for_reconnection):
        self.__max_time_for_reconnection = max_time_for_reconnection

    @property
    def running(self):
        return self.__running

    @running.setter
    def running(self, running):
        self.__running = running

    @property
    def connection(self):
        return self.__connection

    @connection.setter
    def connection(self, connection):
        self.__connection = connection

    @property
    def sampling_time(self):
        return self.__sampling_time

    @sampling_time.setter
    def sampling_time(self, sampling_time):
        self.__sampling_time = sampling_time

    @property
    def new_alarms(self):
        return set(self.__current_alarms) - set(self.__last_alarms)

    @property
    def cleared_alarms(self):
        return set(self.__last_alarms) - set(self.__current_alarms)

    def start_monitoring(self):

        if not self.online:
            try:
                self.__connection = hss_utils.node.cba.Cba(config = self.access_config)
                _INF('%s started' % self.id)
                self.__running = True

            except KeyboardInterrupt:
                _WRN('%s Cancelled by user' % self.id)

            except Exception as e:
                _ERR('%s Cannot start monitoring: %s' % (self.id, str(e)))
        self.start()

    def shutdown(self):
        self.__running = False
        _INF('%s shutdown received' % self.__id)
        if self.connection is None:
            return
        try:
            self.__allow_reconnection = False
            time.sleep(float(self.__sampling_time) + 1)
        except KeyboardInterrupt:
            _WRN('%s Cancelled by user' % self.id)
        self.show_not_cleared_alarms()
        self.__connection.release()
        self.__connection = None

    def add_alarm_info(self, alarm, state = 'New'):
        if self.__connection is None:
            return
        try:
            data = self.__connection.get_alarm_info(alarm)
            if data:
                self.__alarms.update({alarm:{'data':data,'state':state}})
                _INF('%s %s alarm %s stored in DB' % (self.id, state, alarm))

        except (IndexError,KeyError):
            _WRN('%s %s alarm %s data not found in cliss' % (self.id, state, alarm))
            return
 
    def clear_alarm_info(self, alarm):
        try:
            self.__alarms[alarm]['state']='Cleared'
        except KeyError as e:
            _WRN('%s Cleared alarm %s data not found in DB' % (self.id, alarm))
            return

        _INF('%s Cleared alarm %s in DB' % (self.id, alarm))

    def show_alarm(self,alarm,state='New'):
        if self.__connection is None:
            return
        try:
            info = '\n%s     %s\n' % (state, self.__connection.print_alarm_info(alarm,self.__alarms[alarm]['data']))
            self.log_event(info)
        except (IndexError,KeyError) as e:
            _WRN('%s %s alarm %s data to be displayed not found in DB' % (self.id, state, alarm))

    def get_not_cleared_alarms(self):
        not_cleared_alarms = []
        for alarm in self.__alarms.keys():
            if self.__alarms[alarm]['state'] == 'New':
                not_cleared_alarms.append(alarm)
        return not_cleared_alarms

    def show_not_cleared_alarms(self):
        for alarm in self.__alarms.keys():
            if self.__alarms[alarm]['state'] == 'New':
                _INF('%s Alarm received but not cleared %s' % (self.id, alarm))
                self.show_alarm(alarm,state='Alarm received but not cleared')

    def log_event(self, event_info):
        pass

    def alarm_state(self, alarm_filter={}):
        for alarm, alarm_info in self.__alarms.iteritems():
            if alarm_info['state'] == 'Initial':
                continue
            found = True
            for field, value in alarm_filter.iteritems():
                try:
                    if value not in alarm_info['data'][field][0]:
                        found = False
                        break;
                except (KeyError, IndexError) as e:
                    _WRN('%s filter field "%s" not found for alarm %s' % (self.id, field, alarm))
                    return -1,'not found'
            if found:
                return alarm,alarm_info['state']
        return -1,'not found'

    def reconnect(self):
        timeout = float(self.max_time_for_reconnection)
        while (self.__allow_reconnection):
            if self.force_exit:
                return
            now = time.time()
            time.sleep(float(10))
            try:
                self.__connection.release_connection(identity = 'cliss_hssadministrator')
                self.__connection.start_alarm_handling()
                self.__running = True
                _INF('%s reconnected' % self.id)
                return
            except (hss_utils.connection.Unauthorized, hss_utils.connection.ConnectionFailed,
                    hss_utils.connection.ConnectionTimeout,Exception) as e:
                _DEB('Exception: %s' % str(e))

            timeout -= time.time() - now
            if timeout < float(0):
                _ERR('%s Timeout waiting for reconnection' % self.id)
                self.shutdown()


    def run(self):
        _INF('%s start thread execution' % self.id)

        try:
            self.__last_alarms = self.__connection.alarm_info(['FmAlarm'])['FmAlarm']
            for alarm in self.__last_alarms:
                self.add_alarm_info(alarm, state = 'Initial')
        except (hss_utils.connection.ConnectionFailedEOF, hss_utils.connection.ConnectionFailedTimeout) as e:
            _WRN('%s Connection broken' % self.id)
            self.reconnect()

        while (self.online):
            if self.force_exit:
                return
            time.sleep(float(self.__sampling_time))
            try:
                self.__current_alarms = self.__connection.alarm_info(['FmAlarm'])['FmAlarm']
                for alarm in self.new_alarms:
                    self.add_alarm_info(alarm)
                    self.show_alarm(alarm,state='New')

                for alarm in self.cleared_alarms:
                    self.clear_alarm_info(alarm)
                    self.show_alarm(alarm,state='Cleared')

                self.__last_alarms = self.__current_alarms

            except (hss_utils.connection.ConnectionFailedEOF, hss_utils.connection.ConnectionFailedTimeout) as e:
                _WRN('%s Connection broken' % self.id)
                self.reconnect()

        _INF('%s end of thread execution' % self.id)



class AlarmLogEventHandlerBaseCBA(threading.Thread):
    def __init__(self, access_config):
        threading.Thread.__init__(self)

        self.__id = 'ALARM_EVENT_LOG_HANDLER'
        self.__access_config = access_config
        self.__initial_access_host = copy.deepcopy(access_config['host'])
        self.__running = False
        self.__connection = None
        self.__allow_reconnection = True
        self.__max_time_for_reconnection = 300
        self.__sampling_time = 10
        self.__last_processed_event = '2001'
        self.__last_processed_log = None
        self.__events = {}
        self.__force_exit = False

    @property
    def initial_access_host(self):
        return self.__initial_access_host

    @property
    def force_exit(self):
        return self.__force_exit

    def activate_force_exit(self):
        self.__force_exit = True

    @property
    def id(self):
        return self.__id

    @property
    def conId(self):
        return self.connection.conId_for_log

    @property
    def online(self):
        return self.__running

    @property
    def max_time_for_reconnection(self):
        return self.__max_time_for_reconnection

    @max_time_for_reconnection.setter
    def max_time_for_reconnection(self, max_time_for_reconnection):
        self.__max_time_for_reconnection = max_time_for_reconnection

    @property
    def running(self):
        return self.__running

    @running.setter
    def running(self, running):
        self.__running = running

    @property
    def connection(self):
        return self.__connection

    @connection.setter
    def connection(self, connection):
        self.__connection = connection

    @property
    def sampling_time(self):
        return self.__sampling_time

    @sampling_time.setter
    def sampling_time(self, sampling_time):
        self.__sampling_time = sampling_time

    def start_handling(self):

        if not self.online:
            try:
                self.__connection = hss_utils.node.cba.Cba(config = self.__access_config)
                self.__connection.force_primary_controller()
                _INF('%s started' % self.id)
                self.__running = True

            except KeyboardInterrupt:
                _WRN('%s Cancelled by user' % self.id)

            except Exception as e:
                _ERR('%s Cannot start handling: %s' % (self.id, str(e)))

        self.__last_processed_log = self.last_log()
        if self.__last_processed_log is None:
            _ERR('%s Cannot start handling' % self.id)
            self.shutdown(wait=False)
            return

        _INF('%s Current event log %s' % (self.id, self.__last_processed_log))
        self.initialize_last_processed_event()
        _INF('%s Event offset %s' % (self.id, self.last_processed_event))

        self.start()

    def shutdown(self, wait = True):
        self.__force_exit = True
        self.__running = False
        _INF('%s shutdown received' % self.__id)
        if self.connection is None:
            return
        self.__allow_reconnection = False
        if wait:
            try:
                time.sleep(float(self.__sampling_time) + 1)
            except KeyboardInterrupt:
                _WRN('%s Cancelled by user' % self.id)

        self.__connection.release()
        self.__connection = None


    def log_event(self, event_info):
        pass


    def last_log(self):
        if self.__connection:
            _DEB('%s Last log: connection exists' % (self.id))
            active_log = self.__connection.active_log(self.__connection.alarm_path, wildcard='*.log')
            if active_log:
                return active_log

            _WRN('%s Connection broken' % self.id)
            if self.reconnect():
                return self.__connection.active_log(self.__connection.alarm_path, wildcard='*.log')
        _DEB('%s Last log: connection is None' % (self.id))


    def log_to_process(self):
        log_to_process = []
        if not self.__last_processed_log:
            _WRN('%s Last processed log is empty' % self.id)
            return log_to_process

        wildcard = self.__last_processed_log.split('.')[0] + '*'
        log_to_process += self.__connection.find_logs(self.__connection.alarm_path, wildcard=wildcard)
        if not log_to_process:
            _WRN('%s log_to_process is empty ' % self.id)
            return log_to_process

        active_log = self.last_log()
        _DEB('%s Active log is %s' % (self.id, active_log))
        if self.__last_processed_log != active_log:
            log_to_process.append(active_log)
            self.__last_processed_log = active_log
            _INF('%s New event log %s' % (self.id, self.__last_processed_log))
            # Jira HSSSTT-157
            time.sleep(float(2))

        return log_to_process


    def reconnect(self):
        timeout = float(self.max_time_for_reconnection)
        while (self.__allow_reconnection):
            if self.force_exit:
                return
            now = time.time()
            time.sleep(float(15))
            try:
                self.__connection.release_connection(identity = 'main')
                self.__connection.release_connection(identity = self.conId)
                _INF('%s Trying to reconnect....' % self.id)
                _DEB('Creating connection with session type %s' % self.__connection.session_type)
                _DEB('Creating connection with config host  %s' % self.initial_access_host)
                access_config = self.connection.config
                _DEB('Creating connection with config user  %s' % access_config['user'])
                access_config['host'] = self.initial_access_host
                con = self.__connection.create_connection(config=access_config, session_type=self.__connection.session_type)
                if self.__connection.session_type == hss_utils.connection.session.HardenedLinux:
                   con.set_root_passw(self.__connection.get_user_credential('root'))

                self.__connection.set_default_connection()
                self.__connection.open_connection()
                _INF('%s reconnected. Connection: %s' % (self.id, self.connection))
                timeout -= time.time() - now

                _INF('%s Waiting for System Status OK ...' % self.id)
                warn_message = False
                while True:
                    if self.force_exit:
                        return
                    now = time.time()
                    try:
                        if self.__connection.node_status_OK:
                            break
                        else:
                            # To avoid lots of WRN messages in VNF TCs
                            if not warn_message:
                                _WRN('%s System Status NOK' % self.id)
                                warn_message = True

                    except Exception as e:
                        _DEB('Exception: %s' % e)

                    time.sleep(float(5))
                    timeout -= time.time() - now
                    _DEB('Timeout for System Status OK: %s' % timeout)
                    if timeout < float(0):
                        _ERR('%s Timeout waiting for System Status OK' % self.id)
                        self.shutdown(wait=True)

                self.__connection.force_primary_controller()
                self.__running = True
                _INF('%s System Status OK' % self.id)
                self.connection.conId_for_log = None
                return True

            except (hss_utils.connection.Unauthorized, hss_utils.connection.ConnectionFailed,
                    hss_utils.connection.ConnectionTimeout,Exception) as e:
                _DEB('%s Exception: %s' % (self.id, str(e)))
                _WRN('%s Reconnection Failed.' % self.id)
            except CommandFailure as e:
                _WRN('%s Reconnection Failed: %s' % (self.id, str(e)))

            timeout -= time.time() - now
            _DEB('Timeout for Reconnection: %s' % timeout)
            if timeout < float(0):
                _ERR('%s Timeout waiting for reconnection' % self.id)
                self.shutdown()

    @property
    def last_processed_event(self):
        return self.__last_processed_event

    def get_event_info_from_log(self):
        data = ''
        for log_file in self.log_to_process():
            data += self.__connection.get_log_info(os.path.join(self.__connection.alarm_path, log_file))

        return '''<data>
%s
</data>''' % data


    def initialize_last_processed_event(self):
        log_info = self.get_event_info_from_log()
        self.__xml_info = ET.fromstring(log_info)
        for event in self.__xml_info.iter('FmLogRecord'):
            new_event = event.find('LogTimestamp').text
            self.__last_processed_event = new_event

    def process_events(self, initial_state = 'New', show = True):
        _DEB('Processing events ...')
        log_info = self.get_event_info_from_log()
        self.__xml_info = ET.fromstring(log_info)
        for event in self.__xml_info.iter('FmLogRecord'):
            event_data ={}
            new_event = event.find('LogTimestamp').text
            if new_event > self.last_processed_event:
                info = event.find('Alarm').text.split(';')
                event_index = '%s - %s' % (info[11], info[14])
                state= initial_state if info[7] != 'CLEARED' else 'Cleared'
                event_data.update({'lastEventTime':info[1]})
                event_data.update({'source':info[2]})
                event_data.update({'specificProblem':info[5]})
                event_data.update({'additionalText':info[8]})
                event_data.update({'eventType':info[10]})
                event_data.update({'activeSeverity':info[12]})
                event_data.update({'originalAdditionalText':info[13]})

                if state == initial_state:
                    self.__events.update({(event_index):{'data':event_data,'state':state}})
                    if show:
                        self.show_event(event_index)
                else:
                    try:
                        self.__events[(event_index)]['state']=state
                        if show:
                            self.show_event(event_index)
                    except KeyError:
                        _WRN('%s Event to be cleared %s not found' % (self.id, event_index))

                if new_event > self.__last_processed_event:
                    self.__last_processed_event = new_event

    def event_info(self, event):
        info = 'LogTimestamp - sequence number: %s' %event
        info += '\n\t%s' % self.__events[event]['data']['activeSeverity']
        info += '\n\t%s' % self.__events[event]['data']['eventType']
        info += '\n\t%s' % self.__events[event]['data']['lastEventTime']
        info += '\n\t%s' % self.__events[event]['data']['source']
        info += '\n\t%s' % self.__events[event]['data']['specificProblem']
        info += '\n\t%s' % self.__events[event]['data']['additionalText']
        info += '\n\t%s' % self.__events[event]['data']['originalAdditionalText']
        return info

    def show_event(self,event):
        try:
            state = self.__events[event]['state']
            info = '\n%s     %s\n' % (state, self.event_info(event))
            self.log_event(info)
        except (IndexError,KeyError) as e:
            _DEB('Exception %s' % str(e))
            _WRN('%s %s event %s data to be displayed not found in DB' % (self.id, state, event))

    def find_event(self, key='state', value='New'):
        events = []
        for event in self.__events.keys():
            if self.__events[event][key] == value:
                events.append(event)
        return events

    def remove_event(self, event):
        try:
            del self.__events[event]
        except Keyerror:
            _DEB('%s alarm not found' % event)

    def event_state(self, event_filter={}):
        for event, event_info in self.__events.iteritems():
            if event_info['state'] == 'Initial':
                continue
            found = True
            for field, value in event_filter.iteritems():
                try:
                    if value not in event_info['data'][field]:
                        found = False
                        break;
                except (KeyError, IndexError) as e:
                    _WRN('%s filter field "%s" not found for event %s' % (self.id, field, event))
                    return -1,'not found'
            if found:
                return event,event_info['state']
        return -1,'not found'

    def events_by_state(self, state):
        events = []
        for event, event_info in self.__events.iteritems():
            if event_info['state'] == state:
                events.append(event)
        return events

    def report_not_cleared_events(self):
        for event in self.events_by_state('New'):
            _WRN('%s Event received but not cleared %s' % (self.id, event))
            self.show_event(event)

    def not_cleared_events_info(self):
        info = '\n'
        for event in self.events_by_state('New'):
            info += self.event_info(event) + '\n'
        return info

    def run(self):
        _INF('%s start thread execution' % self.id)

        try:
            self.process_events(initial_state = 'Initial', show = False)
        except (hss_utils.connection.ConnectionFailedEOF, hss_utils.connection.ConnectionFailedTimeout) as e:
            _WRN('%s Connection broken' % self.id)
            self.reconnect()

        while (self.online):
            if self.force_exit:
                return
            time.sleep(float(self.__sampling_time))
            try:
                self.process_events()

            except (hss_utils.connection.ConnectionFailedEOF, hss_utils.connection.ConnectionFailedTimeout) as e:
                _WRN('%s Connection broken' % self.id)
                self.reconnect()

        _INF('%s end of thread execution' % self.id)


