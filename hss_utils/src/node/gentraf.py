#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import Queue
import ntpath
import re
import os
import socket
import time
import copy

import hss_utils.connection
import hss_utils.connection.session
import hss_utils.connection.ssh
import hss_utils.connection.telnet
import hss_utils.st_command
from . import Node

import e3utils.log as logging
_DEB = logging.internal_debug
_WRN = logging.warning
_ERR = logging.error
_INF = logging.info

class RemoteFolderError(Exception):
    def __init__(self, message='Error handling remote folder'):
        self.__err = message

    def __str__(self):
        return '%s' % self.__err

CONNECTION = 0
OPENNED = 1

SERVER_PORT=41041

class GenTraf(Node):

    def __init__(self, config={}, force_primary = True, allow_x11_forwarding = False):

        Node.__init__(self)

        if 'host' not in config.keys():
            raise ValueError('host missing')
        if 'port' not in config.keys():
            config['port'] = '22'

        if 'user' in config.keys() and config['user'] == 'hss_st':
            config['password'] = 'hss_st'

        self.__config = config
        self.__session_type=hss_utils.connection.session.StandardLinux
        self.__interfaces = []

        self.create_connection(config=self.config, session_type=hss_utils.connection.session.StandardLinux, allow_x11_forwarding= allow_x11_forwarding)
        self.set_default_connection()
        self.__wd_in_use = False
        self.__working_dir = ''

    def clone_connection(self, identity ='cloned', allow_x11_forwarding = False,force_open=False):
        self.create_connection(config=self.config, session_type=self.__session_type, identity = identity,
                               allow_x11_forwarding=allow_x11_forwarding, force_open=force_open)

    @property
    def working_dir(self):
        return self.__working_dir

    @working_dir.setter
    def working_dir(self, new_wd):
        self.__working_dir = new_wd
        try:
            answer = self.run_command('mkdir -p %s' % new_wd, allow_local_execution = False, full_answer=True)
            if 'cannot create directory' in answer:
                raise RemoteFolderError('Error: "%s"' % answer) 
            answer = self.run_command('cd %s' % new_wd, allow_local_execution = False, full_answer=True)
            if answer:
                raise RemoteFolderError('Error: "%s"' % answer)
        except (hss_utils.connection.ConnectionTimeout, hss_utils.connection.ConnectionFailed, OSError) as e:
            _ERR('Problem creating temporary folder "%s"' % self.working_dir)

        self.__wd_in_use = True

    def clean_working_dir(self, destination = None, backup=[]):
        if not self.__wd_in_use:
            # Directory not created
            return

        # Download files to local node and cwd
        log_lost = False
        for files in backup:
            try:
                _INF('Download "%s" to %s' % (os.path.join(self.working_dir,files), destination))
                self.download(os.path.join(self.working_dir,files), destination)

            except IOError as e:
                error = str(e)
                if 'File not found' in error:
                    _WRN('%s: %s' % (error, os.path.join(self.working_dir,files)))
                    continue
                _ERR('SCP error: %s' % str(e))
                log_lost = True

            except Exception as e:
                error = str(e)
                _ERR('SCP error: %s' % str(e))
                log_lost = True

        if log_lost:
            _WRN('Logs will not be removed from temp directory %s' % self.working_dir)
            return

        try:
            cmd = 'rm -rf %s' % self.working_dir
            output = self.run_command(cmd, timeout=20, allow_local_execution = False, full_answer=True)
            if 'cannot remove' in output:
                _ERR('Error: "%s"' % output)
                raise RemoteFolderError('Error: "%s"' % output)
            self.__wd_in_use = False
            self.__wd_suffix = ''
        except (hss_utils.connection.ConnectionTimeout, hss_utils.connection.ConnectionFailed, OSError) as e:
            _WRN('Problem removing temporary folder "%s"' % self.working_dir)

    @property
    def config(self):
        return self.__config

    @property
    def session_type(self):
        return self.__session_type

    @property
    def is_localhost(self):
        return socket.gethostname() == self.__config['host']

    def extend_connection(self, identity, session_type=hss_utils.connection.session.StandardLinux, parent = 'main'):
        return Node.extend_connection(self, identity,config=self.config, session_type=session_type, parent=parent)

    def run_command(self, cmd, identity = None, answer = {}, timeout = None, full_answer = False, allow_local_execution = False):
        if identity:
            self.create_connection(config=self.config, session_type=hss_utils.connection.session.StandardLinux, identity = identity)

        if self.is_localhost and allow_local_execution:
            _DEB('Executing cmd locally: "%s"' % cmd)
            stdout_value, returncode = hss_utils.st_command.execute_cmd(cmd)

            if full_answer:
                return stdout_value
            else:
                return stdout_value.split('\n')[:-1]

        else:
            _DEB('Executing cmd remotely')
            try:
                return Node.run_command(self,cmd, identity , answer, timeout, full_answer)
            except (hss_utils.connection.Unauthorized, hss_utils.connection.ConnectionFailed,hss_utils.connection.ConnectionTimeout,Exception) as e:
                _ERR('Problem executing cmd remotely: %s' % str(e))

    @property
    def interfaces(self):
        if len (self.__interfaces) == 0:
            interfaces = os.listdir('/sys/class/net/')
            for interface in interfaces:

                if len(self.get_ip_address_nic(interface)) > 0 and interface != 'lo':
                    self.__interfaces.append(interface)

        return self.__interfaces

    def is_interface_allowed(self, interface):
        return interface in self.interfaces


    def get_ip_address_nic(self,nic,IPv6=False):
        try:
            cmd = "ifconfig | grep -A2 \"%s \" | grep inet%s" % (nic,('6' if IPv6 else ''))
            answer = self.run_command(cmd, allow_local_execution = True)
            for line in answer:
                line = hss_utils.st_command.clear_ansi(line)
                if 'inet%s' % ('6' if IPv6 else '') in line:
                    line = line.replace('inet%s addr:' % ('6' if IPv6 else ''),'')
                    value = [line.split()[0]]
                    return value
        except (hss_utils.connection.ConnectionTimeout, hss_utils.connection.ConnectionFailed, OSError) as e:
            _WRN('Problem getting IP address nic')

        return ['']


    def get_nic_ip_to(self,dest,IPv6=False):
        try:
            cmd = "ip route get %s 2>/dev/null |  sed -nr 's/.*src ([^ ]*).*/\\1/p'" % dest
            answer = self.run_command(cmd, allow_local_execution = True)
            if len(answer) and hss_utils.st_command.validate_ip(answer[0], IPv6):
                return answer[0]
        except (hss_utils.connection.ConnectionTimeout, hss_utils.connection.ConnectionFailed, OSError) as e:
            _WRN('Problem getting nic IP address')


    def available_port(self, port, ignore_loopback=True, tcp=True, allow_local_execution = True):
        assert(isinstance(port, int))
        if port < 1024:
            return False

        try:
            output = self.run_command('netstat -n%sl' % ('t' if tcp else 'u'), allow_local_execution = allow_local_execution, timeout=5)
            # Parse netstat output
            for line in output:
                line = line.strip()
                if line.startswith('tcp' if tcp else 'udp'):
                    line = line.split()
                    lsocket = line[3]
                    if lsocket.startswith('127.0.0.1') and ignore_loopback:
                        continue
                    listening_port = int(lsocket.split(':')[-1])
                    if listening_port == port:
                        return False
        except (hss_utils.connection.ConnectionTimeout, hss_utils.connection.ConnectionFailed, OSError) as e:
            _WRN('Problem checking available ports')
        return True

    def find_pid(self,process,exclude=None,allow_local_execution = True):
        grep_exclude = ''
        if exclude is not None:
            grep_exclude += ' '.join([ 'grep -v %s |' % pid for pid in exclude ])
        pids = []
        try:
            cmd = "ps -ef | grep %s | grep -v grep | grep -v /bin/bash | %s awk '{print $2}'" % (process, grep_exclude)
            answer = self.run_command(cmd,full_answer=True,allow_local_execution = allow_local_execution)
            for line in answer.split('\n'):
                line=line.strip()
                if line:
                    pids += [line]
        except (hss_utils.connection.ConnectionTimeout, hss_utils.connection.ConnectionFailed, OSError) as e:
            _WRN('Problem finding PID of a process')
        return pids

    def get_result_code(self, identity = None,allow_local_execution = False):
        try:
            cmd = 'echo EL:$?'
            self.run_command(cmd, identity, timeout = 2.0, full_answer = True)
            channel = self.get_channel()
            if len(channel.stdout) == 0:
                return 0

            for line in channel.stdout.split('\r\n'):
                searchObj = re.search(r'EL:\d+',line)
                if searchObj:
                    error_code = searchObj.group()[3:]
                    return  int(error_code)
        except Exception as e:
            _DEB('get_return_code problem: %s' % e)
            return -1
        return 0

    def ntp_server_time_info(self, ntp_access):
        answer = ''
        cmd = 'date "+%Y%m%d %T %Z"'
        error_pattern = 'date'
        self.__config['host'] = ntp_access['ntp']
        self.__config['port'] = ntp_access['ntp_port']
        self.__config['user'] = ntp_access['ntp_user']
        self.__config['password'] = ntp_access['ntp_pwd']

        try:
            answer = self.run_command(cmd, timeout=60, identity='ntp', full_answer=True, allow_local_execution = False)
            if error_pattern in answer:
                raise hss_utils.st_command.CommandFailure(answer.replace('\r\n',';'))
        except (hss_utils.connection.ConnectionTimeout, hss_utils.connection.ConnectionFailed, OSError) as e:
            _ERR('Problem getting time info from NTP server')
        return answer

    def ntp_server_set_time(self, ntp_access, new_date=None, new_time=None):
        answer = ''
        self.__config['host'] = ntp_access['ntp']
        self.__config['port'] = ntp_access['ntp_port']
        self.__config['user'] = ntp_access['ntp_user']
        self.__config['password'] = ntp_access['ntp_pwd']
        try:
            if new_date:
                cmd = 'sudo date -s "%s"' % new_date
                _DEB(' Executing cmd %s' % cmd)
                answer = self.run_command(cmd, identity = 'ntp', full_answer=True)
                if 'date' in answer:
                    raise hss_utils.st_command.CommandFailure(answer.replace('\r\n',';'))

            if new_time:
                cmd = 'sudo date -s "%s"' % new_time
                _DEB(' Executing cmd %s' % cmd)
                answer = self.run_command(cmd, identity = 'ntp', full_answer=True)
                if 'date' in answer:
                    raise hss_utils.st_command.CommandFailure(answer.replace('\r\n',';'))
            cmd = 'date "+%Y%m%d %T %Z"'
            answer = self.run_command(cmd, identity = 'ntp', full_answer=True)
            if 'date' in answer:
                raise hss_utils.st_command.CommandFailure(answer.replace('\r\n',';'))

        except (hss_utils.connection.ConnectionTimeout, hss_utils.connection.ConnectionFailed, OSError) as e:
            _ERR('Problem setting time to NTP server')
        return answer


    def clean_remote_server_logs(self, remote_access, oam_ip_dir=None):
        answer = ''
        self.__config['host'] = remote_access['remote']
        self.__config['port'] = remote_access['remote_port']
        self.__config['user'] = remote_access['remote_user']
        self.__config['password'] = remote_access['remote_pwd']
        try:
            if oam_ip_dir:
                cmd = 'sudo ls /var/log/HSS/ | grep %s' % oam_ip_dir
                _DEB(' Executing cmd %s' % cmd)
                answer = self.run_command(cmd, identity = 'remote', full_answer=True)
                if oam_ip_dir in answer:
                    _DEB(' %s directory found.' % oam_ip_dir)
                    cmd = 'sudo ls -l /var/log/HSS/%s | grep log' % oam_ip_dir
                    _DEB(' Executing cmd %s' % cmd)
                    answer = self.run_command(cmd, identity = 'remote', full_answer=True)
                    _DEB(' Answer cmd:%s' % answer)
                    for line in answer.split('\n'):
                        if line:
                            line=line.strip()
                            log_file = line.split()[-1]
                            _DEB(' processing log file:%s' % log_file)
                        else:
                            _DEB(' empty line :%s' % line)
                            continue
                        cmd = 'sudo truncate -s 0 /var/log/HSS/%s/%s' % (oam_ip_dir, log_file)
                        _DEB(' Executing cmd %s' % cmd)
                        answer = self.run_command(cmd, identity = 'remote', full_answer=True)

                else:
                    _ERR(' %s directory NOT found under /var/logs/HSS/' % oam_ip_dir)
            else:
                _DEB(' Cleaning all the remotes logs found.')
                cmd = 'sudo ls /var/log/HSS/'
                _DEB(' Executing cmd %s' % cmd)
                answer = self.run_command(cmd, identity = 'remote', full_answer=True)
                _DEB(' Answer cmd:%s' % answer)
                for dirname in answer.split('\n'):
                    if dirname:
                        dirname=dirname.strip()
                        _DEB(' Cleaning directory %s' % dirname)
                    else:
                        _DEB(' empty dirname:%s' % dirname)
                        continue
                    cmd = 'sudo ls -l /var/log/HSS/%s | grep log' % dirname
                    _DEB(' Executing cmd %s' % cmd)
                    answer = self.run_command(cmd, identity = 'remote', full_answer=True)
                    _DEB(' Answer cmd:%s' % answer)
                    for line in answer.split('\n'):
                        line = hss_utils.st_command.clear_ansi(line)
                        if line:
                            log_file = line.split()[-1]
                            _DEB(' processing log file:%s' % log_file)
                        else:
                            _DEB(' empty line :%s' % line)
                            continue
                        cmd = 'sudo truncate -s 0 /var/log/HSS/%s/%s' % (dirname, log_file)
                        _DEB(' Executing cmd %s' % cmd)
                        answer = self.run_command(cmd, identity = 'remote', full_answer=True)

        except (hss_utils.connection.ConnectionTimeout, hss_utils.connection.ConnectionFailed, OSError) as e:
            _ERR('Problem accessing to the Remote server')
        return

    def collect_remote_server_logs(self, remote_access, oam_ip_dir=None):
        answer = ''
        self.__config['host'] = remote_access['remote']
        self.__config['port'] = remote_access['remote_port']
        self.__config['user'] = remote_access['remote_user']
        self.__config['password'] = remote_access['remote_pwd']
        tar_log_file = None
        try:
            if oam_ip_dir:
                cmd = 'sudo ls /var/log/HSS/ | grep %s' % oam_ip_dir
                _DEB(' Executing cmd %s' % cmd)
                answer = self.run_command(cmd, identity = 'remote', full_answer=True)
                if oam_ip_dir in answer:
                    _DEB(' %s directory found.' % oam_ip_dir)
                    tar_log_file = 'remote_logs_%s.tgz' % oam_ip_dir
                    cmd = 'sudo tar -czf %s /var/log/HSS/%s ' % (tar_log_file, oam_ip_dir)
                    _DEB(' Executing cmd %s' % cmd)
                    answer = self.run_command(cmd, identity = 'remote', timeout=300, full_answer=True)
                    cmd = 'ls -l remote_logs_%s.tgz ' % oam_ip_dir
                    _DEB(' Executing cmd %s' % cmd)
                    answer = self.run_command(cmd, identity = 'remote', full_answer=True)
                    _DEB(' Answer cmd: %s' % answer)

                else:
                    _ERR(' %s directory NOT found under /var/logs/HSS/' % oam_ip_dir)
            else:
                _DEB(' Collecting all the remotes logs found.')
                tar_log_file = 'remote_logs_ALL.tgz'
                cmd = 'sudo tar -czf %s /var/log/HSS' % tar_log_file
                _DEB(' Executing cmd %s' % cmd)
                answer = self.run_command(cmd, identity = 'remote', timeout=300, full_answer=True)
                _DEB(' Answer cmd: %s' % answer)


        except (hss_utils.connection.ConnectionTimeout, hss_utils.connection.ConnectionFailed, OSError) as e:
            _ERR('Problem accessing to Remote Server')
        return tar_log_file


    def start_GT_CBACliss(self, identity='tg_cliss', cliss_ip = '0.0.0.0', port = '122' ,user='hssadministrator', password='hsstest'):
        _DEB('start_GT_CBACliss()')
        identity = 'tg_cliss'
        if self.check_available_connection(identity = identity):
            try:
                _DEB('Using available connection for identity %s' % identity)
                connection = self.get_connection(identity = identity)
                self.run_command('', identity=identity, timeout = 5.0)
                return connection
            except (hss_utils.connection.ConnectionFailedEOF, hss_utils.connection.ConnectionFailedTimeout) as e:
                _DEB('%s connection in wrong state. Recreate it' % identity)
                self.release_connection(identity)

        config = {'host':cliss_ip,'port':port, 'user':user, 'password':password}
        _DEB('Creating new connection for identity %s and config:\n%s' % (identity, config))
        try:
            session_type=hss_utils.connection.session.CBACliss
            new_connection = self.create_connection(config=config, session_type=session_type, identity = identity, force_open=True, timeout=60.0)
        except hss_utils.connection.Unauthorized:
            _ERR('%s connection refused for user %s.' % (identity, config['user']))
        return new_connection

    def tg_run_cliss_command(self, cliss_access, cmd, configure):

        cliss_con = self.start_GT_CBACliss(self, cliss_access['cliss_ip'], port = cliss_access['cliss_port'], user=cliss_access['cliss_user'], password=cliss_access['cliss_pwd'])
        _DEB('Executing Cliss command from TG: %s' % cmd)
        try:
            if configure:
                _DEB('Executing command in configuration mode')
                cmd1 = 'configure'
                answer = self.run_command(cmd1, timeout=60, identity='tg_cliss', full_answer=True, allow_local_execution = False)
                cmd = '%s' % cmd
                _DEB('Executing command %s' % cmd)
                answer = self.run_command(cmd, timeout=60, identity='tg_cliss', full_answer=True, allow_local_execution = False)
                cmd = 'commit'
                answer = self.run_command(cmd, timeout=60, identity='tg_cliss', full_answer=True, allow_local_execution = False)
                if 'ERROR' in answer:
                    raise CommandFailure(answer.replace('\r\n',';'))
                if 'commit' in answer:
                    answer = 'commit successful'
            else:
                answer = self.run_command(cmd, timeout=60, identity='tg_cliss', full_answer=True, allow_local_execution = False)
        except (hss_utils.connection.ConnectionTimeout, hss_utils.connection.ConnectionFailed, OSError) as e:
            _ERR('Problem Executing Cliss command from TG')
        return answer


