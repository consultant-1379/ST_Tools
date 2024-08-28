#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import logging.config
import sys
import time
import os

LOGGER_ID = 'hss_utils'
# Load defaults logging options

_YELLOW = '\033[1;33m'
_RED = '\033[1;31m'
_GREEN = '\033[1;32m'
_BLUE = '\033[34m'
_WHITE = '\033[1;38m'
_NORMAL = '\033[0m'
_PINK = '\033[1;35m'

_WARNING_TAG = '[%s WRN %s]' % (_YELLOW, _NORMAL)
_ERROR_TAG =   '[%s ERR %s]' % (_RED, _NORMAL)
_DEBUG_TAG =   '[%s DEB %s]' % (_BLUE, _NORMAL)
_INFO_TAG =    '[%s INF %s]' % (_GREEN, _NORMAL)

DEBUG = logging.DEBUG
INFO =logging.INFO
ERROR =logging.ERROR
WARNING =logging.WARNING

def _time(show_timestamp):
    return '<%s%s%s>' % (_WHITE,
                         time.ctime().split()[3],
                         _NORMAL) if show_timestamp else ''



CONSOLE_LOG_LEVEL = logging.INFO

def change_console_level(level):
    global CONSOLE_LOG_LEVEL 
    CONSOLE_LOG_LEVEL = level

def set_core_name(name, logdir=None, timestamp=True, level=logging.DEBUG):
    global _CORE_NAME

    _CORE_NAME = name

    homepath = os.getenv('HOME')
    if homepath  is None:
        homepath = '/tmp'
    if logdir is None:
        logdir = os.path.join(homepath, '.hss_utils_log')
    if os.path.exists(os.path.join(homepath, '.hss_utils_logging.conf')):
        logging.config.fileConfig(os.path.join(homepath, '.hss_utils_logging.conf'))
    else:
        # No logging configuration found, using DEFAULT
        if not os.path.exists(logdir):
            print os.popen('mkdir -p %s' % logdir).read()
        if timestamp:
            basename = '%s_%s' % (_CORE_NAME, '.'.join(map(str, time.localtime()[:5])))
        else:
            basename = _CORE_NAME
        f_name = os.path.join(logdir, basename)

        if os.path.exists(f_name):
            f_name += '~1'
            i = 1
            while os.path.exists(f_name):
                i += 1
                f_name = f_name.split('~')[0] + '-%s' % i

        logging.basicConfig(
            filename=f_name,
            format='%(asctime)s - %(funcName)s - %(levelname)s - %(message)s',
            level=level
        )
    global _LOGGER
    _LOGGER = logging.getLogger(_CORE_NAME)
    _LOGGER.propagate=False


def logger():
    return _LOGGER


def debug(message, show_time=True):
    try:
        message = str(message).replace('\n', '\n\t')
    except:
        pass
    try:
        name = '(%s)' % _CORE_NAME
    except:
        name = ''    
    try:
        _LOGGER.debug(message)
    except:
        pass

    if CONSOLE_LOG_LEVEL <= logging.DEBUG:
        print >> sys.stderr, '\r%s%s %s %s' % (name, _DEBUG_TAG, _time(show_time), message)


def warning(message, show_time=True):
    try:
        message = str(message).replace('\n', '\n\t')
    except:
        pass
    try:
        name = '(%s)' % _CORE_NAME
    except:
        name = ''
    try:
        _LOGGER.warning(message)
    except:
        pass

    if CONSOLE_LOG_LEVEL <= logging.WARNING:
        print >> sys.stderr, '\r%s%s %s %s' % (name, _WARNING_TAG, _time(show_time), message)


def error(message, show_time=True):
    try:
        message = str(message).replace('\n', '\n\t')
    except:
        pass
    try:
        name = '(%s)' % _CORE_NAME
    except:
        name = ''
    try:
        _LOGGER.error(message)
    except:
        pass

    if CONSOLE_LOG_LEVEL <= logging.ERROR:
        print >> sys.stderr, '\r%s%s %s %s ' % (name, _ERROR_TAG, _time(show_time), message)


def info(message, show_time=True):
    try:
        message = str(message).replace('\n', '\n\t')
    except:
        pass
    try:
        name = '(%s)' % _CORE_NAME
    except:
        name = ''
    try:
        _LOGGER.info(message)
    except:
        pass
    if CONSOLE_LOG_LEVEL <= logging.INFO:

        print >> sys.stderr, '\r%s%s %s %s' % (name, _INFO_TAG, _time(show_time), message)

