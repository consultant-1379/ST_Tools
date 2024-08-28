#!/usr/bin/env python
# -*- mode=python; coding: utf-8 -*-
#

import hss_utils.rosetta
import json
import socket
import os.path
import traceback
import sys
import ipaddress
from ipaddress import IPv4Address, IPv6Address
from e3utils.e3types.node.ericsson import Cudb, Hlr, Hss, Eccd
from e3utils.e3types.node.tool import Tool
try:
    from e3utils.clients.rosetta import Rosetta
    from e3utils.exceptions import ElementNotExistinRosetta
    from e3utils.e3types.basic import Credentials
    _ROSETTA_AVAILABLE_ = True
except ImportError as e:
    print('Cannot import e3utils: %s' % e)
    print('Rosetta access will be disabled')
    _ROSETTA_AVAILABLE_ = False
    class ElementNotExistinRosetta(Exception):
        pass


HOSTNAME = socket.gethostname()

import e3utils.log as logging
_DEB = logging.internal_debug
_WRN = logging.internal_warning
_ERR = logging.internal_error
_INF = logging.internal_info

_ACCESS_URL_ = None
_ACCESS_TOKEN_ = None


def set_rosetta_token(new_token):
    global _ACCESS_TOKEN_
    _ACCESS_TOKEN_ = new_token


def set_rosetta_api_url(new_url):
    global _ACCESS_URL_
    _ACCESS_URL_ = new_url

class UnKonowmNode(Exception):
    def __init__(self, message='Node type unknowm'):
        self.__err = message

    def __str__(self):
        return '%s' % self.__err

def get_single_ip(input,IPv6=False):
    if isinstance(input, unicode) or isinstance(input, str):
        return input

    if isinstance(input, list):
        ip_list = [ipaddress.ip_address(unicode(address)) for address in input]

        filtered_list = [str(add) for add in list( filter((lambda x:isinstance(x,IPv6Address if IPv6 else IPv4Address)), ip_list))]
        if filtered_list:
            return filtered_list[0]

class STConfig(object):
    def __init__(self, config={}):
        assert(isinstance(config, dict))
        self.__config = config
        self.__display_ipv6 = False

    @property
    def display_ipv6(self):
        return self.__display_ipv6

    @display_ipv6.setter
    def display_ipv6(self, display_ipv6):
        self.__display_ipv6 = display_ipv6

    @property
    def raw(self):
        return self.__config

    def _generators_names_(self, only_active=False):
        gens = []
        for generator in self.__config.get('generators', []):
            if not isinstance(generator, dict):
                continue
            if 'name' not in generator.keys():
                continue
            if not generator.get('active', True) and only_active:
                continue
            gens.append(generator['name'])
        return gens

    @property
    def generators(self):
        return self._generators_names_()

    @property
    def active_generators(self):
        return self._generators_names_(only_active=True)

    @property
    def is_cloud(self):
        return  len(self.raw['eccds']) > 0


    def get_single_ip(self,input,IPv6=False):
        if isinstance(input, unicode) or isinstance(input, str):
            return input

        if isinstance(input, list):
            ip_list = [ipaddress.ip_address(unicode(address)) for address in input]

            filtered_list = [str(add) for add in list( filter((lambda x:isinstance(x,IPv6Address if IPv6 else IPv4Address)), ip_list))]
            if filtered_list:
                return filtered_list[0]


    def get_cabinet_name(self,cabinet=0,IPv6=False):
        try:
            return self.raw['cabinets'][cabinet]['name']
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('cabinet name')

    def get_cabinet_type(self,cabinet=0,IPv6=False):
        try:
            return self.raw['cabinets'][cabinet]['type']
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('cabinet type')

    def get_cabinet_cc1(self,cabinet=0,IPv6=False):
        try:
            return self.get_single_ip(self.raw['cabinets'][cabinet]['cc1'],IPv6)
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('cabinet cc1')

    def get_cabinet_cc2(self,cabinet=0,IPv6=False):
        try:
            return self.get_single_ip(self.raw['cabinets'][cabinet]['cc2'],IPv6)
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('cabinet cc2')

    def get_cabinet_map1(self,cabinet=0,IPv6=False):
        try:
            return self.get_single_ip(self.raw['cabinets'][cabinet]['map1'],IPv6)
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('cabinet map1')

    def get_cabinet_map2(self,cabinet=0,IPv6=False):
        try:
            return self.get_single_ip(self.raw['cabinets'][cabinet]['map2'],IPv6)
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('cabinet map2')

    def get_cabinet_oam_vip(self,cabinet=0,IPv6=False):
        try:
            return self.get_single_ip(self.raw['cabinets'][cabinet]['oam_vip'],IPv6)
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('cabinet oam_vip')

    def get_cabinet_http_vip(self,cabinet=0,IPv6=False):
        try:
            return self.get_single_ip(self.raw['cabinets'][cabinet]['http_vip'],IPv6)
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('cabinet http_vip')

    def get_cabinet_vip_raddia(self,cabinet=0,IPv6=False):
        try:
            return self.get_single_ip(self.raw['cabinets'][cabinet]['vip_raddia'],IPv6)
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('cabinet vip_raddia')

    def get_cabinet_vip_diasctp(self,cabinet=0,IPv6=False):
        try:
            return self.get_single_ip(self.raw['cabinets'][cabinet]['vip_diasctp'],IPv6)
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('cabinet vip_diasctp')

    def get_cabinet_ldap_vip(self,cabinet=0,IPv6=False):
        try:
            return self.get_single_ip(self.raw['cabinets'][cabinet]['ldap_vip'],IPv6)
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('cabinet ldap_vip')

    def get_cabinet_scxb(self,cabinet=0,IPv6=False):
        try:
            return self.get_single_ip(self.raw['cabinets'][cabinet]['scxb'],IPv6)
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('cabinet scxb')

    def get_extdb_oam_ip(self,extdb=0,extdb_type='GTLA',IPv6=False):
        try:
            _DEB('Getting OAM ip for extdb %s and index %d' % (extdb_type, extdb))
            extdb_info = self.raw['extdbs']
            _DEB('EXTDB_INFO:%s' % extdb_info)
            extdb_item = extdb_info[extdb]
            _DEB('EXTDB_ITEM_INFO by index:%s' % extdb_item)
            if extdb_type == extdb_item['type']:
                return self.get_single_ip(extdb_item['oam'],IPv6)
            return self.get_single_ip(self.raw['extdbs'][extdb]['oam'],IPv6)
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('extdbs oam')

    def get_extdb_ldap_ip(self,extdb=0,extdb_type='GTLA',IPv6=False):
        try:
            _DEB('Getting LDAP ip for extdb %s and index %d' % (extdb_type, extdb))
            extdb_info = self.raw['extdbs']
            _DEB('extdb info:%s' % extdb_info)
            extdb_item = extdb_info[extdb]
            _DEB('extdb item by index:%s' % extdb_item)
            if extdb_type == extdb_item['type']:
                return self.get_single_ip(extdb_item['ldap'],IPv6)
            return self.get_single_ip(self.raw['extdbs'][extdb]['ldap'],IPv6)
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('extdb ldap')

    def get_extdb_ldap_aux_ip(self,extdb=0,extdb_type='GTLA',IPv6=False):
        try:
            _DEB('Getting LDAP AUX ip for extdb %s and index %d' % (extdb_type, extdb))
            extdb_info = self.raw['extdbs']
            _DEB('extdb info:%s' % extdb_info)
            extdb_item = extdb_info[extdb]
            _DEB('extdb item by index:%s' % extdb_item)
            if extdb_type == extdb_item['type']:
                return self.get_single_ip(extdb_item['ldap_aux'],IPv6)
            return self.get_single_ip(self.raw['extdbs'][extdb]['ldap_aux'],IPv6)
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('extdb ldap aux')

    def get_hlr_sigtran_ip(self,hlr=0,IPv6=False):
        try:
            return self.get_single_ip(self.raw['hlrs'][hlr]['sigtran'],IPv6)
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('hlr sigtran')

    def get_hlr_sigtran2_ip(self,hlr=0,IPv6=False):
        try:
            return self.get_single_ip(self.raw['hlrs'][hlr]['sigtran2'],IPv6)
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('hlr sigtran')

    def get_hlr_garp2e_ip(self,index,hlr=0,IPv6=False):
        try:
            _DEB('GARP2E (%s)' % index)
            return self.get_single_ip(self.raw['hlrs'][hlr]['GARP2E (%s)' % index],IPv6)
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('GARP2E (%s)' % index)

    def get_hss_ss7_gt_address(self,cabinet=0):
        try:
            return self.raw['cabinets'][cabinet]['hss_ss7_gt_address']
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('hss_ss7_gt_address')

    def get_eccd_cloud_vip(self,eccd=0,IPv6=False):
        try:
            return self.get_single_ip(self.raw['eccds'][eccd]['cloud_vip'],IPv6)
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('eccd cloud_vip')

    def get_eccd_oam_vip(self,eccd=0,IPv6=False):
        try:
            return self.get_single_ip(self.raw['eccds'][eccd]['oam_vip'],IPv6)
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('eccd oam_vip')

    def get_eccd_sig_vip(self,eccd=0,IPv6=False):
        try:
            return self.get_single_ip(self.raw['eccds'][eccd]['sig_vip'],IPv6)
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('eccd sig_vip')

    def get_eccd_prov_vip(self,eccd=0,IPv6=False):
        try:
            return self.get_single_ip(self.raw['eccds'][eccd]['prov_vip'],IPv6)
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('eccd prov_vip')

    def get_eccd_type(self):
        try:
            return self.raw['eccds'][0]['type']
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('eccd type')

    def get_eccd_name(self):
        try:
            return self.raw['eccds'][0]['name']
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('eccd name')

    def get_director_credential(self):
        try:
            return self.raw['eccds'][0]['director_credential']
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('eccd director_credential')

    def get_dummynet_name_by_traffic_type(self, traffic_type):
        try:
            for dummynet in self.raw['dummynets']:
                if traffic_type == dummynet['traffic_type']:
                    return dummynet['name']
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('dummynet name by traffic type')

    def get_dummynet_traffic_type_by_name(self, name):
        try:
            for dummynet in self.raw['dummynets']:
                if name == dummynet['name']:
                    return dummynet['traffic_type']
        except Exception as e:
            raise hss_utils.rosetta.InfoNotFound('dummynet traffic_type by name')


    def __str__(self):
        output ='Active generators: \n\t%s\n' % ' '.join(self.active_generators)

        if self.raw['cabinets']:
            output +=  '\nCabinets:'
            for index, cabinet in enumerate(self.raw['cabinets']):
                if cabinet:
                    output +=  '\n\tName:        %s\n' % cabinet['name']
                    output +=  '\tType:        %s\n' % cabinet['type']
                    output +=  '\t%s-1:        %s\n' % (('IO' if 'TSP' in cabinet['type'] else 'SC'),self.get_cabinet_cc1(cabinet=index,IPv6=self.display_ipv6))
                    output +=  '\t%s-2:        %s\n' % (('IO' if 'TSP' in cabinet['type'] else 'SC'),self.get_cabinet_cc2(cabinet=index,IPv6=self.display_ipv6))
                    output +=  '\tOAM:         %s\n' % self.get_cabinet_oam_vip(cabinet=index,IPv6=self.display_ipv6)
                    output +=  '\tRADDIA:      %s\n' % self.get_cabinet_vip_raddia(cabinet=index,IPv6=self.display_ipv6)
                    output +=  '\tDIASCTP:     %s\n' % self.get_cabinet_vip_diasctp(cabinet=index,IPv6=self.display_ipv6)
                    try:
                        output +=  '\tMAP1:        %s\n' % self.get_cabinet_map1(cabinet=index,IPv6=self.display_ipv6)
                        output +=  '\tMAP2:        %s\n' % self.get_cabinet_map2(cabinet=index,IPv6=self.display_ipv6)
                    except hss_utils.rosetta.InfoNotFound:
                        pass

                    try:
                        output +=  '\tUDM:         %s\n' % self.get_cabinet_http_vip(cabinet=index,IPv6=self.display_ipv6)
                    except hss_utils.rosetta.InfoNotFound:
                        pass

                    output +=  '\tLDAP:        %s\n' % self.get_cabinet_ldap_vip(cabinet=index,IPv6=self.display_ipv6)
                    try:
                        output +=  '\tSCXB:        %s\n' % self.get_cabinet_scxb(cabinet=index,IPv6=self.display_ipv6)
                    except hss_utils.rosetta.InfoNotFound:
                        pass
                    try:
                        output +=  '\tOwnGTAdd:    %s\n' % cabinet['hss_ss7_gt_address']
                    except KeyError:
                        pass
                    try:
                        output +=  '\tSP:          %s\n' % cabinet['local_sp']
                    except KeyError:
                        pass

                else:
                    output +=  '\tNo cabinets defined\n'

        if self.raw['extdbs']:
            output +=  '\nExtDb:'
            _DEB('Checking RAW extdbs:%s ' % self.raw['extdbs'])
            for index, extdb in enumerate(self.raw['extdbs']):
                _DEB('Checking extdb %s for index %d ' % (extdb, index))
                if extdb:
                    output +=  '\n\tName:       %s\n' % extdb['name']
                    output +=  '\tType:       %s\n' % extdb['type']
                    try:
                        output +=  '\tOAM:        %s\n' % self.get_extdb_oam_ip(extdb=index,extdb_type=extdb['type'],IPv6=self.display_ipv6)
                    except Exception:
                        output +=  '\tOAM:        Not Found\n'
                        pass

                    try:
                        output +=  '\tLDAP:       %s\n' % self.get_extdb_ldap_ip(extdb=index,extdb_type=extdb['type'],IPv6=self.display_ipv6)
                    except Exception:
                        output +=  '\tLDAP:       Not Found\n'
                        pass
                    try:
                        output +=  '\tLDAPaux:    %s\n' % self.get_extdb_ldap_aux_ip(extdb=index,extdb_type=extdb['type'],IPv6=self.display_ipv6)
                    except Exception:
                        pass
                else:
                    output +=  '\tNo ExtDb defined\n'

        if self.raw['hlrs']:
            output +=  '\nHlr:'
            for index, hlr in enumerate(self.raw['hlrs']):
                if hlr and hlr['type'] == 'SIMU':
                    output +=  '\n\tName:       %s\n' % hlr['name']
                    output +=  '\tType:       %s\n' % hlr['type']
                    output +=  '\tSIGTRAN:    %s\n' % self.get_hlr_sigtran_ip(hlr=index,IPv6=self.display_ipv6)
                    output +=  '\tSIGTRAN2:   %s\n' % self.get_hlr_sigtran2_ip(hlr=index,IPv6=self.display_ipv6)
                    output +=  '\tOwnGTAdd:   %s\n' % hlr['OwnGTAdd']
                    output +=  '\tSP:         %s\n' % hlr['SP']
                    output +=  '\tBC:         %s\n' % hlr['BC']
                elif hlr and hlr['type'] == 'HLR':
                    output +=  '\n\tName:       %s\n' % hlr['name']
                    output +=  '\tType:       %s\n' % hlr['type']
                    output +=  '\tGARP2E (1): %s\n' % self.get_hlr_garp2e_ip(1,hlr=index,IPv6=self.display_ipv6)
                    output +=  '\tGARP2E (2): %s\n' % self.get_hlr_garp2e_ip(2,hlr=index,IPv6=self.display_ipv6)
                    output +=  '\tGARP2E (3): %s\n' % self.get_hlr_garp2e_ip(3,hlr=index,IPv6=self.display_ipv6)
                    output +=  '\tGARP2E (4): %s\n' % self.get_hlr_garp2e_ip(4,hlr=index,IPv6=self.display_ipv6)
                    output +=  '\tGARP2E (5): %s\n' % self.get_hlr_garp2e_ip(5,hlr=index,IPv6=self.display_ipv6)
                    output +=  '\tGARP2E (6): %s\n' % self.get_hlr_garp2e_ip(6,hlr=index,IPv6=self.display_ipv6)
                    output +=  '\tGARP2E (7): %s\n' % self.get_hlr_garp2e_ip(7,hlr=index,IPv6=self.display_ipv6)
                    output +=  '\tGARP2E (8): %s\n' % self.get_hlr_garp2e_ip(8,hlr=index,IPv6=self.display_ipv6)
                    output +=  '\tOwnGTAdd:   %s\n' % hlr['hlr_ss7_gt_address']
                    output +=  '\tSP:         %s\n' % hlr['SP']

        if self.raw['dummynets']:
            output +=  '\nDummynets:'
            for dummynet in self.raw['dummynets']:
                if dummynet:
                    output +=  '\n\tName:       %s\n' % dummynet['name']
                    output +=  '\tType:       %s\n' % dummynet['traffic_type']

        if self.raw['eccds']:
            output +=  '\nEccds:'
            for index, eccd in enumerate(self.raw['eccds']):
                if eccd:
                    output +=  '\n\tName:        %s\n' % eccd['name']
                    output +=  '\tType:        %s\n' % eccd['type']
                    if eccd['type'] == 'IBD':
                        output +=  '\tCLOUD:       %s\n' % self.get_eccd_cloud_vip(eccd=index,IPv6=self.display_ipv6)
                        output +=  '\tOAM:         %s\n' % self.get_eccd_oam_vip(eccd=index,IPv6=self.display_ipv6)
                        output +=  '\tSIG:         %s\n' % self.get_eccd_sig_vip(eccd=index,IPv6=self.display_ipv6)
                        output +=  '\tPROV:        %s\n' % self.get_eccd_prov_vip(eccd=index,IPv6=self.display_ipv6)

        return output


