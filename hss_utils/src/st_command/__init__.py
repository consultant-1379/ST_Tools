#!/usr/bin/env python
#
import subprocess
import argparse
import textwrap
import threading
import collections
import socket
import shutil
import fcntl
import struct
import getpass
import ldap
import re
import os
import json
import os.path
import tempfile
import signal
import copy

from distutils.spawn import find_executable
#from e3utils.e3types.basic import new_address, IPv4Address, IPv6Address
import ipaddress
from ipaddress import IPv4Address, IPv6Address

import e3utils.log as logging
_DEB = logging.internal_debug
_WRN = logging.warning
_ERR = logging.error
_INF = logging.info

import hss_utils.rosetta
import hss_utils.rosetta.services
import hss_utils.connection 
import hss_utils.connection.session
import hss_utils.connection.ssh

EXIT_ERRORS =  {
0: 'Success',
1: 'Not found / do not exist',
2: 'Failure in command',
3: 'Execution Timeout',
4: 'Connection error',
5: 'Authentication error',
7: 'Permission denied',
10: 'Wrong parameter value',
40: 'Rosetta error',
100: 'Implementation error'
    }

# Exit status
EXIT_CODE = 0
SUCCESS = 0
NOT_FOUND = 1
EXECUTION_ERROR = 2
TIMEOUT = 3
CONNECTION_ERROR = 4
AUTHENTICATION_ERROR = 5
PERMISSION_DENIED = 7
WRONG_PARAMETER = 10
RESOURCES_ERROR = 20
ROSETTA_ERROR = 40
IMPLEMENTATION_ERROR = 100

def get_exit_status():
    exit_status = '''\
    EXIT STATUS
'''
    for key in sorted(EXIT_ERRORS):
        exit_status += '\t%s\t%s\n' % (key, EXIT_ERRORS[key])

    return exit_status

class ExecutionTimeout(Exception):
    def __init__(self, message='Timeout reached'):
        self.__err = message

    def __str__(self):
        return '%s' % self.__err

class NotFound(Exception):
    def __init__(self, message='Not found or do not exist'):
        self.__err = message

    def __str__(self):
        return '%s' % self.__err

class CommandFailure(Exception):
    def __init__(self, message='Command failure'):
        self.__err = message

    def __str__(self):
        return '%s' % self.__err

class WrongParameter(Exception):
    def __init__(self, message='Wrong parameter value'):
        self.__err = message

    def __str__(self):
        return '%s' % self.__err

def create_connection_summary(processor_info):
    report = {}
    for line in processor_info:
        if len (line.split()) > 4:
            status = line.split()[5]
            if status not in report.keys():
                report.update({status: 1})
            else:
                report[status] += 1

    for key, value in report.iteritems():
        print '\tNumber of %s connections:\t%s' %(key, value)

DYNAMIC_PROCESSES = [ 
'HSS_CxAppProc',
'HSS_ZxAppProc',
'HSS_CxUpdateSubsDataProc',
'HSS_CxDeregisterProc',
'HSS_ShIncomingServiceProc',
'HSS_ShNotifInfoGatherProc',
'HSS_ZhIncomingServiceProc',
'HSS_CxUpdatePasswordProc',
'HSS_EsmS6aAppProc',
'HSS_EsmSwxAppProc',
'HSS_SihIncomingProc',
'HSS_SmRadAcctAppProc',
'HSS_SmSihIpAppProc',
'HSS_SmSihImsiAppProc',
'HSS_SmSihCslAppProc',
'HSS_SmSihErrorMsgAppProc',
'HSS_IsmSoapWorkerProc',
'HSS_SdaSlhIncomingServiceProc',
'HSS_EsmSwxOutgoingComposerProc',
'HSS_EsmSwxOutgoingSenderProc',
'HSS_EsmOutgoingProc',
'HSS_ShAsNotifierProc',
'HSS_EsmS6tAppProc',
'HSS_EsmSubsOutProc',
'HSS_EsmS6tOutgoingAnswerProc',
'HSS_EsmS6tOutgoingComposerProc',
'HSS_EsmS6tOutgoingSenderProc',
'HSS_EsmS6mS6nAppProc',
'HSS_EsmHttpWorkerProc'
]

