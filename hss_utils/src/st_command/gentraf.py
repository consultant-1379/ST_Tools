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

import e3utils.log as logging
_DEB = logging.internal_debug
_WRN = logging.warning
_ERR = logging.error
_INF = logging.info

from hss_utils.st_command import execute_cmd, get_user_credential, validate_ip
from hss_utils.node.cloud import ANS_CREDENTIAL_PATH,IBD_CREDENTIAL_PATH
import hss_utils.rosetta
import hss_utils.rosetta.services
import hss_utils.node.gentraf
from . import ExecutionTimeout
from . import NotFound
from . import CommandFailure
from . import WrongParameter
from . import ip2int
from . import is_ip_in_net

def run_test(user_config, node):
    #print node.run_command('pwd')
    node.working_dir = '/opt/hss/ECEMIT/prueba'

    print node.run_command('pwd')
    print node.get_return_code()

    node.run_command('cp /home/ecemit/trabajo/trafico/* /opt/hss/ECEMIT/prueba')
    print node.get_return_code()

    node.clean_working_dir('/opt/hss/ECEMIT/output', backup=['*.log','*.py','*.cfg'])
    print node.run_command('pwd')

def run_datetime(user_config, node):
    print node.datetime


def check_empty_files_in_dir_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('DIRNAME',
                      help='Specify the full directory path')
    return (parser)

def run_check_empty_files_in_dir(user_config, node):
    user_config.DIRNAME = hss_utils.st_command.real_path(user_config.DIRNAME)
    try:
        onlyfiles = [f for f in os.listdir(user_config.DIRNAME) if os.path.isfile(os.path.join(user_config.DIRNAME, f))]
    except OSError as e:
        raise CommandFailure('Error: %s' % str(e))

    not_empty = []
    for filename in onlyfiles:
        if os.stat(os.path.join(user_config.DIRNAME, filename)).st_size:
            not_empty.append(filename)

    if not_empty:
        raise CommandFailure('There are files not empty: %s' % ' , '.join(not_empty))


def get_free_port_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-u',
                      action='store', default=65536,
                      help='Upper limit. By default is "%(default)s".',
                      dest='upper')
    command_params.add_argument('-l',
                      action='store', default=11000,
                      help='Lower limit. By default is "%(default)s".',
                      dest='lower')

    return (parser)

def run_get_free_port(user_config, node):

    candidate = random.randint(int(user_config.lower), int(user_config.upper))
    tries = 1000
    while not node.available_port(candidate):
        candidate = random.randint(int(user_config.lower), int(user_config.upper))
        tries -= 1
        if tries == 0:
            raise CommandFailure('Cannot get a free port in host "%s"' % user_config.host)

    print candidate

def is_port_free_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('PORT',type=int,
                      help='Port to check')
    return (parser)

def run_is_port_free(user_config, node):

    if not node.available_port(user_config.PORT):
        raise CommandFailure('"%s" port seems to be busy' % user_config.PORT)

def get_nic_ip_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-n', '--nic',
                        default=None, action='store', dest='interface',
                        help='Network interface name. By default all the available NIC will be displayed ')

    command_params.add_argument('-6',
                        default=False, action='store_true',
                        dest='ipv6',
                        help='Select IPv6')

    return (parser)

def run_get_nic_ip(user_config, node):

    interfaces = []
    allowed_interfaces = node.interfaces
    if user_config.interface is None:
         interfaces = allowed_interfaces
    else:
        if node.is_interface_allowed(user_config.interface) == False:
            raise WrongParameter('Network Interface %s not valid. Allowed values are: %s' % (interface, ' '.join(allowed_interfaces)))

        interfaces.append(user_config.interface)

    for interface in interfaces:
        ip = node.get_ip_address_nic(interface,IPv6=user_config.ipv6)
        if len(ip) > 0 and ip[0] != '':
            if user_config.interface is not None:
                post = ''
            else:
                post = '\t%s' % interface
            print ('%s%s' % (ip[0], post))

def get_nic_ip_to_dest_host_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('DESTHOSTIP',
                        default=None, action='store',
                        help='Destination host IP used as filter ')

    command_params.add_argument('-6',
                        default=False, action='store_true',
                        dest='ipv6',
                        help='Select IPv6')

    return (parser)


def run_get_nic_ip_to_dest_host(user_config, node):
    nic_ip = node.get_nic_ip_to(user_config.DESTHOSTIP,IPv6= user_config.ipv6)
    if nic_ip is None:
        raise CommandFailure('%s route to %s not defined' % (('IPv6' if user_config.ipv6 else 'IPv4'), user_config.DESTHOSTIP))

    print nic_ip

