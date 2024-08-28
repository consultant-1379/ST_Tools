#!/usr/bin/env python
#

#import logging
import e3utils.log as logging
_DEB = logging.internal_debug
_WRN = logging.internal_warning

# 3rdParty
import pexpect

from . import ConnectionTimeout
from . import ConnectionFailed
from . import Unauthorized

from . import Endpoint
from . import Channel
from . import ChannelExtension
from . import Session

_CONN_BUFFER = 1048576
TELNET_CMD = 'telnet'
TELNET_PROMPT = 'telnet> '
TELNET_DEFAULT_PORT = 23
TELNET_READY = "Escape character is '\^\]'\."

class RemoteExecutionError(Exception):
    def __init__(self, error_code):
        self.__err = error_code

    def __str__(self):
        return 'Remote execution error: %s' % self.__err


class TelnetEndpoint(Endpoint):
    def __init__(self, config={}):
        if 'port' not in config.keys():
            config['port'] = TELNET_DEFAULT_PORT
        Endpoint.__init__(self, config)
        
    def __str__(self):
        return 'telnet://%s@%s:%s' % (self.user, self.host, self.port)


class TelnetChannel(Channel):
    def __init__(self, endpoint, timeout=4.0):
        Channel.__init__(self, endpoint, timeout)
        _DEB('Create TELNET channel to %s as [%s]' % (
            str(endpoint),
            str(self.id)
        ))
        self.__telnet = None
        self.__opened = False
        self.__last_buffer = ''

    def clone(self):
        channel = TelnetChannel(TelnetEndpoint(self.endpoint.as_dict),
                                self.timeout)
        _DEB('Clone channel %s to %s' % (self.id, channel.id))
        if self.opened:
            channel.open()
        return channel

    @property
    def ready(self):
        return self.__telnet is not None

    @property
    def opened(self):
        return self.ready and self.__opened

    def open(self):
        if self.opened:
            return

        _DEB('TELNET[%s]: spawning "%s"' % (self.id, TELNET_CMD))
        self.__telnet = pexpect.spawn(TELNET_CMD)
        self.__telnet.maxread = _CONN_BUFFER
        self.__telnet.setecho(False)

        state = self.__telnet.expect([TELNET_PROMPT,
                                      pexpect.TIMEOUT,
                                      pexpect.EOF],
                                     timeout=self.timeout)

        if state != 0:
            _WRN('TELNET[%s]: error spawning telnet' % self.id)
            self.__telnet.close(force=True)
            self.__telnet = None
            raise ConnectionFailed('Cannot spawn telnet. State: %s' % state)

        user = ('-l %s ' % self.endpoint.user) if self.endpoint.user is not None else ''
        self.__telnet.sendline('open %s%s %s' % (user, 
                                                 self.endpoint.host,
                                                 self.endpoint.port))
        state = self.__telnet.expect([TELNET_READY,
                                      pexpect.TIMEOUT,
                                      pexpect.EOF],
                                     timeout=self.timeout)
        if state != 0:
            _WRN('TELNET[%s]: cannot open telnet connection' % self.id)
            self.__telnet.sendline('quit')
            self.__telnet.close(force=True)
            self.__telnet = None
            raise ConnectionFailed('Cannot open telnet connection')
        _DEB('TELNET[%s]: connection stablished' % self.id)
        self.__opened = True

    def close(self):
        super(self.__class__, self).close()
        if not self.opened:
            return
        _DEB('TELNET[%s]: close' % self.id)
        self.__telnet.sendcontrol(']')
        self.__telnet.sendline('quit')
        self.__telnet.close(force=True)
        self.__telnet = None
        self.__opened = False

    @property
    def stdout(self):
        return self.__last_buffer

    def write_line(self, line):
        if not self.opened:
            raise ConnectionFailed('Connection not opened')            
        _DEB('TELNET[%s]: write_line "%s"' % (self.id, line))
        return self.__telnet.sendline(line)

    @property
    def last_match(self):
        if not self.opened:
            raise ConnectionFailed('Connection not opened')            
        return self.__telnet.match.group(0)

    def expect(self, expect_list):
        result = self.__telnet.expect(expect_list, timeout=self.timeout)
        try:
            _DEB('TELNET[%s]: match: %s' % (self.id, repr(self.last_match)))
        except AttributeError:
            _DEB('TELNET[%s]: match: TIMEOUT/EOF' % self.id)

        self.__last_buffer = self.__telnet.before
        _DEB('TELNET[%s]: read %s' % (self.id, repr(self.__last_buffer)))
        return result


