#!/usr/bin/env python
#

import sys
import os
CWD = os.getcwd()
import os.path
import time
import traceback
import argparse
import re
import random

import e3utils.log as logging
_DEB = logging.internal_debug
_WRN = logging.warning
_ERR = logging.error
_INF = logging.info

import hss_utils.rosetta
import hss_utils.rosetta.services
from . import ExecutionTimeout
from . import NotFound
from . import CommandFailure
from . import WrongParameter
from . import ip2int
from . import is_ip_in_net


def DUMMYNET_pipe_list_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--dir','-d',
                      action='store', default='both',
                      choices = ['outgoing', 'incoming', 'both'],
                      help='Pipe direction. outgoing = HSS->PeerNode   incoming = PeerNode->HSS. If omitted both will be listed',
                      dest='direction')

    return (parser)

def run_DUMMYNET_pipe_list(user_config, node):

    if user_config.direction in ['outgoing', 'both']:
            for line in node.pipe_outgoing():
                print 'HSS->%s Peer Node   %s' % (user_config.traffic_type,line)

    if user_config.direction in ['incoming', 'both']:
            for line in node.pipe_incoming():
                print '%s Peer Node->HSS   %s' % (user_config.traffic_type,line)



def DUMMYNET_pipe_enable_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--dir','-d',
                      action='store', default='both',
                      choices = ['outgoing', 'incoming', 'both'],
                      help='Pipe direction. outgoing = HSS->PeerNode   incoming = PeerNode->HSS. If omitted both will be used',
                      dest='direction')
    command_params.add_argument('--pipes',
                      action='store', default=[],nargs='+',
                      help='List of Pipes to be configured. If set then --dir parameter will be ignored',
                      dest='pipes')

    command_params.add_argument('--delay',
                      action='store', default=None,
                      help='Delay value',
                      dest='delay')

    command_params.add_argument('--plr',
                      action='store', default=None,
                      help='Packet lost rate value',
                      dest='plr')

    return (parser)

def run_DUMMYNET_pipe_enable(user_config, node):


    if user_config.pipes:
        node.enable_pipe(user_config.pipes, user_config.delay, user_config.plr)

    else:
        if user_config.direction in ['outgoing', 'both']:
            node.enable_pipe(node.outgoing, user_config.delay, user_config.plr)

        if user_config.direction in ['incoming', 'both']:
            node.enable_pipe(node.incoming, user_config.delay, user_config.plr)


def DUMMYNET_pipe_disable_parser():
    parser = argparse.ArgumentParser(add_help=False)
    command_params = parser.add_argument_group('Specific command options')
    command_params.add_argument('--dir','-d',
                      action='store', default='both',
                      choices = ['outgoing', 'incoming', 'both'],
                      help='Pipe direction. outgoing = HSS->PeerNode   incoming = PeerNode->HSS. If omitted both will be used',
                      dest='direction')
    command_params.add_argument('--pipes',
                      action='store', default=[],nargs='+',
                      help='List of Pipes to be disabled. If set then --dir parameter will be ignored',
                      dest='pipes')

    return (parser)

def run_DUMMYNET_pipe_disable(user_config, node):


    if user_config.pipes:
        node.disable_pipe(user_config.pipes)

    else:
        if user_config.direction in ['outgoing', 'both']:
            node.disable_pipe(node.outgoing)

        if user_config.direction in ['incoming', 'both']:
            node.disable_pipe(node.incoming)


