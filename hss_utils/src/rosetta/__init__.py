#!/usr/bin/env python
# -*- mode=python; coding: utf-8 -*-
#

'''
This module is a wrapper for apirestmgmt (used to access Rosetta).

It provides basic funcionality to fetch typical data like available
test channels, nodes in a test channel and data for a given node.

By default Rosetta access is configured but access token must be provided.
All this settings can be modified via config file in json format. The location
of this file can be setted by ROSETTA_CONFIG environment variable. If this
variable is not setted, $HOME/.rosetta_client is used by default.

Recognized key values in the config file are:

  "auth-token": authorization token used to make requests to Rosetta
  "api-url": URL for Rosetta API
  "default-ndo": use this NDO as default
'''

import os
import json
import urllib2
import e3utils.config

import e3utils.log as logging
_DEB = logging.internal_debug
_WRN = logging.internal_warning
_ERR = logging.internal_error
_INF = logging.internal_info

try:
    from e3utils.clients.rosetta import Rosetta
    from e3utils.exceptions import ElementNotExistinRosetta
    _ROSETTA_AVAILABLE_ = True
except ImportError, e:
    _WRN('Cannot import e3utils: %s' % e)
    _WRN('Rosetta access will be disabled')
    _ROSETTA_AVAILABLE_ = False
    class ElementNotExistinRosetta(Exception):
        pass

# Custom queries
__GET_RELATED__ = 'nodes/%(node)s/related_environments/?format=json'

# Default values
_ACCESS_TOKEN_ = None
_ACCESS_URL_ = None
#_ACCESS_URL_ = 'http://rosetta.seli.gic.ericsson.se/api'

class RosettaUnavailable(Exception):
    def __str__(self):
        return 'Cannot contact rosetta in %s' % _ACCESS_URL_


class ObjectNotFound(Exception):
    def __init__(self, object_name):
        self.__obj = object_name

    def __str__(self):
        return 'Object "%s" not found in rosetta' % self.__obj

class InfoNotFound(Exception):
    def __init__(self, object_name):
        self.__obj = object_name

    def __str__(self):
        return 'Info "%s" not found in rosetta' % self.__obj

class ActionFailure(Exception):
    def __init__(self, object_name):
        self.__obj = object_name

    def __str__(self):
        return 'Action "%s" execution failed' % self.__obj

def rosetta_manager():
    if not _ROSETTA_AVAILABLE_:
        return DummyRosetta()

    if _ACCESS_TOKEN_ is None:
        _WRN('.rosetta_client not found. Using .e3config!')
        return Rosetta()

    return Rosetta(url=_ACCESS_URL_,token= _ACCESS_TOKEN_, timeout=120)

def set_rosetta_token(new_token):
    global _ACCESS_TOKEN_
    _ACCESS_TOKEN_ = new_token


def set_rosetta_api_url(new_url):
    global _ACCESS_URL_
    _ACCESS_URL_ = new_url


def related_environments(node_name):
    # Get related environements
    rosetta = rosetta_manager()
    return rosetta.environments_for_node(node_name)

def get_environment(env):
    # Get related environements
    rosetta = rosetta_manager()
    return rosetta.get(env, 'Environment')

def get_baseline(baseline):
    # Get related environements
    rosetta = rosetta_manager()
    return rosetta.get(baseline, 'SoftwareBaseline')


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
        _WRN('Config file "%s" not found, using defaults' % user_config)


def get_file_from_rosetta(url):
    if _ACCESS_URL_:
        access_url = _ACCESS_URL_
    else:
        access_url = e3utils.config.user('rosetta_api', required=True)
    assert(access_url.startswith('http://') or access_url.startswith('https://'))
    if _ACCESS_TOKEN_:
        token = _ACCESS_TOKEN_
    else:
        token = e3utils.config.user('rosetta_auth_token', default_value=None)

    request_headers = {
    'Authorization': "Token %s" % token
    }
    _DEB('GET file from url : %s/%s' % (access_url, url))
    request = urllib2.Request("%s/%s" % (access_url, url), headers=request_headers)
    response = urllib2.urlopen(request).read()
    return response


class DummyRosetta(object):
    '''This handler mocks RosettaRestMgmt()'''
    def environments_name(self):
        _WRN('DummyRosetta: environments_name()')
        return []

    def environments_name_by_ndo(self, ndo):
        _WRN('DummyRosetta: environments_name_by_ndo(%s)' % ndo)
        return []

    def custom_query(self, query):
        _WRN('DummyRossetta: custom_query(%s)' % repr(query))
        raise RosettaUnavailable()

