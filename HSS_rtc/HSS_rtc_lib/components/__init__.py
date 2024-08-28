#!/usr/bin/env python

from shared import *
import test_cases

class ExecutionConfigurationError(Exception):
    def __init__(self, cause='unknown cause'):
        self.__err = cause

    def __str__(self):
        return 'Execution Configuration Error: %s' % self.__err


class ExecutionStartError(Exception):
    def __init__(self, cause='unknown cause'):
        self.__err = cause

    def __str__(self):
        return 'Execution Start Error: %s' % self.__err

class ExecutionRunError(Exception):
    def __init__(self, cause='unknown cause'):
        self.__err = cause

    def __str__(self):
        return 'Execution Run Error: %s' % self.__err

class ExitRtc(Exception):
    def __init__(self, cause='unknown cause'):
        self.__err = cause

    def __str__(self):
        return 'Exit RTC: %s' % self.__err

class StopTestCaseOnFail(Exception):
    def __init__(self, cause='unknown cause'):
        self.__err = cause

    def __str__(self):
        return 'Stop TestCase on fail: %s' % self.__err

class BatError(Exception):
    def __init__(self, cause='unknown cause'):
        self.__err = cause

    def __str__(self):
        return 'BAT Error: %s' % self.__err

class SkipPhase(Exception):
    def __init__(self, cause='unknown phase'):
        self.__err = cause

    def __str__(self):
        return 'Skip phase on fail: %s ' % self.__err