def execute_cmd(cmd,stdout= True,stderr = False, shell=True, cwd=None):

    try:
        stdout = subprocess.PIPE if stdout else None
        stderr = subprocess.PIPE if stderr else None
        proc = subprocess.Popen(cmd,
                                 stdout=stdout,
                                 stderr=stderr,
                                 shell=shell,
                                 cwd=cwd,
                                 executable='/bin/bash')

        stdout_value, stderr_value = proc.communicate() 

        if stderr:
            return stdout_value, stderr_value, proc.returncode
        else:
            return stdout_value, proc.returncode

    except Exception as e:
        _DEB('Command execution error: %s' % e)
        return EXECUTION_ERROR 

class BackgroundCommand(object):

    def __init__(self, command, shell=True, cwd=None, stop_signal=signal.SIGTERM):
        self.cmd = command
        self.shell= shell
        self.cwd= cwd
        self.stop_signal = stop_signal
        self.thread = None
        self.is_running=False

    def run(self):
        def target():
            self.process = subprocess.Popen(self.cmd,
                                            stdout = subprocess.PIPE,
                                            stderr = subprocess.PIPE,
                                            shell=self.shell,
                                            cwd=self.cwd,
                                            preexec_fn=os.setsid,
                                            executable='/bin/bash')

            self.is_running=True
            self.process.wait()
            self.is_running=False 
            _DEB('Background command finished: "%s"' % self.cmd)

        self.thread = threading.Thread(target=target)
        self.thread.start()

    def stop(self):
        if self.thread.is_alive():
            _DEB('Stopping background command: "%s"' % self.cmd)
            os.killpg(os.getpgid(self.process.pid), self.stop_signal)
            self.thread.join(10.0)



class Command(object):
    def __init__(self, command, stderr=False):
        self.command = command
        self.output= ''
        self.error= ''
        self.status = -1
        self.stderr = stderr

    def run(self, timeout=None, **kwargs):
        def target(**kwargs):
            try:
                self.process = subprocess.Popen(self.command,
                                                executable='/bin/bash',
                                                **kwargs)
                self.output, self.error = self.process.communicate()
                self.status = self.process.returncode

            except Exception as e:
                _DEB('Command execution error: %s' % e)
                return EXECUTION_ERROR

        # default stdout and stderr
        if 'stdout' not in kwargs:
            kwargs['stdout'] = subprocess.PIPE
        if 'stderr' not in kwargs:
            kwargs['stderr'] = subprocess.PIPE
        if 'shell' not in kwargs:
            kwargs['shell'] = True
        if 'cwd' not in kwargs:
            kwargs['cwd'] = None
        # thread
        thread = threading.Thread(target=target, kwargs=kwargs)
        thread.start()
        thread.join(timeout)
        if thread.is_alive():
            self.process.terminate()
            thread.join()
            self.error+= '\nCommand Timeout (%s sec) executing "%s"\n' % (timeout, self.command)

        if self.stderr:
            return self.output,self.error,self.status
        else:
            return self.output, self.status



class stFramework_ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super(stFramework_ArgumentParser, self).__init__(*args, **kwargs)
        self.parents = kwargs.get('parents', [])

class TSP_ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super(TSP_ArgumentParser, self).__init__(*args, **kwargs)

class CBA_ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super(CBA_ArgumentParser, self).__init__(*args, **kwargs)

class CLOUD_ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super(CLOUD_ArgumentParser, self).__init__(*args, **kwargs)

class GTLA_ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super(GTLA_ArgumentParser, self).__init__(*args, **kwargs)

class CUDB_ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super(CUDB_ArgumentParser, self).__init__(*args, **kwargs)

class CBA_scxb_ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super(CBA_scxb_ArgumentParser, self).__init__(*args, **kwargs)

class GENTRAF_ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super(GENTRAF_ArgumentParser, self).__init__(*args, **kwargs)

class DUMMYNET_ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super(DUMMYNET_ArgumentParser, self).__init__(*args, **kwargs)

