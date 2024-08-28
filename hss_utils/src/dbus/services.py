#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import json
import time
import threading
import e3utils.clients.dbuscomm

import e3utils.log as logging
_DEB = logging.internal_debug
_WRN = logging.internal_warning
_ERR = logging.internal_error
_INF = logging.internal_info

_BAD_REQUEST_FORMAT_ = json.dumps({'error': 'Bad request format'})
_INVALID_REQUEST_OPERATION_ = lambda op: json.dumps({
    'error': 'Invalid request operation: %s' % op})
_REQUEST_RAISE_EXCEPTION_ = lambda e: json.dumps({
    'error': str(e),
    'type': e.__class__.__name__,
    'args': e.args})
_REQUEST_DONE_ = lambda result: json.dumps({'result': result})

_SERVICE_PING_ = 'ping'
_SERVICE_PONG_ = 'pong'

_LONG_TIMEOUT_ = 2147400


class CannotConnect(Exception):
    def __str__(self):
        return 'Cannot connect to service via DBus'


class Disconnected(Exception):
    def __str__(self):
        return 'Remote service is down'


def remote(func):
    ''' Decorator used to forward client calls to remote service '''
    def wrapper(*args, **kwargs):
        request = json.dumps({
            'op': func.__name__,
            'args': args[1:],
            'kwargs': kwargs
        })
        client = args[0]
        if not isinstance(client, Client):
            raise ValueError('@remote decorator is for Client() objects only')
        result = client.send_request(request)
        if not isinstance(result, dict):
            _WRN('Unexpected response: %s' % repr(result))
            raise ValueError(result)
        if 'error' in result.keys():
            try:
                e = eval('%s(*%s)' % (result['type'], result['args']))
            except (NameError, KeyError):
                raise Exception(result['error'])
            raise e
        if 'result' in result.keys():
            return result['result']
    return wrapper


class Service(threading.Thread):
    '''
    Synchronous service base class
    '''
    def __init__(self, dbus_obj, dbus_path):
        super(Service, self).__init__()
        self.__dbus_listener = None
        self.__dbus_obj = dbus_obj
        self.__dbus_path = dbus_path
        
    @property
    def running(self):
        if self.__dbus_listener is None:
            return False
        return self.__dbus_listener.running
    
    def run(self):
        _DEB('Starting service %s' % self.__class__.__name__)
        self.__dbus_listener = e3utils.clients.dbuscomm.Listener(
            self.__dbus_obj, self.__dbus_path,
            self.__process_request__,
            only_session=False)

        _DEB('Entering service loop for %s' % self.__class__.__name__)
        self.__dbus_listener.run(main_loop=False)
        while self.__dbus_listener.running:
            if not self.__dbus_listener.iterate():
                time.sleep(.1)
        _DEB('Exit service loop for %s' % self.__class__.__name__)
        self.__dbus_listener = None

    def start(self):
        super(Service, self).start()
        # Allow service to attach to dbus
        time.sleep(1.0)

    def stop(self):
        if self.__dbus_listener is None:
            return
        _DEB('Stopping service %s' % self.__class__.__name__)
        self.__dbus_listener.stop()

    def __process_request__(self, request):
        _DEB('Request: %s' % repr(request))
        try:
            request = json.loads(request)
            op = request['op']
        except Exception as e:
            _WRN('Wrong request format (%s)' % e)
            return _BAD_REQUEST_FORMAT_
        args = request.get('args', tuple())
        kwargs = request.get('kwargs', dict())

        # Avoid calling to basic (protected) service methods
        if op in ['start', 'stop', 'run', 'running']:
            return _INVALID_REQUEST_OPERATION_(op)

        if op == _SERVICE_PING_:
            return _REQUEST_DONE_(_SERVICE_PONG_)
        
        # Get member attribute
        try:
            attr = getattr(self, op)
        except Exception as e:
            _WRN('Failed to get "%s" from service: %s' % (op, e))
            return _REQUEST_RAISE_EXCEPTION_(e)

        # If member is a instance method... call it
        if callable(attr):
            try:
                result = attr(*args, **kwargs)
            except Exception as e:
                _WRN('Failed to execute %s(%s, %s): %s' % (
                    op, repr(args), repr(kwargs), e))
                return _REQUEST_RAISE_EXCEPTION_(e)
        else:
            result = attr

        # Return
        _DEB('Request %s result: %s' % (op, repr(result)))
        return _REQUEST_DONE_(result)


class Client(object):
    '''Base client'''

    def __init__(self, dbus_object, dbus_path):
        self.__sender = None
        self.__dbus_object = dbus_object
        self.__dbus_path = dbus_path
        self.__make_dbus_connection__()
        self.auto_reconnect = True

    def __make_dbus_connection__(self):
        noftries = 3
        no_connected = True
        while no_connected:
            try:
                self.__sender = e3utils.clients.dbuscomm.Publisher(
                    self.__dbus_object,
                    self.__dbus_path,
                    only_session=False)
                self.__sender.timeout = _LONG_TIMEOUT_
                _DEB('Connected to %s' % self.__dbus_object)
                no_connected = False
            except Exception as e:
                noftries -= 1
                if noftries == 0:
                    _WRN('Unable to connect to DBus: %s' % e)
                    raise CannotConnect()
                else:
                    time.sleep(3.0)

    def send_request(self, request):
        _DEB('Sending request: %s' % request)
        if self.__sender is None:
            self.__make_dbus_connection__()
        try:
            result = self.__sender.send(request)
        except Exception as e:
            _WRN('Unable to send request: %s (disconnected)' % e)
            self.__sender = None
            raise Disconnected()
        try:
            result = json.loads(result)
        except Exception as e:
            _WRN('Wrong service response: %s' % e)

        return result

    @remote
    def ping(self):
        pass
