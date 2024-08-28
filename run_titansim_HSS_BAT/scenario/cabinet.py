#!/usr/bin/python2.7

import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning

from shared import *
import shared
from hss_utils.st_command import *
from hss_utils.st_command import CommandFailure
import hss_utils.node.cba
import hss_utils.node.tsp
import hss_utils.node.cloud
import hss_utils.rosetta

# Cabinet abstraction
# Handle traffic types and remote configs
class Cabinet(object):
    def __init__(self, name, scenario = '',traffic_module = '', IPv6=False):
        assert(isinstance(name, unicode) or isinstance(name, str))
        self.__name = name
        self.__scenario = scenario
        self.__vip_data = {}
        self.__IPv6 = IPv6
        self.__supported_traffic = []
        self.__GeoRedActive = True
        self.__filter_blades = []
        self.init_vip()

    @property
    def name(self):
        return self.__name

    @property
    def scenario(self):
        return self.__scenario

    @property
    def IPv6(self):
        return self.__IPv6

    def add_filter_blade(self, blade_id):
        assert(isinstance(blade_id, str))
        self.__filter_blades.append(blade_id)

    @property
    def is_GeoRedActive(self):
        return self.__GeoRedActive

    def set_GeoRedActive(self, value):
        self.__GeoRedActive = value

    @property
    def blade_filter_cfg(self):
        cfg = ''
        for blade_id in self.__filter_blades:
            cfg += 'loadFilter:= "%s"\n' % blade_id
        return cfg

    @property
    def traffic_modules(self):
        return self.__supported_traffic

    def add_module(self, traffic_module):
        assert(isinstance(traffic_module, str))
        for module in traffic_module.split():
            if module not in self.__supported_traffic:
                self.__supported_traffic.append(module)

    def check_vector_supplier(self):
        if 'HLR' in self.traffic_modules:
            if self.vector_supplier == 'AVG':
                _WRN('Vector Supplier configured is AVG but user forces HLR')

            self.vector_supplier = 'HLR'

        elif 'AVG' in self.traffic_modules:
            if self.vector_supplier == 'HLR':
                _WRN('Vector Supplier configured is HLR but user forces AVG')

            self.vector_supplier = 'AVG'

        if self.vector_supplier == '':
            _ERR('The vector supplier can not be read. Be sure that you are using the OAM in the IP list (-V) or use -m') 
            quit_program(CMDLINE_ERROR)
        else:
            _INF('Vector supplier to be used is "%s"' % (self.vector_supplier))

    @property
    def is_TSP(self):
        return False

    @property
    def is_CBA(self):
        return False

    @property
    def is_CNHSS(self):
        return False

    def get_vip(self, vip_name):
        assert isinstance(vip_name, str)
        return self.__vip_data[vip_name]

    def set_vip(self, vip_name, new_address):
        assert(isinstance(vip_name, str) and (isinstance(new_address, unicode)or isinstance(new_address, str)))
        if vip_name not in REQUIRED_IP:
            raise KeyError(vip_name)
        self.__vip_data[vip_name] = new_address

    def init_vip(self):
        for vip in REQUIRED_IP:
            self.__vip_data[vip] = ''



