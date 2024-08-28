#!/usr/bin/env python

import uuid
import getpass
import threading
import Queue

#import logging
import e3utils.log as logging
_DEB = logging.internal_debug
_WRN = logging.internal_warning

# 3rdParty
import pexpect


class ConnectionTimeout(Exception):
    def __str__(self):
        return 'Timeout reached'

class ConnectionFailed(Exception):
    def __init__(self, cause='unknown cause'):
        self.__err = cause

    def __str__(self):
        return 'Connection failed (%s)' % self.__err


class ConnectionFailedTimeout(ConnectionFailed):
    def __init__(self):
        ConnectionFailed.__init__(self, 'Timeout')

class ConnectionFailedEOF(ConnectionFailed):
    def __init__(self):
        ConnectionFailed.__init__(self, 'EOF')



class Unauthorized(Exception):
    def __init__(self, user):
        self.__user = user

    def __str__(self):
        return 'Unauthorized user: %s' % self.__user


class Endpoint(object):
    def __init__(self, config={}):
        if 'host' not in config.keys():
            raise ValueError('host missing')
        if 'port' not in config.keys():
            config['port'] = None
        if 'user' not in config.keys():
            config['user'] = getpass.getuser()
        if 'password' not in config.keys():
            config['password'] = None
        self.__host = config['host']
        self.__user = config['user']
        self.__password = config['password']
        self.__port = config['port']

    @property
    def host(self):
        return self.__host

    @property
    def port(self):
        return self.__port

    @property
    def user(self):
        return self.__user

    @property
    def password(self):
        return self.__password

    @property
    def as_dict(self):
        return {
            'host': self.host,
            'port': self.port,
            'user': self.user,
            'password': self.password
        }

    def __str__(self):
        return 'null://%s@%s:%s' % (self.user, self.host, self.port)


class Channel(object):
    def __init__(self, endpoint, timeout=4.0):
        self.__ep = endpoint
        self.__id = uuid.uuid4()
        self.__to = timeout
        self.__used = False

    @property
    def endpoint(self):
        return self.__ep

    @property
    def id(self):
        return self.__id

    def clone(self):
        return Channel(Endpoint(self.endpoint.as_dict))

    def upload(self, source, destination, timeout=-1):
        raise NotImplementedError()

    def download(self, source, destination, timeout=-1):
        raise NotImplementedError()

    @property
    def timeout(self):
        return self.__to

    def set_timeout(self, timeout):
        self.__to = timeout

    @property
    def ready(self):
        return False

    @property
    def opened(self):
        return False

    def open(self):
        raise NotImplementedError()

    def close(self):
        self.release()

    @property
    def stdout(self):
        return None

    def write_line(self, line):
        raise NotImplementedError()

    @property
    def last_match(self):
        return None

    def expect(self, expect_list):
        raise NotImplementedError()

    @property
    def used(self):
        return self.__used

    def lock(self):
        if self.used:
            raise ConnectionFailed('Already in used!')
        self.__used = True

    def release(self):
        self.__used = False

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class ChannelExtension(object):
    def __init__(self, channel, endpoint, timeout=4.0):
        self.__ch = channel
        self.__ep = endpoint
        self.__id = uuid.uuid4()
        self.__to = timeout
        self.__used = False
        self.subchannel.lock()

    @property
    def subchannel(self):
        return self.__ch

    @property
    def endpoint(self):
        return self.__ep

    @property
    def id(self):
        return self.__id

    def clone(self):
        return ChannelExtension(self.subchannel.clone(),
                                Endpoint(self.endpoint.as_dict),
                                self.timeout)

    @property
    def timeout(self):
        return self.__to

    def set_timeout(self, new_timeout):
        self.__to = timeout

    @property
    def ready(self):
        return False

    @property
    def opened(self):
        return False

    def open(self):
        raise NotImplementedError()

    def close(self):
        self.release()

    @property
    def stdout(self):
        return None

    def write_line(self, line):
        raise NotImplementedError()

    @property
    def last_match(self):
        return None

    def expect(self, expect_list):
        raise NotImplementedError()

    @property
    def used(self):
        return self.__used

    def lock(self):
        if self.used:
            raise ConnectionFailed('Already in used!')
        self.__used = True

    def release(self):
        self.__used = False

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __str__(self):
        return '[%s]->[%s]' % (self.subchannel.endpoint,
                               self.endpoint)


