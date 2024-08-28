#!/usr/bin/python2.7

import os.path
import time
import re
import subprocess
import hss_utils.rosetta

import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning

from hss_utils.st_command import get_user_credential

from components import get_free_port
from components import get_nic_ip_to_dest_host
from components import get_traffic_mix_file
from components import DEFAULT_LOADPLOTTER_PORT
from .cabinet import *
from shared import *
import shared

# Scenario abstraction
class TestScenario(object):
    def __init__(self, scenario_mode):
        if scenario_mode not in SCENARIO_TYPES:
            raise KeyError(scenario_mode)
        self.__scenario_mode = scenario_mode

        self.__proxies = []
        self.__generators = []
        self.__conkeeper = None

        self.__user_trafficMix = ''
        self.__hss_version = None

        self.__cabinets = []

    @property
    def cabinets(self):
        return self.__cabinets

    @property
    def primary_cabinet(self):
        if len(self.cabinets) > 0:
            if self.cabinets[0].is_GeoRedActive:
                return self.cabinets[0]
            else:
                return self.cabinets[1]

    @property
    def secondary_cabinet(self):
        if len(self.cabinets) > 1:
            if self.cabinets[0].is_GeoRedActive:
                return self.cabinets[1]
            else:
                return self.cabinets[0]


    def add_cabinet(self, cabinet):
        # Update modules in cabinet depending of scenario type
        if self.mode in ['IMS-SLF', 'IMS-R', 'EPC-SLF', 'EPC-R']:
            cabinet.add_module('SLF')

        elif self.mode in ['IMS-SLFr']:
            cabinet.add_module('SLFr')

        # Add cabinet
        self.__cabinets.append(cabinet)

    @property
    def mode(self):
        return self.__scenario_mode

    def add_proxy(self, proxy):
        assert(isinstance(proxy, str))
        self.__proxies.append(proxy)

    @property
    def is_redundant(self):
        return self.mode in ['IMS-R', 'EPC-R']

    @property
    def traffic_type(self):
        if self.mode in ['IMS', 'IMS-SLF', 'IMS-SLFr', 'IMS-R']:
            return 'ISMSDA'
        elif self.mode in ['EPC', 'EPC-SLF', 'EPC-R']:
            return 'ESM'
        elif self.mode == 'WLAN':
            return 'WSM'
        elif self.mode == 'OAM':
            return 'OAM'

    def set_trafficMix_preffix(self, preffix):
        assert(isinstance(preffix, str))
        self.__user_trafficMix = preffix

    def set_hss_version(self, hss_version):
        assert(isinstance(hss_version, str))
        self.__hss_version = hss_version

    @property
    def use_conkeeper(self):
        return self.__conkeeper is None

    def set_conkeeper(self, connection_pair):
        if connection_pair is None:
            self.__conkeeper = (HOSTNAME, DEFAULT_CONKEEPER_PORT)
        else:
            assert(isinstance(connection_pair, str))
            if ':' in connection_pair:
                host = connection_pair.split(':')[0]
                try:
                    port = int(connection_pair.split(':')[1])
                except:
                    _ERR('Invalid port: %s' % connection_pair.split(':')[1])
                    quit_program(CMDLINE_ERROR)
                self.__conkeeper = (host, port)
            else:
                self.__conkeeper = (connection_pair, DEFAULT_CONKEEPER_PORT)

    @property
    def generators(self):
        return self.__generators

    def add_generator(self, generator):
        assert(isinstance(generator, str))
        self.__generators.append(generator)

    @property
    def __conkeeper_cfg(self):
        if self.use_conkeeper:
            return 'conkeeperHost:= %s\nconkkeperPort:= %s\n' % (
                self.__conkeeper[0], self.__conkeeper[1])
        return ''

    @property
    def __proxies_cfg(self):
        cfg = ''
        for proxy in self.__proxies:
            proxy = proxy.split(':')
            if len(proxy) != 4:
                _ERR('Invalid proxy definition: "%s"' % proxy)

            host = proxy[0]
            try:
                port = int(proxy[1])
            except:
                _ERR('Invalid proxy definition: "%s"' % proxy)
            try:
                nc = int(proxy[2])
            except:
                _ERR('Invalid proxy definition: "%s"' % proxy)
            local_ip = proxy[3]

            cfg += 'diaProxy:= "%s":%s:%s:%s\n' % (host, port, nc, local_ip)

        return cfg

    @property
    def __SLFr_present(self):
        for cabinet in self.cabinets:
            if 'SLFr' in cabinet.traffic_modules:
                return True
        return False

    @property
    def config_files(self):
        if self.traffic_type == 'ISMSDA':
            return [os.path.join(shared.BAT_CONFIG_FOLDER, 'traffic_IMS', 'debug_flags.cfg'),
                    os.path.join(shared.BAT_CONFIG_FOLDER, 'traffic_IMS', 'HSS_Traffic.cfg'),
                    os.path.join(shared.BAT_CONFIG_FOLDER, 'traffic_IMS', 'params.cfg')]
        elif self.traffic_type == 'ESM':
            return [os.path.join(shared.BAT_CONFIG_FOLDER, 'traffic_EPC', 'debug_flags.cfg'),
                    os.path.join(shared.BAT_CONFIG_FOLDER, 'traffic_EPC', 'HSS_Traffic.cfg'),
                    os.path.join(shared.BAT_CONFIG_FOLDER, 'traffic_EPC', 'params.cfg')]
        elif self.traffic_type == 'WSM':
            return [os.path.join(shared.BAT_CONFIG_FOLDER, 'traffic_WLAN', 'debug_flags.cfg'),
                    os.path.join(shared.BAT_CONFIG_FOLDER, 'traffic_WLAN', 'HSS_Traffic.cfg'),
                    os.path.join(shared.BAT_CONFIG_FOLDER, 'traffic_WLAN', 'params.cfg')]

        elif self.traffic_type == 'OAM':
            return [os.path.join(shared.BAT_CONFIG_FOLDER, 'traffic_OAM', 'debug_flags.cfg'),
                    os.path.join(shared.BAT_CONFIG_FOLDER, 'traffic_OAM', 'HSS_Traffic.cfg'),
                    os.path.join(shared.BAT_CONFIG_FOLDER, 'traffic_OAM', 'params.cfg')]
        return []

    @property
    def sdg_input_file(self):
        if self.mode in ['IMS', 'IMS-SLF', 'IMS-SLFr','IMS-R']:
            if self.__SLFr_present:
                preffix = 'SLFr'
            else:
                preffix = 'IMS'
            suffix = 'IMS'
        elif self.mode in ['EPC', 'EPC-SLF', 'EPC-R']:
            preffix = 'EPC'
            suffix = 'EPC'
        else:
            preffix = self.mode
            suffix = self.mode
        bat_scenario_dir = os.path.join(
            shared.BAT_CONFIG_FOLDER,
            'traffic_%s' % suffix)

        hss_version = self.primary_cabinet.hss_version if self.__hss_version is None else self.__hss_version

        if hss_version == '':
            header = 'HSS version seems to be unset'
            configured_traffic_mix = None
        else:
            _INF('HSS version is %s' % hss_version)
            header = 'Traffic mix file for %s not found' % hss_version
            configured_traffic_mix = get_traffic_mix_file(hss_version, bat_scenario_dir)

        if self.__user_trafficMix is '':
            if configured_traffic_mix is None:
                _WRN('%s. Using default %s' % (header,('%s%s'% (preffix,DEFAULT_TRAFFICMIX_SUFFIX))))
                return os.path.join(bat_scenario_dir,
                                    '%s%s' % (preffix,DEFAULT_TRAFFICMIX_SUFFIX))

            else:
                _INF('Traffic mix file for %s is %s' % (hss_version,configured_traffic_mix))
                return os.path.join(bat_scenario_dir,
                                    configured_traffic_mix)

        elif configured_traffic_mix != self.__user_trafficMix:
            _WRN('Using traffic mix set by user %s but it should be %s' % (self.__user_trafficMix, configured_traffic_mix))

        return os.path.join(bat_scenario_dir,
                            self.__user_trafficMix)


    @property
    def __cabinet_cfg(self):
        # Primary cabinet config
        cfg = self.primary_cabinet.config_file_contents
        cfg += 'defParam:= q:PRIMARY_HOSTNAME:%s\n' % self.primary_cabinet.name
        # Secondary cabinet if present
        if self.secondary_cabinet is not None:
            cfg += 'defParam:= q:SECONDARY_HOSTNAME:%s\n' % self.secondary_cabinet.name
        # Check cabinet traffic type
        slf_proxy = False
        for cabinet in self.cabinets:
            if ('SLF' in cabinet.traffic_modules) or ('SLFr' in cabinet.traffic_modules):
                slf_proxy = True
                break

        cfg += 'slf_proxy_mode:= %s\n' % ('true' if slf_proxy else 'false')
        return cfg

    @property
    def __redundant_cfg(self):
        cfg = ''
        if self.is_redundant:
            cfg += 'remGroupName:= EXCLUDE_ON_REDUNDANCY\n'
            if self.__conkeeper is not None:
                cfg += 'secvip_dia_tcp:= "%s"\n' % self.secondary_cabinet.get_vip('dia_tcp')
                cfg += 'secvip_oam:= "%s"\n' % self.secondary_cabinet.get_vip('oam')
                cfg += 'secvip_controller:= "%s"\n' % self.secondary_cabinet.get_vip('controller')  
        return cfg

    @property
    def __conkeeper_cfg(self):
        if self.__conkeeper is not None:
            return 'conkeeperHost:= "%s"\nconkeeperPort:= %s\n' % (
                self.__conkeeper[0], self.__conkeeper[1])
        else:
            return ''

    @property
    def config_file_contents(self):
        cfg = ''

        # Check internal config
        if (self.mode in ['IMS', 'IMS-R', 'EPC', 'EPC-R']) and (len(self.__proxies) == 0):
            _ERR('No proxies defined but required')
            quit_program(CMDLINE_ERROR)
        if (self.mode in ['WLAN', 'OAM']) and (len(self.__proxies) > 0):
            _ERR('Proxies defined but not needed')
            quit_program(CMDLINE_ERROR)

        # Set generators
        for generator in self.generators:
            cfg += 'lgen:= "%s"\n' % generator

        cfg += self.__proxies_cfg
        cfg += self.__cabinet_cfg
        if self.mode in ['IMS-R', 'EPC-R']:
            cfg += self.__redundant_cfg
        cfg += self.__conkeeper_cfg

        return cfg 


