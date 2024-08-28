#!/usr/bin/env python
# -*- coding: utf-8 -*-

import SocketServer
import threading
import json
import os
import pickle
import socket

import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning

import hss_utils.dbus.services
from hss_utils.dbus.clients import RTC_GATEWAY_SERVICE_OBJ 
from hss_utils.dbus.clients import RTC_GATEWAY_SERVICE_PATH

class InvalidTcpMessage(Exception):
    def __init__(self, cause='unknown cause'):
        self.__err = cause

    def __str__(self):
        return 'FAILED. %s' % self.__err


DISPACHER=None
TCP_PORT=10000
FORWARD_TO=[]
#TRIGGER_TRANSLATOR = {
    #'new_build':['build_info_add','priority_add','check_priority_list'],
    #'faulty_build':['priority_del','set_test_to_faulty'],
    #'promote_release':['priority_increase']
#}
TRIGGER_TRANSLATOR = {}

CONFIG_PATH='/etc/rtc_gateway'
CFG_FILE= 'service_configuration.json'

class Dispacher(object):
    def __init__(self):
        self.__actions={}

    def install_handler(self, key, handler):
        self.__actions.update({key:handler})

    @property
    def actions(self):
        return self.__actions

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):pass

class TCP_Handler(SocketServer.StreamRequestHandler):

    def handle(self):
        while True:
            message = self.rfile.readline().strip()
            if not message:  # EOF
                break

            try:
                trigger, build, args, request_answer = self.decode(message)
            except InvalidTcpMessage as e:
                _ERR('%s' % e)
                continue

            if FORWARD_TO:
                self.forward_to(message)

            actions = TRIGGER_TRANSLATOR.get(trigger,[])
            _INF('')
            _INF('Received trigger      : %s' % trigger)
            _INF('Actions               : %s' % '  '.join(actions))
            _INF('Build                 : %s' % build)
            _INF('Request answer        : %s' % request_answer)
            _INF('Received parameters   : %s' % args)
            _INF('')
            if len(actions) == 0:
                answer = 'WARNING. No actions for the received trigger "%s"' % trigger
                _WRN(answer)
                if request_answer:
                    self.wfile.write(answer)
                continue

            allowed = True
            for action in actions:
                if action not in DISPACHER.actions.keys():
                    answer = 'FAILED. Configured action %s not in allowed values: %s' % (action, ' '.join(DISPACHER.actions.keys()))
                    _ERR(answer)
                    if request_answer:
                        self.wfile.write(answer)
                    allowed = False
                    break

            if allowed:
                answer = 'OK. The following actions have been executed %s' % ' '.join(actions)
                for action in actions:
                    try:
                        DISPACHER.actions[action](build, args)
                    except Exception as e:
                        answer = 'FAILED. Error handling action %s: %s' % (action, e)
                        _ERR(answer)
                        break

                if request_answer:
                    self.wfile.write(answer)


    def forward_to(self,message):
        _DEB('Function forward_to')
        for host in FORWARD_TO:
            # Create a socket (SOCK_STREAM means a TCP socket)
            _DEB('Trying to create a socket for %s' % host)
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            except Exception as e:
                _ERR('create socket problem: %s' % e)
                continue

            _DEB('Trying to open a connection to %s' % host)
            try:
                sock.connect((host, TCP_PORT))
            except Exception as e:
                _ERR('connect to %s problem: %s' % (host,e))
                continue

            _DEB('Trying to forward the just received message to %s' % host)
            try:
                sock.sendall(message)
            except Exception as e:
                _ERR('sendall to %s problem: %s' % (host,e))
                sock.close()
                continue

            _INF('The just received message has been forwarded to %s' % host)
            sock.close()

        return



    def decode(self,message):
        try:
            message = json.loads(message)
        except Exception as e:
            error = 'Cannot decode message "%s": %s' % (message, e)
            raise InvalidTcpMessage(error)
        try:
            trigger = message['op']
            build = message['build']
            args = message.get('args',[])
            request_answer = message.get('request_answer',False)
        except KeyError as e:
            error = 'Error extracting %s from TCP message: %s' % (e,message)
            raise InvalidTcpMessage(error)

        return trigger, build, args, request_answer


