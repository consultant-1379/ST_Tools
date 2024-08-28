#!/usr/bin/env python

#import logging
import e3utils.log as logging
_DEB = logging.internal_debug
_WRN = logging.internal_warning
_ERR = logging.internal_error

# 3rdParty
import pexpect

from . import Session
from . import ConnectionFailed

_DUMMY_PROMPT = 'next_command>'


class RemoteExecutionError(Exception):
    def __init__(self, error_code):
        self.__err = error_code

    def __str__(self):
        return 'Execution error: %s' % self.__err


class StandardLinux(Session):
    def __init__(self, channel):
        Session.__init__(self, channel)
        self.__autoclose = False
        self.__ready = False

    def clone(self):
        session = StandardLinux(self.channel.clone())
        if self.ready:
            session.open()
        return session

    @property
    def session_type(self):
        return 'Standard Linux'

    @property
    def ready(self):
        return self.__ready

    @property
    def sync_expression(self):
        return '%s>' % super(StandardLinux,self).sync_expression
        #return _DUMMY_PROMPT

    def open(self):
        if not self.channel.opened:
            self.channel.open()
            self.__autoclose = True
        _DEB('[%s]: starting %s session' % (self.channel.id, self.session_type))
        self.channel.write_line('stty -echo')
        cmd = 'export PS1="%(ps)s" ;  set prompt="%(ps)s"' % {
            'ps': self.sync_expression}
        self.channel.write_line(cmd)
        # Remove preamble ECO
        self.echo_removal = self.channel.expect([cmd,pexpect.TIMEOUT, pexpect.EOF], timeout=0.5) == 0

        result = self.channel.expect([self.sync_expression,
                                      pexpect.TIMEOUT, pexpect.EOF])
        if result != 0:
            _ERR('[%s]: error opening %s session' % (self.channel.id, self.session_type))
            raise ConnectionFailed('Connection not opened')
        else:
            _DEB('[%s]: session becames READY' % self.channel.id)
            self.__ready = True

    def close(self):
        Session.close(self)
        _DEB('[%s]: closing %s session' % (self.channel.id, self.session_type))
        if not self.ready:
            return
        self.channel.write_line('exit')
        if self.__autoclose:
            self.channel.close()
        self.__autoclose = False
        self.__ready = False

class HardenedLinux(Session):
    def __init__(self, channel):
        Session.__init__(self, channel)
        _DEB('[%s]: Initializing %s session' % (self.channel.id, self.session_type))
        self.__autoclose = False
        self.__ready = False
        self.__root_passw = 'rootroot'

    def set_root_passw(self,root_passw):
        self.__root_passw = root_passw

    def clone(self):
        session = HardenedLinux(self.channel.clone())
        if self.ready:
            session.open()
        return session

    @property
    def session_type(self):
        return 'Hardened Linux'

    @property
    def ready(self):
        return self.__ready

    @property
    def sync_expression(self):
        _DEB('[%s]: Syncing expression %s session' % (self.channel.id, self.session_type))
        return '%s>' % super(HardenedLinux,self).sync_expression
        #return _DUMMY_PROMPT

    def open(self):
        if not self.channel.opened:
            _DEB('[%s]: opening channel %s session' % (self.channel.id, self.session_type))
            self.channel.open()
            self.__autoclose = True
        _DEB('[%s]: starting %s session' % (self.channel.id, self.session_type))
        self.channel.write_line('stty -echo')
        cmd = 'export PS1="%(ps)s" ;  set prompt="%(ps)s"' % {
            'ps': self.sync_expression}
        self.channel.write_line(cmd)

        # Remove preamble ECO
        self.echo_removal = self.channel.expect([cmd,pexpect.TIMEOUT, pexpect.EOF], timeout=0.5) == 0
        result = self.channel.expect([self.sync_expression,
                                      pexpect.TIMEOUT, pexpect.EOF])
        if result != 0:
            _ERR('[%s]: error opening %s session' % (self.channel.id, self.session_type))
            raise ConnectionFailed('Connection not opened')

        # getting root privileges in the Hardened Environment
        self.channel.write_line('su -')
        # Remove preamble ECO
        self.echo_removal = self.channel.expect([cmd,pexpect.TIMEOUT, pexpect.EOF], timeout=0.5) == 0
        result = self.channel.expect(['Password:',
                                      pexpect.TIMEOUT, pexpect.EOF])
        if result != 0:
            _ERR('[%s]: error getting root privileges for  %s session' % (self.channel.id, self.session_type))
            raise ConnectionFailed('Connection not opened')
        else:
            self.channel.write_line(self.__root_passw)

        self.channel.write_line('stty -echo')
        cmd = 'export PS1="%(ps)s" ;  set prompt="%(ps)s"' % {
            'ps': self.sync_expression}
        self.channel.write_line(cmd)
        # Remove preamble ECO
        self.echo_removal = self.channel.expect([cmd,pexpect.TIMEOUT, pexpect.EOF], timeout=0.5) == 0
        result = self.channel.expect([self.sync_expression,
                                      pexpect.TIMEOUT, pexpect.EOF])
        if result != 0:
            _ERR('[%s]: error opening %s session' % (self.channel.id, self.session_type))
            raise ConnectionFailed('Connection not opened')
        else:
            _DEB('[%s]: session becames READY' % self.channel.id)
            self.__ready = True


    def close(self):
        Session.close(self)
        _DEB('[%s]: closing %s session' % (self.channel.id, self.session_type))
        if not self.ready:
            return
        #Exiting the session as root
        self.channel.write_line('exit')

        #Exiting the session as the original user
        self.channel.write_line('exit')
        if self.__autoclose:
            self.channel.close()
        self.__autoclose = False
        self.__ready = False