def get_env_for_localhost():
    try:
        _DEB('Getting env for localhost %s' % HOSTNAME)
        env = hss_utils.rosetta.related_environments(HOSTNAME)
    except Exception as e:
        raise hss_utils.rosetta.ObjectNotFound('Can not fetch Object "%s" from Rosetta (%s)' % (HOSTNAME,e))
    if env is None or len(env) == 0:
        raise hss_utils.rosetta.ObjectNotFound(HOSTNAME)

    try:
        config = st_config_for(env[0])
    except Exception as e:
        raise hss_utils.rosetta.ObjectNotFound('Can not fetch Object "%s" from Rosetta (%s)' % (HOSTNAME,e))

    if config is None:
        raise hss_utils.rosetta.ObjectNotFound(HOSTNAME)
    return (env[0].name, config)

def st_config_for(env):

    config = {'generators':[],'extdbs':[],'dummynets':[],'cabinets':[],'hlrs':[],'ess':[],'eccds':[]}

    for node in  env.nodes:
        _DEB('getting st config for node %s' % node)
        key, new_element = cast_node(node)
        _DEB('INFO st config for node: key=%s NEW_ELE=%s' % (key, new_element))
        if key is None:
            continue
        config[key].append(new_element)

    return STConfig(config) if isinstance(config, dict) else config


##########################################################
#   Functions for parsing information returned by Rosetta
##########################################################

def search_key(src, candidates):
    for key in candidates:
        if key in src.keys():
            return src[key]
    _DEB('Available keys: %s, Candidate keys: %s' % (
            ','.join(src.keys()),
            ','.join(candidates)))

    return 'Not Configured Yet'

def stringfy_dict(src):
    assert isinstance(src, dict)
    result = {}
    for key in src.keys():
        result.update({key:str(src[key])})
    return result

def ip_list(net_list,valid_names=[]):
    return _ip_search('hosts',net_list,valid_names)

def vip_list(net_list,valid_names=[]):
    return _ip_search('vips',net_list,valid_names)

def router_list(net_list,valid_names=[]):
    return _ip_search('routers',net_list,valid_names)

def gateway_list(net_list,valid_names=[]):
    return _ip_search('gateways',net_list,valid_names)

def add_info_list(net_list,valid_names=[]):
    return _ip_search('additional_info',net_list,valid_names)

def _ip_search(ip_type, net_list,valid_names=[]):
    result = {}
    if not isinstance(net_list,list):
        valid_names = [net_list.name]
        net_list = [net_list]

    for net in net_list:
        if net.name in valid_names:
            result.update(eval('net.%s' % ip_type))

    if not result:
        _DEB('Available Nets: %s, Candidate nets: %s' % (
            ','.join([net.name for net in net_list]),
            ','.join(valid_names)))

    result_6 = {}
    for net in net_list:
        if net.name in [('%s_ipv6' % net_name) for net_name in valid_names]:
            result_6.update(eval('net.%s' % ip_type))

    if not result_6:
        _DEB('IPv6 Available Nets: %s, Candidate nets: %s' % (
            ','.join([net.name for net in net_list]),
            ','.join([('%s_ipv6' % net_name) for net_name in valid_names])))

    return join_dict(stringfy_dict(result), stringfy_dict(result_6))

