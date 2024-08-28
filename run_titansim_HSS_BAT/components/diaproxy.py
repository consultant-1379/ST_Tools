#!/usr/bin/python2.7

import random
import time
import pexpect

import hss_utils.connection as connection
import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning

from hss_utils.st_command import *
import hss_utils.node.gentraf
from shared import *
from components import get_free_port
from scenario.config_handler import get_BAT_config
import shared

DIAPROXY = 'DiaProxy5.0'

APPIDS = {
    "Cx":{'appid':16777216,'sctp':False},
    "Zx":{'appid':16777217,'sctp':False},
    "Sh":{'appid': 16777217,'sctp':False},
    "S6a":{'appid':16777251,'sctp':False},
    "S6t":{'appid':16777345,'sctp':False},
    "S6m":{'appid':16777310,'sctp':False}
}

class Appid(object):
    def __init__(self, info):
        # info  ->   appid:numOfCon:
        self.__origin_realm = "ericsson.se"
        self.__numOfCon = 1
        self.__ip = None
        self.__port = None
        elements =  info.count(':')
        self.__name = elements[0]
        if len(elements) > 1:
            self.__numOfCon = elements[1]
        
        try:
            self.__appid = APPIDS[self.__name]['appid']
            self.__sctp = APPIDS[self.__name]['sctp']
        except KeyError as e:
            _ERR('Appid creation problem: %s' % e)
            quit_program(DIAPROXY_ERROR)
    @property
    def name(self):
        return self.__name

    @property
    def ip(self):
        return self.__ip

    @ip.setter
    def ip(self, value):
        self.__ip = value

    @property
    def port(self):
        return self.__ip

    @port.setter
    def port(self, value):
        self.__port = value

    def __str__(self):
        if not self.__ip:
            _ERR('Missing Diameter server IP for %s' % self.__name)
            quit_program(DIAPROXY_ERROR)

        if not self.__port:
            _ERR('Missing Diameter server port for %s' % self.__name)
            quit_program(DIAPROXY_ERROR)

        return '''
{
enable = true;
name = "%s";
origin_realm = "ericsson.se";
appid = %d;
ip = "%s";
port = %d;
numOfCon = %d;
sctp = %s;
}
''' % (self.__name, self.__appid, self.__ip, self.__port, self.__numOfCon,
       ('true' if self.__sctp else 'false'))


