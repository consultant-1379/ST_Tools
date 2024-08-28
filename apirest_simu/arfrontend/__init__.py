#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

'''API Rest simulator: frontends base module'''


import string
import fnmatch
import logging
import threading


__version__ = '1.0'


class FrontendBase(threading.Thread):
    '''
    Properties container for servers
    '''
    def __init__(self, api_handler, address='0.0.0.0', port=8080, ssl=None):
        super(FrontendBase, self).__init__()
        self._api_handler_ = api_handler
        self._addr_ = address
        self._port_ = port
        self._ssl_ = ssl

    @property
    def sap(self):
        return (self._addr_, self._port_)

    @property
    def api_handler(self):
        return self._api_handler_
    
    def run(self):
        raise NotImplementedError('BaseServer() is not runnable')

    def __str__(self):
        return 'frontend at {}:{}{}'.format(
            self._addr_,
            self._port_,
            ' (with SSL/TSL)' if self._ssl_ is not None else ''
        )


## Factory ##

_FRONTENDS_ = {}
import arfrontend.http11
_FRONTENDS_['http1'] = arfrontend.http11.Frontend
try:
    import arfrontend.http2
    _FRONTENDS_['http2'] = arfrontend.http2.Frontend
except Exception as error:
    logging.warning('HTTP2 frontend not available: {}'.format(error))


def new(frontend_type, address, port, ssl, handler):
    if frontend_type not in _FRONTENDS_:
        raise ValueError(
            'Invalid frontend_type, available: {}'.format(', '.join(list(_FRONTENDS_.keys())))
        )
    return _FRONTENDS_[frontend_type](handler, address=address, port=port, ssl=ssl)
