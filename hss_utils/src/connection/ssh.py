#!/usr/bin/env python
#

import os
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


_SCP_OPTIONS = '-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no'
_SCP_BUFFER = 1048576
_SCP_NOFILE = 'o such file'
_SCP_COMPLETED = '100%'

_SSH_CMD_ = 'ssh -v%(ssh_key)s%(x11_forwarding)s -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ConnectTimeout=%(timeout)s -o ServerAliveInterval=120 -p %(port)s %(destination)s%(ssh_subsystem)s'
_SSH_NEWKEY = 'Are you sure you want to continue connecting'
_SSH_PASSWD = 'assword:'
_SSH_FAIL = 'Permission denied'
_SSH_LOST = 'lost connection'
_SSH_REFUSED = 'Connection refused'
_SSH_CONTIMEOUT = 'Connection timed out'
_SSH_NOROUTE = 'No route to host'
_SSH_BAD_KEY = 'WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!'
_SSH_READY = 'debug1: Sending command:'
_SSH_SHELL_READY = 'Entering interactive session.'
_SSH_TERMINATION = 'debug1: Exit status.*\n'

SSH_DEFAULT_PORT = 22

class RemoteExecutionError(Exception):
    def __init__(self, error_code):
        self.__err = error_code

    def __str__(self):
        return 'Remote execution error: %s' % self.__err

class EnableX11Error(Exception):
    def __str__(self):
        return 'Not allowed to enable X11 forwarding for an opened channel'

class SshKeyFileNotFoundError(Exception):
    def __init__(self, error_code):
        self.__err = error_code

    def __str__(self):
        return 'ssh key file %s not found' % self.__err


class SSHEndpoint(Endpoint):
    def __init__(self, config={}):
        if 'port' not in config.keys():
            config['port'] = SSH_DEFAULT_PORT
        Endpoint.__init__(self, config)

    def __str__(self):
        return 'ssh://%s@%s:%s' % (self.user, self.host, self.port)