class ExecutionProperties(object):
    def __init__(self, mc_host, password):
        self.__mc = mc_host
        self.password = password
        self.__mc_port = get_free_port(self.__mc, self.password)
        self.__mode = 'Automatic'
        self.__gui_mode = False
        self.__PTCs = DEFAULT_PTCS

        self.__CPS = None
        self.__CPS_delta_load = None
        self.__CPS_delta_pre = None
        self.__CPS_delta_post = None

        self.__l1 = None
        self.__l2 = None
        self.__l3 = None

        self.__graph_size = None
        self.__load_type = None

        self.__time = None
        self.__range = None
        self.__titansim_timeout = -1

        self.__loadplotter_port = DEFAULT_LOADPLOTTER_PORT
        self.__refresh_plot = 15
        self.__scenario = None

        self.__load_scheduling = []

        self.__user_traffic_scripts = []
        self.__user_disabled_scripts = []
        self.__user_parameters = []
        self.__subscriber_ranges = []
        self.__skip_groups = []
        self.__traffic_groups = []

        self.__file_mask = FILE_MASK

        self.__async = False

    def set_async_mode(self, enabled):
        assert(isinstance(enabled, bool))
        self.__async = enabled

    def set_loadplotter_port(self, port):
        assert(isinstance(port, int))
        self.__loadplotter_port = port

    def set_mc_port(self, port):
        assert(isinstance(port, int))
        self.__mc_port = port

    def set_execution_mode(self, mode):
        assert(mode in ['Automatic', 'Manual', 'Semiautomatic'])
        self.__mode = mode

    @property
    def skipped_groups(self):
        return self.__skip_groups

    def add_skipped_group(self, groupname):
        self.__skip_groups.append(groupname)

    @property
    def traffic_groups(self):
        return self.__traffic_groups

    def add_traffic_group(self, groupname):
        self.__traffic_groups.append(groupname)

    def add_excluded_tc(self, excluded_tc):
        self.__user_disabled_scripts.append(excluded_tc)

    def add_user_tc(self, user_tc):
        self.__user_traffic_scripts.append(user_tc)

    def add_subscriber_range(self, subscriber_range):
        self.__subscriber_ranges.append(subscriber_range)

    def add_user_parameter(self, parameter):
        self.__user_parameters.append(parameter)

    def add_file_mask(self, mask):
        if mask != '':
            self.__file_mask.append(mask)

    def set_gui(self, state):
        assert(isinstance(state, bool))
        self.__gui_mode = state

    def set_running_time(self, time):
        if time == 0:
            self.__time = None
        else:
            self.__time = time

    def set_range_loops(self, loops):
        if loops == 0:
            self.__range = None
        else:
            self.__range = loops

    def set_titansim_timeout(self, timeout):
        self.__titansim_timeout = timeout

    def set_traffic_setting(self, setting_string):
        setting_string = setting_string.split(':')
        try:
            self.__PTCs = int(setting_string[0])
        except:
            pass
        try:
            self.__CPS = int(setting_string[1])
        except:
            pass
        try:
            self.__CPS_delta_load = int(setting_string[2])
        except:
            pass
        try:
            self.__CPS_delta_pre = int(setting_string [3])
        except:
            pass
        try:
            self.__CPS_delta_post = int(setting_string[4])
        except:
            pass

    def set_load_level_setting(self, setting_string):
        setting_string = setting_string.split(':')
        try:
            self.__l1 = int(setting_string[0])
        except:
            pass
        try:
            self.__l2 = int(setting_string[1])
        except:
            pass
        try:
            self.__l3 = int(setting_string[2])
        except:
            pass
        try:
            self.__graph_size = int(setting_string [3])
        except:
            pass
        try:
            self.__load_type = setting_string[4]
        except:
            pass


    def set_scenario(self, scenario):
        self.__scenario = scenario

    @property
    def scenario(self):
        return self.__scenario

    @property
    def PTCs(self):
        return self.__PTCs

    @property
    def mc_host(self):
        return self.__mc

    @property
    def gui_host(self):
        return self.scenario.generators[0]

    def add_schedule(self, schedule):
        self.__load_scheduling.append(schedule)

    @property
    def __user_traffic_scripts_config(self):
        cfg = ''
        for traffic_script in self.__user_traffic_scripts:
            cfg += 'modTc:= %s\n' % traffic_script
        return cfg

    @property
    def __user_disabled_scripts_config(self):
        cfg = ''
        for traffic_script in self.__user_disabled_scripts:
            cfg += 'remTc:= %s\n' % traffic_script
        return cfg

    @property
    def __gui_config(self):
        if self.__gui_mode:
            port = get_free_port(self.gui_host, self.password)
            return '''guiPort:= %s
guiHost:= "%s"
headlessmode:= false
servermode:= false
''' % (port, self.gui_host)
        else:
            return '''headlessmode:= true
servermode:= true
'''

    @property
    def __load_scheduling_config(self):
        cfg = ''
        for schedule in self.__load_scheduling:
            cfg += 'loadSched:= %s\n' % schedule
        return cfg

    @property
    def __loadplotter_config(self):
        cfg = ''
        if self.__scenario.primary_cabinet.is_CNHSS:
            return cfg

        if (self.__graph_size is not None) or (self.__CPS is None):
            cfg += 'loadplotterHost:= "%s"\n' % self.gui_host
            cfg += 'loadplotterPort:= %s\n' % self.__loadplotter_port
            cfg += 'defParam:= q:MEASUREMODE:REMOTE\n'
            if self.__scenario.primary_cabinet:
                if self.__scenario.primary_cabinet.is_TSP:
                    cfg += 'defParam:= q:LOAD_DESTHOSTIP:%s\n' % self.__scenario.primary_cabinet.get_vip('oam')
                else:
                    cfg += 'defParam:= q:LOAD_DESTHOSTIP:%s\n' % self.__scenario.primary_cabinet.get_vip('oam')

                cfg += 'defParam:= q:LOAD_DESTHOSTCONTROLLER:%s\n' % self.__scenario.primary_cabinet.get_vip('controller')
                #cfg += 'defParam:= q:PLATFORM:%s\n' % ('TSP' if self.__scenario.primary_cabinet.is_TSP else 'CBA')
                cfg += 'defParam:= q:LOAD_MEASURETIME:%s\n' % (1 if self.__scenario.primary_cabinet.is_TSP else 5)
                if self.__scenario.primary_cabinet.is_CBA:
                    cfg += 'defParam:= q:LOAD_REG_TYPE:all\n'
                    cfg += 'defParam:= q:CBA_USER:%s\n' % shared.CLISS_USER
                    cfg += 'defParam:= q:CBA_PASSWORD:%s\n' % get_user_credential('hss_cba',shared.CLISS_USER)
            if self.__scenario.secondary_cabinet:
                cfg += 'defParam:= q:LOAD_SEC_DESTHOSTIP:%s\n' % self.__scenario.secondary_cabinet.get_vip('oam')
                cfg += 'defParam:= q:LOAD_SEC_DESTHOSTCONTROLLER:%s\n' % self.__scenario.secondary_cabinet.get_vip('controller')

            if self.__graph_size is not None:
                cfg += 'defParam:= :GRAPH_SCAN_SIZE:%s\n' % self.__graph_size
            else:
                cfg += 'defParam:= :REFRESH_PLOT_TIME:0\n'

            if not self.__gui_mode:
                cfg += 'defParam:= :REFRESH_PLOT_TIME:0\n'

            if self.__CPS is None:
                cfg += 'LoadRegHostName:="%s"\n' % self.gui_host
        return cfg

    @property
    def __async_config(self):
        cfg = ''
        if self.__async:
            cfg += 'defParam:= :PTCSPERLGEN:%s\n' % int(self.__PTCs / len(self.scenario.generators))
            cfg += 'defParam:= :NOTBLOCKING:true\n'
            cfg += 'defParam:= :NUMBEROFENTITIES:50000\n'
            cfg += 'remGroupName:= EXCLUDE_FOR_ASYNC\n'
        return cfg

    @property
    def config_file_contents(self):
        if self.__time and self.__range:
            _ERR('Execution modes -r and -t can not be selected at the same time')
            quit_program(CMDLINE_ERROR)
        if self.__l1 and self.__CPS:
            _ERR('CPS (-z :cps:) and load regulation (-l) can not be used at the same time')
            quit_program(CMDLINE_ERROR)
        cfg = (self.__gui_config +
               self.__loadplotter_config +
               self.__load_scheduling_config +
               self.__user_traffic_scripts_config +
               self.__user_disabled_scripts_config +
               self.__async_config)

        cfg += 'mcPort:= %s\n' % self.__mc_port
        if self.__time is not None:
            cfg += 'Time:= %s.0\n' % self.__time
        if self.__range is not None:
            cfg += 'Range:= %s\n' % self.__range
        if self.__l1 is not None:
            cfg += 'LoadTarget:= %s.0\n' % self.__l1
        if self.__l2 is not None:
            cfg += 'PreLoadTarget:= %s.0\n' % self.__l2
        if self.__l3 is not None:
            cfg += 'PostLoadTarget:= %s.0\n' % self.__l3
        if self.__load_type is not None:
            cfg += 'LoadRegType:= %s\n' % self.__load_type
        if self.__CPS_delta_load is not None:
            cfg += 'cpsDeltaLoad:= %s.0\n' % self.__CPS_delta_load
        if self.__CPS_delta_pre is not None:
            cfg += 'cpsDeltaPre:= %s.0\n' % self.__CPS_delta_pre
        if self.__CPS_delta_post is not None:
            cfg += 'cpsDeltaPost:= %s.0\n' % self.__CPS_delta_post
        if self.__CPS is not None:
            cfg += 'numOfCps:= %s.0\n' % self.__CPS
        if self.__PTCs is not None:
            cfg += 'numOfPTCs:= %s\n' % self.__PTCs

        cfg += 'manualControl:= %s\n' % ('false' if self.__mode == 'Automatic' else 'true')

        for group in self.__skip_groups:
            cfg += 'remGroupName:= %s\n' % group

        for group in self.__traffic_groups:
            cfg += 'trafficGroupName:= %s\n' % group

        for subscriber_range in self.__subscriber_ranges:
            cfg += 'sub_range:= %s\n' % subscriber_range

        for user_parameter in self.__user_parameters:
            cfg += 'defParam:= %s\n' % user_parameter

        cfg += 'LogFile:= "%r-%n-%e.%h.log"\n'
        cfg += 'ConsoleMask:= LOG_NOTHING | TTCN_ACTION\n'
        cfg += 'FileMask:= %s\n' % '|'.join(self.__file_mask)
        cfg += 'defParam:= :NUMHCS:%s\n' % shared.NUMHCS
        return cfg


