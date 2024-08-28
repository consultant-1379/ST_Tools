#!/usr/bin/env python

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