class EprtSetup(StandardLinux):
    def __init__(self, channel):
        super(EprtSetup,self).__init__(channel)

    @property
    def session_type(self):
        return 'EprtSetup linux'

    def clone(self):
        session = EprtSetup(self.channel.clone())
        if self.ready:
            session.open()
        return session

    def open(self):
        _DEB('[%s]: opening %s session' % (self.channel.id, self.session_type))
        super(EprtSetup,self).open()
        self.channel.write_line('eprtsetup')
        result = self.channel.expect(['Configuring base installation config path.',
                                      pexpect.TIMEOUT, pexpect.EOF])
        if result != 0:
            _ERR('[%s]: cannot start %s session' % (self.channel.id, self.session_type))
            raise ConnectionFailed('Connection not opened')

        cmd = 'export PS1="%(ps)s"' % {
            'ps': self.sync_expression}
        self.channel.write_line(cmd)

        result = self.channel.expect([self.sync_expression,
                                      pexpect.TIMEOUT, pexpect.EOF])
        if result != 0:
            _ERR('[%s]: error opening %s session' % (self.channel.id, self.session_type))
            raise ConnectionFailed('Connection not opened')
        else:
            _DEB('[%s]: session becames READY' % self.channel.id)
            self.__ready = True


    def close(self):
        _DEB('[%s]: closing %s session' % (self.channel.id, self.session_type))
        self.channel.write_line('exit')
        super(EprtSetup,self).close()

class NetconfCBA(Session):
    def __init__(self, channel):
        Session.__init__(self, channel)
        self.__autoclose = False
        self.__ready = False
        self.channel.ssh_subsystem = 'netconf'

    @property
    def session_type(self):
        return 'NetconfCBA'

    def clone(self):
        session = NetconfCBA(self.channel.clone())
        if self.ready:
            session.open()
        return session

    @property
    def ready(self):
        return self.__ready

    #@property
    #def sync_expression(self):
        #return '\n(\(.*\))?>'

    @property
    def hello_message(self):
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<hello xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
<capabilities>
<capability>urn:ietf:params:netconf:base:1.0</capability>
</capabilities>
</hello>]]>]]>
'''

    @property
    def close_message(self):
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<rpc message-id="1" xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
<close-session/>
</rpc>
]]>]]>
'''

    @property
    def sync_expression(self):
        return ']]>]]>'

    def open(self):
        if not self.channel.opened:
            self.channel.open()
            self.__autoclose = True
        _DEB('[%s]: starting %s session' % (self.channel.id, self.session_type))
        result = self.channel.expect([self.sync_expression,
                                      pexpect.TIMEOUT, pexpect.EOF])
        if result != 0:
            _ERR('[%s]: error opening %s session' % (self.channel.id, self.session_type))
            raise ConnectionFailed('Connection not opened')

        self.channel.write_line(self.hello_message)

        _DEB('[%s]: session becames READY' % self.channel.id)
        self.__ready = True

    def close(self):
        super(self.__class__, self).close()
        _DEB('[%s]: closing %s session' % (self.channel.id, self.session_type))
        if not self.ready:
            return
        self.channel.write_line(self.close_message)
        result = self.channel.expect([self.sync_expression, pexpect.TIMEOUT, pexpect.EOF])
        if result != 0:
            _WRN('[%s]: error closing %s' % (self.channel.id, self.session_type))

        if self.__autoclose:
            self.channel.close()
        self.__autoclose = False
        self.__ready = False