class Handler(object):
    def __init__(self):
        global DISPACHER
        global TRIGGER_TRANSLATOR
        global FORWARD_TO
        self.__tcpserver = None
        self.__tcpserver_thread = None

        try:
            with open(os.path.join(CONFIG_PATH,CFG_FILE)) as json_data:
                data = json.load(json_data)
                TCP_PORT = data['tcp_port']
                TRIGGER_TRANSLATOR = data['trigger_translator']
                FORWARD_TO = data.get('forward_to',[])
        except IOError as e:
            _INF('Missing configuration file. %s' % e)
            self.save_config()
        except Exception as e:
            _ERR('Error parsing json %s file: %s' % (os.path.join(CONFIG_PATH,CFG_FILE), e))
            raise e

        self.__build_handler_client = hss_utils.dbus.clients.Build_handler_Client()
        self.open_tcp_server()

        DISPACHER = Dispacher()
        DISPACHER.install_handler('build_info_add',self.build_info_add)
        DISPACHER.install_handler('build_info_update',self.build_info_update)
        DISPACHER.install_handler('release_info_purge',self.release_info_purge)
        DISPACHER.install_handler('project_info_purge',self.project_info_purge)

        DISPACHER.install_handler('check_priority_list',self.check_priority_list) 
        DISPACHER.install_handler('set_test_to_faulty',self.set_test_to_faulty)  

        DISPACHER.install_handler('priority_add',self.priority_add)
        DISPACHER.install_handler('priority_del',self.priority_del)
        DISPACHER.install_handler('priority_increase',self.priority_increase)

        DISPACHER.install_handler('baseline_add',self.baseline_add)

        self.__watcher = hss_utils.dbus.Watcher()
        self.__watcher.install_handler('cli_update_trigger',self.update_trigger)
        self.__watcher.install_handler('cli_fetch_tcp_port',self.fetch_tcp_port)
        self.__watcher.install_handler('cli_fetch_trigger',self.fetch_trigger)


    def open_tcp_server(self):
        _INF('Open TCP server at %s' % TCP_PORT)
        self.__tcpserver = ThreadedTCPServer(("0.0.0.0", TCP_PORT), TCP_Handler)
        self.__tcpserver_thread = threading.Thread(target=self.__tcpserver.serve_forever)
        self.__tcpserver_thread.daemon = True


    def fetch_tcp_port(self,signal_answer):
        _DEB('Function fetch_tcp_port')
        answer = '%s' % TCP_PORT
        self.__watcher.emit(signal_answer,answer)


    def update_trigger(self,signal_answer, operation, trigger, actions):
        _DEB('Function update_trigger')
        global TRIGGER_TRANSLATOR

        if operation == 'update':
            for action in actions:
                if action not in DISPACHER.actions.keys():
                    answer = '%s is not in allowed actions: %s' % (action, ' '.join(DISPACHER.actions.keys()))
                    _WRN(answer)
                    self.__watcher.emit(signal_answer,answer)

            try:
                TRIGGER_TRANSLATOR[trigger] = actions
                self.save_config()
                answer = 'EXECUTED'
            except KeyError:
                answer = 'Trigger not valid. Allowed values are: %s' % (' | '.join(TRIGGER_TRANSLATOR.keys()))
        elif operation == 'delete':
            try:
                del TRIGGER_TRANSLATOR[trigger]
                self.save_config()
                answer = 'EXECUTED'
            except KeyError:
                answer = 'Trigger not valid. Allowed values are: %s' % (' | '.join(TRIGGER_TRANSLATOR.keys()))
        else:
            answer = 'Operation not valid. Allowd values are: update | delete'

        self.__watcher.emit(signal_answer,answer)


    def fetch_trigger(self,signal_answer):
        _DEB('Function fetch_trigger')
        answer = 'Available actions: '
        for action in sorted(DISPACHER.actions.keys()):
            answer += '\n\t%s' % action
        answer += '\nAvailable triggers: '
        for key, value in TRIGGER_TRANSLATOR.items():
            answer += '\n\t%s:   \n\t\t%s' %(key, '\n\t\t'.join(value))
        answer += '\n'
        self.__watcher.emit(signal_answer,answer)


    def save_config(self):
        _DEB('Function save_config')
        data = {'trigger_translator':TRIGGER_TRANSLATOR,
                'tcp_port':TCP_PORT}

        if not os.path.exists(CONFIG_PATH):
            os.makedirs(CONFIG_PATH)

        with open(os.path.join(CONFIG_PATH, CFG_FILE), 'w') as fp:
            json.dump(data, fp, indent=4)


    def start(self):
        self.__tcpserver_thread.start()


    def stop(self):
        self.__watcher.stop()
        self.__tcpserver.shutdown()
        self.__tcpserver.server_close()


    @property
    def running(self):
        return self.__tcpserver_thread.isAlive()


    def build_info_add(self, build, info):
        _DEB('Function build_info_add for %s' % build)
        try:
            test_info = info[0]
        except Exception as e:
            _WRN('Problem reading test info %s' % e)
            raise e

        assert(isinstance(test_info, dict))

        self.__build_handler_client.build_info_add(build,test_info)


    def build_info_update(self, build, info):
        _DEB('Function build_info_update for %s' % build)
        try:
            test_info = info[0]
        except Exception as e:
            _WRN('Problem reading test info %s' % e)
            raise e

        assert(isinstance(test_info, dict))

        self.__build_handler_client.build_info_update(build,test_info)


    def release_info_purge(self, build, info):
        _DEB('Function release_info_purge for %s' % build)
        release = self.__build_handler_client.get_release(build)
        _INF('cleanning all builds for %s release except %s' % (release,build))
        self.__build_handler_client.clean_build(release)


    def project_info_purge(self, build, info):
        _DEB('Function project_info_purge for %s' % build)
        project = self.__build_handler_client.get_project(build)
        _INF('cleanning all builds for %s project except %s' % (project,build))
        self.__build_handler_client.clean_build(project,exclude=build)


    def check_priority_list(self, build, info):
        _DEB('Function check_priority_list')
        self.__watcher.emit('rtc_check_priority_list')


    def set_test_to_faulty(self, build, info):
        _DEB('Function set_test_to_faulty for %s' % build)
        self.__watcher.emit('rtc_set_test_to_faulty', build)


    def priority_add(self, build, info):
        _DEB('Function priority_add for %s' % build)
        self.__build_handler_client.priority_add(build)


    def priority_del(self, build, info):
        _DEB('Function priority_del for %s' % build)
        self.__build_handler_client.priority_del(build,update_status=True)


    def priority_increase(self, build, info):
        _DEB('Function priority_increase for %s' % build)
        was_pending = self.__build_handler_client.priority_increase(build)
        self.__watcher.emit('rtc_priority_increase', build, was_pending)


    def baseline_add(self, build, info):
        _DEB('Function baseline_add for %s' % build)
        self.__build_handler_client.baseline_add(build)