def patch_config(raw_config):
    patched_config = ''
    for line in raw_config.splitlines():
        clean_line = line.strip()

        # Search SPECIAL lines to comment them
        if clean_line in [
            '[INCLUDE]',
            '"params.cfg"',
            '"debug_flags.cfg"',
            '"deployment.cfg"',
            '"scenario.cfg"']:
            patched_config += '//%s\n' % line
            continue

        # Skip clear lines and comments
        if (clean_line.startswith('#')  or clean_line.startswith('//')):
            continue

        # Change some options
        if clean_line.startswith('tsp_EPTF_GUI_Main_Window_Title'):
            patched_config += 'tsp_EPTF_GUI_Main_Window_Title := "HSS traffic <> %s"\n' % time.asctime()
            continue

        patched_config += '%s\n' % line

    return patched_config


def build_config_file(user_options):
    # Configure cabinet(s)
    vip_info = parse_vip_parameter(user_options.vip_data)
    if user_options.node_type != 'CNHSS' and not validate_ip(vip_info[0],IPv6=False):
        _ERR ('OAM ip shall be always an IPv4 address')
        quit_program(CMDLINE_ERROR)

    if user_options.node_type == 'CNHSS':
        cabinet = Cabinet_CNHSS(user_options.eccd_type,user_options.access_config,
                               user_options.appid, user_options.scenario,
                               user_options.modules,IPv6=user_options.ipv6)

    else:
        cabinet = eval("Cabinet_%s(vip_info[0], user_options.scenario, user_options.modules, zone=1, IPv6=user_options.ipv6)" % user_options.node_type)

    for index, vip in enumerate(parse_vip_parameter(user_options.vip_data)):
        cabinet.set_vip(REQUIRED_IP[index], vip)


    for blade_id in user_options.dicos.split():
        cabinet.add_filter_blade(blade_id)

    # Configure secondary cabinet

    if user_options.sec_traffic_vip:
        vip_info = user_options.sec_traffic_vip.split(':')
        sec_cabinet = Cabinet_TSP(vip_info[0], user_options.scenario, user_options.modules, zone=2)

        for index, vip in enumerate(user_options.sec_traffic_vip.split(':')):
            sec_cabinet.set_vip(REQUIRED_IP[index], vip)

    else:
        sec_cabinet = None

    # Configure scenario
    scenario = TestScenario(user_options.scenario)
    scenario.add_cabinet(cabinet)
    if sec_cabinet:
        scenario.add_cabinet(sec_cabinet)

    if user_options.conkeeper != '':
        scenario.set_conkeeper(user_options.conkeeper)

    if user_options.trafficmix_preffix:
        scenario.set_trafficMix_preffix(user_options.trafficmix_preffix)

    if user_options.hss_version:
        scenario.set_hss_version(user_options.hss_version)

    execution = ExecutionProperties(user_options.mc_host, user_options.password)
    execution.set_scenario(scenario)
    execution.set_gui(user_options.gui_mode)
    if user_options.mc_port:
        execution.set_mc_port(user_options.mc_port)

    execution.set_loadplotter_port(user_options.loadplotter_port)
    execution.set_running_time(user_options.time)
    execution.set_range_loops(user_options.range_loops)
    execution.set_titansim_timeout(user_options.titansim_timeout)
    execution.set_traffic_setting(user_options.traf_settings)
    execution.set_load_level_setting(user_options.load_parameters)
    execution.set_async_mode(user_options.async_mode)

    if user_options.generators is None:
        number_of_generators = 1 + execution.PTCs / (RATIO_PTC_ASYNC if user_options.async_mode else RATIO_PTC_SYNC)
        if number_of_generators > MAX_NUM_LGEN:
            number_of_generators = MAX_NUM_LGEN

        for index in range(0,number_of_generators):
            scenario.add_generator(HOSTNAME)

    else:
        for generator in user_options.generators.split():
            scenario.add_generator(generator)

        shared.set_numhcs(len(set(user_options.generators.split())))

    if user_options.scenario in ['IMS','IMS-SLF', 'IMS-SLFr', 'EPC', 'EPC-SLF', 'IMS-R','EPC-R']:
        if user_options.scenario in ['IMS','IMS-SLF', 'IMS-SLFr', 'IMS-R']:
            upper=8999
            lower=8000
        else:
            upper=9999
            lower=9000

        offset = user_options.dia_port_offset
        if user_options.proxies is None:
            scenario.add_proxy('%s:%s:1:' % (HOSTNAME, get_free_port(HOSTNAME, user_options.password,upper=upper, lower=lower, offset=offset)))
        else:
            for proxy in user_options.proxies.split():

                elements = proxy.count(':')
                if elements == 0:
                    proxy += ':%s:1:' % get_free_port(proxy, user_options.password,upper=upper, lower=lower, offset=offset)

                elif elements == 1:
                    data = proxy.split(':')
                    if data[0] == '' and data[1] == '':
                        data[0] = HOSTNAME
                        data[1] = '%s' % get_free_port(HOSTNAME, user_options.password,upper=upper, lower=lower, offset=offset)
                        data.append('1')
                        data.append('')
                        proxy = ':'.join([str(element) for element in data])

                    elif data[0] == '':
                        data[0] = HOSTNAME
                        data.append('1')
                        data.append('')
                        proxy = ':'.join([str(element) for element in data])

                    elif data[1] == '':
                        data[1] = '%s' % get_free_port(HOSTNAME, user_options.password,upper=upper, lower=lower, offset=offset)
                        data.append('1')
                        data.append('')
                        proxy = ':'.join([str(element) for element in data])

                    else:
                        proxy += ':0:'

                elif elements in [2, 3]:
                    data = proxy.split(':')

                    if data[0] == '':
                        data[0] = HOSTNAME

                    if data[1] == '':
                        data[1] = '%s' % get_free_port(HOSTNAME, user_options.password,upper=upper, lower=lower, offset=offset)

                    if data[2] == '':
                        data[2] = 1

                    if elements == 2:
                        data.append('')

                    proxy = ':'.join([str(element) for element in data])

                scenario.add_proxy(proxy)

                if user_options.dia_port_offset is not None:
                    offset += 10


    if user_options.file_mask:
        execution.add_file_mask(user_options.file_mask)

    for schedule in user_options.load_schemes.split():
        execution.add_schedule(schedule)

    for remove_groups in user_options.remove_groups:
        for group in remove_groups.split():
            execution.add_skipped_group(group)

    for traffic_groups in user_options.traffic_groups:
        for group in traffic_groups.split():
            execution.add_traffic_group(group)

    common_groups = set(execution.skipped_groups).intersection(execution.traffic_groups)

    if common_groups:
        _ERR('Group names in --set-traffic-group (%s) are not allowed in -B' % ' '.join(common_groups))
        quit_program(CMDLINE_ERROR)


    for subs_ranges in user_options.subs_ranges:
        for subscriber_range in subs_ranges.split():
            execution.add_subscriber_range(subscriber_range)

    if user_options.scenario in ['EPC', 'EPC-SLF', 'EPC-R']:
        dest_host = cabinet.get_vip('dia_sctp')
        ip = get_nic_ip_to_dest_host(dest_host, scenario.generators[0], IPv6 = user_options.ipv6)
        if ip:
            _INF('DIA_LOCAL_IP found by application %s' % ip)
            execution.add_user_parameter('q:DIA_LOCAL_IP:%s' % ip)

    dest_host = cabinet.get_vip('dia_tcp')
    ip = get_nic_ip_to_dest_host(dest_host, scenario.generators[0], IPv6 = user_options.ipv6)
    if ip:
        _INF('DIA_TCP_LOCAL_IP found by application %s' % ip)
        execution.add_user_parameter('q:DIA_TCP_LOCAL_IP:%s' % ip)

    if user_options.scenario in ['EPC']:
        dest_host = cabinet.get_vip('udm')
        if dest_host not in ['0.0.0.0','0:0']:
            ip = get_nic_ip_to_dest_host(dest_host, scenario.generators[0], IPv6 = user_options.ipv6)
            if ip:
                _INF('UDM_LOCAL_IP found by application %s' % ip)
                execution.add_user_parameter('q:UDM_LOCAL_IP:%s' % ip)

    for extra_parameters in user_options.extra_parameters:
        for parameter in extra_parameters.split():
            execution.add_user_parameter(parameter)

    for disabled_scripts in user_options.disabled_scripts:
        for script in disabled_scripts.split():
            execution.add_excluded_tc(script)

    for set_traffic_mix in user_options.set_traffic_mix:
        for script in set_traffic_mix.split():
            execution.add_user_tc(script)

    add_trafficmix = False
    for add_traffic_mix in user_options.add_traffic_mix:
        for script in add_traffic_mix.split():
            add_trafficmix = True
            execution.add_user_tc(script)

    if user_options.force_manual:
        execution.set_execution_mode('Manual')
    elif user_options.mode_automatic:
        execution.set_execution_mode('Automatic')
    elif user_options.mode_semiautomatic:
        execution.set_execution_mode('Semiautomatic')
    elif user_options.mode_manual:
        execution.set_execution_mode('Manual')

    # Dump config into file
    fd = open(CONFIG_INPUT_FILE_FOR_SDG, 'w')
    fd.write(scenario.config_file_contents)
    fd.write(execution.config_file_contents)
    fd.close()

    # Prepare for Scenario Deploy Generator call
    sdg_program = SCENARIO_GENERATOR

    # Command for generation
    if (user_options.set_traffic_mix or user_options.traffic_groups):
        cmd = '%s -i %s -c %s -t %s -cfg_path %s -s> scenarioGenerator_result.txt 2>&1' % (
            sdg_program,
            scenario.sdg_input_file,
            CONFIG_INPUT_FILE_FOR_SDG,
            scenario.traffic_type,
            shared.BAT_CONFIG_FOLDER)
    else:
        cmd = '%s -i %s -c %s -t %s -cfg_path %s> scenarioGenerator_result.txt 2>&1' % (
            sdg_program,
            scenario.sdg_input_file,
            CONFIG_INPUT_FILE_FOR_SDG,
            scenario.traffic_type,
            shared.BAT_CONFIG_FOLDER)

    # Run command
    try:
        output = subprocess.check_output(cmd, shell=True)
    except Exception as e:
        _ERR('Scenario deploy generator failed!')
        _ERR('Cause: %s' % str(e))
        _WRN('Execute "cat scenarioGenerator_result.txt" for more information')
        quit_program(CMDLINE_ERROR)

    # Append config files to deplyment cfg file
    deployment_config = ''
    cat_files = [DEPLOYMENT_OUTPUT_FILE]
    for filename in scenario.config_files:
        cat_files.append(filename)
    cat_files.append('scenario.cfg')
    for filename in cat_files:
        fd = open(filename, 'r')
        deployment_config += fd.read()
        fd.close()

    # Remove unused lines
    deployment_config = patch_config(deployment_config)
    config_file = user_options.output_config_file if user_options.output_config_file else DEFAULT_CONFIG_FILE
    config_file = hss_utils.st_command.real_path(config_file)
    fd = open(config_file, 'w')
    fd.write(deployment_config)
    fd.close()

    return config_file


