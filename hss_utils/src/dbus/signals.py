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

def create_signal(signal_id, *args):
    ''' Encode signal with signal_id and optional arguments '''
    signal_id = str(signal_id)
    return json.dumps({
        'signal': signal_id,
        'args': args
    })


def read_signal(signal):
    ''' Decode signal returning signal_id and arguments '''
    try:
        signal = json.loads(signal)
    except Exception as e:
        _WRN('Cannot decode signal "%s": %s' % (signal, e))
    try:
        signal_id = str(signal['signal'])
        args = signal['args']
    except KeyError:
        _WRN('Invalid signal: %s' % signal)
        return None, None
    return signal_id, args


class Emitter(object):
    ''' Register to DBUS and emit signals '''
    def __init__(self):
        self.__dbus = e3utils.clients.dbuscomm.SignalEmitter(only_session=False)

    @property
    def active(self):
        return self.__dbus is not None

    def shutdown(self):
        self.__dbus.remove_from_connection()
        self.__dbus = None

    def emit(self, signal_id, *args):
        if not self.active:
            raise ValueError('Emitter() is down')
        _DEB('Emit signal "%s"' % signal_id)
        self.__dbus.signal(create_signal(signal_id, *args))


class Watcher(threading.Thread):
    ''' Register to DBUS and receive/emit signals '''
    def __init__(self):
        super(Watcher, self).__init__()
        self.__dbus = e3utils.clients.dbuscomm.SignalReceiver(
            self._dispatcher_, only_session=False)
        self.__dispatchers__ = {}
        self.start()

    def install_handler(self, signal_id, handler):
        if not callable(handler):
            raise ValueError('Only callable objects can be connected')
        self.__dispatchers__[signal_id] = handler

    def remove_handler(self, signal_id):
        if signal_id not in self.__dispatchers__.keys():
            raise ValueError('Signal "%s" is not connected' % signal_id)
        del(self.__dispatchers__[signal_id])

    def emit(self, signal_id, *args):
        _DEB('Watcher emit "%s"' % signal_id)
        self.__dbus.signal(create_signal(signal_id, *args))

    def _signal_lost_(self, signal_id):
        _DEB('Signal lost "%s"' % signal_id)

    def is_excited_with(self, signal_id):
        return signal_id in self.__dispatchers__.keys()

    @property
    def running(self):
        return self.__dbus.running

    def _dispatcher_(self, signal, E3Signal=None, Event=None):
        signal_id, args = read_signal(signal)
        if signal_id is None:
            return
        _DEB('Received signal %s' % signal_id)
        if signal_id not in self.__dispatchers__.keys():
            self._signal_lost_(signal_id)
            return
        try:
            self.__dispatchers__[signal_id](*args)
        except Exception as e:
            _WRN('Error calling dispatcher for signal %s: %s' % (signal_id, e))

    def start(self):
        self.__dbus.run(main_loop=False)
        super(Watcher, self).start()

    def stop(self):
        self.__dbus.stop()

    def run(self):
        _DEB('Start dbus listener')
        while self.running:
            if not self.__dbus.iterate():
                time.sleep(.1)


def emit(signal_id, *args):
    '''Emitter() shortcut'''
    e = Emitter()
    e.emit(signal_id, *args)
    e.shutdown()