class SignManCLI(Session):
    def __init__(self, channel, user='telorb', password='telorb'):
        Session.__init__(self, channel)
        self.__autoclose = False
        self.__ready = False

        self.__user = user
        self.__password = password

    @property
    def session_type(self):
        return 'SignManCLI'

    def clone(self):
        session = SignManCLI(self.channel.clone())
        if self.ready:
            session.open()
        return session

    @property
    def ready(self):
        return self.__ready

    @property
    def sync_expression(self):
        return '\ncli>'

    def open(self):
        if not self.channel.opened:
            self.channel.open()
            self.__autoclose = True
        _DEB('[%s]: starting Signalling Manager CLI session' % self.channel.id)
        self.channel.write_line('/opt/SignallingManager/bin/signmcli')
        result = self.channel.expect(
            ['User \[\]: ', pexpect.TIMEOUT, pexpect.EOF])
        if result != 0:
            _WRN('[%s]: error starting %s' % (self.channel.id, self.session_type))
            raise ConnectionFailed('Cannot open "signmcli"')
        self.channel.write_line(self.__user)
        result = self.channel.expect(['Pass: ', pexpect.TIMEOUT, pexpect.EOF])
        if result != 0:
            _WRN('[%s]: error starting %s' % (self.channel.id, self.session_type))
            return
        self.channel.write_line(self.__password)

        result = self.channel.expect(['EXECUTED', '\(yes,no,abort\):',
                                      pexpect.TIMEOUT, pexpect.EOF])
        if result == 1:
            _WRN('[%s]: %s is already in use, entering in RO mode' % (self.channel.id, self.session_type))
            self.channel.write_line('yes')
            result = self.channel.expect(['EXECUTED',
                                          pexpect.TIMEOUT, pexpect.EOF])

        result = self.channel.expect([self.sync_expression,
                                      pexpect.TIMEOUT, pexpect.EOF])
        if result != 0:
            _WRN('[%s]: error opening %s session' % (self.channel.id, self.session_type))
        else:
            _DEB('[%s]: session becames READY' % self.channel.id)
            self.__ready = True

    def close(self):
        super(self.__class__, self).close()
        _DEB('[%s]: closing %s session' % (self.channel.id, self.session_type))
        if not self.ready:
            return
        self.channel.write_line('exit')
        if self.__autoclose:
            self.channel.close()
        self.__autoclose = False
        self.__ready = False


class CBACliss(Session):
    def __init__(self, channel):
        Session.__init__(self, channel)
        self.__autoclose = False
        self.__ready = False
        self.__config_mode = False

    @property
    def session_type(self):
        return 'CBACliss'

    def clone(self):
        session = CBACliss(self.channel.clone())
        if self.ready:
            session.open()
        return session

    @property
    def ready(self):
        return self.__ready

    @property
    def sync_expression(self):
        return '\n%s>' % self.session_type
        #return '\n(\(.+\))?>|\n>'

    def open(self):
        if not self.channel.opened:
            self.channel.open()
            self.__autoclose = True

        self.channel.write_line('stty -echo')

        if self.channel.endpoint.port != 122:
            _DEB('[%s]: starting %s session' % (self.channel.id, self.session_type))
            self.channel.write_line('/opt/com/bin/cliss')
            result = self.channel.expect([' \>|\n>','Authentication with COM failed',
                                        pexpect.TIMEOUT, pexpect.EOF],timeout=300.0 )
            if result != 0:
                _ERR('[%s]: error opening %s session' % (self.channel.id, self.session_type))
                raise ConnectionFailed('Connection not opened')

        cmd = 'prompt %s' %self.session_type
        self.channel.write_line(cmd)
        #self.echo_removal = self.channel.expect([cmd, pexpect.TIMEOUT, pexpect.EOF], timeout = 0.5) == 0

        result = self.channel.expect([self.sync_expression,
                                      pexpect.TIMEOUT, pexpect.EOF])

        if result != 0:
            _ERR('[%s]: error changing pronpt in %s session' % (self.channel.id, self.session_type))
            raise ConnectionFailed('Connection not opened')

        _DEB('[%s]: session becames READY' % self.channel.id)
        self.__ready = True

    def close(self):
        super(self.__class__, self).close()
        _DEB('[%s]: closing %s session' % (self.channel.id, self.session_type))
        if not self.ready:
            return
        if self.__config_mode:
            _WRN('[%s]: ** uncommited changes will be discarded **' % self.channel.id)
            self.channel.write_line('abort')
        self.channel.write_line('exit')
        if self.__autoclose:
            self.channel.close()
        self.__autoclose = False
        self.__ready = False