def network_info_element_to_str(net_list,net_name, info):
    for net in net_list:
        if net.name == net_name:
            try:
                return eval('str(net.%s)' % info)
            except KeyError:
                return None

def get_network(net_list,net_name):
    for net in net_list:
        if net.name == net_name:
            return net

    raise ValueError('Required network %s not found' % net_name)


def get_credential_id(cred_list,cred_name):
    for cred in cred_list:
        if cred.name == cred_name:
            return cred.id

    raise ValueError('Required credential %s not found' % cred_name)


def join_dict(dict_a, dict_b):
    assert(isinstance(dict_a, dict) and isinstance(dict_b, dict))
    dict_c ={}
    for key in dict_a.keys():
        if dict_a[key] in [None,'']:
            continue
        dict_c[key] = [dict_a[key]]

    for key in dict_b.keys():
        if dict_b[key] in [None,'']:
            continue
        try:
            dict_c[key].append(dict_b[key])
        except KeyError:
            dict_c[key] = [dict_b[key]]

    return dict_c


def traffic_generator_adaptor(node):
    info = {}
    if isinstance(node, Tool):
        if node.infratype.name.startswith('traffic_generator') or node.infratype.name.startswith('5g_dev') or node.infratype.name.startswith('5g_tg'):
            return  {'active': True,'name':node.name}
    raise ValueError('Node is not a traffic generator')

def dummynet_adaptor(node):
    info = {}
    if isinstance(node, Tool):
        if 'dummynet' in node.infratype.name:
            try:
                return  {'active': True,'name':node.name,'traffic_type':node.additional_info['traffic_type']}
            except KeyError:
                pass
    raise ValueError('Node is not a dummynet')


def traffic_gtla_adaptor(node):
    if isinstance(node, Tool):
        info = {'active': True,'name':node.name}
        if node.infratype.name.startswith('gtla_virtual'):
            info.update({'type':'vGTLA'})
            info.update({'oam': search_key(ip_list(node.networks,['UDM GIC POD OM ']), ['host01','host02'])})
            info.update({'ldap': search_key(ip_list(node.networks,['UDM GIC POD ldap CUDB']), ['host01'])})
            return info
        elif node.infratype.name.startswith('gtla'):
            info.update({'type':'GTLA'})
            info.update({'oam': search_key(ip_list(node.networks,['UDM_POD_Tools_OM']), ['host01','host02'])})
            info.update({'provisioning': search_key(ip_list(node.networks,['UDM_POD_Tools_PROV']), ['host01'])})
            info.update({'ldap': search_key(ip_list(node.networks,['UDM_POD_Tools_LDAP_1']), ['host01'])})
            return info
        elif node.infratype.name.startswith('5g_gtla'):
            info.update({'type':'vGTLA'})

            if 'sero' in node.name:
                info.update({'oam': search_key(ip_list(node.networks,[node.networks[0].name.replace('_ipv6','')]), ['host01'])})
                info.update({'ldap': info['oam']})            
            elif len(node.networks) == 1:
                info.update({'oam': node.networks[0].hosts['host01']})
                info.update({'ldap': info['oam']})
            else:
                oam_list=[]
                ldap_list=[]
                for net in node.networks:
                    if net.name.startswith('UDM 5G SIG DATA'):
                        ldap_list.append(net.hosts['host01'])
                    elif net.name.startswith('UDM 5G management '):
                        oam_list.append(net.hosts['host01'])
                
                if oam_list:
                    info.update({'oam': oam_list})
                if ldap_list:
                    info.update({'ldap': ldap_list})

            return info
    raise ValueError('Node is not a gtla')

def cabinet_adaptor(node):
    if isinstance(node, Hss):
        if 'vnf' in node.infratype.name or node.infratype.name.startswith('hss_cba_vnf'):
            info = {'active': True,'name':node.name,'type':'VNF'}
            try:
                info.update({'hss_ss7_gt_address':node.additional_info['hss_ss7_gt_address']})
            except KeyError:
                info.update({'hss_ss7_gt_address':'Not Configured yet'})

            try:
                info.update({'local_sp':node.additional_info['SP']})
            except KeyError:
                info.update({'local_sp':'Not Configured yet'})

            info.update({'oam_vip': search_key(vip_list(node.networks,['oam']), ['oam_vip'])})
            info.update({'vip_diasctp': search_key(vip_list(node.networks,['diameter']), ['dia_vip'])})
            info.update({'vip_raddia': search_key(vip_list(node.networks,['raddia']), ['raddia_vip'])})
            info.update({'http_vip': search_key(vip_list(node.networks,['http']), ['http_vip'])})

            info.update({'map1': search_key(vip_list(node.networks,['sigtran']), ['map1_vip'])})
            info.update({'map2': search_key(vip_list(node.networks,['sigtran']), ['map2_vip'])})

            info.update({'cc1': search_key(ip_list(node.networks,['hssfe_oam_sp1','hssfe_om_sp1']), ['cc1'])})
            info.update({'cc2': search_key(ip_list(node.networks,['hssfe_oam_sp1','hssfe_om_sp1']), ['cc2'])})

            info.update({'ldap_vip': search_key(vip_list(node.networks,['ldap']), ['ldap_vip'])})
            info.update({'scxb': search_key(ip_list(node.networks,['nbi']), ['scxb0','scxb_mgmt'])})

            return info

        elif 'cba' in node.name or node.infratype.name.startswith('hss_cba'):
            info = {'active': True,'name':node.name,'type':'CBA'}
            try:
                info.update({'hss_ss7_gt_address':node.additional_info['hss_ss7_gt_address']})
            except KeyError:
                info.update({'hss_ss7_gt_address':'Not Configured yet'})

            try:
                info.update({'local_sp':node.additional_info['SP']})
            except KeyError:
                info.update({'local_sp':'Not Configured yet'})

            info.update({'oam_vip': search_key(vip_list(node.networks,['oam']), ['oam_vip'])})
            info.update({'vip_diasctp': search_key(vip_list(node.networks,['diameter']), ['dia_vip'])})
            info.update({'vip_raddia': search_key(vip_list(node.networks,['raddia']), ['raddia_vip'])})
            info.update({'http_vip': search_key(vip_list(node.networks,['http']), ['http_vip'])})

            info.update({'map1': search_key(vip_list(node.networks,['sigtran']), ['map1_vip'])})
            info.update({'map2': search_key(vip_list(node.networks,['sigtran']), ['map2_vip'])})

            info.update({'cc1': search_key(ip_list(node.networks,['sysoam']), ['cc1'])})
            info.update({'cc2': search_key(ip_list(node.networks,['sysoam']), ['cc2'])})
            info.update({'ldap_vip': search_key(vip_list(node.networks,['ldap']), ['ldap_vip'])})
            info.update({'scxb': search_key(ip_list(node.networks,['hss_bsp_nbi']), ['scxb0'])})
            return info

        elif 'vTSP' in node.infratype.name or node.infratype.name.startswith('hss_vtsp'):
            info = {'active': True,'name':node.name,'type':'vTSP' }
            try:
                info.update({'hss_ss7_gt_address':node.additional_info['hss_ss7_gt_address']})
            except KeyError:
                info.update({'hss_ss7_gt_address':'Not Configured yet'})

            try:
                info.update({'local_sp':node.additional_info['SP']})
            except KeyError:
                info.update({'local_sp':'Not Configured yet'})

            info.update({'oam_vip': search_key(vip_list(node.networks,['oam']), ['oam_vip'])})
            info.update({'vip_raddia': search_key(vip_list(node.networks,['raddia']), ['raddia_vip'])})
            info.update({'vip_diasctp': search_key(vip_list(node.networks,['sigtran']), ['dia_vip'])})

            info.update({'cc1': search_key(ip_list(node.networks,['sysoam']), ['cc1'])})
            info.update({'cc2': search_key(ip_list(node.networks,['sysoam']), ['cc2'])})
            info.update({'ldap_vip': search_key(vip_list(node.networks,['ldap']), ['ldap_vip'])})
            return info

        elif node.infratype.name.startswith('hss_tsp'):
            info = {'active': True,'name':node.name,'type':'TSP' }
            try:
                info.update({'hss_ss7_gt_address':node.additional_info['hss_ss7_gt_address']})
            except KeyError:
                info.update({'hss_ss7_gt_address':'Not Configured yet'})

            try:
                info.update({'local_sp':node.additional_info['SP']})
            except KeyError:
                info.update({'local_sp':'Not Configured yet'})

            info.update({'oam_vip': search_key(vip_list(node.networks,['oam']), ['oam_vip'])})
            info.update({'vip_diasctp': search_key(vip_list(node.networks,['raddia']), ['raddia_vip'])})
            info.update({'vip_raddia': search_key(vip_list(node.networks,['raddia']), ['raddia_vip'])})

            info.update({'cc1': search_key(ip_list(node.networks,['mpbn_sysoam']), ['cc1'])})
            info.update({'cc2': search_key(ip_list(node.networks,['mpbn_sysoam']), ['cc2'])})
            info.update({'ldap_vip': search_key(vip_list(node.networks,['ldap']), ['ldap_vip'])})
            return info
        else:
            info = {'active': True,'name':node.name,'type':'TSP' }
            try:
                info.update({'hss_ss7_gt_address':node.additional_info['hss_ss7_gt_address']})
            except KeyError:
                info.update({'hss_ss7_gt_address':'Not Configured yet'})
            try:
                info.update({'local_sp':node.additional_info['SP']})
            except KeyError:
                info.update({'local_sp':'Not Configured yet'})

            info.update({'oam_vip': search_key(vip_list(node.networks,['oam']), ['oam_vip'])})
            info.update({'vip_diasctp': search_key(vip_list(node.networks,['raddia']), ['raddia_vip'])})
            info.update({'vip_raddia': search_key(vip_list(node.networks,['raddia']), ['raddia_vip'])})

            info.update({'cc1': search_key(ip_list(node.networks,['mpbn_sysoam']), ['cc1'])})
            info.update({'cc2': search_key(ip_list(node.networks,['mpbn_sysoam']), ['cc2'])})
            info.update({'ldap_vip': search_key(vip_list(node.networks,['ldap']), ['ldap_vip'])})
            return info


    raise ValueError('Node is not a cabinet')