def default_tsp_command_parser():

    parser = TSP_ArgumentParser(add_help=False)
    parser.add_argument('--node',
                        action='store', default=None,
                        help='IP address of the primary IO node. If omitted local hostname will be used to find env in rosetta',
                        dest='NODE')

    access_params = parser.add_argument_group('Access options')
    access_params.add_argument('--port',
                      action='store', default=22,
                      help='Port used in ssh. Default value is 22',
                      dest='port')

    access_params.add_argument('--user',
                      action='store', default='telorb',
                      help='User for ssh. Default value is "telorb"',
                      dest='user')

    access_params.add_argument('--password',
                      action='store', default='telorb',
                      help='Password used in ssh. Default value is "telorb"',
                      dest='password')

    access_params.add_argument('--not_force_primary',
                      action='store_true', default=False,
                      help='Do not force the connection to the primary controller"',
                      dest='primary')

    program_params = parser.add_argument_group('Program options')
    program_params.add_argument('-v', '--verbose',
                      action='store_true', default=False,
                      help='Verbose. Prints internal input/output from command.',
                      dest='verbose')

    return (parser)

def default_cba_command_parser():

    parser = CBA_ArgumentParser(add_help=False)
    parser.add_argument('--node',
                        action='store', default=None,
                        help='IP address of the OAM IP node. If omitted local hostname will be used to find env in rosetta',
                        dest='NODE')

    access_params = parser.add_argument_group('Access options')
    access_params.add_argument('--port',
                      action='store', default=22,
                      help='Port used in ssh.  Default value is 22',
                      dest='port')

    access_params.add_argument('--user',
                      action='store', default='com-emergency',
                      help='User for ssh.  Default value is "com-emergency"',
                      dest='user')

    program_params = parser.add_argument_group('Program options')
    program_params.add_argument('-v', '--verbose',
                      action='store_true', default=False,
                      help='Verbose. Prints internal input/output from command.',
                      dest='verbose')

    return (parser)

def default_cloud_command_parser():

    parser = CLOUD_ArgumentParser(add_help=False)
    parser.add_argument('--eccd-type',
                      action='store', default=None,
                      choices = ['IBD', 'ANS'],
                      help='Used for selecting the access mode. If omitted local hostname will be used to find env in rosetta',
                      dest='eccd_type')

    access_ibd_params = parser.add_argument_group('Access options for IBD')
    access_ibd_params.add_argument('--node',
                        action='store', default=None,
                        help='IP address of the OAM DIRECTOR IP. If omitted local hostname will be used to find env in rosetta',
                        dest='NODE')

    access_ibd_params.add_argument('--port',
                      action='store', default=22,
                      help='Port used in ssh in IBD.  Default value is 22',
                      dest='port')

    access_ibd_params.add_argument('--user',
                      action='store', default='eccd',
                      help='User for sshin IBD.  Default value is "eccd"',
                      dest='user')

    access_ibd_params.add_argument('--ssh-key',
                      action='store', default=None,
                      help='Full path of the ssh id_rsa key file. If omitted local hostname will be used to find env in rosetta',
                      dest='ssh_key')

    access_ans_params = parser.add_argument_group('Access options for ANSIBLE')
    access_ans_params.add_argument('--kubeconfig',
                      action='store', default=None,
                      help='Full path of the configuration file to be set as KUBECONFIG. If omitted local hostname will be used to find env in rosetta',
                      dest='kubeconfig')


    program_params = parser.add_argument_group('Program options')
    program_params.add_argument('-v', '--verbose',
                      action='store_true', default=False,
                      help='Verbose. Prints internal input/output from command.',
                      dest='verbose')

    return (parser)


def default_cudb_command_parser():

    parser = CUDB_ArgumentParser(add_help=False)
    parser.add_argument('--node',
                        action='store', default=None,
                        help='IP address of the OAM IP node. If omitted local hostname will be used to find env in rosetta',
                        dest='NODE')

    access_params = parser.add_argument_group('Access options')
    access_params.add_argument('--port',
                      action='store', default=22,
                      help='Port used in ssh.  Default value is 22',
                      dest='port')

    access_params.add_argument('--user',
                      action='store', default='com-emergency',
                      help='User for ssh.  Default value is "com-emergency"',
                      dest='user')

    access_params.add_argument('--password',
                      action='store', default='ericsson',
                      help='Password used in ssh.  Default value is "ericsson"',
                      dest='password')

    program_params = parser.add_argument_group('Program options')
    program_params.add_argument('-v', '--verbose',
                      action='store_true', default=False,
                      help='Verbose. Prints internal input/output from command.',
                      dest='verbose')

    return (parser)