class Cabinet_TSP(Cabinet):
    def __init__(self, name, scenario = '',traffic_module = '', zone=1, IPv6=False):
        Cabinet.__init__(self, name, scenario = scenario,traffic_module = traffic_module, IPv6=False)

        self.__traffic_info = {'hss_version':'', 'dia_tcp': '', 'dia_sctp':'','oam':name,
                               'radius':'','extdb':'', 'udm':'','vector_supplier' : '',
                               'controller': '','HSS-MapSriForLcs':False}
        self.__GeoRedZone = 1
        self.add_module(traffic_module)
        self.get_traffic_info_from_cabinet(zone=zone)

        if self.scenario in ['IMS-R', 'EPC-R']:
            self.get_GeoRed_info()
            if self.__GeoRedZone != zone:
                _WRN ('Wrong zone set for %s node. Getting traffic info again' % self.name)
                self.get_traffic_info_from_cabinet(zone=self.__GeoRedZone)

        _DEB('Traffic info from cabinet %s: %s' %  (self.name, self.__traffic_info))
        for vip in REQUIRED_IP:
            try:
                if vip == 'soap':
                    config = shared.get_env_data()
                    data = config.get_cabinet_oam_vip(cabinet=0, IPv6=False)
                    self.set_vip(vip, data,initiate=True)

                elif  self.__traffic_info[vip] in [None, '']:
                    self.set_vip(vip, '0.0.0.0',initiate=True)
                else:
                    self.set_vip(vip, self.__traffic_info[vip],initiate=True)
            except (hss_utils.rosetta.ObjectNotFound, hss_utils.rosetta.RosettaUnavailable,hss_utils.rosetta.InfoNotFound) as e:
                _WRN ('%s' % str(e))
                self.set_vip(vip, '0.0.0.0',initiate=True)
            except KeyError as e:
                self.set_vip(vip, '0.0.0.0',initiate=True)

        self.check_vector_supplier()


    @property
    def hss_version(self):
        return self.__traffic_info['hss_version']

    @property
    def vector_supplier(self):
        return self.__traffic_info['vector_supplier']
 
    @vector_supplier.setter
    def vector_supplier(self, value):
        self.__traffic_info['vector_supplier'] = value
  
    @property
    def specific_nic_sctp(self):
        return self.__traffic_info['dia_sctp'] != self.__traffic_info['dia_tcp']


    def get_traffic_info_from_cabinet(self, zone = 1):
        if self.scenario in ['IMS', 'IMS-SLF', 'IMS-R', 'OAM']:
            traffic_type = 'IMS'
        else:
            traffic_type = 'EPC'

        try:
            access_config = {'host':self.name}
            NODE = hss_utils.node.tsp.Tsp(config = access_config, force_primary = False)
            self.__traffic_info = NODE.get_traffic_info(traffic_type, nodename = shared.NODENAME, zone=zone)
            _DEB('Traffic info read: %s' % ' '.join(self.__traffic_info))
        except CommandFailure as e:
            _ERR('Get traffic info problem: %s' % e)
            quit_program(CONFIGURATION_ERROR)
        except Exception as e:
            _ERR('Get traffic info problem: %s' % e)
            _ERR('Problem reading traffic info from %s. Be sure that you are using the OAM in the IP list (-V).' % self.name)

            quit_program(CMDLINE_ERROR)

    def get_GeoRed_info(self):

        access_config = {'host':self.__traffic_info['controller']}
        NODE = hss_utils.node.tsp.Tsp(config = access_config)

        geoRedZone, geoRedActive = NODE.get_GeoRed_info()
        if geoRedZone:
            self.__GeoRedZone = geoRedZone
            self.set_GeoRedActive = geoRedActive

        _INF('"%s" GeoRed info: zone %s Active %s' % (self.__traffic_info['controller'], self.__GeoRedZone, self.is_GeoRedActive))

    @property
    def is_TSP(self):
        return True

    @property
    def HLR_configured(self):
        return self.__traffic_info['vector_supplier'] == 'HLR'

    @property
    def use_HLR(self):
        return self.HLR_configured

    @property
    def use_AVG(self):
        return not self.use_HLR

    @property
    def __use_MapSriForLcs(self):
        return self.__traffic_info['HSS-MapSriForLcs']

    @property
    def __isEsmActive(self):
        return False

    @property
    def is_monolithic(self):
        return  self.get_vip('extdb') == '0.0.0.0'

    def set_vip(self, vip_name, new_address,initiate=False):
        if vip_name not in REQUIRED_IP:
            raise KeyError(vip_name)
        else:
            # Do nothing if address is empty
            if not new_address:
                return

            if not validate_ip(new_address,IPv6=False):
                _ERR ('%s %s shall be always an IPv4 address' % (vip_name,new_address))
                quit_program(CMDLINE_ERROR)

            if not initiate and self.get_vip(vip_name) != new_address and self.get_vip(vip_name) != '0.0.0.0':
                _WRN('User set %s as %s but node is configured with %s' % (new_address, vip_name, self.get_vip(vip_name)))

            Cabinet.set_vip(self,vip_name, new_address)

    @property
    def __vip_cfg(self):
        return '''
vip_oam:= "%s"
vip_dia_tcp:= "%s"
vip_dia_sctp:= "%s"
vip_radius:= "%s"
vip_controller:= "%s"
vip_udm:="%s"
''' % (self.get_vip('oam'), self.get_vip('dia_tcp'), self.get_vip('dia_sctp'),
       self.get_vip('radius'), self.get_vip('controller'), self.get_vip('udm'))

    @property
    def __layer_cfg(self):
        if self.is_monolithic:
            return '''
layer:= false
remGroupName:= EXCLUDE_ON_MONOLITHIC
'''
        else:
            return '''
layer:= true
vip_soap:= "%s"
ExtDB_ip:= "%s"
defParam:= :EXTRA_TIME:1.5
remGroupName:= EXCLUDE_ON_LAYER
''' % (self.get_vip('soap'), self.get_vip('extdb'))


    @property
    def config_file_contents(self):
        return (self.__vip_cfg +
                self.__layer_cfg +
                'remGroupName:= EXCLUDE_WITH_%s\n' % ('HLR' if self.use_HLR else 'AVG') +
                'remGroupName:= EXCLUDE_ON_TSP\n' +
                '%s' % ('remGroupName:= EXCLUDE_FOR_ESM_INACTIVE\n'  if not self.__isEsmActive else '') +
                ('defParam:= :MAPSRIFORLCS:%s\n' % ('true' if self.__use_MapSriForLcs else 'false')) +
                ('defParam:= :IPV6:%s\n' % ('true' if self.IPv6 else 'false')) +
                ('defParam:= :AUTH_VECT_SUPP_HLR:%s\n' % ('true' if self.use_HLR else 'false')) +
                'defParam:= q:PLATFORM:CBA\n' +
                'defParam:= q:NODE_TYPE:CBA\n' +
                self.blade_filter_cfg)