def cudb_adaptor(node):
    if isinstance(node, Cudb):
        info = {'active': True,'name':node.name,'type':'CUDB'}
        info.update({'oam': search_key(vip_list(node.networks,['cudb_oam']), ['oam_vip'])})
        info.update({'ldap': search_key(vip_list(node.networks,['cudb_fe']), ['fe_vip'])})
        try:
            info.update({'ldap_aux': search_key(vip_list(node.networks,['cudb_fe']), ['fe_vip2'])})
        except KeyError:
            pass

        info.update({'provisioning': search_key(vip_list(node.networks,['cudb_provisioning']), ['provisioning_vip'])})
        return info

    raise ValueError('Node is not a cudb')

def eccd_adaptor(node):
    if isinstance(node, Eccd):
        info = {'active': True,'name':node.name,'type':'IBD' if node.is_ibd else 'ANS'}
        if node.is_ibd:
            try:
                info.update({'director_credential': get_credential_id(node.credentials,'eccd-private')})
            except Exception as e:
                _DEB('Error reading eccd-private: %s' % e)
            info.update({'cloud_vip': search_key(vip_list(node.networks,['DIRECTOR_OAM']), ['network_def_oam_vip'])})
            info['cloud_vip'] += search_key(vip_list(node.networks,['DIRECTOR_OAM_IPV6']), ['network_def_oam_vip_ipv6'])
            info.update({'oam_vip': search_key(vip_list(node.networks,['WORKER_OAM']), ['worker_oam_vip'])})
            info['oam_vip'] += search_key(vip_list(node.networks,['WORKER_OAM_IPV6']), ['worker_oam_vip_ipv6'])
            info.update({'sig_vip': search_key(vip_list(node.networks,['WORKER_SIG']), ['worker_sig_vip'])})
            info['sig_vip'] += search_key(vip_list(node.networks,['WORKER_SIG_IPV6']), ['worker_sig_vip_ipv6'])
            info.update({'prov_vip': search_key(vip_list(node.networks,['WORKER_PROV']), ['worker_prov_vip'])})
            info['prov_vip'] += search_key(vip_list(node.networks,['WORKER_PROV_IPV6']), ['worker_prov_vip_ipv6'])

        return info

    raise ValueError('Node is not a Eccd')

def hlr_adaptor(node):
    if isinstance(node, Hlr):
        if 'simu' in node.infratype.name:
            info = {'active': True,'name':node.infratype.name,'type':'SIMU'}
            info.update({'sigtran': search_key(ip_list(node.networks,['sigtran']), ['ip'])})
            info.update({'sigtran2': search_key(ip_list(node.networks,['sigtran']), ['ip2'])})
            for net in node.networks:
                if net.name == 'sigtran':
                    try:
                        info.update({'SP': net.additional_info['SP']})
                    except KeyError:
                        info.update({'SP': 'Not Configured yet'})
                    try:
                        info.update({'BC': net.additional_info['BC']})
                    except KeyError:
                        info.update({'BC': 'Not Configured yet'})
                    try:
                        info.update({'OwnGTAdd' : net.additional_info['ss7_gt_address']})
                    except KeyError:
                        info.update({'OwnGTAdd': 'Not Configured yet'})
            return info

        elif 'hlr' in node.infratype.name:
            info = {'active': True,'name':node.infratype.name,'type':'HLR'}
            try:
                info.update({'hlr_ss7_gt_address':node.additional_info['hlr_ss7_gt_address']})
            except KeyError:
                info.update({'hlr_ss7_gt_address':'Not Configured yet'})

            try:
                info.update({'SP':node.additional_info['SP']})
            except KeyError:
                info.update({'SP':'Not Configured yet'})

            info.update({'GARP2E (1)': search_key(ip_list(node.networks,['sigtran']), ['GARP2E'])})
            info.update({'GARP2E (2)': search_key(ip_list(node.networks,['sigtran']), ['GARP2E2'])})
            info.update({'GARP2E (3)': search_key(ip_list(node.networks,['sigtran']), ['GARP2E3'])})
            info.update({'GARP2E (4)': search_key(ip_list(node.networks,['sigtran']), ['GARP2E4'])})
            info.update({'GARP2E (5)': search_key(ip_list(node.networks,['sigtran']), ['GARP2E5'])})
            info.update({'GARP2E (6)': search_key(ip_list(node.networks,['sigtran']), ['GARP2E6'])})
            info.update({'GARP2E (7)': search_key(ip_list(node.networks,['sigtran']), ['GARP2E7'])})
            info.update({'GARP2E (8)': search_key(ip_list(node.networks,['sigtran']), ['GARP2E8'])})

            return info


    raise ValueError('Node is not a hlr')

def ait_adaptor(node):
    info = {}
    if isinstance(node, Tool):
        if node.infratype.name.startswith('ait'):
            info = {'name':node.name}
            info.update({'mgmt': search_key(ip_list(node.networks,['mgmt']), ['host01','hots01'])})
            return info

    raise ValueError('Node is not a ait')

def cast_node(node):
    try:
        return 'generators', traffic_generator_adaptor(node)
    except ValueError:
        pass

    try:
        return 'dummynets', dummynet_adaptor(node)
    except ValueError:
        pass

    try:
        return 'extdbs', traffic_gtla_adaptor(node)
    except ValueError:
        pass
    try:
        return 'ess', ait_adaptor(node)
    except ValueError as e:
        pass

    try:
        return 'cabinets', cabinet_adaptor(node)
    except ValueError:
        pass
    try:
        return 'extdbs', cudb_adaptor(node)
    except ValueError:
        pass

    try:
        return 'hlrs', hlr_adaptor(node)
    except ValueError:
        pass

    try:
        return 'eccds', eccd_adaptor(node)
    except ValueError:
        pass

    return None, None

def cast_install_node(node):
    try:
        return 'cabinet',cabinet_install_adaptor(node)
    except UnKonowmNode:
        pass

    try:
        return 'ait', ait_install_adaptor(node)
    except UnKonowmNode:
        pass

    try:
        return 'hlrs', hlr_install_adaptor(node)
    except UnKonowmNode:
        pass

    return None, None



def installation_info_for(env):
    info = {'ait':None,'cabinet':None}
    for node in  env.nodes:
        key, new_element  = cast_install_node(node)
        if key is None:
            continue

        info[key]=new_element

    return info

def hlr_install_adaptor(node):
    if isinstance(node, Hlr):
        if 'simu' in node.infratype.name:
            info = {'name':node.infratype.name,'type':'SIMU','config':{}}

            net = get_network(node.networks,'sigtran')
            info['config'].update({'CLIENT_SIGTRAN_NETWORK_1': get_single_ip(search_key(ip_list(net), ['ip']))})
            info['config'].update({'CLIENT_SIGTRAN_NETWORK_2': get_single_ip(search_key(ip_list(net), ['ip2']))})
            info['config'].update({'HLR_SIGTRAN_IP_1': get_single_ip(search_key(ip_list(net), ['ip']))})
            info['config'].update({'HLR_SIGTRAN_IP_2': get_single_ip(search_key(ip_list(net), ['ip2']))})
            info['config'].update({'REMOTE_SPC': search_key(add_info_list(net), ['SP'])[0].split('-')[-1]})

            return info

        elif 'hlr' in node.infratype.name:
            info = {'name':node.infratype.name,'type':'HLR','config':{}}

            info['config'].update({'CLIENT_SIGTRAN_NETWORK_1': search_key(ip_list(node.networks,['sigtran']), ['GARP2E'])[0]})
            info['config'].update({'CLIENT_SIGTRAN_NETWORK_2': search_key(ip_list(node.networks,['sigtran']), ['GARP2E5'])[0]})
            info['config'].update({'HLR_SIGTRAN_IP_1': search_key(ip_list(node.networks,['sigtran']), ['GARP2E'])[0]})
            info['config'].update({'HLR_SIGTRAN_IP_2': search_key(ip_list(node.networks,['sigtran']), ['GARP2E5'])[0]})
            info['config'].update({'REMOTE_SPC': node.additional_info['SP'].split('-')[-1]})

            return info

    raise UnKonowmNode('Node is not a hlr')

def ait_install_adaptor(node):
    if isinstance(node, Tool):
        info = {'name':node.name}
        if node.infratype.name.startswith('ait'):
            info.update({'mgmt': search_key(ip_list(node.networks,['mgmt']), ['host01','hots01'])})
            return info

    raise UnKonowmNode('Node is not a ait')