def default_gtla_command_parser():

    parser = GTLA_ArgumentParser(add_help=False)
    parser.add_argument('--node',
                        action='store', default=None,
                        help='IP address or hostname of gtla. If omitted local hostname will be used to find env in rosetta',
                        dest='NODE')

    program_params = parser.add_argument_group('Program options')
    program_params.add_argument('-v', '--verbose',
                      action='store_true', default=False,
                      help='Verbose. Prints internal input/output from command.',
                      dest='verbose')

    return (parser)

def scxb_cba_command_parser():

    parser = CBA_scxb_ArgumentParser(add_help=False)
    parser.add_argument('--node',
                        action='store', default=None,
                        help='IP MGMT address of the SCXB. If omitted local hostname will be used to find env in rosetta',
                        dest='NODE')

    access_params = parser.add_argument_group('Access options')
    access_params.add_argument('--port',
                      action='store', default=2024,
                      help='Port used in ssh.  Default value is 2024',
                      dest='port')

    access_params.add_argument('--user',
                      action='store', default='advanced',
                      help='User for ssh.  Default value is "advanced"',
                      dest='user')

    program_params = parser.add_argument_group('Program options')
    program_params.add_argument('-v', '--verbose',
                      action='store_true', default=False,
                      help='Verbose. Prints internal input/output from command.',
                      dest='verbose')

    return (parser)

USERID = getpass.getuser()
HOSTNAME = socket.gethostname()

def default_gentraf_command_parser():
    parser = GENTRAF_ArgumentParser(add_help=False)
    access_params = parser.add_argument_group('Access options')
    access_params.add_argument('--node',
                        default=HOSTNAME, action='store', dest='NODE',
                        help='Hostname or IP address of the traffic generator. Default: local host %(default)s')

    access_params.add_argument('--port',
                      action='store', default=22,
                      help='Port used in ssh. Default value is 22',
                      dest='port')

    access_params.add_argument('--user',
                      action='store', default=USERID,
                      help='User for ssh. Default: User connected right now %(default)s',
                      dest='user')

    access_params.add_argument('--password',
                      action='store', default=None,
                      help='Password used in ssh. Not used by default',
                      dest='password')


    program_params = parser.add_argument_group('Program options')
    program_params.add_argument('-v', '--verbose',
                      action='store_true', default=False,
                      help='Verbose. Prints internal input/output from command.',
                      dest='verbose')

    return (parser)


def default_dummynet_command_parser():
    parser = DUMMYNET_ArgumentParser(add_help=False)
    access_params = parser.add_argument_group('Access options')
    access_params.add_argument('--node',
                        action='store', default=None,
                        help='Hostaname or IP address of the dummynet.',
                        dest='NODE')

    access_params.add_argument('--port',
                      action='store', default=22,
                      help='Port used in ssh. Default value is 22',
                      dest='port')

    access_params.add_argument('--user',
                      action='store', default='test',
                      help='User for ssh. Default: User connected right now %(default)s',
                      dest='user')

    access_params.add_argument('--password',
                      action='store', default='ericsson',
                      help='Password used in ssh. Default value is "%(default)s"',
                      dest='password')

    access_params.add_argument('--traffic_type',
                      action='store', default=None,
                      choices=['ldap','map','udm'],
                      help='Traffic type configured in dummynet',
                      dest='traffic_type')


    program_params = parser.add_argument_group('Program options')
    program_params.add_argument('-v', '--verbose',
                      action='store_true', default=False,
                      help='Verbose. Prints internal input/output from command.',
                      dest='verbose')

    return (parser)

def validate_ip(ip,IPv6=False):
    if isinstance(ip, unicode) or isinstance(ip, str):
        try:
            address = ipaddress.ip_address(unicode(ip))
        except ValueError:
            return False
        return isinstance(address,IPv6Address if IPv6 else IPv4Address)

    return False

def get_ip(host,IPv6=False):
    if validate_ip(host,IPv6=IPv6):
        return host
    else:
        return resolve_hostname(host)


# Get IP from a given machine name
def resolve_hostname(hostname):
    assert(isinstance(hostname, str) or isinstance(ip, unicode))
    try:
        if hasattr(socket, 'setdefaulttimeout'):
            socket.setdefaulttimeout(5)
        return socket.gethostbyname(hostname)

    except socket.error:
        return None

def get_ip_address(ifname):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', ifname[:15])
        )[20:24])

    except IOError:
        return ''