def get_node_user_credential_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('NODETYPE',
                        action='store',
                        choices=['hss_cba'],
                        help='Type of node ')

    command_params.add_argument('USER',
                        action='store',
                        help='User')

    return (parser)


def run_get_node_user_credential(user_config, node):
    print get_user_credential(user_config.NODETYPE,user_config.USER)

def get_env_info_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-6',
                        default=False, action='store_true',
                        dest='ipv6',
                        help='Select IPv6')

    command_params.add_argument('--json',
                        default=False, action='store_true',
                        dest='json',
                        help='Just return a json file with the full information stored in Rosetta for the environment')

    command_params.add_argument('--env',
                        default=None, action='store',
                        dest='env',
                        help='Find the rosetta info for an specific environment')

    command_params.add_argument('--cloud-credential',
                        default=False, action='store_true',
                        dest='cloud_credential',
                        help='''Get from rosetta the credential file and store in
%s/<eccd-name>.conf for ANS and 
%s/id_rsa_<eccd-name> for IBD''' %(ANS_CREDENTIAL_PATH, IBD_CREDENTIAL_PATH))
    command_params.add_argument('--file',
                      action='store', default=None,
                      help='Full path of an specific file where to store the credential',
                      dest='credential_file')
    return (parser)



def run_get_env_info(user_config, node):

    try:
        if user_config.env is None:
            envs = hss_utils.rosetta.related_environments(user_config.NODE)
        else:
            envs = [hss_utils.rosetta.get_environment(user_config.env)]
        if not envs:
            raise CommandFailure('Rosetta return an empty list')
        if envs[0] is None:
            raise CommandFailure('Rosetta return None')
    except Exception as e:
        raise CommandFailure('Can not fetch Object "%s" from Rosetta (%s)' % (
            (user_config.NODE if user_config.env is None else user_config.env),e))

    import json
    for env in envs:
        _DEB('Environment: %s' % env.name)
        if user_config.json:
            with open('%s.json' % env.name, 'w') as outfile:
                json.dump(env.as_dict, outfile, indent=4)

            continue

        st_config = hss_utils.rosetta.services.st_config_for(env)

        if user_config.cloud_credential:
            try:
                eccd_type = st_config.get_eccd_type()
            except (hss_utils.rosetta.ObjectNotFound, hss_utils.rosetta.InfoNotFound, hss_utils.rosetta.RosettaUnavailable, KeyError) as e:
                raise CommandFailure(str(e))

            if eccd_type == 'ANS':
                if user_config.credential_file:
                    user_config.credential_file = hss_utils.st_command.real_path(user_config.credential_file)
                else:
                    user_config.credential_file = os.path.join(hss_utils.st_command.real_path(ANS_CREDENTIAL_PATH),
                                                               '%s.conf' % st_config.get_eccd_name())

                cmd = 'mkdir -p %s' % os.path.dirname(user_config.credential_file)
                stdout_value, stderr_value, returncode = hss_utils.st_command.execute_cmd(cmd,stdout= True,stderr = True)
                if returncode:
                    raise CommandFailure('Error: %s' % stderr_value)

                try:
                    file_content = hss_utils.rosetta.get_file_from_rosetta('eccds/%s/download_config_file/ ' % st_config.get_eccd_name())
                except Exception as e:
                    raise CommandFailure('Error: %s' % str(e))

                with open(user_config.credential_file,'w') as fd:
                    fd.write(file_content)

            elif eccd_type == 'IBD':
                if user_config.credential_file:
                    user_config.credential_file = hss_utils.st_command.real_path(user_config.credential_file)
                else:
                    user_config.credential_file = os.path.join(hss_utils.st_command.real_path(IBD_CREDENTIAL_PATH),
                                                'id_rsa_%s' % st_config.get_eccd_name())

                cmd = 'mkdir -p %s' % os.path.dirname(user_config.credential_file)
                stdout_value, stderr_value, returncode = hss_utils.st_command.execute_cmd(cmd,stdout= True,stderr = True)
                if returncode:
                    raise CommandFailure('Error: %s' % stderr_value)

                try:
                    file_content = hss_utils.rosetta.get_file_from_rosetta('credentials/%s/download_ssh_key_file/ ' % st_config.get_director_credential())
                except Exception as e:
                    raise CommandFailure('Error: %s' % str(e))

                with open(user_config.credential_file,'w') as fd:
                    fd.write(file_content)

                cmd = 'chmod 600 %s' % user_config.credential_file
                stdout_value, stderr_value, returncode = hss_utils.st_command.execute_cmd(cmd,stdout= True,stderr = True)
                if returncode:
                    raise CommandFailure('Error: %s' % stderr_value)


            else:
                error = 'Error: %s is not a vlid ECCD type. Allowed values are "ANS" or "IBD"' % eccd_type
                raise CommandFailure(error)


            continue

        st_config.display_ipv6 = user_config.ipv6
        print 'Name: \n\t%s\n' % env.name
        print st_config


