#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

'''API Rest simulator: backend'''

import re
import string
import fnmatch
import logging


__version__ = '1.0'


NOT_FOUND = (404, '''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
        "http://www.w3.org/TR/html4/strict.dtd">
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html;charset=utf-8">
        <title>Error response</title>
    </head>
    <body>
        <h1>Error response</h1>
        <p>Error code: ${STATUS_CODE}</p>
        <p>Path: Object not found (${PATH}).</p>
        <p>Error code explanation: HTTPStatus.NOT_FOUND - Server does not have this object.</p>
    </body>
</html>''')

UNSUPPORTED_METHOD = (503, '''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
        "http://www.w3.org/TR/html4/strict.dtd">
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html;charset=utf-8">
        <title>Error response</title>
    </head>
    <body>
        <h1>Error response</h1>
        <p>Error code: ${STATUS_CODE}</p>
        <p>Message: Unsupported method (${METHOD}).</p>
        <p>Error code explanation: HTTPStatus.NOT_IMPLEMENTED - Server does not support this operation.</p>
    </body>
</html>''')


class Headers(dict):
    '''
    Case-insensitive dictionary
    Taken from: https://stackoverflow.com/questions/3296499/case-insensitive-dictionary-search
    '''
    def __init__(self, data):
        self._proxy_ = dict((k.lower(), k) for k in data)
        for k in data:
            self[k] = data[k]

    def __contains__(self, k):
        return k.lower() in self._proxy_

    def __delitem__(self, k):
        try:
            key = self._proxy_[k.lower()]
        except KeyError:
            raise KeyError(k)
        super(Headers, self).__delitem__(key)
        del self._proxy_[k.lower()]

    def __getitem__(self, k):
        try:
            key = self._proxy_[k.lower()]
        except KeyError:
            raise KeyError(k)
        return super(Headers, self).__getitem__(key)

    def get(self, k, default=None):
        return self[k] if k in self else default

    def __setitem__(self, k, v):
        super(Headers, self).__setitem__(k, v)
        self._proxy_[k.lower()] = k

    def update(self, other_dict):
        for k in other_dict:
            self[k] = other_dict[k]


class Response:
    '''Handle data of an HTTP response'''
    def __init__(self, status_code=0, data='', headers={}, method='UNKNOWN', path='/'):
        self._code_ = int(status_code)
        self._method_ = method
        self._headers_ = Headers(headers)
        self._path_ = path
        self._data_ = ''
        self.data = data

    @property
    def status_code(self):
        if not self._code_:
            # 200 if data / 204 if no data
            return 200 if str(self) else 204
        return self._code_

    @property
    def method(self):
        return self._method_

    @method.setter
    def method(self, new_method):
        self._method_ = new_method

    @property
    def path(self):
        return self._path_

    @property
    def data(self):
        return str(self).encode('utf-8')

    @data.setter
    def data(self, new_data):
        self._data_ = string.Template(new_data)
        if self.data:
            self.headers.update({'Content-Length': len(self.data)})
        
    @property
    def headers(self):
        return self._headers_

    @property
    def headers_as_list(self):
        headers = []
        for header in self.headers:
            headers.append((header, str(self.headers[header])))
        return headers

    def update_context(self, method, path):
        self._method_ = method
        self._path_ = path
        return self
        
    def __str__(self):
        return self._data_.safe_substitute({
            'STATUS_CODE': self.status_code,
            'METHOD': self.method,
            'PATH': self.path
        })


class APIRest:
    '''
    Simple query/response API implementation
    '''
    def __init__(self, api_config={}):
        self._base_config_ = api_config

        # Pre-compile regexp
        self._translation_ = {}
        self._compiled_ = {}
        for method in self.available_methods:
            self._compiled_[method] = {}
            for path in self._base_config_[method]:
                candidate = re.compile(fnmatch.translate(path))
                self._translation_[candidate] = path
                self._compiled_[method][candidate] = Response(
                    status_code=self._base_config_[method][path].get('status', 0),
                    data=self._base_config_[method][path].get('data', ''),
                    headers=self._base_config_[method][path].get('additional_headers', {})
                )

    @property
    def available_methods(self):
        return list(self._base_config_.keys())
    
    def run_request(self, method, path, data):
        if method not in self.available_methods:
            return Response(*UNSUPPORTED_METHOD, method=method, path=path)
        for candidate in self._compiled_[method]:
            if candidate.match(path):
                logging.debug('Match: {} ({})'.format(path, method))
                return self._compiled_[method][candidate].update_context(method, path)
            else:
                logging.debug('Not match with: {}'.format(self._translation_[candidate]))
        return Response(*NOT_FOUND, method=method, path=path)


## Factory ##

_APIS_ = {
    'rest': APIRest
}

def new(api_type, api_config={}):
    if api_type not in _APIS_:
        raise ValueError(
            'Invalid api_type: "{}". Available: {}'.format(api_type, ', '.join(list(_APIS_)))
        )
    return _APIS_[api_type](api_config)