def cabinet_install_adaptor(node):
    if isinstance(node, Hss):
        if 'vnf' in node.infratype.name or node.infratype.name.startswith('hss_cba_vnf'):
            info = {'name':node.vnf.tenant.name,'type':'VNF','config':{}}
            #info.update({'cpus': node.infratype.cpus })
            #info.update({'vms_number': node.infratype.vms_number})
            info.update({'CLOUD': node.vnf.cloud.apis})

            for instance in node.infratype.assigned_flavor:
                if 'PL' in instance.flavor.name:
                    info.update({'cpus_pl': instance.flavor.cpus})
                    info.update({'ram_pl': instance.flavor.ram})
                    info.update({'disk_pl': instance.flavor.disk})
                    info.update({'nof_pls': instance.min_assign})

                elif 'SC' in  instance.flavor.name:
                    info.update({'cpus_sc': instance.flavor.cpus})
                    info.update({'ram_sc': instance.flavor.ram})
                    info.update({'disk_sc': instance.flavor.disk})
                    if 'scaleio' in instance.flavor.name:
                        info['config'].update({'HOT_DEPLOYMENT': 'ephemeral'})
                    else:
                        info['config'].update({'HOT_DEPLOYMENT': 'persistent'})

            if 'enterprise' in node.infratype.name:
                info['config'].update({'HOT_DEPLOYMENT': 'enterprise'})

            info['config'].update({'NODENAME':node.vnf.name})
            info['config'].update({'HSS_VNF_TENANT_NAME': node.vnf.tenant.name})

            index = node.vnf.tenant.name.rfind('-')
            info['config'].update({'VNF_NAME': 'VNF' + node.vnf.tenant.name[index+1:]})
            info['config'].update({'VNF_ID': node.vnf.tenant.name[index+1:]})

            info['config'].update({'AVAIL_ZONE': node.vnf.availability_zone['hss_availability_zone']})
            info['config'].update({'HSS_VNF_USERNAME': node.vnf.tenant.credentials[0].username})
            info['config'].update({'HSS_VNF_USERNAME_PWD': info['config']['HSS_VNF_USERNAME'] + 'pwd'})

            info['config'].update({'IMAGE_PXE': 'vhss_' + info['config']['VNF_NAME'].lower() + '_pxe'})
            info['config'].update({'IMAGE_SC1': 'vhss_' + info['config']['VNF_NAME'].lower() + '_sc'})

            info['config'].update({'CEE_CLOUD_URI': node.vnf.cloud.apis.pop('cloud')})

            try:
                info['config'].update({'OWNGTADD':node.additional_info['hss_ss7_gt_address']})
                info['config'].update({'LOCAL_SPC':node.additional_info['SP'].split('-')[-1]})
            except KeyError as e:
                print '%s' % e
                pass

            net = get_network(node.networks,'oam')
            info['config'].update({'SITE_SPECIFIC_bt1_snmp_target_addr': get_single_ip(search_key(vip_list(net), ['oam_vip']))})
            info['config'].update({'HSS_VIP_OAM': get_single_ip(search_key(vip_list(net), ['oam_vip']))})

            info['config'].update({'NW_VIP_OAM_1': get_single_ip(search_key(vip_list(net), ['oam_vip']))})
            info['config'].update({'NW_OAM_VRRP_IP': get_single_ip(search_key(add_info_list(net), ['app_fee_gw']))})
            info['config'].update({'NW_OAM_FIXED_IP_NODE_01': get_single_ip(search_key(add_info_list(net), ['app_fee1_router_id']))})
            info['config'].update({'NW_OAM_FIXED_IP_NODE_02': get_single_ip(search_key(add_info_list(net), ['app_fee2_router_id']))})
            info['config'].update({'NW_OAM_NET_ID': search_key(add_info_list(net), ['app_network'])[0].split('/')[0]})
            info['config'].update({'NW_OAM_NET_MASK': search_key(add_info_list(net), ['app_mask'])[0]})
            info['config'].update({'NW_OAM_SEGMENT_ID': search_key(add_info_list(net), ['app_tag'])[0]})

            net = get_network(node.networks,'oam_ipv6')
            if net:
                info['config'].update({'NW_VIP_OAM_1_IPv6': get_single_ip(search_key(vip_list(net), ['oam_vip']),IPv6=True)})
                info['config'].update({'NW_OAM_FIXED_IP_NODE_01_IPv6': get_single_ip(search_key(add_info_list(net), ['app_fee1_router_id']),IPv6=True)})
                info['config'].update({'NW_OAM_FIXED_IP_NODE_02_IPv6': get_single_ip(search_key(add_info_list(net), ['app_fee2_router_id']),IPv6=True)})
                info['config'].update({'NW_OAM_VRRP_IP_IPv6': get_single_ip(search_key(add_info_list(net), ['app_fee_gw']),IPv6=True)})
                info['config'].update({'NW_OAM_NET_MASK_IPv6': search_key(add_info_list(net), ['app_mask'])[0]})

            net = get_network(node.networks,'diameter')
            info['config'].update({'NW_VIP_DIA_1': get_single_ip(search_key(vip_list(net), ['dia_vip']))})

            net = get_network(node.networks,'diameter_ipv6')
            if net:
                info['config'].update({'NW_VIP_DIA_1_IPv6': get_single_ip(search_key(vip_list(net), ['dia_vip']),IPv6=True)})

            net = get_network(node.networks,'raddia')
            info['config'].update({'NW_VIP_RADDIA_1': get_single_ip(search_key(vip_list(net), ['raddia_vip']))})
            info['config'].update({'NW_RADDIA_VRRP_IP': get_single_ip(search_key(add_info_list(net), ['app_fee_gw']))})
            info['config'].update({'NW_RADDIA_FIXED_IP_NODE_03': get_single_ip(search_key(add_info_list(net), ['app_fee3_router_id']))})
            info['config'].update({'NW_RADDIA_FIXED_IP_NODE_04': get_single_ip(search_key(add_info_list(net), ['app_fee4_router_id']))})
            info['config'].update({'NW_RADDIA_NET_ID': search_key(add_info_list(net), ['app_network'])[0].split('/')[0]})
            info['config'].update({'NW_RADDIA_NET_MASK': search_key(add_info_list(net), ['app_mask'])[0]})
            info['config'].update({'NW_RADDIA_SEGMENT_ID': search_key(add_info_list(net), ['app_tag'])[0]})

            net = get_network(node.networks,'raddia_ipv6')
            print repr(net.name)
            if net:
                info['config'].update({'NW_VIP_RADDIA_1_IPv6': get_single_ip(search_key(vip_list(net), ['raddia_vip']),IPv6=True)})
                info['config'].update({'NW_RADDIA_VRRP_IP_IPv6': get_single_ip(search_key(add_info_list(net), ['app_fee_gw']),IPv6=True)})
                info['config'].update({'NW_RADDIA_FIXED_IP_NODE_03_IPv6': get_single_ip(search_key(add_info_list(net), ['app_fee3_router_id']),IPv6=True)})
                info['config'].update({'NW_RADDIA_FIXED_IP_NODE_04_IPv6': get_single_ip(search_key(add_info_list(net), ['app_fee4_router_id']),IPv6=True)})
                info['config'].update({'NW_RADDIA_NET_MASK_IPv6': search_key(add_info_list(net), ['app_mask'])[0]})

            net = get_network(node.networks,'sigtran')
            info['config'].update({'NW_VIP_MAP_1': get_single_ip(search_key(vip_list(net), ['map1_vip']))})
            info['config'].update({'NW_VIP_MAP_2': get_single_ip(search_key(vip_list(net), ['map2_vip']))})
            info['config'].update({'NW_VIP_DIA_2': get_single_ip(search_key(vip_list(net), ['spare_vip']))})
            info['config'].update({'NW_SIG_VRRP_IP': get_single_ip(search_key(add_info_list(net), ['app_fee_gw']))})
            info['config'].update({'NW_SIG_FIXED_IP_NODE_03': get_single_ip(search_key(add_info_list(net), ['app_fee3_router_id']))})
            info['config'].update({'NW_SIG_FIXED_IP_NODE_04': get_single_ip(search_key(add_info_list(net), ['app_fee4_router_id']))})
            info['config'].update({'NW_SIG_NET_ID': search_key(add_info_list(net), ['app_network'])[0].split('/')[0]})
            info['config'].update({'NW_SIG_NET_MASK': search_key(add_info_list(net), ['app_mask'])[0]})
            info['config'].update({'NW_SIG_SEGMENT_ID': search_key(add_info_list(net), ['app_tag'])[0]})

            net = get_network(node.networks,'sigtran_ipv6')
            if net:
                info['config'].update({'NW_VIP_MAP_1_IPv6': get_single_ip(search_key(vip_list(net), ['map1_vip']),IPv6=True)})
                info['config'].update({'NW_VIP_MAP_2_IPv6': get_single_ip(search_key(vip_list(net), ['map2_vip']),IPv6=True)})
                info['config'].update({'NW_VIP_DIA_2_IPv6': get_single_ip(search_key(vip_list(net), ['spare_vip']),IPv6=True)})
                info['config'].update({'NW_SIG_VRRP_IP_IPv6': get_single_ip(search_key(add_info_list(net), ['app_fee_gw']),IPv6=True)})
                info['config'].update({'NW_SIG_FIXED_IP_NODE_03_IPv6': get_single_ip(search_key(add_info_list(net), ['app_fee3_router_id']),IPv6=True)})
                info['config'].update({'NW_SIG_FIXED_IP_NODE_04_IPv6': get_single_ip(search_key(add_info_list(net), ['app_fee4_router_id']),IPv6=True)})
                info['config'].update({'NW_SIG_NET_MASK_IPv6': search_key(add_info_list(net), ['app_mask'])[0]})

            net = get_network(node.networks,'ldap')
            info['config'].update({'NW_VIP_LDAP_1': get_single_ip(search_key(vip_list(net), ['ldap_vip']))})
            info['config'].update({'NW_LDAP_VRRP_IP': get_single_ip(search_key(add_info_list(net), ['app_fee_gw']))})
            info['config'].update({'NW_LDAP_FIXED_IP_NODE_03': get_single_ip(search_key(add_info_list(net), ['app_fee3_router_id']))})
            info['config'].update({'NW_LDAP_FIXED_IP_NODE_04': get_single_ip(search_key(add_info_list(net), ['app_fee4_router_id']))})
            info['config'].update({'NW_LDAP_FIXED_IP_NODE_05': get_single_ip(search_key(add_info_list(net), ['app_fee5_router_id']))})
            info['config'].update({'NW_LDAP_FIXED_IP_NODE_06': get_single_ip(search_key(add_info_list(net), ['app_fee6_router_id']))})
            info['config'].update({'NW_LDAP_FIXED_IP_NODE_07': get_single_ip(search_key(add_info_list(net), ['app_fee19_router_id']))})
            info['config'].update({'NW_LDAP_FIXED_IP_NODE_08': get_single_ip(search_key(add_info_list(net), ['app_fee20_router_id']))})
            info['config'].update({'NW_LDAP_FIXED_IP_NODE_09': get_single_ip(search_key(add_info_list(net), ['app_fee21_router_id']))})
            info['config'].update({'NW_LDAP_FIXED_IP_NODE_10': get_single_ip(search_key(add_info_list(net), ['app_fee22_router_id']))})
            info['config'].update({'NW_LDAP_NET_ID': search_key(add_info_list(net), ['app_network'])[0].split('/')[0]})
            info['config'].update({'NW_LDAP_NET_MASK': search_key(add_info_list(net), ['app_mask'])[0]})
            info['config'].update({'NW_LDAP_SEGMENT_ID': search_key(add_info_list(net), ['app_tag'])[0]})

            net = get_network(node.networks,'ldap_ipv6')
            if net:
                info['config'].update({'NW_VIP_LDAP_1_IPv6': get_single_ip(search_key(vip_list(net), ['ldap_vip']),IPv6=True)})
                info['config'].update({'NW_LDAP_FIXED_IP_NODE_03_IPv6': get_single_ip(search_key(add_info_list(net), ['app_fee3_router_id']),IPv6=True)})
                info['config'].update({'NW_LDAP_FIXED_IP_NODE_04_IPv6': get_single_ip(search_key(add_info_list(net), ['app_fee4_router_id']),IPv6=True)})
                info['config'].update({'NW_LDAP_FIXED_IP_NODE_05_IPv6': get_single_ip(search_key(add_info_list(net), ['app_fee5_router_id']),IPv6=True)})
                info['config'].update({'NW_LDAP_FIXED_IP_NODE_06_IPv6': get_single_ip(search_key(add_info_list(net), ['app_fee6_router_id']),IPv6=True)})
                info['config'].update({'NW_LDAP_FIXED_IP_NODE_07_IPv6': get_single_ip(search_key(add_info_list(net), ['app_fee19_router_id']),IPv6=True)})
                info['config'].update({'NW_LDAP_FIXED_IP_NODE_08_IPv6': get_single_ip(search_key(add_info_list(net), ['app_fee20_router_id']),IPv6=True)})
                info['config'].update({'NW_LDAP_FIXED_IP_NODE_09_IPv6': get_single_ip(search_key(add_info_list(net), ['app_fee21_router_id']),IPv6=True)})
                info['config'].update({'NW_LDAP_FIXED_IP_NODE_10_IPv6': get_single_ip(search_key(add_info_list(net), ['app_fee22_router_id']),IPv6=True)})
                info['config'].update({'NW_LDAP_NET_MASK_IPv6': search_key(add_info_list(net), ['app_mask'])[0]})
                info['config'].update({'NW_LDAP_VRRP_IP_IPv6': get_single_ip(search_key(add_info_list(net), ['app_fee_gw']),IPv6=True)})

            net = get_network(node.networks,'hssfe_oam_sp1')
            info['config'].update({'NW_SYS_OAM_NET_ID': net.prefix})
            info['config'].update({'NW_SYS_OAM_FIXED_IP_NODE_01': get_single_ip(search_key(ip_list(net), ['cc1']))})
            info['config'].update({'NW_SYS_OAM_FIXED_IP_NODE_02': get_single_ip(search_key(ip_list(net), ['cc2']))})
            info['config'].update({'NW_SYS_OAM_SC_VRRP_IP': str(net.vrrp_ip)})
            info['config'].update({'NW_SYS_OAM_SEGMENT_ID': net.tag})
            info['config'].update({'NW_SYS_OAM_NET_MASK': net.cidr})

            net = get_network(node.networks,'hssfe_oam_sp1_ipv6')
            if net:
                info['config'].update({'NW_SYS_OAM_NET_ID_IPv6': net.prefix})
                info['config'].update({'NW_SYS_OAM_FIXED_IP_NODE_01_IPv6': get_single_ip(search_key(ip_list(net), ['cc1']),IPv6=True)})
                info['config'].update({'NW_SYS_OAM_FIXED_IP_NODE_02_IPv6': get_single_ip(search_key(ip_list(net), ['cc2']),IPv6=True)})
                info['config'].update({'NW_SYS_OAM_SC_VRRP_IP_IPv6': str(net.vrrp_ip)})
                info['config'].update({'NW_SYS_OAM_NET_MASK_IPv6': net.cidr})

            return info

        elif 'cba' in node.name or node.infratype.name.startswith('hss_cba'):
            info = {'name':node.infratype.name,'hydra_id':node.additional_info['hydra_network_ci'],'type':'CBA','config':{}}
            if 'nano' in node.infratype.name:
                info.update({'suffix': '-R' if 'right' in node.infratype.name else '-L'})
            else:
                info.update({'suffix': ''})

            try:
                info['config'].update({'OWNGTADD':node.additional_info['hss_ss7_gt_address']})
                info['config'].update({'LOCAL_SPC':node.additional_info['SP'].split('-')[-1]})
            except KeyError as e:
                print '%s' % e
                pass

            net = get_network(node.networks,'ldap')
            info['config'].update({'HSS_VIP_LDAP': get_single_ip(search_key(vip_list(net), ['ldap_vip']))})
            info['config'].update({'LDAP_UPLINK_CMX_0_26': get_single_ip(search_key(router_list(net), ['router0']))})
            info['config'].update({'LDAP_UPLINK_CMX_0_28': get_single_ip(search_key(router_list(net), ['router1']))})
            info['config'].update({'LDAP_UPLINK_GW1': get_single_ip(search_key(gateway_list(net), ['gw_0']))})
            info['config'].update({'LDAP_UPLINK_GW2': get_single_ip(search_key(gateway_list(net), ['gw_1']))})
            info['config'].update({'LDAP_UPLINK_TAG': net.tag})
            info['config'].update({'LDAP_UPLINK_MASK': net.cidr})

            net = get_network(node.networks,'oam')
            info['config'].update({'HSS_VIP_OAM': get_single_ip(search_key(vip_list(net), ['oam_vip']))})
            info['config'].update({'OAM_UPLINK_CMX_0_26': get_single_ip(search_key(router_list(net), ['router0']))})
            info['config'].update({'OAM_UPLINK_CMX_0_28': get_single_ip(search_key(router_list(net), ['router1']))})
            info['config'].update({'OAM_UPLINK_GW1': get_single_ip(search_key(gateway_list(net), ['gw_0']))})
            info['config'].update({'OAM_UPLINK_GW2': get_single_ip(search_key(gateway_list(net), ['gw_1']))})
            info['config'].update({'OAM_UPLINK_TAG': net.tag})
            info['config'].update({'OAM_UPLINK_MASK': net.cidr})

            net = get_network(node.networks,'diameter')
            info['config'].update({'HSS_VIP_DIA_1': get_single_ip(search_key(vip_list(net), ['dia_vip']))})

            net = get_network(node.networks,'raddia')
            info['config'].update({'HSS_VIP_RADDIA': get_single_ip(search_key(vip_list(net), ['raddia_vip']))})
            info['config'].update({'RAD_UPLINK_CMX_0_26': get_single_ip(search_key(router_list(net), ['router0']))})
            info['config'].update({'RAD_UPLINK_CMX_0_28': get_single_ip(search_key(router_list(net), ['router1']))})
            info['config'].update({'RAD_UPLINK_GW1': get_single_ip(search_key(gateway_list(net), ['gw_0']))})
            info['config'].update({'RAD_UPLINK_GW2': get_single_ip(search_key(gateway_list(net), ['gw_1']))})
            info['config'].update({'RAD_UPLINK_TAG': net.tag})
            info['config'].update({'RAD_UPLINK_MASK': net.cidr})

            net = get_network(node.networks,'sigtran')
            info['config'].update({'HSS_VIP_MAP_1': get_single_ip(search_key(vip_list(net), ['map1_vip']))})
            info['config'].update({'HSS_VIP_MAP_2': get_single_ip(search_key(vip_list(net), ['map2_vip']))})
            info['config'].update({'SIG_UPLINK_CMX_0_26': get_single_ip(search_key(router_list(net), ['router0']))})
            info['config'].update({'SIG_UPLINK_CMX_0_28': get_single_ip(search_key(router_list(net), ['router1']))})
            info['config'].update({'SIG_UPLINK_GW1': get_single_ip(search_key(gateway_list(net), ['gw_0']))})
            info['config'].update({'SIG_UPLINK_GW2': get_single_ip(search_key(gateway_list(net), ['gw_1']))})
            info['config'].update({'SIG_UPLINK_TAG': net.tag})
            info['config'].update({'SIG_UPLINK_MASK': net.cidr})

            net = get_network(node.networks,'hss_bsp_nbi')
            info['config'].update({'SYS_BSP_CMX_0_26': get_single_ip(search_key(router_list(net), ['router0']))})
            info['config'].update({'SYS_BSP_CMX_0_28': get_single_ip(search_key(router_list(net), ['router1']))})
            info['config'].update({'SYS_BSP_CNBI': get_single_ip(search_key(ip_list(net), ['scxb0']))})
            info['config'].update({'SYS_BSP_NETWORK': net.prefix})
            info['config'].update({'SYS_BSP_TAG': net.tag})
            info['config'].update({'SYS_BSP_VRRP_IP': str(net.vrrp_ip)})

            net = get_network(node.networks,'sysoam')
            info['config'].update({'HSSFE_SYS_OAM_SC_1': get_single_ip(search_key(ip_list(net), ['cc1']))})
            info['config'].update({'HSSFE_SYS_OAM_SC_2': get_single_ip(search_key(ip_list(net), ['cc2']))})
            info['config'].update({'HSSFE_SYS_OAM_SC_CMX_0_26': get_single_ip(search_key(router_list(net), ['router0']))})
            info['config'].update({'HSSFE_SYS_OAM_SC_CMX_0_28': get_single_ip(search_key(router_list(net), ['router1']))})
            info['config'].update({'HSSFE_SYS_OAM_SC_TAG': net.tag})
            info['config'].update({'HSSFE_SYS_OAM_SC_MASK': net.cidr})
            info['config'].update({'HSSFE_SYS_OAM_SC_NETWORK': net.prefix})
            info['config'].update({'HSSFE_SYS_OAM_SC_VRRP_IP': str(net.vrrp_ip)})


            return info

    raise UnKonowmNode('Node is not a cabinet')