def get_BAT_config(config_file):
    cfg = quick_config_parser(config_file)
    BAT_config = {}
    BAT_config.update({'primary_cabinet': cfg.get('PRIMARY_HOSTNAME', None)})
    BAT_config.update({'secondary_cabinet': cfg.get('SECONDARY_HOSTNAME', None)})
    BAT_config.update({'conkeeper': parse_host_definition(cfg.get('conkeeperHost', None))})
    BAT_config.update({'tcp_port': cfg.get('TCPPORT', None)})

    BAT_config.update({'manual_control': cfg.get('MANUALCONTROL', None)})
    BAT_config['execution_mode'] = 'Manual' if BAT_config['manual_control'] else 'Automatic'

    BAT_config.update({'loadplotter': parse_host_definition(cfg.get('loadplotterHost', None))})
    BAT_config.update({'asynchronous': cfg.get('NOTBLOCKING', False)})

    generators = None

    for key in cfg.keys():
        if key.endswith('_HostList'):
            generators = parse_list_definition(cfg.get(key, None))

    if generators:
        BAT_config.update({'generators': generators})

    data = find_diaproxy_list(config_file)
    diameter_proxies = []
    for proxy in data:
        diameter_proxies.append((proxy[0], int(proxy[1]), int(proxy[2]), proxy[3] ))

    if diameter_proxies:
        BAT_config.update({'diaproxies': diameter_proxies})

    BAT_config.update({'headless_mode': cfg.get('HEADLESSMODE', None)})
    if not BAT_config['headless_mode']:
        BAT_config.update({
                'gui_mode': True,
                'port_gui': cfg.get('tsp_xtdp_listen_port', None),
                'gui_host': generators[0]})
    else:
        BAT_config['gui_mode'] = False

    # Additional config (used in LOGGING)
    BAT_config.update({'layer': cfg.get('LAYER_SCENARIO', False)})
    if BAT_config['layer']:
        BAT_config.update({'external_db': cfg.get('SUT_LDAP_IP', 'unknown')})

    BAT_config.update({'cli_port':
                           cfg.get('CLI_TELNET_PORTNUM',
                                   None)})
    BAT_config.update({'cli_prompt':
                           cfg.get('*.EPTF_CLI_TELNET_PCO.CTRL_SERVER_PROMPT',
                                   None)})
    BAT_config.update({'cli_nologin':
                           cfg.get('*.EPTF_CLI_TELNET_PCO.CTRL_LOGIN_SKIPPED',
                                   None)})

    # Detect scenario type
    if 'tsp_use_ISMSDA_Stack' in cfg.keys():
        BAT_config['scenario_type'] = 'ISMSDA'
    elif 'tsp_use_ESM_Stack' in cfg.keys():
        BAT_config['scenario_type'] = 'ESM'
    elif 'tsp_use_OAM_Stack' in cfg.keys():
        BAT_config['scenario_type'] = 'OAM'
    else:
        BAT_config['scenario_type'] = 'undefined/WSM'

    BAT_config.update({'slf': cfg.get('SLF_PROXY_MODE', False)})
    BAT_config.update({'diameter_server_sctp': cfg.get('SUT_DIAMETER_SCTP', '')})
    BAT_config.update({'diameter_server_tcp': cfg.get('SUT_DIAMETER_TCP', '')})
    BAT_config.update({'diameter_server_port': cfg.get('SUT_DIAMETER_PORT', '')})
    BAT_config.update({'sec_diameter_server_tcp': cfg.get('SUT_SEC_DIAMETER_TCP', '')})
    BAT_config.update({'dia_local_ip': cfg.get('DIA_LOCAL_IP', '')}) 
    BAT_config.update({'originhostoffset': cfg.get('ORIGINHOSTOFFSET',0)})

    BAT_config.update({'node_type': cfg.get('NODE_TYPE','')})
    BAT_config.update({'cnhss_appid': cfg.get('CNHSS_APPID','')})

    return BAT_config