def parse_vip_parameter(parameter):
    vips = re.findall( r"([\d.]+)|\[([0-9a-fA-F\.:]*)\]|(:)", parameter)

    result=[]
    empty=True
    for vip in vips:
        ipv4,ipv6,separator= vip
        if ipv4 !='':
            empty=False
            result.append(ipv4)
        elif ipv6 !='':
            empty=False
            result.append(ipv6)
        elif empty:
            result.append('')
        else:
            empty=True

    return result

USE_NIS = True # Only in reverse nslookups!!

# Search LDAPv3
OAM_LDAP_PORT = 7323
OAM_LDAP_PASS = 'Txvf123'

def ldap_search(host, dn, base, port=OAM_LDAP_PORT, passwd=OAM_LDAP_PASS, attribute='', searchScope = ldap.SCOPE_BASE, timeout=5.0):

    try:
        l = ldap.open(host, port=port)
        l.protocol_version = ldap.VERSION3
        l.simple_bind(dn, passwd)

    except ldap.LDAPError as e:
        _DEB('ldap error: %s' % e)
        return None

    attrlist=[]
    attrlist.append(attribute)
    _DEB('ldap attrlist: %s' % attrlist)
    try:
        ldap_result_id = l.search(base, searchScope, attrlist=attrlist)
        result_set = []
        while 1:
            result_type, result_data = l.result(ldap_result_id, 0)
            if (result_data == []):
                break
            elif result_type == ldap.RES_SEARCH_ENTRY:
                _DEB('ldap result_data: %s' % result_data)
                for entry in result_data:
                    dn, atrr = entry
                    _DEB('ldap atrr: %s' % atrr)
                    try:
                        return atrr[attribute]
                    except KeyError:
                        return None

        return result_set

    except ldap.LDAPError as e:
        _DEB('ldap error: %s' % e)
        return None

def send_udp_command(command, host, port, timeout=5.0):

    _DEB('Sending command "%s" to %s:%s' % (command, host, port))
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)

    # Send command
    sock.sendto(command, (host, port))
    # Read response
    try:
        response, addr = sock.recvfrom(65535)
        return response
    except:
        return None

def clear_ansi(line):
    ansi_escape = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
    return ansi_escape.sub('', line)

def real_path(path):
    path = os.path.expandvars(path)
    path = os.path.expanduser(path)
    path = os.path.realpath(path)
    return path

def diff_list(list1, list2):
    c = set(list1).union(set(list2))  # or c = set(list1) | set(list2)
    d = set(list1).intersection(set(list2))  # or d = set(list1) & set(list2)
    return list(c - d)

def remove_quottes(text_string):
    if text_string.startswith('"') and text_string.endswith('"'):
        return text_string[1:-1]

    return text_string

def fix_args(arg):
    return ('"%s"' % arg) if ' ' in arg else arg

def ip2int(ip):
    o = map(int, ip.split('.'))
    return (16777216 * o[0]) + (65536 * o[1]) + (256 * o[2]) + o[3]

def int2ip(num):
    return '%s.%s.%s.%s' % (((num / 16777216) % 256),
                            ((num / 65536) % 256),
                            ((num / 256) % 256),
                            ((num) % 256))

def is_ip_in_net(net, ip):
    net = net.split('/')
    mask = int('1'* int(net[1]) + '0' * (32 - int(net[1])), 2)
    return ip2int(net[0]) & mask == ip2int(ip) & mask

def get_stFramework_error_message(stderr, header='stFramework_message ', maxnoflines=5):
    for line in reversed(stderr.splitlines()):
        position = line.find(header)
        if  position != -1:
            return line[position + len(header) :]
        maxnoflines -= 1
        if maxnoflines <= 0:
            break

def sorted_nicely(strlist ):
    if not strlist:
        return strlist
    convert = lambda text: int(text) if text.isdigit() else text
    alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(strlist, key = alphanum_key)