##########################################################################
#   Functions for parsing information returned by APIs for virtualization
##########################################################################
def get_vnf_info (pod, vnf):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    data = {"action":"vnf_detailed", "vnf": '%s-%s' % (pod,vnf)}
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
    except Exception as e:
        _ERR('Error in action vnf_detailed: %s' % str(e))
        raise hss_utils.rosetta.ActionFailure('vnf_detailed' )

    return response['data']

def get_hss_vnf_info (pod, vnf):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    data = {"action":"hss_vnf_detailed", "vnf": '%s-%s' % (pod,vnf)}
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
    except Exception as e:
        _ERR('Error in action hss_vnf_detailed: %s' % str(e))
        raise hss_utils.rosetta.ActionFailure('hss_vnf_detailed')

    _DEB('HSS_VNF_DETAILED response:\n%s' % response)
    return response['data']

def get_hss_vnf_info_params (hss_vnf_data, vm, params=[]):
    if len(params)== 0:
        params = ['status','ha-policy','hypervisor_id','hypervisor','flavor','server_id']
    _DEB('vnf info parameters: %s' % params)
    params_info = ''
    for vm_data in hss_vnf_data:
        vm_name = vm_data['name']
        if (vm_name == vm):
            params_info = params_info + '{0: <30}'.format(vm_name)
            _DEB('vnf info for VM %s' % vm_name)
            for param in params:
                if (param == 'status'):
                    params_info = params_info + '\t' + vm_data['status']
                if (param == 'server_id'):
                    params_info = params_info + '\t' + vm_data['server_id']
                if (param == 'ha-policy'):
                    params_info = params_info + '\t' + vm_data['ha-policy'] + '\t'
                if (param == 'hypervisor_id'):
                    params_info = params_info + '\t' + str(vm_data['hypervisor_id'])
                if (param == 'hypervisor'):
                    params_info = params_info + '\t' + vm_data['hypervisor'] + '\t'
                if (param == 'host_status'):
                    params_info = params_info + '\t' + vm_data['host_status'] + '\t'
                if (param == 'flavor'):
                    flavor_data = vm_data['flavor']
                    params_info = params_info + '\t' + flavor_data['name']

    return params_info

