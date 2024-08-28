#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

'''
HTTP/1.1 frontend
'''

import json
import logging
from socketserver import ThreadingMixIn, TCPServer
from http.server import BaseHTTPRequestHandler

from arfrontend import FrontendBase


DEFAULT_PORT = 8081

CONTENT_LENGTH = 'content-length'
CONTENT_TYPE = 'content-type'

JSON_DATA = 'application/json'


class _H11Handler_(BaseHTTPRequestHandler):
    def _read_data_(self):
        data = None
        data_len = self._get_header_(CONTENT_LENGTH)
        if data_len:
            try:
                data_len = int(data_len)
            except Exception as error:
                logging.warning('Unknown value at {} header: {}'.format(CONTENT_LENGTH, data_len))
                data_len = 0
            data = self.rfile.read(data_len)
            # FIXME: hardcoded encoding is BAD, get it from headers if available
            data = data.decode('utf-8')
            data_format = self._get_header_(CONTENT_TYPE)
            if data_format.lower() == JSON_DATA:
                try:
                    data = json.loads(data)
                except Exception as error:
                    logging.warning(
                        'Content type is JSON but data cannot be parsed: {}'.format(error)
                    )
            elif data_format.lower() == TEXT_PLAIN:
                pass
            else:
                logging.warning('Unsupported MIME: {}'.format(data_format))
        return data
    
    def _get_header_(self, header_name):
        '''Return the first occurence of "header_name" or None'''
        for header in self.headers.keys():
            if header_name.lower() == header.lower():
                return self.headers[header]
        logging.debug('Expected header does not found: {}'.format(header_name))

    def do_GET(self):
        logging.debug('GET: {}'.format(self.path))
        data = self._read_data_()
        logging.debug('Dispatching {} {}'.format('GET', self.path))
        response = self._api_handler_.run_request('GET', self.path, data)
        self.send_response(response.status_code)
        for header in response.headers:
            self.send_header(header, response.headers[header])
        self.end_headers()
        self.wfile.write(response.data)
        
    def do_POST(self):
        logging.debug('POST: {}'.format(self.path))
        data = self._read_data_()
        logging.debug('Dispatching {} {}'.format('POST', self.path))
        response = self._api_handler_.run_request('POST', self.path, data)
        self.send_response(response.status_code)
        for header in response.headers:
            self.send_header(header, response.headers[header])
        self.end_headers()
        self.wfile.write(response.data)


class ThreadingSimpleServer(ThreadingMixIn, TCPServer):
    def __init__(self, server_address, request_handler, ssl=None, bind_and_activate=True):
        super(ThreadingSimpleServer, self).__init__(server_address, request_handler, False)
        if ssl is not None:
            self.socket = self._ssl_context_.wrap_socket(self.socket, server_side=True)
        if bind_and_activate:
            self.server_bind()
            self.server_activate()
            

class HTTP1Server(ThreadingSimpleServer):
    def __init__(self, server_address, api_handler, ssl=None):
        # Inject api_handler in the class as private attribute
        meta_class = type('meta_class', (_H11Handler_,), dict(_api_handler_=api_handler))       
        super(HTTP1Server, self).__init__(server_address, meta_class, ssl)


class Frontend(FrontendBase):
    def __init__(self, api_handler, address='0.0.0.0', port=DEFAULT_PORT, ssl=None):
        super(Frontend, self).__init__(api_handler, address, port, ssl)
        self._server_ = HTTP1Server(self.sap, self.api_handler, ssl=ssl)
        self._server_.allow_reuse_address = True
        self._running_ = False

    @property
    def running(self):
        return self._running_
    
    def stop(self):
        self._server_.shutdown()
        self._running_ = False
        
    def run(self):
        logging.debug('HTTP/1 thread server STARTED')
        self._running_ = True
        self._server_.serve_forever()
        logging.debug('HTTP/1 thread server CLOSED')

    def __str__(self):
        return 'HTTP/1 {}'.format(super(Frontend, self).__str__())
    
