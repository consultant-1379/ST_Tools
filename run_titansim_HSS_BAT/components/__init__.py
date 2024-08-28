#!/usr/bin/env python

import hss_utils.st_command
import ntpath
from shared import *

class RemoteFolderError(Exception):
    def __init__(self, path, err_code):
        self.__path = path
        self.__err_code = err_code

    def __str__(self):
        return 'Error (%s) handling folder "%s"' % (self.__err_code,
                                                    self.__path)
    @property
    def error_code(self):
        return self.__err_code


class ConnectionError(Exception):
    def __init__(self, remote_host):
        self.__remote_host = remote_host

    def __str__(self):
        return 'Error connecting to "%s"' % (self.__remote_host)

    @property
    def error_code(self):
        return self.__err_code

# Get available TCP port on "machine"
def get_free_port(machine, password=None, upper=65536,lower=11000, offset=None):

    if offset is not None:
        for port in range(lower+offset,lower+offset+10):
            cmd = 'run_command_node is_port_free %s' % port
            stdout_value, returncode = hss_utils.st_command.execute_cmd(cmd)
            if returncode == 0:
                return port

    cmd = 'run_command_node get_free_port -u %s -l %s --node  %s%s' % (upper, lower, machine, ('' if password is None else (' --password %s ' % password)))
    stdout_value, returncode = hss_utils.st_command.execute_cmd(cmd)
    if returncode == 0:
        return int(stdout_value[:-1])

def get_nic_ip_to_dest_host(dest_host, machine, IPv6 = False, password=None):
    cmd = 'run_command_node get_nic_ip_to_dest_host %s --node  %s%s%s' % (dest_host, machine,
                                                                        (' -6' if IPv6 else ''),
                                                                        ('' if password is None else (' --password %s ' % password)))
    stdout_value, returncode = hss_utils.st_command.execute_cmd(cmd)
    if returncode == 0:
        return stdout_value[:-1]


def get_traffic_mix_file(hss_version, cfg_path):
    if hss_version.count('/')> 1:
        hss_version = hss_version[:hss_version.rfind('/')]

    cmd = 'grep -r "%s" %s' % (hss_version, cfg_path)
    stdout_value, returncode = hss_utils.st_command.execute_cmd(cmd)
    if returncode == 0:
        return ntpath.basename(stdout_value[:-1].split(':')[0])