class Session(object):
    def __init__(self, channel):
        self.__channel = channel
        self.channel.lock()
        self.echo_removal = False

    def clone(self):
        return Session(self.channel.clone())

    @property
    def channel(self):
        return self.__channel

    @property
    def session_type(self):
        raise NotImplementedError()

    @property
    def ready(self):
        return False

    @property
    def stdout(self):
        return self.filter_output(self.channel.stdout)

    def filter_output(self, raw_data):
        return raw_data

    @property
    def sync_expression(self):
        return self.channel.id
        #raise NotImplementedError()

    def wait_sync(self):
        raise NotImplementedError()

    def open(self):
        raise NotImplementedError()

    def wait_sync(self, timeout = None):
        result = self.channel.expect([self.sync_expression,
                                      pexpect.TIMEOUT,
                                      pexpect.EOF],
                                      timeout)
        if result == 0:
            _DEB('[%s]: synced with %s' % (self.channel.id,
                                           repr(self.channel.last_match)))                
        else:
            _WRN('[%s]: out of sync with "%s"' % (self.channel.id,
                                                  repr(self.channel.stdout)))
        return (result == 0)

    def close(self):
        self.channel.release()

    def sendline(self, line, synchronous=True, timeout = None):
        if not self.ready:
            raise ConnectionFailed('Connection not opened')
        _DEB('[%s]: sending "%s"' % (self.channel.id, line))
        self.channel.write_line(line)
        if self.echo_removal:
            if self.channel.expect([line, pexpect.TIMEOUT, pexpect.EOF], timeout=0.5) != 0:
                _WRN('[%s]: error removing ECHO in %s session' % (self.channel.id, self.session_type))

        if synchronous:
            self.wait_sync(timeout)
            return self.stdout


    def sendoptionallines(self, line, answers, synchronous=True, timeout = None):
        self.sendline(line, synchronous=False,timeout=timeout)
        queries = answers.keys()
        while True:
            expects = queries + [pexpect.TIMEOUT, pexpect.EOF]
            if synchronous:
                expects.append(self.sync_expression)
            elif len(queries) == 0:
                return
            state = self.channel.expect(expects, timeout)
            if synchronous and (state == len(expects) - 1):
                # Prompt found: assumming command ends
                return self.stdout
            if state not in range(len(queries)):
                _WRN('[%s]: raised Timeout/EOF' % self.channel.id)
                _WRN('[%s]: Buffer: %s' % (self.channel.id,
                                           repr(self.channel.stdout)))
                if state == len(queries) + 1:
                    raise ConnectionFailedEOF()

                raise ConnectionFailedTimeout()

            query = queries[state]
            response = answers.get(queries[state], None)
            if response is None:
                _DEB('[%s]: skip response (no answer)' % self.channel.id)
            else:
                _DEB('[%s]: answer for %s is %s' % (
                    self.channel.id,
                    repr(query),
                    repr(response)
                ))
                self.channel.write_line(response)

            if not synchronous:
                # Remove this query
                queries.remove(query)
                if len(queries) == 0:
                    _DEB('[%s]: no more questions to answer!' % self.channel.id)
                    return


    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __str__(self):
        return '%s session at [%s]' % (self.session_type, self.channel.endpoint)

    def __call__(self, line):
        return self.sendline(line)



class Monitor(threading.Thread):

    def __init__(self, channel):
        threading.Thread.__init__(self)

        self.__events = Queue.Queue()

    @property
    def monitor_type(self):
        raise NotImplementedError()

    @property
    def events(self):
        return self.__events

    @property
    def session(self):
        raise NotImplementedError()

    @property
    def ready(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError() 

    def shutdown(self):
        raise NotImplementedError()

    def bootstrap(self):
        pass

    def get(self, timeout=-1):
        return self.events.get(timeout=timeout)

    @property
    def filter_expression(self):
        raise NotImplementedError()

    def run(self):
        _DEB('%s monitor running' % self.monitor_type)

        self.bootstrap()

        while self.ready:
            result = self.session.channel.expect([self.filter_expression,'Connection closed by foreign host', pexpect.TIMEOUT, pexpect.EOF], timeout=5)
            if result == 0:
                self.__events.put(self.session.channel.last_match)

            if result == 1:
                _DEB('Connection closed by foreign host waiting for events in %s monitor' % self.monitor_type)
                self.session.close()
                self.bootstrap(force_restart=True)

            if result == 2:
                _DEB('Timeout waiting for events in %s monitor. Sending keep alive' % self.monitor_type)
                self.session.channel.write_line('')

            if result == 3:
                _DEB('EOF received waiting for events in %s monitor' % self.monitor_type)
                self.session.close()
                self.bootstrap(force_restart=True)


        self.shutdown()