# It does not support values with more than one line long
def quick_config_parser(filename):
    cfg = {}
    fd = open(filename, 'r')
    for line in fd.readlines():
        # Clean line
        line = line.strip()
        # Remove comments
        if ((line == '') or line.startswith('//') or line.startswith('#')):
            continue
        # "var := value" pair found!
        if ':=' in line:
            variable = line.split(':=')[0].strip()
            value = ':='.join(line.split(':=')[1:]).strip()
            # Remove ';' if found
            if value.endswith(';'):
                value = value[:-1].strip()
            # Remove inline comments
            if '//' in value:
                value = value[:value.index('//')].strip()
            # Convert strings to python strings
            if value.startswith('"') and value.endswith('"'):
                value = eval(value)
            # Convert booleans to python booleans
            elif value == 'true':
                value = True
            elif value == 'false':
                value = False
            # Convert to integer or float if possible
            else:
                try:
                    value = int(value)
                except:
                    try:
                        value = float(value)
                    except:
                        pass
            cfg[variable] = value
    fd.close()
    return cfg

# Parse {active:=true,host:=XXX,port:=XXXX} strings
def parse_host_definition(definition):
    if definition is None:
        return None
    assert(definition.startswith('{') and definition.endswith('}'))
    definition = definition[1:-1]
    definition = definition.split(',')
    if 'active:=false' in definition:
        return None
    host = definition[1].split(':=')[1]
    port = definition[2].split(':=')[1]
    host = host.replace('"', '')
    port = int(port)
    return (host, port)


# Parse {"element1","element2",...,"elementN"} strings
def parse_list_definition(definition):
    if definition is None:
        return []
    assert(definition.startswith('{') and definition.endswith('}'))
    definition = definition[1:-1]
    raw_list = definition.split(',')
    parsed = []
    for element in raw_list:
        parsed.append(element.replace('"', ''))
    return parsed

def find_diaproxy_list(filename):
    data = []
    regex = re.compile(r".+hostname:=\"(.+)\", listeningPort:=\"(.+)\", connections_number:=(\d+), local_ip:=\"(.*)\"}")
    fd = open(filename, 'r')
    for line in fd.readlines():
        # Clean line
        line = line.strip()
        # Remove comments
        if ((line == '') or line.startswith('//') or line.startswith('#')):
            continue

        res = regex.match(line)
        if res:
            data.append(res.groups())

    fd.close()
    return data