class DiaproxyBase(object):
    def __init__(self, diaproxy_definition, config_file, password=None, instanceno=None,dia_port_offset=None, cnhss=False):
        #assert(diaproxy_definition is None)
        self.__cnhss = cnhss
        if diaproxy_definition is None:
            # Enter dummy mode
            self.__host = None
            self.__port = None
            self.__local_ip = None
            self.__node = None
        else:
            self.__host = diaproxy_definition[0]
            self.__port = diaproxy_definition[1]
            self.__instance_id = instanceno
            if dia_port_offset is None:
                self.__dia_port_offset = None
            else:
                self.__dia_port_offset = dia_port_offset + 10 * int(instanceno)

            self.__config = config_file
            self.__config_contents = get_BAT_config(self.__config)
            self.__password = password
            self.__udp_port = None

            _INF('Creating Diaproxy in %s:%s' % (self.__host, self.__port))
            access_config = {'host':self.__host,'password':self.__password} 
            try:
                self.__node = hss_utils.node.gentraf.GenTraf(config = access_config)
                self.__node.working_dir = '%s_Diaproxy_%s' % (shared.EXECUTION_PATH, self.__instance_id)
                self.__channel = self.__node.get_channel()
            except connection.Unauthorized, e: 
                _ERR('Error: %s' % str(e))
                quit_program(CONNECTION_ERROR)
            except (connection.ConnectionFailed, connection.ConnectionTimeout), e: 
                _ERR('Error: %s' % str(e))
                quit_program(CONNECTION_ERROR)
            except KeyboardInterrupt:
                _WRN('Cancelled by user')
                quit_program(USER_CANCEL)
            except Exception as e:
                _ERR('Diaproxy creation problem: %s' % e)
                quit_program(DIAPROXY_ERROR)

    @property
    def config(self):
        return self.__config_contents

    @property
    def instance_id(self):
        return self.__instance_id

    @property
    def host(self):
        return self.__host

    @property
    def port(self):
        return self.__port

    @property
    def oh_prefix(self):
        return ' -oh_prefix "Diaproxy.%s"' % self.config['scenario_type']

    @property
    def udp_port(self):
        if self.__udp_port is None:
            upper=10999
            lower=10000

            self.__udp_port = get_free_port(self.__host, self.__password,upper=upper, lower=lower, offset=self.__dia_port_offset)
        return self.__udp_port

    def start(self):
        if self.__node is None: 
            return None

        _INF('Diaproxy cmd: ulimit -c unlimited')
        self.__channel.write_line('ulimit -c unlimited')

        _INF('Diaproxy cmd: %s' % self.command_line)
        self.__channel.write_line(self.command_line)
        try:

            result = self.__channel.expect(['DIAPROXY UP & RUNNING',
                                    'DIAMETER_UNABLE_TO_COMPLY',
                                    'Failed to bind socket on port',
                                    'Failed to send CER to Diameter'],timeout=30.0 )

            cause = self.__channel.last_match
            if result == 0:
                _INF('Diaproxy %s:%s:%s UP & RUNNING' % (self.__host, self.__port, self.udp_port))
            elif result == 1:
                _ERR('Diaproxy %s:%s There is not a free connection for the used peer node. It could be another Diaproxy using it' % (self.__host, self.__port))
                quit_program(DIAPROXY_ERROR)
            elif result == 2:
                _ERR('Diaproxy %s:%s using a listener port that is busy. It could be another Diaproxy using it' % (self.__host, self.__port))
                quit_program(DIAPROXY_ERROR)
            elif result == 3:
                _ERR('Diaproxy %s:%s routing problem from Diaproxy to HSS' % (self.__host, self.__port))
                quit_program(DIAPROXY_ERROR)
            else:
                _ERR('Diaproxy %s:%s start problem: %s' % (self.__host, self.__port, cause))
                quit_program(DIAPROXY_ERROR)

        except pexpect.TIMEOUT, e:
            _ERR('Diaproxy %s:%s timeout waiting for start' % (self.__host, self.__port))
            quit_program(DIAPROXY_ERROR)

        except pexpect.EOF, e:
            _ERR('EOF waiting to Diaproxy %s:%s ' % (self.__host, self.__port))
            quit_program(DIAPROXY_ERROR)


    @property
    def available(self):
        if self.__host is None:
            return False
        status = send_udp_command('getstatus', self.__host, self.udp_port, timeout=4.0)
        return status is not None

    def kill(self):
        if self.__node is None:
            return
        try:
            _INF('Terminate Diaproxy %s:%s' % (self.__host, self.__port))
            while self.available:
                send_udp_command('exit', self.__host, self.udp_port)
                time.sleep(3.0)

            destination = os.getcwd()
            self.__node.clean_working_dir(destination, backup=['\*.log','\*.data','\*core*'])
            self.__node.release()

        except Exception, e:
            _WRN('Diaproxy %s:%s killing problem: %s' % (self.__host, self.__port, e))

class Diaproxy(DiaproxyBase):
    def __init__(self, diaproxy_definition, config_file, password=None, instanceno=None,dia_port_offset=None, cnhss=False):
        DiaproxyBase.__init__(self, diaproxy_definition, config_file, password=password, instanceno=instanceno, dia_port_offset=dia_port_offset, cnhss=cnhss)

        self.__cnhss = cnhss
        if diaproxy_definition is None:
            # Enter dummy mode
            self.__nc = None
            self.__local_ip = None
        else:
            self.__nc = diaproxy_definition[2]
            self.__local_ip = diaproxy_definition[3]


    @property
    def server(self):
        if self.config['scenario_type'] == 'ISMSDA':
            server = self.config['diameter_server_tcp']
        else:
            server = self.config['diameter_server_sctp']

        return ' -server %s%s' % (server, (' -6' if validate_ip(server,IPv6=True) else ''))

    @property
    def secondary(self):
        if self.config['sec_diameter_server_tcp'] != "":
            return ' -secondary %s' % self.config['sec_diameter_server_tcp']

        return ''

    @property
    def protocol(self):
        if self.config['scenario_type'] == 'ESM':
            return ' -t sctp %s' % ('-proxy %s' if self.__local_ip != '' else '')

        return ' -t tcp'

    @property
    def server_port(self):
        if self.__cnhss:
            return ' -p %s' % self.config['diameter_server_port']
        elif self.config['scenario_type'] == 'ISMSDA':
            return ' -p %s' % ('3872' if self.config['slf'] else '3868')
        else:
            return ' -p %s' % ('3872' if self.config['slf'] else '3870')

    @property
    def additional_ism(self):
        if self.config['scenario_type'] == 'ESM' and not self.__cnhss:
            return '%s' % ('' if self.config['slf'] else (' -ism 3868 -ism_server %s' % self.config['diameter_server_tcp']))

        return ''

    @property
    def command_line(self):
        cmd = '%s -li %s -udp %s -nc %s -e %s' % (DIAPROXY, self.port, self.udp_port, self.__nc, (self.instance_id +  self.config['originhostoffset']) )
        return cmd + self.server + self.protocol + self.server_port + self.additional_ism + self.oh_prefix + self.secondary


    def __str__(self):
        return 'Diaproxy running on %s:%s' % (self.host, self.port)