def check_node_type(host, cba_user = 'com-emergency'):
    config={'host': host,
            'port': '31310',
            'user':'jambala' ,
            'password': 'Pokemon1'}

    try:
        endpoint = hss_utils.connection.ssh.SSHEndpoint(config)
        channel = hss_utils.connection.ssh.SSHChannel(endpoint, timeout=5.0)
        new_connection =  hss_utils.connection.session.JambalaCLI(channel)
        new_connection.open()
        new_connection.close()
        return 'TSP'

    except:
        config={'host': host,
                'port': '22',
                'user': cba_user }

        credentials = get_node_credentials(node_type='hss_cba')
        config.update({'password': credentials[cba_user]})

        try:
            endpoint = hss_utils.connection.ssh.SSHEndpoint(config)
            channel = hss_utils.connection.ssh.SSHChannel(endpoint, timeout=5.0)
            new_connection =  hss_utils.connection.session.StandardLinux(channel)
            new_connection.open()
            new_connection.close()
            return 'CBA'
        except Exception as e:
            _DEB(str(e))
            return None

def get_node_credentials(node_type='hss_cba'):
    _FULL_PERMS_ = 0o0777
    if node_type == 'hss_cba':
        credentials = {
            'hssadministrator':'hsstest',
            'ericssonhsssupport':'hsstest',
            'SystemAdministrator':'hsstest',
            'com-emergency':'com-emergency',
            'root':'rootroot',
            'hss_st':'hss_st',
            'advanced' : 'ett,30'
            }
    else:
        credentials = {}

    credentials_file = os.path.join(os.path.expanduser("~"),'.node_credentials')
    if os.path.exists(credentials_file):
        st = oct(os.stat(credentials_file).st_mode & _FULL_PERMS_)
        if not st.endswith('00'):
            raise CommandFailure('"%s" permission shall be "600' % credentials_file)

        try:
            with open(credentials_file) as json_data:
                data = json.load(json_data)[node_type]
                if not isinstance(data, dict):
                    raise CommandFailure('%s in %s file shall be a dict' % (node_type, credentials_file))
                credentials.update(data)

        except Exception as e:
            raise CommandFailure('Error parsing json %s file: %s' % (credentials_file, e))

    return credentials

def get_user_credential(node_type, user):
    return get_node_credentials(node_type).get(user,None)

def parse(raw_data):
    listed_raw_data = raw_data.splitlines()
    listed_raw_data.reverse()
    return __parse_block__(listed_raw_data)


def __parse_block__(list_data, block_identation=0):
    def identation(text_line):
        '''Get line identation'''
        return len(text_line) - len(text_line.lstrip())

    def autocast(value):
        """Try to evaluate string as interger"""
        try:
            if value.startswith('0-') or value.startswith('1-') or value.startswith('2-'):
                return value
            return eval(value)
        except:
            pass
        try:
            return int(value)
        except:
            pass
        return value

    data = {}
    last_key = None
    last_value = None

    while len(list_data) > 0:
        line = list_data.pop()

        # Skip empty lines
        if line.strip() == '':
            continue
        # Skip unrecognized lines
        if '=' not in line:
            _DEB('Ignoring unrecognized line: "%s"' % line)
            continue

        # Format current line
        current_identation = identation(line)
        key = autocast(line.split('=')[0].strip())
        value = autocast('='.join(line.split('=')[1:]).strip())

        if value is None:
            value = ''

        # Analyze identation
        if current_identation < block_identation:
            # Close identation block
            # Adding last line again for the new block
            list_data.append(line)
            return data

        if current_identation > block_identation:
            # Open new identation block
            new_subblock = __parse_block__(list_data, current_identation)

            # Adding current key:value
            new_subblock.update({key: value})

            if last_key is None:
                _DEB('New identation block cannot be attached to any key')
                continue
            if last_key not in data.keys():
                data[last_key] = {}
            if isinstance(data[last_key], dict):
                data[last_key][last_value] = new_subblock
            else:
                data[last_key] = {data[last_key]: new_subblock}
            continue

        # Current identation
        if key in data.keys():
            if isinstance(data[key], list):
                data[key].append(value)
            else:
                if isinstance(data[key], dict):
                    data[key].update({value: {}})
                else:
                    new_value = [data[key], value]
                    data[key] = new_value
        else:
            data.update({key: value})
        last_key = key
        last_value = value

    return data

class QLock:
    #https://stackoverflow.com/questions/19688550/how-do-i-queue-my-python-locks
    def __init__(self):
        self.lock = threading.Lock()
        self.waiters = collections.deque()
        self.count = 0

    def acquire(self):
        self.lock.acquire()
        if self.count:
            new_lock = threading.Lock()
            new_lock.acquire()
            self.waiters.append(new_lock)
            self.lock.release()
            new_lock.acquire()
            self.lock.acquire()
        self.count += 1
        self.lock.release()

    def release(self):
        with self.lock:
            if not self.count:
                raise ValueError("lock not acquired")
            self.count -= 1
            if self.waiters:
                self.waiters.popleft().release()

    def locked(self):
        return self.count > 0