class TelnetChannelExtension(ChannelExtension):
    def __init__(self, channel, endpoint):
        ChannelExtension.__init__(self, channel, endpoint)
        _DEB('Create TELNET extension from %s to %s as [%s]' % (
            str(self.subchannel.endpoint),
            str(self.endpoint),
            str(self.id)
        ))
        self.__opened = False
        self.__last_buffer = ''
        self.force_echo_removal = False

    def clone(self):
        extension = TelnetChannelExtension(self.subchannel.clone(),
                                           TelnetEndpoint(
                                               self.endpoint.as_dict))
        _DEB('Clonning extension channel %s to %s' % (
            self.id,
            extension.id))
        if self.opened:
            extension.open()
        return extension

    @property
    def ready(self):
        return self.subchannel.ready is not None

    @property
    def opened(self):
        return self.ready and self.__opened

    def open(self):
        _DEB('EXT[%s]: re-spawning "%s"' % (self.id, TELNET_CMD))
        self.subchannel.sendline(TELNET_CMD)
        state = self.subchannel.expect([TELNET_PROMPT,
                                        pexpect.TIMEOUT,
                                        pexpect.EOF],
                                       timeout=self.timeout)

        if state != 0:
            _WRN('TELNET[%s]: error spawning telnet' % self.id)
            self.__telnet.close(force=True)
            self.__telnet = None
            raise ConnectionFailed('Cannot spawn telnet. State: %s' % state)

        user = ('-l %s ' % self.endpoint.user) if self.endpoint.user is not None else ''
        opncmd = 'open %s%s %s' % (user, 
                                   self.endpoint.host,
                                   self.endpoint.port)
        self.__telnet.sendline(opencmd)
        state = self.__telnet.expect([TELNET_READY,
                                      pexpect.TIMEOUT,
                                      pexpect.EOF],
                                     timeout=self.timeout)
        if state != 0:
            _WRN('TELNET[%s]: cannot open telnet connection' % self.id)
            self.__telnet.sendline('quit')
            self.__telnet.close(force=True)
            self.__telnet = None
            raise ConnectionFailed('Cannot open telnet connection')
        self.__opened = True

    def close(self):
        super(self.__class__, self).close()
        if not self.opened:
            return
        _DEB('EXT[%s]: close' % self.id)
        self.subchannel.close()
        self.__opened = False

    @property
    def stdout(self):
        return self.__last_buffer

    def write_line(self, line):
        if not self.opened:
            raise ConnectionFailed('Connection not opened')
        _DEB('EXT[%s]: write_line "%s"' % (self.id, line))
        self.subchannel.write_line(line)

        # Subchannels has echo!
        if isinstance(self.subchannel, Channel) and self.force_echo_removal:
            result = self.expect([line, pexpect.EOF, pexpect.TIMEOUT])
            if result == 2:
                _WRN('EXT[%s]: echo removal timeout!' % self.id)

    @property
    def last_match(self):
        if not self.opened:
            raise ConnectionFailed('Connection not opened')
        return self.subchannel.last_match

    def expect(self, expect_list):
        result = self.subchannel.expect(expect_list)
        self.__last_buffer = self.subchannel.stdout
        return result