class CBASignmcli(Session):
    def __init__(self, channel):
        Session.__init__(self, channel)
        self.__autoclose = False
        self.__ready = False

    @property
    def session_type(self):
        return 'CBASignmcli'

    def clone(self):
        session = CBASignmcli(self.channel.clone())
        if self.ready:
            session.open()
        return session

    @property
    def ready(self):
        return self.__ready

    @property
    def sync_expression(self):
        return 'cli>'

    def open(self):
        if not self.channel.opened:
            self.channel.open()
            self.__autoclose = True

        self.channel.write_line('stty -echo')

        _DEB('[%s]: starting %s session' % (self.channel.id, self.session_type))
        #self.channel.write_line('/opt/sign/EABss7050/bin/signmcli  -own.conf /opt/sign/etc/signmgr.cnf -online=yes')
        self.channel.write_line('/opt/sign/bin/ss7caf-sm-cli')
        connected = False
        while not connected:
            result = self.channel.expect(['\nEXECUTED\r\ncli>','\(yes,no,abort\):',
                                        pexpect.TIMEOUT, pexpect.EOF])
            if result == 1:
                self.channel.write_line('no')
                continue
            elif result == 0:
                connected = True
            else:
                _ERR('[%s]: error opening %s session' % (self.channel.id, self.session_type))
                raise ConnectionFailed('Connection not opened')

        cmd = ''
        self.channel.write_line(cmd)
        #self.echo_removal = self.channel.expect([cmd, pexpect.TIMEOUT, pexpect.EOF], timeout = 0.5) == 0

        result = self.channel.expect([self.sync_expression,
                                      pexpect.TIMEOUT, pexpect.EOF])

        #if result != 0:
            #_ERR('[%s]: error changing pronpt in %s session' % (self.channel.id, self.session_type))
            #raise ConnectionFailed('Connection not opened')

        _DEB('[%s]: session becames READY' % self.channel.id)
        self.__ready = True

    def close(self):
        super(self.__class__, self).close()
        _DEB('[%s]: closing %s session' % (self.channel.id, self.session_type))
        if not self.ready:
            return

        self.channel.write_line('exit')
        if self.__autoclose:
            self.channel.close()
        self.__autoclose = False
        self.__ready = False

class CBANBICliss(Session):
    def __init__(self, channel):
        Session.__init__(self, channel)
        self.__autoclose = False
        self.__ready = False
        self.__config_mode = False

    @property
    def session_type(self):
        return 'CBANBICliss'

    def clone(self):
        session = CBACliss(self.channel.clone())
        if self.ready:
            session.open()
        return session

    @property
    def ready(self):
        return self.__ready

    @property
    def sync_expression(self):
        return '\n(\(.+\))?>'

    def open(self):
        if not self.channel.opened:
            self.channel.open()
            self.__autoclose = True

        cmd = 'prompt ""'
        self.channel.write_line(cmd)
        self.echo_removal = self.channel.expect([cmd, pexpect.TIMEOUT, pexpect.EOF], timeout = 1.5) == 0

        result = self.channel.expect([self.sync_expression,
                                      pexpect.TIMEOUT, pexpect.EOF])

        if result != 0:
            _ERR('[%s]: error changing pronpt in %s session' % (self.channel.id, self.session_type))
            raise ConnectionFailed('Connection not opened')

        _DEB('[%s]: session becames READY' % self.channel.id)
        self.__ready = True

    def close(self):
        super(self.__class__, self).close()
        _DEB('[%s]: closing %s session' % (self.channel.id, self.session_type))
        if not self.ready:
            return
        if self.__config_mode:
            _WRN('[%s]: ** uncommited changes will be discarded **' % self.channel.id)
            self.channel.write_line('abort')
        self.channel.write_line('exit')
        if self.__autoclose:
            self.channel.close()
        self.__autoclose = False
        self.__ready = False