class Installation_helper(object):
    def __init__(self, config, required_packages):
        self.__config = config
        self.__local_dir = None
        self.__baseline = None
        self.__required_packages = required_packages
        self.__packages = []
        self.__license_file = None

        self.__population_netconf_repo = None
        self.__license_repo = None


    def release(self):
        if self.local_dir:
            shutil.rmtree(self.local_dir, ignore_errors=True)

    @property
    def local_dir(self):
        if not self.__local_dir:
            self.__local_dir = tempfile.mkdtemp(dir='/opt/hss')

        _INF('Using temporary directory %s ' % self.__local_dir)
        return self.__local_dir


    @property
    def population_netconf_repo(self):
        if not self.__population_netconf_repo:
            self.clone_repo('ST_Population_Netconf')
            self.__population_netconf_repo = os.path.join(self.__local_dir, 'ST_Population_Netconf')

        return self.__population_netconf_repo

    @property
    def license_repo(self):
        if not self.__license_repo:
            self.clone_repo('TCM/HSS_TCM_DOCS')
            self.__license_repo = os.path.join(self.__local_dir, 'HSS_TCM_DOCS')

        return self.__license_repo

    def clone_repo(self,repo):
        cmd = 'git clone ssh://%s:29418/HSS/%s' % (('git-hss_st' if USERID == 'hss_st' else '%s@gerrit-gamma.gic.ericsson.se' % USERID)
                                                           ,repo)

        self.run_command(cmd, cwd=self.local_dir)

    def checkout_commit(self, repo, commit):
        cmd = 'git checkout %s ' % commit
        self.run_command(cmd, cwd=repo)

    @property
    def population_netconf_commit(self):
        return self.baseline.additional_info['ST_Population_Netconf']

    @property
    def license_commit(self):
        return self.baseline.additional_info['TCM/HSS_TCM_DOCS']

    @property
    def license_file(self):
        if not self.__license_file:
            self.checkout_commit( self.population_netconf_repo,self.population_netconf_commit)

            cmd = 'cat test_info.data'
            stdout_value = self.run_command(cmd, cwd=self.population_netconf_repo)

            for line in stdout_value.split():
                if 'HSS_LICENSE' in line:
                    filename=line.split(':')[-1]
                    self.__license_file = filename.replace('$GIT_PATH/HSS_TCM_DOCS',self.license_repo)

            _INF('License file: %s' % self.__license_file)

            self.checkout_commit( self.license_repo,self.license_commit)

        return self.__license_file

    @property
    def baseline(self):
        if not self.__baseline:
            self.__baseline = hss_utils.rosetta.get_baseline(self.__config.baseline)
            if not self.__baseline:
                raise CommandFailure('Missing %s baseline in Rosetta' % self.__config.baseline)

        return self.__baseline

    @property
    def packages(self):
        package_to_find = copy.deepcopy(self.__required_packages)
        if not self.__packages:
            for software in self.baseline.software:
                for package in software.packages:
                    if package.name in self.__required_packages:
                        try:
                            self.__packages.append(package.file_locations[0])
                            _INF('%s:     %s' % (package.name, package.file_locations[0]))
                            package_to_find.remove(package.name)
                        except IndexError as e:
                            raise CommandFailure('Missing ARM link for %s' % package.name)

            if package_to_find:
                raise CommandFailure('Missing ARM links: %s' % ' '.join(package_to_find))

        return self.__packages

    def get_single_package(self, package_name):
        for software in self.baseline.software:
            for package in software.packages:
                if package.name == package_name:
                    return package.file_locations[0]


    def get_package_by_file_location(self, file_location):
        for software in self.baseline.software:
            for package in software.packages:
                if package.file_locations[0] == file_location:
                    return package.name


    def run_command(self, cmd, cwd=None):
        _INF('Executing: %s' % cmd)
        stdout_value, stderr_value, returncode = execute_cmd(cmd,stderr = True,cwd=cwd)
        if returncode:
            raise CommandFailure('%s' % stderr_value) 

        return stdout_value