class SSHChannel(Channel):
    def __init__(self, endpoint, timeout=60.0, transfer_timeout=None):
        Channel.__init__(self, endpoint, timeout)
        _DEB('Create SSH channel to %s as [%s]' % (
            str(endpoint),
            str(self.id)
        ))
        self.__transfer_timeout = transfer_timeout
        self.__opened = False
        self.__last_buffer = ''
        self.__ssh = None
        self.__x11_forwarding = ''
        self.__ssh_key = ''
        self.__ssh_subsystem = ''

    def clone(self):
        channel = SSHChannel(SSHEndpoint(self.endpoint.as_dict),
                             self.timeout, self.transfer_timeout)
        _DEB('Clone channel %s to %s' % (self.id, channel.id))

        if self.__x11_forwarding == ' -Y':
            channel.enable_x11_forwarding()

        if self.ssh_key != '':
            channel.ssh_key=self.ssh_key

        if self.ssh_subsystem != '':
            channel.ssh_subsystem=self.ssh_subsystem

        if self.opened:
            channel.open()
        return channel

    def set_transfer_timeout(self, timeout):
        self.__transfer_timeout = timeout

    @property
    def x11_forwarding(self):
        return self.__x11_forwarding

    def enable_x11_forwarding(self):
        if self.opened:
            raise EnableX11Error()

        self.__x11_forwarding = ' -Y'

    @property
    def ssh_key(self):
        return self.__ssh_key

    @ssh_key.setter
    def ssh_key(self, key):
        if not os.path.isfile(key):
            raise SshKeyFileNotFoundError(key)

        self.__ssh_key = ' -i %s' % key

    @property
    def ssh_subsystem(self):
        return self.__ssh_subsystem

    @ssh_subsystem.setter
    def ssh_subsystem(self, subsystem):
        self.__ssh_subsystem = ' -s %s' % subsystem

    @property
    def transfer_timeout(self):
        return self.__transfer_timeout

    def upload(self, source, destination):
        _DEB('upload file %s to %s (using %s)' % (source,
                                               destination,
                                               self.endpoint))
        command = 'scp %s%s -p -P %s %s %s@%s:%s' % (_SCP_OPTIONS,
                                                     self.ssh_key,
                                                   self.endpoint.port,
                                                   source,
                                                   self.endpoint.user,
                                                   self.endpoint.host,
                                                   destination)
        return self._scp_(command)

    def download(self, source, destination):
        _DEB('download file %s to %s (using %s)' % (source,
                                                    destination,
                                                    self.endpoint))
        conn = '%s %s@%s' % (self.endpoint.port,
                             self.endpoint.user,
                             self.endpoint.host)
        command = 'scp %s%s -p -P %s:%s %s' % (_SCP_OPTIONS,
                                               self.ssh_key,
                                             conn,
                                             source,
                                             destination)
        return self._scp_(command)

    def _scp_(self, scp_command):
        _DEB('scp_spawn: %s' % repr(scp_command))
        scp = pexpect.spawn(scp_command)
        scp.maxread = _SCP_BUFFER
        scp.setecho(False)

        tries = 0
        while True:
            state = scp.expect([pexpect.TIMEOUT,
                                _SSH_NEWKEY,
                                _SSH_PASSWD,
                                _SSH_BAD_KEY,
                                pexpect.EOF],
                               timeout=self.transfer_timeout)
            _DEB('scp_send_state: %s[%s]' % (state, repr(scp.before)))
            if state == 0:
                _DEB('scp_send: Unable to open connection')
                scp.close(force=True)
                raise ConnectionTimeout()

            if state == 1:
                # Accept public key
                scp.sendline('yes')

            if state == 2:
                # Send password
                if self.endpoint.password is None:
                    # Password requested but not provided
                    _WRN('scp_send: password needed but not provided')
                    scp.close(force=True)
                    raise ConnectionFailed(
                        'Password needed to connect to %s' % self.endpoint.host
                    )
                scp.sendline(self.endpoint.password)
                tries += 1

            if state == 3:
                _WRN('scp_send: invalid SSH fingerprint')
                scp.close(force=True)
                raise ConnectionFailed(
                    'Invalid entry for %s in known_host' % self.endpoint.host
                )

            if state == 4:
                if ((_SSH_FAIL in scp.before) or (_SSH_LOST in scp.before)):
                    _WRN('scp_send: unable to open SSH connection')
                    scp.close(force=True)
                    raise ConnectionFailed(
                        'Cannot connect to %s' % self.endpoint.host
                    )

                # scp terminated, check ouput
                if _SCP_NOFILE in scp.before:
                    _WRN('scp_send: file not found')
                    scp.close(force=True)
                    raise IOError('File not found')

                if _SCP_COMPLETED in scp.before:
                    _DEB('scp_send: file transferred')
                    scp.close(force=True)
                    return True

                _WRN('scp_send: scp finished with unknown result')
                scp.close(force=True)
                raise ConnectionFailed('Unknown scp output: \n%s' % scp.before)

            if tries > 3:
                # Buggy server?
                _WRN('scp_send: buggy server, unable to login')
                scp.close(force=True)
                raise ConnectionFailed(
                    'Unknown response from %s' % self.endpoint.host
                )

    @property
    def ready(self):
        return self.__ssh is not None

    @property
    def opened(self):
        return self.ready and self.__opened

    def open(self):
        if self.opened:
            return

        if self.endpoint.user is None:
            destination = self.endpoint.host
        else:
            destination = '%s@%s' % (self.endpoint.user, self.endpoint.host)

        cmd = _SSH_CMD_ % {
            'destination': destination,
            'timeout': int(self.timeout),
            'port': int(self.endpoint.port),
            'x11_forwarding' : self.__x11_forwarding,
            'ssh_key' : self.__ssh_key,
            'ssh_subsystem' : self.__ssh_subsystem
        }

        _DEB('SSH[%s]: spawning "%s"' % (self.id, cmd))
        self.__ssh = pexpect.spawn(cmd)
        self.__ssh.maxread = _SCP_BUFFER
        self.__ssh.setecho(False)
        password_already_provided = False

        while True:
            state = self.__ssh.expect([
                _SSH_NEWKEY,
                _SSH_PASSWD,
                _SSH_FAIL,
                _SSH_LOST,
                _SSH_REFUSED,
                _SSH_CONTIMEOUT,
                _SSH_NOROUTE,
                _SSH_BAD_KEY,
                _SSH_READY,
                _SSH_SHELL_READY,
                pexpect.TIMEOUT,
                pexpect.EOF], timeout=self.timeout)
            _DEB('SSH[%s]: init_state: %s' % (self.id, state))

            if state == 0:
                self.__ssh.sendline('yes')
                continue

            if state == 1:
                if self.endpoint.password is None or password_already_provided:
                    # Password requested but not provided
                    self.__ssh.close(force=True)
                    self.__ssh = None
                    raise Unauthorized(self.endpoint.user)
                else:
                    _DEB('SSH[%s]: password: %s' % (
                        self.id,
                        '*' * len(self.endpoint.password)
                    ))
                    self.__ssh.sendline(self.endpoint.password)
                    password_already_provided = True
                    continue

            if state in [8, 9]:
                _DEB('SSH[%s]: channel opened' % self.id)
                self.__opened = True
                return

            if state in [2, 3, 4, 5, 6, 7, 10, 11]:
                _WRN('SSH[%s]: cannot open channel' % self.id)
                self.__ssh.close(force=True)
                self.__ssh = None
                if state == 2:
                    raise Unauthorized(self.endpoint.user)
                if state == 10:
                    raise ConnectionTimeout()
                raise ConnectionFailed(
                    'Cannot open channel. Init state: %s' % state)

    def close(self):
        super(self.__class__, self).close()
        if not self.opened:
            return
        _DEB('SSH[%s]: close' % self.id)
        self.__ssh.close(force=True)
        self.__ssh = None
        self.__opened = False

    @property
    def stdout(self):
        return self.__last_buffer

    def write_line(self, line):
        if not self.opened:
            raise ConnectionFailed('Connection not opened')
        _DEB('SSH[%s]: write_line "%s"' % (self.id, line))
        return self.__ssh.sendline(line)

    @property
    def last_match(self):
        if not self.opened:
            raise ConnectionFailed('Connection not opened')
        return self.__ssh.match.group(0)

    def expect(self, expect_list, timeout = None):
        if timeout == None:
            timeout = self.timeout
        elif timeout < 0:
            timeout = None

        result = self.__ssh.expect(expect_list, timeout)

        try:
            _DEB('SSH[%s]: match: %s' % (self.id, repr(self.last_match)))
            _DEB('SSH[%s]: after %s' % (self.id, repr(self.__ssh.after)))
        except AttributeError:
            _DEB('SSH[%s]: exception after  %s' % (self.id, repr(self.__ssh.after)))
            _DEB('SSH[%s]: match: TIMEOUT/EOF' % self.id)

        self.__last_buffer = self.__ssh.before
        _DEB('SSH[%s]: read %s' % (self.id, repr(self.__last_buffer)))
        _DEB('SSH[%s]: result expect %s' % (self.id, result))
        return result