class TelorbCLI(Session):
    def __init__(self, channel):
        Session.__init__(self, channel)
        self.__autoclose = False
        self.__ready = False
        self.__CLI_host = None
        self.__CLI_port = None
        self.__sync_expression = '\$ /.*>'

    @property
    def session_type(self):
        return 'TelorbCLI'


    def clone(self):
        session = TelorbCLI(self.channel.clone())
        if self.ready:
            session.open()
        return session

    @property
    def CLI_host(self):
        return self.__CLI_host

    @property
    def CLI_port(self):
        return self.__CLI_port

    def set_CLI_server(self, host, port):
        self.__CLI_host = host
        self.__CLI_port = port

    @property
    def ready(self):
        return self.__ready

    @property
    def sync_expression(self):
        return self.__sync_expression

    def set_sync_expression(self, sync_expression):
        self.__sync_expression = sync_expression

    def open(self):
        if not self.channel.opened:
            self.channel.open()
            self.__autoclose = True
        self.echo_removal = True
        _DEB('[%s]: starting %s session' % (self.channel.id, self.session_type))
        self.channel.write_line('telnet %s %s' % (self.CLI_host, self.CLI_port))
        result = self.channel.expect([self.sync_expression,
                                      pexpect.TIMEOUT, pexpect.EOF])
        if result != 0:
            _ERR('[%s]: error opening %s session' % (self.channel.id, self.session_type))
            raise ConnectionFailed('Connection not opened')
        else:
            _DEB('[%s]: session becames READY' % self.channel.id)
            self.__ready = True

    def close(self):
        super(self.__class__, self).close()
        _DEB('[%s]: closing %s session' % (self.channel.id, self.session_type))
        if not self.ready:
            return

        self.channel.write_line('quit')
        if self.__autoclose:
            self.channel.close()
        self.__autoclose = False
        self.__ready = False

class JambalaCLI(Session):
    def __init__(self, channel):
        Session.__init__(self, channel)
        self.__autoclose = False
        self.__ready = False
        self.__sync_expression = '.*>'

    @property
    def session_type(self):
        return 'JambalaCLI'


    def clone(self):
        session = TelorbCLI(self.channel.clone())
        if self.ready:
            session.open()
        return session

    @property
    def ready(self):
        return self.__ready

    @property
    def sync_expression(self):
        return self.__sync_expression

    def set_sync_expression(self, sync_expression):
        self.__sync_expression = sync_expression

    def open(self):
        if not self.channel.opened:
            self.channel.open()
            self.__autoclose = True
        #_DEB('[%s]: starting %s session' % (self.channel.id, self.session_type))
        self.channel.write_line('stty -echo')
        cmd = 'export PS1="%(ps)s" ;  set prompt="%(ps)s"' % {
            'ps': self.sync_expression}
        self.channel.write_line(cmd)
        # Remove preamble ECO
        self.echo_removal = self.channel.expect([cmd,pexpect.TIMEOUT, pexpect.EOF], timeout=0.5) == 0

        result = self.channel.expect([self.sync_expression,
                                      pexpect.TIMEOUT, pexpect.EOF])
        if result != 0:
            _ERR('[%s]: error opening %s session' % (self.channel.id, self.session_type))
            raise ConnectionFailed('Connection not opened')
        else:
            _DEB('[%s]: session becames READY' % self.channel.id)
        self.__ready = True

    def close(self):
        Session.close(self)
        _DEB('[%s]: closing %s session' % (self.channel.id, self.session_type))
        if not self.ready:
            return
        self.channel.write_line('exit')
        if self.__autoclose:
            self.channel.close()
        self.__autoclose = False
        self.__ready = False