def hss_vnf_info_header (params_to_show=[]):
    if len(params_to_show)== 0:
        params = ['status','ha-policy','hypervisor_id','hypervisor','flavor','server_id']
    head_params = 'VM Name   \t\t'
    head_underline = '-------   \t\t'
    for param in params_to_show:
        head_params = head_params + '\t' + param
        if (param == 'status'):
            head_underline = head_underline + '\t' + '------'
        if (param == 'ha-policy'):
            head_underline = head_underline + '\t' + '---------'
        if (param == 'hypervisor_id'):
            head_underline = head_underline + '\t' + '-------------'
        if (param == 'hypervisor'):
            head_params = head_params + '\t\t'
            head_underline = head_underline + '\t' + '------------------\t'
        if (param == 'flavor'):
            head_params = head_params + '\t'
            head_underline = head_underline + '\t' + '--------------'
        if (param == 'server_id'):
            head_underline = head_underline + '\t' + '------------------------------------'
    return (head_params + "\n" + head_underline)


def display_hss_vnf_info (hss_vnf_data, list_vms, params_to_show):
    hss_vnf_info = hss_vnf_info_header (params_to_show)
    for key, vm in list_vms.items():
        _DEB('vnf info for VM %s' % vm)
        hss_vnf_info = hss_vnf_info + "\n" + get_hss_vnf_info_params(hss_vnf_data, vm, params_to_show)
    return hss_vnf_info


def get_hss_vnf_type (hss_vnf_data, list_vms):
    # Single-compute (Enterprise) systems all instances are defined with ha-policy as "managed-on-host"
    # Multi-compute (Telco) systems SC instances are defined with ha-policy as "ha-offline"
    type_vnf='Enterprise'
    params=['ha-policy']
    for key, vm in list_vms.items():
        vm_policy = get_hss_vnf_info_params(hss_vnf_data, vm, params)
        vm_policy_name = vm_policy.split()[1]
        _DEB('HA policy for VM %s: %s ' % (vm,vm_policy_name))
        if 'ha-offline' in vm_policy_name:
            type_vnf='TelcoPersist'
            if 'sc' in vm:
                type_vnf='TelcoNoPersist'
                return type_vnf
    return type_vnf


def get_hss_vnf_hypervisor (hss_vnf_data, virt_machine):
    params=['hypervisor']
    vm_hypervisor = get_hss_vnf_info_params(hss_vnf_data, virt_machine, params)
    if vm_hypervisor:
        hypervisor_name = vm_hypervisor.split()[1]
        _DEB('Hypervisor for VM %s: %s ' % (virt_machine,hypervisor_name))
        return hypervisor_name

    return None

def get_hss_vnf_hypervisor_ha_policy (hss_vnf_data, ha_policy):
    list_hyp_names = []
    params=['ha-policy']
    _DEB('Getting Hypervisors with HA policy %s' % ha_policy)
    for vm_data in hss_vnf_data:
        vm_name = vm_data['name']
        vm_policy = get_hss_vnf_info_params(hss_vnf_data, vm_name, params)
        vm_policy_name = vm_policy.split()[1]
        _DEB('HA policy for VM %s: %s ' % (vm_name,vm_policy_name))
        if vm_policy_name == ha_policy:
            vm_hypervisor = get_hss_vnf_info_params(hss_vnf_data, vm_name, params=['hypervisor'])
            if vm_hypervisor:
                hypervisor_name = vm_hypervisor.split()[1]
                _DEB('Hypervisor %s for VM %s has ha-policy %s ' % (hypervisor_name,vm_name,ha_policy))
                if hypervisor_name not in list_hyp_names:
                    list_hyp_names.append(hypervisor_name)
            _DEB('List Hypervisor: %s ' % list_hyp_names)
        else:
            _DEB('HA policy to check %s and ha-policy obtained:%s' % (ha_policy, vm_policy_name))

    return list_hyp_names


def get_hss_vnf_vms (hss_vnf_data):
    list_vm_names = {}
    for vm_data in hss_vnf_data:
        vm_id = vm_data['server_id']
        vm_name = vm_data['name']
        list_vm_names[vm_id] = vm_name

    return list_vm_names


def get_hss_vnf_vms_status (pod, vnf, vm):
    hss_vnf_data = get_hss_vnf_info (pod, vnf)
    for vm_data in hss_vnf_data:
        status = vm_data['status']
        vm_name = vm_data['name']
        if vm_name == vm:
           return status

    return None

def get_vnf_vms_status (pod, vnf, vm):
    vnf_data = get_vnf_info (pod, vnf)
    for vm_data in vnf_data:
        status = vm_data['status']
        vm_name = vm_data['name']
        if vm_name == vm:
           return status

    return None


def get_hss_vnf_flavor (hss_vnf_data,vm_name):
    for vm_data in hss_vnf_data:
        vm_name_line = vm_data['name']
        if (vm_name_line == vm_name):
            flavor_data = vm_data['flavor']
            flavor_name = flavor_data['name']
            return flavor_name

    return None


def get_vnf_status_stack (stack_data, stack_name):
    stack_status = stack_data['stack_status']
    _DEB('STACK_STATUS is: %s' % stack_status)

    return stack_status


def vnf_restart_router_compute(pod,vnf,compute_name):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    data = {"action":"restart_router", "vnf": '%s-%s' % (pod,vnf), "compute_name": '%s' % compute_name}
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
        _DEB('RESTART ROUTER COMPUTE response: %s' % response)
    except Exception as e:
        _ERR('Error in action restart_router: %s' % str(e))
        raise hss_utils.rosetta.ActionFailure('restart_router')
    return response['data']

def vnf_lock_compute(pod,vnf,compute_name):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    data = {"action":"change_compute_status", "vnf": '%s-%s' % (pod,vnf), "compute_name": '%s' % compute_name, "status": "LOCKED"}
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
        _DEB('LOCK COMPUTE response: %s' % response)
    except Exception as e:
        _ERR('Error in action change_compute_status: %s' % str(e))
        raise hss_utils.rosetta.ActionFailure('change_compute_status')
    return response['data']


def vnf_unlock_compute(pod,vnf,compute_name):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    data = {"action":"change_compute_status", "vnf": '%s-%s' % (pod,vnf), "compute_name": '%s' % compute_name, "status": "UNLOCKED"}
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
        _DEB('UNLOCK COMPUTE response: %s' % response)
    except Exception as e:
        _ERR('Error in action change_compute_status: %s' % str(e))
        raise hss_utils.rosetta.ActionFailure('change_compute_status')

    return response['data']


def vnf_num_cpus_compute(pod,vnf,compute_name):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    data = {"action":"compute_stats", "vnf": '%s-%s' % (pod,vnf), "compute_name":'%s' % compute_name}
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
    except Exception as e:
        _ERR('Error in action compute_stats: %s' % str(e))
        raise hss_utils.rosetta.ActionFailure('compute_stats')

    compute_n_cpus_used = response['data']['vcpus_used']
    _DEB('COMPUTE_STATS num_cpus used: %s' % compute_n_cpus_used)
    compute_n_cpus = response['data']['vcpus']
    _DEB('COMPUTE_STATS num_cpus: %s' % compute_n_cpus)
    return compute_n_cpus, compute_n_cpus_used


def get_vnf_compute_status(pod,vnf,compute_name):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    data = {"action":"compute_stats", "vnf": '%s-%s' % (pod,vnf), "compute_name":'%s' % compute_name}
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
    except Exception as e:
        _DEB('Error in action compute_stats: %s' % str(e))
        raise hss_utils.rosetta.ActionFailure('compute_stats')

    state = response['data']['state']
    status = response['data']['status']
    _DEB('compute %s with state=%s and status=%s' % (compute_name,state,status))
    return state, status


def get_vnf_avzone (pod, vnf):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    data = {"action":"avzones_from_vnf", "vnf": '%s-%s' % (pod,vnf)}
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
        _DEB('AVZONES_FROM_VNF response: %s' % response)
    except Exception as e:
        _ERR('Error in action avzones_from_vnf: %s' % str(e))
        raise hss_utils.rosetta.ActionFailure('avzones_from_vnf')

    avzone_data = []
    avzone_data = response['data']
    _DEB('AVZONE data is: %s' % avzone_data)
    return avzone_data


def get_vnf_computes_avzone (pod, vnf):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    computes_data = []
    avzone_list = get_vnf_avzone (pod, vnf);

    avzone_name = avzone_list[0]
    data = {"action":"hypervisors_on_avzone", "vnf": '%s-%s' % (pod,vnf), "avzone_name": '%s' % avzone_name}
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
    except Exception as e:
        if 'no_hosts_founded' in str(e):
            _DEB('Not hypervisors_on_avzone: %s' % e)
        else:
            _ERR('Error in action hypervisors_on_avzone: %s' % str(e))
            raise hss_utils.rosetta.ActionFailure('hypervisors_on_avzone')
        return computes_data

    for compute in response['data']:
        computes_data.append(str(compute))
    _DEB('HYPERVISORES AVZONE data: %s' % computes_data)
    return computes_data


def get_vnf_free_computes (pod, vnf):
    free_computes = []
    free_computes = get_vnf_computes_avzone (pod, vnf)
    _DEB('HYPERVISORS defined for the environment: %s' % free_computes)
    hss_vnf_data = get_hss_vnf_info (pod, vnf)
    for vm_data in hss_vnf_data:
        vm_name = vm_data['name']
        vm_hypervisor = get_hss_vnf_info_params (hss_vnf_data, vm_name, params=['hypervisor'])
        hypervisor_name = vm_hypervisor.split()[1]
        _DEB('HYPERVISOR %s assigned for vm %s' % (hypervisor_name, vm_name))
        if hypervisor_name in free_computes:
           free_computes.remove(hypervisor_name)
           _DEB('FREE HYPERVISORS for the environment: %s' % free_computes)
    return free_computes