ALLOWED_TOOLS_TOBE_STOPPED=['CBA_testcase','run_titansim_HSS_BAT','DiaProxy','LoadPlotter','run_command_node',
           'CBA_memory_monitor','mctr_cli','BAT_HSSTraffic','gnuplot','HSS_rtc','UserKnownHostsFile=/dev/null'
           ]

def stop_st_tool_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('NAME',
                        choices= ALLOWED_TOOLS_TOBE_STOPPED,
                        help='String used for selecting the tool to be stopped.')

    command_params.add_argument('--signal',
                        default=None, action='store',
                        dest='signal',
                        help='Specify the signal name to be send with kill instead of sending "kill -9"')

    command_params.add_argument('--exclude',
                        default=[], nargs='+',action='store',
                        dest='exclude',
                        help='Set a list of PIDs that shall not be killed')


    return (parser)

def run_stop_st_tool(user_config, node):
    own_pids = node.find_pid('stop_st_tool')
    pids = node.find_pid(user_config.NAME, exclude=user_config.exclude+own_pids)

    if pids:
        cmd = 'kill %s %s' % (('-9' if user_config.signal is None else '-s %s' % user_config.signal),
                              ' '.join(pids))

        stdout_value, stderr_value, returncode = execute_cmd(cmd,stderr = True)
        if returncode:
            raise CommandFailure('%s' % stderr_value)
    else:
        raise NotFound('%s Not found' % user_config.NAME)


def download_package_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('FROM',
                        help='ARM link or full NFS path of package')

    command_params.add_argument('TO',
                        help='Full path output')

    command_params.add_argument('-t','--timeout',
                      action='store', default=3600,type=int,
                      help='Max time in sec waiting for. By default is "%(default)s" seconds',
                      dest='max_time')


    return (parser)

def run_download_package(user_config, node):
    cmd = 'ls -l %s' % user_config.TO
    answer = node.run_command(cmd)
    if node.get_result_code() == 0:
        cmd = 'rm %s' % user_config.TO
        answer = node.run_command(cmd)
        if node.get_result_code():
            raise CommandFailure('%s' % answer)

    cmd = 'mkdir -p %s' % os.path.dirname(user_config.TO)
    answer = node.run_command(cmd)
    if node.get_result_code():
        raise CommandFailure('%s' % answer)

    if 'arm' in user_config.FROM:
        cmd = 'wget %s -O %s -nc' % (user_config.FROM, user_config.TO)
        answer = node.run_command(cmd,timeout=float(user_config.max_time))
        if node.get_result_code():
            raise CommandFailure('%s' % answer)

    else:
        node.download(user_config.FROM,user_config.TO, timeout=float(user_config.max_time))


def ntp_server_get_time_parser():
    parser = argparse.ArgumentParser(add_help=False)
    ntp_params = parser.add_argument_group('NTP access options ')
    ntp_params.add_argument('--ntp',
                        action='store', default=None,
                        help='IP address of the NTP Server. This parameter is mandatory.',
                        dest='ntp_server')

    ntp_params.add_argument('--ntp-port',
                      action='store', default=22,
                      help='Port to get connected to ntp server via ssh.  Default value is 22',
                      dest='ntp_port')

    ntp_params.add_argument('--ntp-user',
                      action='store', default='hss_st',
                      help='User to get connected to ntp server via ssh.  Default: User %(default)s',
                      dest='ntp_user')

    ntp_params.add_argument('--ntp-pwd',
                      action='store', default='hss_st',
                      help='User password for the ssh connection.  Default value is "%(default)s"',
                      dest='ntp_pwd')

    return (parser)