class Cabinet_CBA(Cabinet):
    def __init__(self, name, scenario = '',traffic_module = '', zone=1, IPv6=False):
        Cabinet.__init__(self, name, scenario = scenario,traffic_module = traffic_module, IPv6=IPv6)

        self.__traffic_info = {'hss_version':'', 'dia_tcp': '', 'dia_sctp':'','soap':'','soap_ldap':'','oam':name,
                               'radius':'','extdb':'', 'udm':'','vector_supplier' : '',
                               'controller': '','HSS-MapSriForLcs':False,'HSS-EsmIsActive':False,
                               'HSS-CommonAuthenticationVectorSupplier':''}

        self.add_module(traffic_module)
        self.get_traffic_info_from_cabinet(IPv6=self.IPv6)
        _DEB('Traffic info from cabinet %s: %s' %  (self.name, self.__traffic_info))
        for vip in REQUIRED_IP:
            try:
                if  self.__traffic_info[vip] in [None, '']:
                    data = '::' if (self.IPv6 and vip in ['dia_tcp','dia_sctp','extdb','udm','soap','soap_ldap']) else '0.0.0.0'
                    self.set_vip(vip, data,initiate=True)
                else:
                    self.set_vip(vip, self.__traffic_info[vip],initiate=True)
            except (hss_utils.rosetta.ObjectNotFound, hss_utils.rosetta.RosettaUnavailable,hss_utils.rosetta.InfoNotFound) as e:
                _WRN ('%s' % str(e))
                data = '::' if (self.IPv6 and vip in ['dia_tcp','dia_sctp','extdb','soap','udm','soap_ldap']) else '0.0.0.0'
                self.set_vip(vip, data,initiate=True)
            except KeyError as e:
                data = '::' if (self.IPv6 and vip in ['dia_tcp','dia_sctp','extdb','soap','udm','soap_ldap']) else '0.0.0.0'
                self.set_vip(vip, data,initiate=True)

        self.check_vector_supplier()

    @property
    def hss_version(self):
        return self.__traffic_info['hss_version']

    @property
    def vector_supplier(self):
        return self.__traffic_info['vector_supplier']
 
    @vector_supplier.setter
    def vector_supplier(self, value):
        self.__traffic_info['vector_supplier'] = value
 
    @property
    def specific_nic_sctp(self):
        return self.__traffic_info['dia_sctp'] != self.__traffic_info['dia_tcp']

    def get_traffic_info_from_cabinet(self, IPv6=False):
        try:
            access_config = {'host':self.name, 'user':shared.CLISS_USER}
            NODE = hss_utils.node.cba.Cba(config = access_config)
            self.__traffic_info.update(NODE.get_traffic_info(traffic_type=self.scenario,IPv6=IPv6))

        except CommandFailure as e:
            _ERR('Get traffic info problem: %s' % e)
            quit_program(CONFIGURATION_ERROR)
        except Exception as e:
            _ERR('Get traffic info problem: %s' % e)
            _ERR('Problem reading traffic info from %s. Be sure that you are using the OAM in the IP list (-V) and port 22 is open for ssh connections.' % self.name)

            quit_program(CMDLINE_ERROR)

    @property
    def is_CBA(self):
        return True

    @property
    def HLR_configured(self):
        return self.__traffic_info['vector_supplier'] == 'HLR'

    @property
    def use_HLR(self):
        return self.HLR_configured

    @property
    def use_AVG(self):
        return not self.use_HLR

    @property
    def __use_MapSriForLcs(self):
        return self.__traffic_info['HSS-MapSriForLcs']

    @property
    def __isEsmActive(self):
        try:
            return self.__traffic_info['HSS-EsmIsActive']
        except KeyError:
            return True

    def set_vip(self, vip_name, new_address,initiate=False):
        if vip_name not in REQUIRED_IP:
            raise KeyError(vip_name)
        else:
            # Do nothing if address is empty
            if not new_address:
                return

            # Jira HSSSTT-196 UDM migth be IPv4 although running traffic IPv6
            if vip_name in ['dia_tcp','dia_sctp','extdb','soap','soap_ldap'] and not validate_ip(new_address,IPv6=self.IPv6):
                _ERR ('%s %s must be an %s address' % (vip_name,new_address, ('IPv6' if self.IPv6 else 'IPv4')))
                quit_program(CMDLINE_ERROR)

            if vip_name in ['oam','radius','controller'] and not validate_ip(new_address,IPv6=False):
                _ERR ('%s %s must be always an IPv4 address' % (vip_name,new_address))
                quit_program(CMDLINE_ERROR)

            if vip_name in ['udm']:
                if self.IPv6:
                    if not validate_ip(new_address,IPv6=self.IPv6) and not validate_ip(new_address,IPv6=False):
                        _ERR ('%s %s is not an IPv4 nor IPv6 address' % (vip_name,new_address))
                        quit_program(CMDLINE_ERROR)
                else:
                    if not validate_ip(new_address,IPv6=False):
                        _ERR ('%s %s is not an IPv4 address' % (vip_name,new_address))
                        quit_program(CMDLINE_ERROR)

            if not initiate and self.get_vip(vip_name) != new_address and self.get_vip(vip_name) not in ['0.0.0.0','::']:
                _WRN('User set %s as %s but node is configured with %s' % (new_address, vip_name, self.get_vip(vip_name)))

            Cabinet.set_vip(self, vip_name, new_address)

    @property
    def __vip_cfg(self):
        external_db = self.get_vip('extdb')
        if external_db == '0.0.0.0':
            _ERR('For CBA platform is mandatory to set Ip for ExtDb. Use option -V')
            quit_program(CMDLINE_ERROR)

        return '''
vip_oam:= "%s"
vip_dia_tcp:= "%s"
vip_dia_sctp:= "%s"
vip_radius:= "%s"
vip_controller:= "%s"
vip_udm:="%s"
vip_soap:= "%s"
vip_soap_ldap:= "%s"
ExtDB_ip:= "%s"
''' % (self.get_vip('oam'), self.get_vip('dia_tcp'), self.get_vip('dia_sctp'),
       self.get_vip('radius'), self.get_vip('controller'), self.get_vip('udm'),
       self.get_vip('soap'), self.get_vip('soap_ldap'), external_db)


    @property
    def hss_CommonAuthenticationVectorSupplier(self):
        info = ''
        if self.__traffic_info['HSS-CommonAuthenticationVectorSupplier'] == 'ARPFforAllUsers':
            info = 'remGroupName:= EXCLUDE_WITH_ARPF\n'

        elif self.__traffic_info['HSS-CommonAuthenticationVectorSupplier'] in ['NONE','None','']:
            info = 'remGroupName:= EXCLUDE_WITH_ARPF_NONE\n'

        return info

    @property
    def config_file_contents(self):
        _DEB('config_file contensts CBA %s' %  self.name)
        return (self.__vip_cfg +
                'remGroupName:= EXCLUDE_WITH_%s\n' % ('HLR' if self.use_HLR else 'AVG') +
                'remGroupName:= EXCLUDE_ON_CBA\n' +
                'remGroupName:= EXCLUDE_ON_LAYER\n' +
                'layer:= true\n' +
                'defParam:= :EXTRA_TIME:1.5\n' +
                '%s' % ('remGroupName:= EXCLUDE_FOR_ESM_INACTIVE\n'  if not self.__isEsmActive else '') +
                ('defParam:= :MAPSRIFORLCS:%s\n' % ('true' if self.__use_MapSriForLcs else 'false')) +
                ('defParam:= :IPV6:%s\n' % ('true' if self.IPv6 else 'false')) +
                ('defParam:= :AUTH_VECT_SUPP_HLR:%s\n' % ('true' if self.use_HLR else 'false')) +
                'defParam:= q:PLATFORM:CBA\n' +
                'defParam:= q:NODE_TYPE:CBA\n' +
                self.blade_filter_cfg +
                self.hss_CommonAuthenticationVectorSupplier)


