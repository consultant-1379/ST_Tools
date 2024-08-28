#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.spawn import find_executable
import os
CWD = os.getcwd()
import os.path
import sys
import getpass
import subprocess
import atexit
import socket
HOSTNAME = socket.gethostname()
import hss_utils.rosetta.services

import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning


EXIT_CODE = 0    
RUNNING_COMPONENTS=[]
def quit_program(exit_code):    
    global EXIT_CODE
    global RUNNING_COMPONENTS
    _INF('Collecting logs...')
    for component in reversed(RUNNING_COMPONENTS):
        try:
            component.kill()

        except KeyboardInterrupt:
            _WRN('Be patient!!!.......I know you want me to finish')

    EXIT_CODE = exit_code
    _DEB('Exit code: %s' % EXIT_ERRORS[exit_code])
    sys.exit(EXIT_CODE)

# Exit status
CMDLINE_ERROR = 1
CONNECTION_ERROR = 10
CONFIGURATION_ERROR = 11
TTCNVER_ERROR = 12
CREATEDIR_ERROR = 13
CHANGEDIR_ERROR = 14
TRANSFER_ERROR = 15
GUI_ERROR = 20
LOADPLOTTER_ERROR = 21
CONKEEPER_ERROR = 22
DIAPROXY_ERROR = 23
HC_ERROR = 24
MC_ERROR = 25
TTCNLIC_ERROR = 31
CONFIG_ERROR = 32
ROSETTA_ERROR = 45
USER_CANCEL = 40

EXIT_ERRORS =  {
0: 'Success',
1: "Command line error",
10: "Connection error",
11: "Configuration error",
12: "Set TTCN version error",
13: "Create directory error",
14: "Change directory error",
15: "Transfering file error",
20: "GUI error",
21: "LoadPlotter error",
22: "Conkepper error",
23: "Diaproxy error",
24: "HC error",
25: "MC error",
31: "TTCN license error",
32: "Configuration error",
40: "Execution cancel by user",
45: "Rosetta error",
50: "Source code error"
}

def get_exit_status():
    exit_status = '''\
    EXIT STATUS
'''
    for key in sorted(EXIT_ERRORS):
        exit_status += '\t%s\t%s\n' % (key, EXIT_ERRORS[key])

    return exit_status

# Some default values
FILE_MASK = ['USER', 'ACTION', 'PARALLEL']

DEFAULT_TRAFFICMIX_SUFFIX = '_TrafficMix.cfg'
DEFAULT_CONFIG_FILE='HSSBatTitanSim.cfg'

SCENARIO_GENERATOR = find_executable('scenarioDeployGenerator')
BAT_CONFIG_FOLDER = os.environ['BAT_CFG_PATH']
DEFAULT_ALIAS_FILE = '%s/gui_xml_files/alias.json' % BAT_CONFIG_FOLDER
XUL_PATH = '%s/gui_xml_files/HSSTraffic.xul' % BAT_CONFIG_FOLDER

def set_bat_config_folder(value):
    global BAT_CONFIG_FOLDER
    global DEFAULT_ALIAS_FILE
    global XUL_PATH

    BAT_CONFIG_FOLDER = value
    DEFAULT_ALIAS_FILE = '%s/gui_xml_files/alias.json' % BAT_CONFIG_FOLDER
    XUL_PATH = '%s/gui_xml_files/HSSTraffic.xul' % BAT_CONFIG_FOLDER


CONFIG_INPUT_FILE_FOR_SDG = 'HSSBat_config.data'
DEPLOYMENT_OUTPUT_FILE = 'deployment.cfg'

DEFAULT_PTCS = 100
SCENARIO_TYPES = [None, 'IMS', 'IMS-SLF','IMS-SLFr','IMS-R', 'EPC', 'EPC-SLF', 'EPC-R', 'WLAN', 'OAM']

TTCN_PROMPT = 'TTCN> '
#TTCN_PROXY_CMD = find_executable('ttcn_proxy')
#TTCN_MONITOR_CMD = find_executable('ttcn_monitor')
#DEFAULT_CLI_PROXY_PORT = 7777
#DEFAULT_MONITOR_UDP_PORT = 8888

REQUESTED_ALIASES = {
    'ISMSDA': ['default', 'alias_IMS'],
    'ESM' : ['default', 'alias_EPC'],
    'OAM' : ['default', 'alias_OAM']
}

TRAFFIC_TYPES = ['CBA', 'TSP', 'SLF', 'SLFr', 'AVG', 'HLR']

REQUIRED_IP= ['oam','dia_tcp','dia_sctp','radius',
              'controller', 'extdb','soap','udm','soap_ldap','secdia_tcp']


DEFAULT_LOADPLOTTER_PORT = 5555
DEFAULT_CONKEEPER_PORT = 4444

EXECUTION_PATH = '/opt/hss/%s/HSSBatTitansim_%s' % (getpass.getuser(), os.getpid())
def set_tmp_path(tmp_path):
    global EXECUTION_PATH
    EXECUTION_PATH = tmp_path

def set_cwd(tmp_path):
    global CWD
    CWD = tmp_path

RATIO_PTC_SYNC = 150
RATIO_PTC_ASYNC = 50
MAX_NUM_LGEN = 5

TTCN_VERSION = ''
def set_ttcn_version(ttcn_version):
    global TTCN_VERSION
    TTCN_VERSION = ttcn_version

CLISS_USER ='com-emergency'
def set_cliss_user(cliss_user):
    global CLISS_USER
    CLISS_USER = cliss_user

JAVA = None
def set_java_path(java_path):
    global JAVA
    if java_path is None:
        JAVA = None
        return
    if not os.path.isdir(java_path):
        ERR('JAVA path not found "%s"' % java_path)
        quit_program(CMDLINE_ERROR)
    JAVA = java_path


NODENAME = 'jambala'
def set_nodename(nodename):
    global NODENAME
    NODENAME = nodename

NUMHCS = 1
def set_numhcs(numhcs):
    global NUMHCS
    NUMHCS = numhcs

ENV_CONFIG = None
def get_env_data():
    global ENV_CONFIG
    if ENV_CONFIG is None:
        _INF('Using rosetta for getting enviroment info')
        env, config = hss_utils.rosetta.services.get_env_for_localhost()
        _INF('Environment  : %s' % env)
        ENV_CONFIG = config

    return ENV_CONFIG

class ZombieCollector(object):
    def __init__(self):
        self.__pids = []

    def annotate_execution(self, pid=None):

        if pid is not None:
            self.__pids.append(pid)

    def clean_all(self):
        if len(self.__pids):
            _INF('Cleaning zombie process...')

            for pid in self.__pids:
                cmd = ['kill', '-KILL', str(pid)]
                proc = subprocess.Popen(cmd,
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
                stdout_value, stderr_value = proc.communicate() 

                if stderr_value is not None:
                    _DEB('Killing result error %s...' % (stderr_value))
                else:
                    _WRN('Zombie process found with pid=%s ' % (pid))

            _DEB('Exit code: %s (%s)' % (EXIT_CODE, EXIT_ERRORS.get(EXIT_CODE, 'unknown error code')))

ZOMBIE_COLLECTOR = ZombieCollector()
atexit.register(ZOMBIE_COLLECTOR.clean_all)

