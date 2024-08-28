#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
LOGGING_FILE=None
_private_log = logging.getLogger(__name__)
_private_log.propagate = False
_ERR = _private_log.error
_WRN = _private_log.warning
_INF = _private_log.info
_DEB = _private_log.debug

LDAP_AVAIL = True
LDAP_TIMEOUT = 10.0

try:
    import ldap
    import ldif
    import ldap.modlist

except ImportError, e:
    _ERR('Cannot find ldap library for python (%s)' % e)
    LDAP_AVAIL = False

import cStringIO

def set_ldap_log_prefix(prefix, level=logging.ERROR):
    global LOGGING_FILE
    global _private_log
    LOGGING_FILE = '%sldap_PID%s.log' % (prefix, os.getpid())
    log_dir = os.path.dirname(LOGGING_FILE)
    if log_dir != '':
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
    fh = logging.FileHandler(LOGGING_FILE)
    fh.setLevel(level)
    fh.setFormatter(logging.Formatter('%(message)s'))
    _private_log.addHandler(fh)
    

class LdapObjectNotFound(Exception):
    def __init__(self, dn):
        self.__objdn = dn
    def __str__(self):
        return 'Object "%s" not found.' % self.__objdn


class LdapObjectAlreadyExists(Exception):
    def __init__(self, dn, info=None):
        self.__objdn = dn
        self.__info = info
    def __str__(self):
        info = '' if self.__info is None else (' (%s)' % self.__info)
        return 'Object "%s" already exists%s.' % (
            self.__objdn,
            info)


class LdapObjectError(Exception):
    def __init__(self, dn, info):
        self.__objdn = dn
        self.__info = info
    def __str__(self):
        return 'Object "%s" error: %s.' % (self.__objdn, self.__info)


class LdapError(Exception):
    def __init__(self, info):
        self.__info = info
    def __str__(self):
        return 'LDAP error: %s.' % self.__info