def run_ntp_server_get_time(user_config, node):
    if user_config.ntp_server:
        if not validate_ip(user_config.ntp_server):
            raise WrongParameter('Wrong IP adress format for parameter %s ' % user_config.ntp_server)
    else:
        raise WrongParameter('Mandatory parameter ntp_server has been omited')

    ntp_access = {}
    ntp_access['ntp'] = user_config.ntp_server
    ntp_access['ntp_user'] = user_config.ntp_user
    ntp_access['ntp_pwd'] = user_config.ntp_pwd
    ntp_access['ntp_port'] = user_config.ntp_port
    info = node.ntp_server_time_info(ntp_access)
    print '%s' % info


def ntp_server_set_time_parser():
    parser = argparse.ArgumentParser(add_help=False)
    ntp_params = parser.add_argument_group('NTP access options ')
    ntp_params.add_argument('--ntp',
                        action='store', default=None,
                        help='IP address of the NTP Server. This parameter is mandatory.',
                        dest='ntp_server')

    ntp_params.add_argument('--ntp-port',
                      action='store', default=22,
                      help='Port to get connected to ntp server via ssh.  Default value is 22',
                      dest='ntp_port')

    ntp_params.add_argument('--ntp-user',
                      action='store', default='hss_st',
                      help='User to get connected to ntp server via ssh.  Default: User %(default)s',
                      dest='ntp_user')

    ntp_params.add_argument('--ntp-pwd',
                      action='store', default='hss_st',
                      help='User password for the ssh connection.  Default value is "%(default)s"',
                      dest='ntp_pwd')

    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('-d','--new-date',
                      action='store', default=None,
                      help='Parameter to set a new  date on the NTP server with format "yyyy:mm:dd"',
                      dest='new_date')

    command_params.add_argument('-t','--new-time',
                      action='store', default=None,
                      help='Parameter to set a new time on the NTP server with format "HH:MM:SS"',
                      dest='new_time')

    return (parser)

def run_ntp_server_set_time(user_config, node):
    if user_config.ntp_server:
        if not validate_ip(user_config.ntp_server):
            raise WrongParameter('Wrong IP adress format for parameter %s ' % user_config.ntp_server)
    else:
        raise WrongParameter('Mandatory parameter ntp_server has been omited.')

    ntp_access = {}
    ntp_access['ntp'] = user_config.ntp_server
    ntp_access['ntp_user'] = user_config.ntp_user
    ntp_access['ntp_pwd'] = user_config.ntp_pwd
    ntp_access['ntp_port'] = user_config.ntp_port
    new_date = user_config.new_date
    new_time = user_config.new_time
    new_date_info = node.ntp_server_set_time(ntp_access, new_date, new_time)
    print '%s' % new_date_info


def tg_run_cliss_command_parser ():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('CLISS access options ')
    command_params.add_argument('CMD',action='store',
                      help='Cliss command to be executed')
    command_params.add_argument('--oam-ip',
                      action='store', default=None,
                      help='IP address of the OAM HSS environment. ',
                      dest='oam_ip')

    command_params.add_argument('--cliss-port',
                      action='store', default=122,
                      help='Port to get connected to ECLI via ssh.  Default value is 122',
                      dest='cliss_port')

    command_params.add_argument('--cliss-user',
                      action='store', default='hssadministrator',
                      choices=['hssadministrator','ericssonhsssupport','SystemAdministrator','com-emergency','root'],
                      help='Cliss user to be used. By default is "%(default)s"',
                      dest='cliss_user')

    command_params.add_argument('--cliss-pwd',
                      action='store', default='hsstest',
                      help='Password for the user to be used. By default is "%(default)s"',
                      dest='cliss_pwd')

    command_params.add_argument('--configure',
                      action='store_true', default=False,
                      help='To indicate if the command will modify the configuration. Then a "configure" a "commit" commands will be executed to apply the update.',
                      dest='cliss_conf')

    command_params.add_argument('--file',
                      action='store', default=None,
                      help='Store the output in an specific file instead of showing it in console',
                      dest='file')

    return (parser)

def run_tg_run_cliss_command(user_config, node):
    if user_config.oam_ip:
        if not validate_ip(user_config.oam_ip):
            raise WrongParameter('Wrong IP adress format for parameter %s ' % user_config.oam_ip)

    cliss_access = {}
    cliss_access['cliss_ip'] = user_config.oam_ip
    cliss_access['cliss_user'] = user_config.cliss_user
    cliss_access['cliss_pwd'] = user_config.cliss_pwd
    cliss_access['cliss_port'] = user_config.cliss_port

    answer = node.tg_run_cliss_command(cliss_access, user_config.CMD, user_config.cliss_conf)
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