class TTCN_TelnetChannel(Channel):
    def __init__(self, endpoint, timeout=4.0):
        Channel.__init__(self, endpoint, timeout)
        _DEB('Create TELNET channel to %s as [%s]' % (
            str(endpoint),
            str(self.id)
        ))
        self.__telnet = None
        self.__opened = False
        self.__last_buffer = ''
        self.__sync_expression = 'TTCN> '

    def clone(self):
        channel = TTCN_TelnetChannel(TelnetEndpoint(self.endpoint.as_dict),
                                self.timeout)
        _DEB('Clone channel %s to %s' % (self.id, channel.id))
        if self.opened:
            channel.open()
        return channel

    @property
    def ready(self):
        return self.__telnet is not None

    @property
    def opened(self):
        return self.ready and self.__opened

    @property
    def sync_expression(self):
        return self.__sync_expression

    def set_sync_expression(self, sync_expression):
        self.__sync_expression = sync_expression

    def open(self):
        if self.opened:
            return
        cmd = 'telnet %s %s' % (self.endpoint.host,self.endpoint.port)
        _DEB('TELNET[%s]: spawning "%s"' % (self.id, cmd))
        self.__telnet = pexpect.spawn(cmd)

        state = self.__telnet.expect([self.sync_expression,
                                      pexpect.TIMEOUT,
                                      pexpect.EOF],
                                      timeout=self.timeout)

        if state != 0:
            _WRN('TELNET[%s]: cannot open telnet connection. State %d' % (self.id, state))
            self.__telnet.sendline('quit')
            self.__telnet.close(force=True)
            self.__telnet = None
            raise ConnectionFailed('Cannot open telnet connection')
        _DEB('TELNET[%s]: connection stablished' % self.id)
        self.__opened = True

    def close(self):
        super(self.__class__, self).close()
        if not self.opened:
            return
        _DEB('TELNET[%s]: close' % self.id)
        self.__telnet.sendline('quit')
        self.__telnet.close(force=True)
        self.__telnet = None
        self.__opened = False

    @property
    def stdout(self):
        return self.__last_buffer

    def write_line(self, line):
        if not self.opened:
            raise ConnectionFailed('Connection not opened')            
        _DEB('TELNET[%s]: write_line "%s"' % (self.id, line))
        return self.__telnet.sendline(line)

    @property
    def last_match(self):
        if not self.opened:
            raise ConnectionFailed('Connection not opened')            
        return self.__telnet.match.group(0)

    def expect(self, user_list = []):
        expect_list= [self.sync_expression, pexpect.TIMEOUT, pexpect.EOF] + user_list
        result = self.__telnet.expect(expect_list, timeout=self.timeout)
        self.__last_buffer = self.__telnet.before
        return result


class CBA_console_TelnetChannel(Channel):
    def __init__(self, endpoint, timeout=4.0):
        Channel.__init__(self, endpoint, timeout)
        _DEB('Create TELNET channel to %s as [%s]' % (
            str(endpoint),
            str(self.id)
        ))
        self.__telnet = None
        self.__opened = False
        self.__last_buffer = ''
        self.__sync_expression = 'TTCN> '

    def clone(self):
        channel = CBA_console_TelnetChannel(TelnetEndpoint(self.endpoint.as_dict),
                                self.timeout)
        _DEB('Clone channel %s to %s' % (self.id, channel.id))
        if self.opened:
            channel.open()
        return channel

    @property
    def ready(self):
        return self.__telnet is not None

    @property
    def opened(self):
        return self.ready and self.__opened

    @property
    def sync_expression(self):
        return self.__sync_expression

    def set_sync_expression(self, sync_expression):
        self.__sync_expression = sync_expression

    def open(self):
        if self.opened:
            return
        cmd = 'telnet %s %s' % (self.endpoint.host,self.endpoint.port)
        _DEB('TELNET[%s]: spawning "%s"' % (self.id, cmd))
        self.__telnet = pexpect.spawn(cmd)

        state = self.__telnet.expect(['Entering server port',
                                      'Port is in use',
                                      pexpect.TIMEOUT,
                                      pexpect.EOF],
                                      timeout=self.timeout)

        if state != 0:
            _WRN('TELNET[%s]: cannot open telnet connection. State %d' % (self.id, state))
            self.__telnet.close(force=True)
            self.__telnet = None
            raise ConnectionFailed('Cannot open telnet connection')
        _DEB('TELNET[%s]: connection stablished' % self.id)
        self.__opened = True

    def close(self):
        super(self.__class__, self).close()
        if not self.opened:
            return
        _DEB('TELNET[%s]: close' % self.id)
        self.__telnet.sendcontrol('z')
        state = self.__telnet.expect(['close current connection to port',
                                      pexpect.TIMEOUT,
                                      pexpect.EOF],
                                      timeout=self.timeout)

        if state != 0:
            _WRN('TELNET[%s]: cannot close telnet connection. State %d' % (self.id, state))
            self.__telnet.close(force=True)
            self.__telnet = None

        self.__telnet.sendline('x')
        self.__telnet.close(force=True)
        self.__telnet = None
        self.__opened = False


    @property
    def stdout(self):
        return self.__last_buffer

    def write_line(self, line):
        if not self.opened:
            raise ConnectionFailed('Connection not opened')            
        _DEB('TELNET[%s]: write_line "%s"' % (self.id, line))
        return self.__telnet.sendline(line)

    @property
    def last_match(self):
        if not self.opened:
            raise ConnectionFailed('Connection not opened')            
        return self.__telnet.match.group(0)

    def expect(self, user_list = []):
        expect_list= user_list + [self.sync_expression, pexpect.TIMEOUT, pexpect.EOF]
        result = self.__telnet.expect(expect_list, timeout=1.0)
        self.__last_buffer = self.__telnet.before
        return result
