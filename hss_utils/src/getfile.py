#!/usr/bin/env python
#
'''Support fetching files from several sources'''

import shlex
import base64
import shutil
import hashlib
import getpass
import os.path
import urllib2
import tempfile
import subprocess

try:
    import hss_utils.connection
    import hss_utils.connection.ssh
    _USE_SSH_ = True
except ImportError:
    _USE_SSH_ = False

_ARM_GET_ = None


class InvalidProtocolHandler(Exception):
    def __init__(self, handler):
        self.__hnd = handler

    def __str__(self):
        return 'Unknown protocol handler: %s' % self.__hnd


class ChecksumFailed(Exception):
    def __init__(self, got, expected):
        self.__got = got
        self.__exp = expected

    def __str__(self):
        return 'Checksum failed! (got: "%s" expected: "%s")' % (
            self.__got, self.__exp)


class CannotGetResource(Exception):
    def __init__(self, resource):
        self.__res = resource

    def __str__(self):
        return 'Cannot get "%s"' % self.__res


def _local_file_(src, dest):
    '''Get file from local file'''
    try:
        shutil.copyfile(src, dest)
    except Exception, e:
        raise CannotGetResource('file://%s' % src)


def _http_file_(src, dest):
    '''Get file from HTTP'''
    try:
        _get_url_('http://%s' % src, dest)
    except urllib2.HTTPError, e:
        raise CannotGetResource('http://%s' % src)


def _https_file_(src, dest):
    '''Get file from HTTPS'''
    try:
        _get_url_('https://%s' % src, dest)
    except urllib2.HTTPError, e:
        raise CannotGetResource('https://%s' % src)


def _arm_https_(src, dest):
    '''Download files from ARM repo using HTTPS'''
    # Load API key
    try:
        with open(os.path.expanduser('~/.armkey'), 'r') as fd:
            key = fd.read().replace('\n', '').strip()
    except Exception, e:
        raise CannotGetResource('arm+https://%s (".armkey" not found)' % src)
    # Add header
    auth_str = base64.encodestring(
        '%s:%s' % (getpass.getuser(), key)).replace('\n', '')
    try:
        _get_url_('https://%s' % src, dest,
                  {'Authorization': 'Basic %s' % auth_str })
    except urllib2.HTTPError, e:
        raise CannotGetResource('arm+https://%s' % src)


def _arm_md5_(src, dest):
    '''Download files from ARM repo using MD5 search'''
    global _ARM_GET_
    if _ARM_GET_ is None:
        try:
            _ARM_GET_ = subprocess.check_out(['which', 'arm_get']).strip()
        except Exception, e:
            raise CannotGetResource('arm+md5://%s (arm_get not found!)' % src)
    filename = os.path.basename(dest)
    out_folder = os.path.dirname(dest)
    if out_folder == '':
        out_folder = os.path.abspath(os.path.curdir)
    armget_cmd = '%s -f %s -o %s md5:%s' % (_ARM_GET_,
                                            filename,
                                            out_folder,
                                            src)
    try:
        subprocess.check_call(shlex.split(armget_cmd))
    except Exception, e:
        raise CannotGetResource('arm+md5://%s (%s)' % (src, e))


def _arm_sha1_(src, dest):
    '''Download files from ARM repo using SHA-1 search'''
    global _ARM_GET_
    if _ARM_GET_ is None:
        try:
            _ARM_GET_ = subprocess.check_out(['which', 'arm_get']).strip()
        except Exception, e:
            raise CannotGetResource('arm+sha1://%s (arm_get not found!)' % src)
    filename = os.path.basename(dest)
    out_folder = os.path.dirname(dest)
    if out_folder == '':
        out_folder = os.path.abspath(os.path.curdir)
    armget_cmd = '%s -f %s -o %s sha1:%s' % (_ARM_GET_,
                                             filename,
                                             out_folder,
                                             src)
    try:
        subprocess.check_call(shlex.split(armget_cmd))
    except Exception, e:
        raise CannotGetResource('arm+sha1://%s (%s)' % (src, e))


def _get_url_(url, filename, extra_headers={}):
    file_get = urllib2.build_opener()
    file_get.addheaders = extra_headers.items()
    conn = file_get.open(url)
    with open(filename, 'w') as fd:
        while True:
            buffer = conn.read(8192)
            if not buffer:
                break
            fd.write(buffer)


def _scp_(src, dest):
    if not _USE_SSH_:
        raise CannotGetResource('scp://%s (hss-utils not installed)' % src)

    # src = "user@host:/source/file"
    if '@' in src:
        user = src.split('@')[0]
        src = '@'.join(src.split('@')[1:])
    else:
        user = getpass.getuser()

    # src = "host:/source/file"
    host = src.split(':')[0]
    src = src.split(':')[1]

    # This onnly works if current user has a "ssh-key-paired" connection
    try:
        remote_host = connection.ssh.SSHEndpoint({'host': host,
                                                  'user': user})
        scp = connection.ssh.SSHChannel(remote_host)
        scp.set_transfer_timeout(-1)
        scp.download(src, filename)
    except Exception, e:
        raise CannotGetResource('scp://%s (%s)' % (src, e))


_HANDLERS_ = {
    'file': _local_file_,
    'http': _http_file_,
    'https': _https_file_,
    'arm+https': _arm_https_,
    'arm+md5': _arm_md5_,
    'arm+sha1': _arm_sha1_,
    'ssh': _scp_,
    'scp': _scp_
}


def from_uri(uri, destination=None, md5=None, sha1=None):
    def split_uri(uri):
        if '://' not in uri:
            # Assuming local filename
            return 'file', uri
        handler = uri.split('://')[0]
        ref = '://'.join(uri.split('://')[1:])
        return handler, ref

    def check_sum(filename, cksum, hasher):
        if cksum is None:
            return
        with open(filename, 'rb') as fd:
            for chunk in iter(lambda: fd.read(4096), b""):
                hasher.update(chunk)
        if cksum != hasher.hexdigest():
            raise ChecksumFailed(hasher.hexdigest(), md5)
        
    def check_md5(filename, md5):
        check_sum(filename, md5, hashlib.md5())

    def check_sha1(filename, sha1):
        check_sum(filename, md5, hashlib.sha1())

    handler, ref = split_uri(uri)
    if handler not in _HANDLERS_.keys():
        raise InvalidProtocolHandler(handler)

    if destination is None:
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        tmp_file.close()
        destination = tmp_file.name

    _HANDLERS_[handler](ref, destination)
    check_md5(destination, md5)
    check_sha1(destination, sha1)

    return destination


def from_list(uri_list, destination=None, md5=None):
    for uri in uri_list:
        try:
            return from_uri(uri, destination, md5)
        except CannotGetResource:
            continue
    raise CannotGetResource('Failed to fetch: %s' % ','.join(uri_list))