class TTCN_cli(object):

    def __init__(self, config={}, open = True, owner=None):

        if 'host' not in config.keys():
            raise ValueError('host missing')
        if 'port' not in config.keys():
            raise ValueError('port missing')

        self.__config = config
        self.__owner = owner

        endpoint = hss_utils.connection.telnet.TelnetEndpoint(config)
        self.__channel = hss_utils.connection.telnet.TTCN_TelnetChannel(endpoint, timeout=10.0)
        self.__channel.open()

    @property
    def expect_list(self):    
        return ['TTCN> ']

    @property
    def channel(self):
        return self.__channel


    def close(self):
        self.__channel.close()


    @property
    def stdout(self):
        return self.channel.stdout

    @property
    def owner_running(self):
        if self.__owner:
            return self.__owner.is_owner_running

        return False

    @property
    def owner_id(self):
        if self.__owner:
            return self.__owner.id

        return ''

    @property
    def last_match(self):
        return self.channel.last_match

    def send_line(self, line, expect_list =[]):
        self.channel.write_line(line)

        valid_answer = False
        first_try = True
        while not valid_answer:
            answer = self.channel.expect(expect_list)
            if answer == 0:
                if len(self.stdout.strip()) or line == '':
                    valid_answer = True
                else:
                    _WRN('%s TTCN empty answer. Keep on waiting' % self.owner_id)
                continue
            if answer in [1, 2]:
                if first_try:
                    _WRN('%s Received pexpect.%s' % (self.owner_id,
                                                     ('TIMEOUT' if answer == 1 else 'EOF')))
                    if self.owner_running:
                        _INF('%s Trying to reconnect' % self.owner_id)
                        try:
                            self.__channel.close()
                            self.__channel.open()
                            self.channel.write_line(line)
                            first_try = False
                            continue

                        except Exception as e:
                            _ERR('%s Problem during reconnection: %s' % (self.owner_id,str(e)))
                    valid_answer = True
                else:
                    _ERR('%s Received pexpect.%s after reconnection' % (self.owner_id,
                                                                        ('TIMEOUT' if answer == 1 else 'EOF')))
                    break

        return answer