class SSHChannelExtension(ChannelExtension):
    def __init__(self, channel, endpoint):
        ChannelExtension.__init__(self, channel, endpoint)
        _DEB('Create SSH extension from %s to %s as [%s]' % (
            str(self.subchannel.endpoint),
            str(self.endpoint),
            str(self.id)
        ))
        self.__opened = False
        self.__last_buffer = ''
        self.force_echo_removal = False
        self.__x11_forwarding = channel.x11_forwarding
        self.__ssh_key = channel.ssh_key

    def clone(self):
        extension = SSHChannelExtension(self.subchannel.clone(),
                                        SSHEndpoint(self.endpoint.as_dict))
        _DEB('Clonning extension channel %s to %s' % (
            self.id,
            extension.id))

        if self.__x11_forwarding == ' -Y':
            extension.enable_x11_forwarding()

        if self.opened:
            extension.open()
        return extension

    def enable_x11_forwarding(self):
        if self.opened:
            raise EnableX11Error()

        self.__x11_forwarding = ' -Y'

    @property
    def ready(self):
        return self.subchannel.ready is not None

    @property
    def opened(self):
        return self.ready and self.__opened

    def open(self):
        if self.opened:
            return

        if not self.subchannel.opened:
            self.subchannel.open()

        if self.endpoint.user is None:
            destination = self.endpoint.host
        else:
            destination = '%s@%s' % (self.endpoint.user, self.endpoint.host)

        cmd = _SSH_CMD_ % {
            'destination': destination,
            'timeout': int(self.subchannel.timeout),
            'port': int(self.endpoint.port),
            'x11_forwarding' : self.__x11_forwarding,
            'ssh_key' : self.__ssh_key,
            'ssh_subsystem' : ''
        }

        _DEB('EXT[%s]: re-spawning "%s"' % (self.id, cmd))
        self.subchannel.write_line(cmd)
        while True:
            state = self.subchannel.expect([
                _SSH_NEWKEY,
                _SSH_PASSWD,
                _SSH_FAIL,
                _SSH_LOST,
                _SSH_REFUSED,
                _SSH_CONTIMEOUT,
                _SSH_NOROUTE,
                _SSH_BAD_KEY,
                _SSH_READY,
                _SSH_SHELL_READY,
                pexpect.TIMEOUT,
                pexpect.EOF])
            _DEB('EXT[%s]: init_state: %s' % (self.id, state))

            if state == 0:
                self.subchannel.write_line('yes')
                continue

            if state == 1:
                if self.endpoint.password is None:
                    # Password requested but not provided
                    self.subchannel.close()
                    raise ConnectionFailed('Password is requested')
                else:
                    _DEB('EXT[%s]: password: %s' % (
                        self.id,
                        '*' * len(self.endpoint.password)
                    ))
                    self.subchannel.write_line(self.endpoint.password)
                    continue

            if state in [8, 9]:
                _DEB('EXT[%s]: channel opened' % self.id)
                self.__opened = True
                return

            if state in [2, 3, 4, 5, 6, 7, 10, 11]:
                if state == 2 and 'key_load' in self.subchannel.stdout:
                    _DEB('EXT[%s]: Ignore key_load.... Permission denied' % self.id)
                    continue

                _WRN('EXT[%s]: cannot open channel. Reason: %s' % (self.id, self.subchannel.stdout))
                #print self.subchannel.stdout
                self.subchannel.close()
                if state == 2:
                    raise Unauthorized(self.endpoint.user)
                if state == 10:
                    raise ConnectionTimeout()
                raise ConnectionFailed(
                    'Cannot open channel. Init state: %s' % state)

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

    def expect(self, expect_list, timeout = None):
        result = self.subchannel.expect(expect_list, timeout)
        self.__last_buffer = self.subchannel.stdout
        return result