def clean_remote_server_logs_parser():
    parser = argparse.ArgumentParser(add_help=False)
    remote_params = parser.add_argument_group('Remote Server access options ')
    remote_params.add_argument('--remote-server',
                        action='store', default=None,
                        help='Name of the Remote Server. This parameter is mandatory.',
                        dest='remote_server')

    remote_params.add_argument('--remote-port',
                      action='store', default=22,
                      help='Port to get connected to ntp server via ssh.  Default value is 22',
                      dest='remote_port')

    remote_params.add_argument('--remote-user',
                      action='store', default='hss_st',
                      help='User to get connected to ntp server via ssh.  Default: User %(default)s',
                      dest='remote_user')

    remote_params.add_argument('--remote-pwd',
                      action='store', default='hss_st',
                      help='User password for the ssh connection.  Default value is "%(default)s"',
                      dest='remote_pwd')

    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--oam-ip',
                      action='store', default=None,
                      help='Parameter to filter for the OAM IP to clean. If not defined, it will removed all the logs found under /var/log/HSS',
                      dest='oam_ip_dir')
    return (parser)

def run_clean_remote_server_logs(user_config, node):
    if not user_config.remote_server:
        raise WrongParameter('Mandatory parameter remote-server has been omited.')

    remote_access = {}
    remote_access['remote'] = user_config.remote_server
    remote_access['remote_user'] = user_config.remote_user
    remote_access['remote_pwd'] = user_config.remote_pwd
    remote_access['remote_port'] = user_config.remote_port
    try:
        node.clean_remote_server_logs(remote_access, user_config.oam_ip_dir)
    except Exception as e:
        raise CommandFailure('Error cleaning remote server logs: %s' % e)


def collect_remote_server_logs_parser():
    parser = argparse.ArgumentParser(add_help=False)
    remote_params = parser.add_argument_group('Remote Server access options ')
    remote_params.add_argument('--remote-server',
                        action='store', default=None,
                        help='Name of the Remote Server. This parameter is mandatory.',
                        dest='remote_server')

    remote_params.add_argument('--remote-port',
                      action='store', default=22,
                      help='Port to get connected to ntp server via ssh.  Default value is 22',
                      dest='remote_port')

    remote_params.add_argument('--remote-user',
                      action='store', default='hss_st',
                      help='User to get connected to ntp server via ssh.  Default: User %(default)s',
                      dest='remote_user')

    remote_params.add_argument('--remote-pwd',
                      action='store', default='hss_st',
                      help='User password for the ssh connection.  Default value is "%(default)s"',
                      dest='remote_pwd')

    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--oam-ip',
                      action='store', default=None,
                      help='Parameter to filter for the OAM IP to collect the logs. If not defined, all the logs found under /var/log/HSS will be collected',
                      dest='oam_ip_dir')
    command_params.add_argument('--collect-dir',
                      action='store', default=None,
                      help='Full path where to save the tar file with the logs collected. If not defined, it will be saved under the current directory',
                      dest='collect_dir')
    return (parser)

def run_collect_remote_server_logs(user_config, node):
    if not user_config.remote_server:
        raise WrongParameter('Mandatory parameter remote-server has been omited.')

    remote_access = {}
    remote_access['remote'] = user_config.remote_server
    remote_access['remote_user'] = user_config.remote_user
    remote_access['remote_pwd'] = user_config.remote_pwd
    remote_access['remote_port'] = user_config.remote_port
    try:
        path_file_log = node.collect_remote_server_logs(remote_access, user_config.oam_ip_dir)
    except Exception as e:
        raise CommandFailure('Error collecting remote server logs: %s' % e)

    if not path_file_log:
        raise CommandFailure('Remote logs cannot be collected')

    if not user_config.collect_dir:
        cmd = 'pwd'
        stdout_value, stderr_value, returncode = hss_utils.st_command.execute_cmd(cmd,stdout= True,stderr = True)
        if returncode:
            raise CommandFailure('Error: %s' % stderr_value)
        _DEB('PWD=%s' % stdout_value)
        user_config.collect_dir = stdout_value
    _DEB(' Saving tar log file under %s' % user_config.collect_dir)
    cmd = 'sshpass -p "%s" scp %s@%s:/%s/%s %s' % (user_config.remote_pwd, user_config.remote_user, user_config.remote_server, user_config.remote_user, path_file_log, user_config.collect_dir)

    stdout_value, stderr_value, returncode = hss_utils.st_command.execute_cmd(cmd,stdout= True,stderr = True)
    if returncode:
        raise CommandFailure('Error: %s' % stderr_value)
    _DEB('File saved correctly under %s' % user_config.collect_dir)