def get_vnf_stack (pod, vnf):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    data = {"action":"deployments", "vnf": '%s-%s' % (pod,vnf)}
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
    except Exception as e:
        _ERR('Error in action deployments: %s' % str(e))
        raise hss_utils.rosetta.ActionFailure('deployments')

    deploy_data = {}
    deploy_data = response['data']
    for stack_name in deploy_data:
        _DEB('Stack name is: %s' % stack_name)
        if 'ephemeral' in stack_name:
            return stack_name
        if 'persistent' in stack_name:
            return stack_name
        if 'enterprise' in stack_name:
            return stack_name
    return None

def get_vnf_stack_info (pod, vnf, stack_name):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    data = {"action":"stack_details", "vnf": '%s-%s' % (pod,vnf), "stack_name": '%s' % stack_name}
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
    except Exception as e:
        _ERR('Error in action stack_details: %s' % str(e))
        raise hss_utils.rosetta.ActionFailure('stack_details')

    stack_data = {}
    stack_data = response['data']
    _DEB('STACK data is: %s' % stack_data)
    return stack_data


def get_vnf_stack_info_params (stack_info, params=[]):
    if len(params)== 0:
        params = ['description','deletion_time','stack_status_reason','creation_time','updated_time','stack_status','id']
    _DEB('vnf stack info parameters: %s' % params)
    params_info = ''
    for param in params:
        if (param == 'description'):
            params_info = params_info + param + ':\t\t' + stack_info['description'] + '\n'
        if (param == 'deletion_time'):
            if stack_info['deletion_time'] is None:
                params_info = params_info + param + ':\t\t' + 'None' + '\n'
            else:
                params_info = params_info + param + ':\t\t' + stack_info['deletion_time'] + '\n'
        if (param == 'stack_status_reason'):
            params_info = params_info + param + ':\t' + stack_info['stack_status_reason'] + '\n'
        if (param == 'creation_time'):
            params_info = params_info + param + ':\t\t' + stack_info['creation_time'] + '\n'
        if (param == 'updated_time'):
            params_info = params_info + param + ':\t\t' + stack_info['updated_time'] + '\n'
        if (param == 'stack_status'):
            params_info = params_info + param + ':\t\t' + stack_info['stack_status'] + '\n'
        if (param == 'id'):
            params_info = params_info + param + ':\t\t\t' + str(stack_info['id'])
    return params_info


def vnf_scale_out (pod,vnf,stack_name,num):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    data = {"action":"update_existing_deploy", "vnf": '%s-%s' % (pod,vnf), "stack_name": '%s' % str(stack_name), "parameters": {"number_of_total_scaled_vms": '%d' % num}}
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
        _DEB('UPDATE EXISTING DEPLOY response: %s' % response)
    except Exception as e:
        _ERR('Error in action update_existing_deploy: %s' % str(e))
        raise hss_utils.rosetta.ActionFailure('update_existing_deploy')
    return response['data']


def vnf_scale_in (pod,vnf,stack_name,num,str_idx):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    data = {"action":"update_existing_deploy", "vnf": str("%s-%s" % (pod,vnf)), "stack_name": "%s" % str(stack_name), "parameters": {"number_of_total_scaled_vms": "%d" %num, "list_of_vms_to_scale_in":"%s" % str(str_idx)} }
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
        _DEB('UPDATE EXISTING DEPLOY response: %s' % response)
    except Exception as e:
        _ERR('Error in action update_existing_deploy: %s' % str(e))
        raise hss_utils.rosetta.ActionFailure('update_existing_deploy')
    return response['data']


def get_vnf_cee_list_alarms (pod):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    data = {"action":"list_alarms"}
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
    except Exception as e:
        _ERR('Error in action list_alarms: %s' % str(e))
        raise hss_utils.rosetta.ActionFailure('list_alarms')

    _DEB('LIST_ALARMS response: %s' % response)
    status = 'enabled'
    alarms_data = response['data']

    alarms_list = {}
    for alarms_info_data in alarms_data:
        if (status == alarms_info_data['status']):
            s_name = alarms_info_data['binary']
            s_host = alarms_info_data['host']
            s_state = alarms_info_data['state']
            #s_zone = alarms_info_data['zone']
            #s_forced_down = alarms_info_data['forced_down']
            _INF('Alarm %s enabled in host %s with state %s' % (s_name, s_host, s_state))
        else:
            _DEB('Alarm not enabled. Status:%s' % alarms_info_data['status'])

    _DEB('Alarms info is: %s' % alarms_list)
    return alarms_list


def get_vnf_nova_service_status (pod, status=['enabled','disabled']):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    data = {"action":"list_services"}
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
    except Exception as e:
        _ERR('Error in action list_services: %s' % str(e))
        raise hss_utils.rosetta.ActionFailure('list_services')
    _DEB('LIST_SERVICES response: %s' % response)

    service_data = response['data']
    service_list = []
    service_keys = ['name_service','host','state','zone','date']
    service_dict = []
    for service_info_data in service_data:
        if (status == service_info_data['status']):
            s_name = service_info_data['binary']
            s_host = service_info_data['host']
            s_state = service_info_data['state']
            s_zone = service_info_data['zone']
            #s_forced_down = service_info_data['forced_down']
            s_updated_at = service_info_data['updated_at']
            service_dict = [s_name, s_host, s_state, s_zone, s_updated_at]
            service_list.append(dict(zip(service_keys,service_dict)))
        else:
            _DEB('Status Service is not %s. Its status is %s' % (status,service_info_data['status']))

    return service_list


def get_vnf_router_id (pod,compute_name):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    data = {"action":"list_routers"}
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
    except Exception as e:
        _ERR('Error in action list_routers: %s' % str(e))
        raise hss_utils.rosetta.ActionFailure('list_routers')
    _DEB('LIST_ROUTERS response: %s' % response)

    router_data = response['data']
    for router_info_data in router_data:
        name = router_info_data['compute']
        router_id = router_info_data['router_id']
        if name == compute_name:
            _DEB('ROUTER ID %s found for compute %s' % (router_id, name))
            return router_id

    _WARN ('ROUTER not found for compute %s' % compute_name)
    return None


def vnf_start_server (pod,vnf,server_name):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    data = {"action":"start_server", "vnf": '%s-%s' % (pod,vnf), "server_name": '%s' % server_name}
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
    except Exception as e:
        _DEB('Error in action start_server: %s' % str(e))
        raise hss_utils.rosetta.ActionFailure('start_server')
    return response


def vnf_stop_server (pod,vnf,server_name):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    data = {"action":"stop_server", "vnf": '%s-%s' % (pod,vnf), "server_name": '%s' % server_name}
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
    except Exception as e:
        _DEB('Error in action stop_server: %s' % str(e))
        raise hss_utils.rosetta.ActionFailure('stop_server')
    return response


def vnf_reboot_server (pod,vnf,server_name):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    data = {"action":"reboot_server", "vnf": '%s-%s' % (pod,vnf), "server_name": '%s' % server_name}
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
    except Exception as e:
        _ERR('Error in action reboot_server: %s' % str(e))
        raise hss_utils.rosetta.ActionFailure('reboot_server')
    return response

def vnf_reboot_compute (pod,vnf,compute_name):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    data = {"action":"reboot_compute", "vnf": '%s-%s' % (pod,vnf), "compute_name": '%s' % compute_name}
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
    except Exception as e:
        _ERR('Error in action reboot_compute: %s' % str(e))
        raise hss_utils.rosetta.ActionFailure('reboot_compute')
    return response


def vnf_live_migration (pod,vnf,hypervisor_target,vm_pl_name):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    data = {"action":"live_migration", "vnf": '%s-%s' % (pod,vnf), "hypervisor_target": '%s' % str(hypervisor_target), "vm_name": '%s' % str(vm_pl_name)}
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
    except Exception as e:
        _ERR('Error in action live_migration: %s' % str(e))
        raise hss_utils.rosetta.ActionFailure('live_migration')

    if response['infos']:
       info_msg = 'INFO: %s' % str(response['infos'])
       _INF(info_msg)
    if response['warnings']:
       info_msg = 'Warnings: %s' % str(response['warnings'])
       _WRN(info_msg)
    if response['errors']:
       info_msg = 'Errors: %s' % str(response['errors'])
       _ERR(info_msg)

    return response


def vnf_hot_migration (pod,vnf,vm_pl_name):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    data = {"action":"migration", "vnf": '%s-%s' % (pod,vnf), "vm_name": '%s' % str(vm_pl_name)}
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
        _DEB('MIGRATION ANSWER: %s' % response)
    except Exception as e:
        _ERR('Error in action migration: %s' % str(e))
        raise hss_utils.rosetta.ActionFailure('migration')

    if response['infos']:
       info_msg = 'INFO: %s' % str(response['infos'])
       _INF(info_msg)
    if response['warnings']:
       info_msg = 'Warnings: %s' % str(response['warnings'])
       _WRN(info_msg)
    if response['errors']:
       info_msg = 'Errors: %s' % str(response['errors'])
       _ERR(info_msg)

    return response


def vnf_migration_resize_confirm (pod,vnf,vm_pl_name):
    client = Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_)
    url = "clouds/%s/e3cloudaction/" % pod
    data = {"action":"resize_confirm", "vnf": '%s-%s' % (pod,vnf), "vm_name": '%s' % str(vm_pl_name)}
    _DEB('DATA POST: %s' % data)
    try:
        response = client.custom_post(url, data)
        _DEB('RESIZE CONFIRM ANSWER: %s' % response)
    except Exception as e:
        _ERR('Error in action resize_confirm: %s' % str(e))
        raise hss_utils.rosetta.ActionFailure('resize_confirm')

    if response['infos']:
       info_msg = 'INFO: %s' % str(response['infos'])
       _INF(info_msg)
    if response['warnings']:
       info_msg = 'Warnings: %s' % str(response['warnings'])
       _WRN(info_msg)
    if response['errors']:
       info_msg = 'Errors: %s' % str(response['errors'])
       _ERR(info_msg)

    return response


def vnf_apis_rosetta():
    if _ROSETTA_AVAILABLE_:
        user_config = os.environ.get('ROSETTA_CONFIG', '~/.rosetta_client')
        user_config = os.path.expanduser(os.path.expandvars(user_config))
        if os.path.exists(user_config):
            _DEB('Loading Rosetta client settings from: %s' % user_config)
            with open(user_config, 'r') as conf_file:
                user_config = json.load(conf_file)
                set_rosetta_token(user_config.get('auth-token', _ACCESS_TOKEN_))
                set_rosetta_api_url(user_config.get('api-url', _ACCESS_URL_))
        else:
            _DEB('Config file "%s" not found, using defaults' % user_config)


