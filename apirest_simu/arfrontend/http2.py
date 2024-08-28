#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

'''
HTTP/2 backend
'''

import io
import asyncio
import logging


from arfrontend import FrontendBase

try:
    import nghttp2
    from nghttp2 import BaseRequestHandler, HTTP2Server
    _NGHTTP2_ = True
except ImportError:
    logging.warning('nghttp2 python wrapper not found!')
    logging.warning('Cannot use HTTP/2 server!')
    class BaseRequestHandler:
        pass
    class HTTP2Server:
        pass
    _NGHTTP2_ = False


DEFAULT_PORT = 8082


class _Body_:
    '''Buffered responses for HTTP/2'''
    def __init__(self, handler, response):
        self.handler = handler
        self.handler.eof = False
        self.handler.buf = io.BytesIO(response.data)

    def generate(self, n):
        data = self.handler.buf.read1(n)
        if not data and not self.handler.eof:
            return None, nghttp2.DATA_DEFERRED
        return data, nghttp2.DATA_EOF if self.handler.eof else nghttp2.DATA_OK


class _H2Handler_(BaseRequestHandler):
    request_data = None

    def get_header(self, header, default_value=None):
        for candidate_header, value in self.headers:
            if header.lower() == candidate_header.decode('utf-8').lower():
                return value.decode('utf-8')
        return default_value

    def on_headers(self):
        logging.debug('Headers: {}'.format(self.headers))

    def on_data(self, data):
        logging.debug('Data: {}'.format(data))
        self.request_data = data

    def on_request_done(self):
        method = self.get_header(':method', 'UNKNOWN')
        path = self.get_header(':path', '/')
        logging.debug('Dispatching {} {}'.format(method, path))
        response = self._api_handler_.run_request(method, path, self.request_data)
        body = _Body_(self, response)        
        self.send_response(
            status=response.status_code, headers=response.headers_as_list, body=body.generate
        )
        self.request_data = None


class HTTP2APIServer(HTTP2Server):
    def __init__(self, server_address, api_handler, ssl=None):
        # Inject api_handler in the class as private attribute
        meta_class = type('meta_class', (_H2Handler_,), dict(_api_handler_=api_handler))
        super(HTTP2APIServer, self).__init__(server_address, meta_class, ssl)


class Frontend(FrontendBase):
    def __init__(self, api_handler, address='0.0.0.0', port=DEFAULT_PORT, ssl=None):
        if not _NGHTTP2_:
            raise NotImplementedError('HTTP/2 not available due to missing library')
        super(Frontend, self).__init__(api_handler, address, port, ssl)
        self._server_ = HTTP2APIServer(self.sap, self.api_handler, ssl=ssl)

    @property
    def running(self):
        return self._server_.server.is_serving()
    
    def stop(self):
        import time
        self._server_.server.close()
        self._server_.loop.call_soon_threadsafe(self._server_.loop.stop)
        
    def run(self):
        logging.debug('HTTP/2 event loop STARTED')
        asyncio.set_event_loop(self._server_.loop)
        self._server_.serve_forever()
        logging.debug('HTTP/2 event loop CLOSED')

    def __str__(self):
        return 'HTTP/2 {}'.format(super(Frontend, self).__str__())