class Cabinet_CNHSS(Cabinet):
    def __init__(self, eccd_type, access_config, appid, scenario = '',traffic_module = '', zone=1, IPv6=False):
        Cabinet.__init__(self, eccd_type, scenario = scenario,traffic_module = traffic_module, IPv6=IPv6)

        self.__traffic_info = {'hss_version':'', 'oam':'0.0.0.0',
                               'dia_tcp':'0.0.0.0', 'dia_sctp':'0.0.0.0',
                               'radius':'0.0.0.0', 'extdb':'0.0.0.0','soap':'0.0.0.0',
                               'udm':'0.0.0.0', 'controller': '0.0.0.0',
                               'vector_supplier' : 'AVG','HSS-MapSriForLcs':False,
                               'HSS-EsmIsActive':False
                }

        self.__eccd_type = eccd_type
        self.__access_config = access_config
        self.__appid = appid

        if appid:
            self.get_traffic_info_from_cabinet()
            _DEB('Traffic info from cabinet %s: %s' %  (self.name, self.__traffic_info))

        for vip in REQUIRED_IP: 

            try:
                if  self.__traffic_info[vip] in [None, '']:
                    data = '::' if (self.IPv6 and vip in ['dia_tcp','dia_sctp','soap','extdb']) else '0.0.0.0'
                    self.set_vip(vip, data,initiate=True)
                else:
                    self.set_vip(vip, self.__traffic_info[vip],initiate=True)
            except (hss_utils.rosetta.ObjectNotFound, hss_utils.rosetta.RosettaUnavailable,hss_utils.rosetta.InfoNotFound) as e:
                _WRN ('%s' % str(e))
                data = '::' if (self.IPv6 and vip in ['dia_tcp','dia_sctp','soap','extdb']) else '0.0.0.0'
                self.set_vip(vip, data,initiate=True)
            except KeyError as e:
                data = '::' if (self.IPv6 and vip in ['dia_tcp','dia_sctp','extdb','soap','udm','soap_ldap']) else '0.0.0.0'
                self.set_vip(vip, data,initiate=True)


    @property
    def hss_version(self):
        return self.__traffic_info['hss_version']

    @property
    def specific_nic_sctp(self):
        return self.__traffic_info['dia_sctp'] != self.__traffic_info['dia_tcp']


    def get_traffic_info_from_cabinet(self):
        try:
            if self.__eccd_type == 'IBD':
                NODE = hss_utils.node.cloud.CloudIBD(config = self.__access_config)
            else:
                NODE = hss_utils.node.cloud.CloudANS(config = self.__access_config)

            self.__traffic_info.update(NODE.get_traffic_info(self.__appid))

            _DEB('Traffic info read: %s' % ' '.join(self.__traffic_info))
        except CommandFailure as e:
            _ERR('Get traffic info problem: %s' % e)
            quit_program(CONFIGURATION_ERROR)
        except Exception as e:
            _ERR('Get traffic info problem: %s' % e)
            quit_program(CMDLINE_ERROR)


    @property
    def is_CNHSS(self):
        return True

    def set_vip(self, vip_name, new_address,initiate=False):
        if vip_name not in REQUIRED_IP:
            raise KeyError(vip_name)
        else:
            # Do nothing if address is empty
            if not new_address:
                return

            if vip_name in ['dia_tcp','dia_sctp','soap','extdb']and not validate_ip(new_address,IPv6=self.IPv6):
                _ERR ('%s %s shall be an %s address' % (vip_name,new_address, ('IPv6' if self.IPv6 else 'IPv4')))
                quit_program(CMDLINE_ERROR)

            if vip_name in ['oam','radius','controller']and not validate_ip(new_address,IPv6=False):
                _ERR ('%s %s shall be always an IPv4 address' % (vip_name,new_address))
                quit_program(CMDLINE_ERROR)

            if not initiate and self.get_vip(vip_name) != new_address and self.get_vip(vip_name) not in ['0.0.0.0','::']:
                _WRN('User set %s as %s but node is configured with %s' % (new_address, vip_name, self.get_vip(vip_name)))

            Cabinet.set_vip(self, vip_name, new_address)


    @property
    def __vip_cfg(self):
        return '''
vip_oam:= "%s"
vip_dia_tcp:= "%s"
vip_dia_sctp:= "%s"
vip_radius:= "%s"
vip_controller:= "%s"
vip_udm:="%s"
ExtDB_ip:= "%s"
vip_soap:= "%s"
''' % (self.get_vip('oam'), self.get_vip('dia_tcp'), self.get_vip('dia_sctp'),
       self.get_vip('radius'), self.get_vip('controller'), self.get_vip('udm'),
       self.get_vip('extdb'), self.get_vip('soap'))

    @property
    def config_file_contents(self):
        cfg = self.__vip_cfg
        cfg += 'layer:= true\n'
        cfg += 'defParam:= q:NODE_TYPE:CNHSS\n'
        cfg += 'defParam:= q:CNHSS_APPID:%s\n' % self.__appid
        cfg += 'defParam:= :EXTRA_TIME:1.5\n'
        cfg += 'defParam:= :NUMBERLDAPPROXIES:1\n'
        cfg += 'defParam:= :LDAP_ENABLED:true\n'
        cfg += 'remGroupName:= EXCLUDE_WITH_AVG\n'
        cfg += 'remGroupName:= EXCLUDE_ON_LAYER\n' 
        cfg += 'defParam:= :MAPSRIFORLCS:false\n'
        cfg += 'defParam:= :NONIPPDNAPN:false\n'
        cfg += 'defParam:= :AUTH_VECT_SUPP_HLR:false\n'
        cfg += 'defParam:= :IPV6:%s\n' % ('true' if self.IPv6 else 'false')
        if self.__appid:
            cfg += 'defParam:= :SUT_DIAMETER_PORT:%s\n' % self.__traffic_info['dia_port']
        cfg += 'defParam:= :SUT_SOAP_PORT:%s\n' % self.__traffic_info.get('soap_port',-1)
        return cfg