if LDAP_AVAIL:
    def _build_ldif_(dn, entry):
        ldif_result = cStringIO.StringIO()
        ldif_writer = ldif.LDIFWriter(ldif_result)
        ldif_writer.unparse(dn, entry)
        return ldif_result.getvalue()


    class LdapConnection(object):
        '''LDAP connection handling.'''
        class MyLdifParser(ldif.LDIFParser):
            def __init__(self, fd, stop_on_error=False):
                ldif.LDIFParser.__init__(self, fd)
                self.__add_function = None
                self.__modify_function = None
                self.__stop_on_error = stop_on_error

            def __optional_raise__(self, excp):
                if self.__stop_on_error:
                    raise excp

            def __add_handler(self, dn, entry):
                ldif = ldap.modlist.addModlist(entry)
                try:
                    _INF('# Adding object: %s' % dn)
                    self.__add_function(dn, ldif)
                except ldap.ALREADY_EXISTS, e:
                    if self.__modify_function is None:
                        _ERR('#\tObject already exists on ldap_add()')
                        _ERR(_build_ldif_(dn, entry))
                        self.__optional_raise__(
                            LdapObjectAlreadyExists(dn, str(e)))
                    else:
                        _WRN('#\tObject exists, trying to modify...')
                        self.__modify_handler(dn, entry)
                except ldap.TYPE_OR_VALUE_EXISTS, e:
                    self.__optional_raise__(LdapObjectError(dn, str(e)))
                except ldap.STRONG_AUTH_REQUIRED, e:
                    _ERR('#\tStrong authentication required on ldap_add()')
                    _ERR(_build_ldif_(dn, entry))
                    self.__optional_raise__(LdapError(str(e)))
                except ldap.CONSTRAINT_VIOLATION, e:
                    _ERR('#\tConstraint violation on ldap_add(): %s' % str(e))
                    _ERR(_build_ldif_(dn, entry))
                    self.__optional_raise__(LdapObjectError(dn, str(e)))
                except ldap.UNDEFINED_TYPE, e:
                    info = e.args[0]['info']
                    # python-ldap doesn't document how to access exception info
                    if (info == 'No object class with "nodeName" as primary attribute') and (self.__modify_function is not None):
                        self.__modify_handler(dn, entry)
                    else:
                        _ERR('#\tUndefined type on ldap_add(): %s' % str(e))
                        _ERR(_build_ldif_(dn, entry))
                        self.__optional_raise__(LdapObjectError(dn, str(e)))
                except ldap.OPERATIONS_ERROR, e:
                    # python-ldap doesn't document how to access exception info
                    info = e.args[0]['info']
                    if info == 'Duplicated requestedApp':
                        _DEB('Ignoring OPERATIONS_ERROR response')
                    else:
                        _ERR('#\tOperation error on ldap_add(): %s' % str(e))
                        _ERR(_build_ldif_(dn, entry))                        
                        self.__optional_raise__(LdapObjectError(dn, str(e)))
                except ldap.OBJECT_CLASS_VIOLATION, e:
                    # python-ldap doesn't document how to access exception info
                    info = e.args[0]['info']
                    if 'not allowed as child' in info:
                        self.__modify_handler(dn, entry)
                    else:
                        _ERR('\t#Object class violation on ldap_add(): %s' % str(e))
                        _ERR(_build_ldif_(dn, entry))
                        self.__optional_raise__(LdapObjectError(dn, str(e)))
                except Exception, e:
                    _ERR('#\tUnknown error on ldap_add(): %s' % str(e))
                    _ERR('#\tException type: %s' % type(e))
                    _ERR(_build_ldif_(dn, entry))
                    self.__optional_raise__(LdapError(str(e)))


            def __modify_handler(self, dn, entry):
                ldif = []
                for attr in entry:
                    ldif += [(ldap.MOD_REPLACE, attr, entry[attr])]
                try:
                    _INF('# Modifying object: %s' % dn)
                    self.__modify_function(dn, ldif)
                except ldap.TYPE_OR_VALUE_EXISTS, e:
                    _ERR('#\tType or value exists on ldap_modify(): %s' % str(e))
                    _ERR(_build_ldif_(dn, entry))
                    self.__optional_raise__(LdapObjectError(dn, str(e)))
                except ldap.STRONG_AUTH_REQUIRED, e:
                    _ERR('#\tThis change requires strong auth on ldap_modify(): %s' % str(e))
                    _ERR(_build_ldif_(dn, entry))
                    self.__optional_raise__(LdapError(str(e)))
                except ldap.CONSTRAINT_VIOLATION, e:
                    # python-ldap doesn't document how to access exception info
                    info = e.args[0]['info']
                    if 'Write-once' in info:
                        _DEB('Ignoring CONSTRAINT_VIOLATION response')
                    else:
                        _ERR('#\tConstraint violation on ldap_modify(): %s' % str(e))
                        _ERR(_build_ldif_(dn, entry))
                        self.__optional_raise__(LdapObjectError(dn, str(e)))
                except ldap.OPERATIONS_ERROR, e:
                    # python-ldap doesn't document how to access exception info
                    info = e.args[0]['info']
                    if info == 'Duplicated requestedApp':
                        _DEB('Ignoring OPERATIONS_ERROR response')
                    elif 'Object can not be created. It already exists' in info:
                        _DEB('Ignoring OPERATIONS_ERROR response')
                    else:
                        _ERR('#\tOperation error on ldap_modify(): %s' % str(e))
                        _ERR(_build_ldif_(dn, entry))                        
                        self.__optional_raise__(LdapObjectError(dn, str(e)))
                except ldap.NO_SUCH_ATTRIBUTE, e:
                    _ERR('#\tNo such attribute on ldap_modify(): %s' % str(e))
                    _ERR(_build_ldif_(dn, entry))
                    self.__optional_raise__(LdapObjectError(dn, str(e)))
                except Exception, e:
                    _ERR('#\tUnknown error on ldap_modify(): %s' % str(e))
                    _ERR('#\tException type: %s' % type(e))
                    _ERR(_build_ldif_(dn, entry))
                    self.__optional_raise__(LdapError(str(e)))


            def add_entries(self, add_function, modify_function=None):
                self.__add_function = add_function
                self.__modify_function = modify_function
                self.handle = self.__add_handler
                self.parse()

            def modify_entries(self, modify_function):
                self.__modify_function = modify_function
                self.handle = self.__modify_handler
                self.parse()
            

        def __init__(self, server_uri, use_LDAPv2=False,
                     auto_update=True, stop_on_error=False):
            self.__url = server_uri
            if server_uri.startswith('ldaps://'):
                ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)                
            self.__ldap = ldap.initialize(self.__url)
            self.__ldap.set_option(ldap.OPT_NETWORK_TIMEOUT, LDAP_TIMEOUT)
            self.__ldap.set_option(ldap.OPT_TIMEOUT, LDAP_TIMEOUT)
            self.__ldap.protocol_version = (
                ldap.VERSION2 if use_LDAPv2 else ldap.VERSION3)
            self.__auto_update = auto_update
            self.__stop_on_error = stop_on_error


        def set_user(self, user_id):
            self.__user_dn = user_id[0]
            self.__passwd = user_id[1]


        def open(self, user_dn, password):
            try:
                self.__ldap.simple_bind_s(user_dn, password)
            except ldap.SERVER_DOWN:
                _ERR('Cannot connect to LDAP server')
                raise LdapError('Unable to connect to LDAP server')
            except ldap.INVALID_CREDENTIALS:
                _ERR('Incalid credentials')
                raise LdapError('Invalid credentials')


        def close(self):
            self.__ldap.unbind_s()


        def add(self, ldif_content):
            parsed_ldif = self.MyLdifParser(cStringIO.StringIO(ldif_content),
                                            self.__stop_on_error)
            parsed_ldif.add_entries(
                self.__ldap.add_s,
                self.__ldap.modify_s if self.__auto_update else None)


        def modify(self, ldif_content):
            parsed_ldif = self.MyLdifParser(cStringIO.StringIO(ldif_content),
                                            self.__stop_on_error)
            parsed_ldif.modify_entries(self.__ldap.modify_s)


        def search(self, dn, scope=ldap.SCOPE_SUBTREE):
            try:
                result = self.__ldap.search_s(dn, scope)
            except ldap.NO_SUCH_OBJECT:
                raise LdapObjectNotFound(dn)
            ldif_result = ''
            for dn, entry in result:
                ldif_result += _build_ldif_(dn, entry)
            return ldif_result


        def __split_dn_list__(self, raw_dn_list):
            dn_list = []
            for candidate in raw_dn_list.splitlines():
                candidate = candidate.strip()
                if candidate == '':
                    continue
                dn_list.append(candidate)
            return dn_list


        def delete(self, dn):
            dn_list = self.__split_dn_list__(dn)
            for dn in dn_list:
                try:
                    self.__ldap.delete_s(dn)
                except ldap.NO_SUCH_OBJECT, e:
                    _ERR('#\tNo such attribute on ldap_delete(): %s' % str(e))
                    if self.__stop_on_error:
                        raise LdapObjectError(dn, str(e))

                except ldap.CONSTRAINT_VIOLATION, e:
                    _ERR('#\tConstraint violation on ldap_delete(): %s' % str(e))
                    if self.__stop_on_error:
                        raise LdapObjectError(dn, str(e))
                except Exception, e:
                    _ERR('#\tUnknown error on ldap_delete(): %s' % str(e))
                    _ERR('#\tException type: %s' % type(e))
                    if self.__stop_on_error:
                        raise LdapObjectError(dn, str(e))

else:
    class LdapConnection(object):
        '''Empty class, just to avoid errors if python-ldap is not installed'''
        def __init__(self, server_uri, use_LDAPv2=False, auto_update=False):
            pass

        def set_user(self, user_id):
            pass

        def open(self):
            pass

        def close(self):
            pass

        def add(self, ldif):
            pass

        def modify(self, ldif):
            pass

        def search(self, dn):
            pass

        def delete(self, dn):
            pass
