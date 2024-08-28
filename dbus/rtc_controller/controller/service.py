#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import os
import os.path
import json
import pprint
import sys
import traceback
from packaging import version as fversion
import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning

from distutils.version import LooseVersion
import threading
import hss_utils.dbus.services
from hss_utils.dbus.clients import RTC_CONTROLLER_SERVICE_OBJ 
from hss_utils.dbus.clients import RTC_CONTROLLER_SERVICE_PATH 
from . import ExecutionConfigurationError
from . import ExecutionStartError
from . import ExecutionRunError
from . import rtc_handler

CONFIG_PATH='/etc/rtc_controller'
#CONFIG_PATH='/opt/hss/rtc_controller'
CFG_FILE= 'service_configuration.json'

class Handler(object):
    def __init__(self):

        self.__build_handler_client = hss_utils.dbus.clients.Build_handler_Client()

        self.__watcher = hss_utils.dbus.Watcher()
        self.__watcher.install_handler('rtc_check_priority_list',self.check_priority_list)
        self.__watcher.install_handler('rtc_set_test_to_faulty',self.set_test_to_faulty)
        self.__watcher.install_handler('rtc_priority_increase',self.priority_increase)
        self.__watcher.install_handler('test_tool_ready_for_new_build',self.test_tool_ready_for_new_build)
        self.__watcher.install_handler('test_tool_shutdown',self.test_tool_shutdown)
        self.__watcher.install_handler('cli_fetch_pending_build_list',self.fetch_pending_build_list)
        self.__watcher.install_handler('cli_fetch_available_builds',self.fetch_available_builds)
        self.__watcher.install_handler('cli_fetch_build_test_result',self.fetch_build_test_result)
        self.__watcher.install_handler('cli_force_build',self.force_build)
        self.__watcher.install_handler('cli_clean_build',self.clean_build)
        self.__watcher.install_handler('cli_purge_build',self.purge_build)
        self.__watcher.install_handler('cli_set_build_status',self.set_build_status)
        self.__watcher.install_handler('cli_status',self.status)
        self.__watcher.install_handler('cli_pause',self.pause)
        self.__watcher.install_handler('cli_resume',self.resume)
        self.__watcher.install_handler('cli_fetch_config',self.fetch_config)
        self.__watcher.install_handler('cli_update_config',self.update_config)
        self.__watcher.install_handler('cli_activate_baseline',self.activate_baseline)
        self.__watcher.install_handler('cli_fetch_baseline',self.fetch_baseline)
        self.__watcher.install_handler('cli_add_baseline',self.add_baseline)
        self.__watcher.install_handler('cli_del_baseline',self.del_baseline)
        self.__watcher.install_handler('cli_fetch_build_test_info',self.fetch_build_test_info)
        self.__watcher.install_handler('cli_update_build_test_info',self.update_build_test_info)

        self.__rtc_handler = None
        self.rtc_start_event = None
        self.__service_paused = True
        self.__have_to_exit = False
        self.__current_test_can_be_stopped = False
        self.__service_config = {}

        try:
            with open(os.path.join(CONFIG_PATH,CFG_FILE)) as json_data:
                self.__service_config = json.load(json_data)

        except IOError as e:
            _WRN('Service not configured yet. %s' % e)
        except Exception, e:
            _ERR('Error parsing json %s file: %s' % (os.path.join(CONFIG_PATH,CFG_FILE), e))

        self.__test_config = {'build':None,
                              'build_info':None,
                              'high_priority':False}

    def save_service_config(self):
        try:
            if not os.path.exists(CONFIG_PATH):
                os.makedirs(CONFIG_PATH)

            with open(os.path.join(CONFIG_PATH, CFG_FILE), 'w') as fp:
                json.dump(self.__service_config, fp, indent=4)
        except Exception, e:
            _ERR('Error saving %s file: %s' % (os.path.join(CONFIG_PATH,CFG_FILE), e))

    @property
    def build(self):
        return self.__test_config['build']

    @build.setter
    def build(self, value):
        self.__test_config['build']=value

    @property
    def build_info(self):
        return self.__test_config['build_info']

    @build_info.setter
    def build_info(self, value):
        self.__test_config['build_info']=value

    @property
    def high_priority(self):
        return self.__test_config['high_priority']

    @high_priority.setter
    def high_priority(self, value):
        self.__test_config['high_priority']=value

    @property
    def running(self):
        return self.__watcher.running

    def stop(self):
        self.__have_to_exit = True
        if self.ongoing_test:
            self.__rtc_handler.shutdown()
        self.__watcher.stop()

        for thread in threading.enumerate():
            try:
                if isinstance(thread,rtc_handler.RTC_Handler):
                    thread.activate_force_exit()
            except Exception as e:
                _WRN(str(e))


    @property
    def ongoing_test(self):
        return False if self.__rtc_handler is None else self.__rtc_handler.ongoing_test


    def start_hss_rtc_execution(self, build=None,build_info=None,high_priority=False,test_suite=None):
        _DEB('Function start_hss_rtc_execution')

        if build is None:
            try:
                self.build, self.build_info, self.high_priority = self.__build_handler_client.get_build
                if None in [self.build, self.build_info]:
                    _WRN('Build or build_info not found in start_hss_rtc_execution')
                    return
            except Exception as e:
                _WRN('Error finding a build. %s' % e)
                return

        elif build_info is None:
            try:
                self.build_info = self.__build_handler_client.fetch_build(build)
                if self.build_info is None:
                    _WRN('Build_info not found in start_hss_rtc_execution')
                    return
            except Exception as e:
                _WRN('Problem searching build_info: %s' % e)
                return

            self.build = build
            self.high_priority = high_priority

        else:
            self.build = build
            self.build_info = build_info
            self.high_priority = high_priority

        _INF('Start testing build %s %s' % (self.build, ('(High priority)' if self.high_priority else '')))

        try:
            self.rtc_start_event = threading.Event()
            self.__rtc_handler = rtc_handler.RTC_Handler(self.__test_config,self.__service_config,
                                                         self.rtc_start_event, self.baseline_test_info,
                                                         test_suite=test_suite)
            self.__rtc_handler.daemon = True
        except Exception as e:
            _ERR('Problem creating RTC_Handler for %s build test: %s' % (self.build, e))
            exc_type, exc_value, exc_traceback = sys.exc_info()
            for tb in traceback.format_tb(exc_traceback):
                _ERR(tb)
            if not self.__service_paused:
                self.__build_handler_client.update_build_status(self.build,'TEST_FAULTY')
            self.clean()
            return

        self.__current_test_can_be_stopped=False
        try:
            self.__rtc_handler.prepare_test_scenario()
        except Exception as e:
            _ERR('%s' % e)
            if not self.__service_paused:
                self.__build_handler_client.update_build_status(self.build,'TEST_FAULTY')
            self.clean()
            return

        self.__rtc_handler.start()
        self.rtc_start_event.wait()
        if self.__rtc_handler.execution_info_error is not None:
            _ERR('Problem starting %s build test: %s' % (self.build, self.__rtc_handler.execution_info_error))
            if not self.__service_paused:
                self.__build_handler_client.update_build_status(self.build,'TEST_FAULTY')
            self.clean()
        else:
            if not self.__service_paused:
                self.__build_handler_client.update_build_status(self.build,'TEST_ONGOING')

    def stop_test(self):
        self.__rtc_handler.stop()
        self.clean()

    def clean(self):
        self.__rtc_handler = None
        self.__current_test_can_be_stopped = False
        self.build = None
        self.build_info = None
        self.high_priority = False

    ## Signals from service

    def check_priority_list(self):
        _DEB('Function check_priority_list')
        if self.__service_paused:
            _WRN('Service in paused state. No actions')
            return
        if self.high_priority and not self.__current_test_can_be_stopped:
            _INF('Testing a High priority build that can not be stopped. No actions')
            return

        if self.__build_handler_client.is_there_build_to_test:
            if self.ongoing_test:
                if not self.__current_test_can_be_stopped:
                    _INF('Ongoing test for %s build can not be stopped. No actions' % self.build)
                else:
                    _INF('Ongoing test for %s build will be stopped' % self.build)
                    self.__rtc_handler.stop()
            else:
                self.start_hss_rtc_execution()

        else:
            _INF('There is not a build for testing.')

    def set_test_to_faulty(self, build):
        _DEB('Function set_test_to_faulty for %s' % build)
        if self.__service_paused:
            _WRN('Service in paused state. No actions')
            return

        if self.build != build:
            _INF('%s is not being tested. No actions' % build)
            return

        if self.__rtc_handler is None:
            _INF('There is not an ongoing test')
            return

        self.__rtc_handler.set_test_excution_as_discarded()
        self.__build_handler_client.update_build_status(self.build,'CANCELLED')
        self.__current_test_can_be_stopped = True
        self.__watcher.emit('rtc_check_priority_list')


    def priority_increase(self, build, was_pending):
        _DEB('Function priority_increase of %s that was %spending' %(build,
                                                                      ('' if was_pending else 'not ')))
        if self.__service_paused:
            _WRN('Service in paused state. No actions')
            return

        if self.ongoing_test and self.build == build:
                _INF('Update High priority in Test Tool')
                self.__rtc_handler.high_priority = True
                self.high_priority = True
                return

        if not self.high_priority and was_pending:
            self.__current_test_can_be_stopped = True
            self.__watcher.emit('rtc_check_priority_list')


    ## Signals from HSS_rtc test tool

    def test_tool_ready_for_new_build(self, build):
        _DEB('Function test_tool_ready_for_new_build')
        if self.__service_paused:
            _WRN('Service in paused state. Keep on executing ongoing test')
            if self.__rtc_handler is not None:
                self.__rtc_handler.resume_test()
            return

        if build != self.build:
            _INF('Delayed signal. No actions.')
            return

        self.__current_test_can_be_stopped=True
        if self.__build_handler_client.is_there_build_to_test:
            self.__watcher.emit('rtc_check_priority_list')
        else:
            self.__rtc_handler.resume_test()


    def test_tool_shutdown(self, build, test_result):
        _DEB('Function test_tool_shutdown')
        self.__build_handler_client.add_build_test_result(build, test_result)

        if build != self.build:
            _INF('Delayed signal. No actions.')
            return

        self.__current_test_can_be_stopped = False
        self.__rtc_handler = None
        self.build = None
        self.build_info = None
        self.high_priority = False

        self.__watcher.emit('rtc_check_priority_list')


    ## Signals from rtc_cli. The signal_answer received as parameter shall be sent

    def status(self,signal_answer):
        _DEB('Function status called via rtc_cli')
        info = 'Service is %s\n' % ('in paused state' if self.__service_paused else 'running')
        if self.ongoing_test:
            info += '\tTesting %s %susing %s' % (self.build,
                                               ('(High Priority) ' if self.high_priority else ''),
                                               self.build_info)
 
        self.__watcher.emit(signal_answer,info)

    def fetch_config(self,signal_answer):
        _DEB('Function fetch_config called via rtc_cli')
        answer = 'Not configured yet'
        if self.__service_config:
            answer = self.__service_config

        self.__watcher.emit(signal_answer,answer)


    def update_config(self,signal_answer, cfg, persist=False):
        _DEB('Function update_config called via rtc_cli')
        if not self.__service_paused:
            _WRN('Service shall be in paused state. No actions')
            answer= 'Service shall be in paused state. No actions'
            self.__watcher.emit(signal_answer,answer)
            return

        try:
            baseline = cfg['service_parameters']['base_release']
            if baseline:
                if self.check_baseline(baseline):
                    answer = 'EXECUTED'
                    self.__service_config = cfg
                    if persist:
                        self.save_service_config()
                else:
                    answer = 'ERROR: Baseline not allowed. Be sure that there is a build with valid test info for this baseline'
            else:
                raise KeyError
        except KeyError:
            message = 'base_release not set in rtc_service config file'
            _WRN(message)
            answer = 'EXECUTED. Warning: %s' % message
            self.__service_config = cfg
            if persist:
                self.save_service_config()

        self.__watcher.emit(signal_answer,answer)


    @property
    def baseline(self):
        try:
            return self.__service_config['service_parameters']['base_release']
        except KeyError:
            return None

    @property
    def baseline_test_info(self):
        if self.baseline is None:
            _WRN('Baseline no set yet')
            return {}
        try:
            build, build_info =  self.__build_handler_client.fetch_baseline_test_info(self.baseline)
            test_info = {'build':build,'build_info': build_info,'hss_release':self.hss_release(build, build_info)}
        except Exception as e:
            _ERR('Problem base_hss_release:%s' % e)
            test_info = {}

        return test_info

    def hss_release(self, build, test_info):
        try:
            hss_release = '/'.join(test_info['packages']['ESM_UP_link'].split('/')[-1].split('-')[2:]).split('_')[0]
            if fversion.parse(build) > fversion.parse('HSS-1.28.2.20'):
                hss_release = hss_release.replace('/','_')

            return hss_release + '_%s' % build.split('-')[-1]
        except Exception as e:
            _ERR('Problem building hss_release:%s' % e)

    def baseline_data(self, baseline):
        try:
            build, test_info =  self.__build_handler_client.fetch_baseline_test_info(baseline)
            data = '\n Build      : %s' % build
            data += '\n HSS version: %s\n' % self.hss_release(build, test_info)
        except Exception as e:
            _ERR('%s' % e)
            data = 'Info for %s baseline not available' % self.baseline
        return data

    def fetch_baseline(self,signal_answer):
        _DEB('Function fetch_baseline called via rtc_cli')
        answer = ''
        for baseline in self.__build_handler_client.baseline_list:
            answer += '\n Baseline   : %s  %s' % (baseline, ('(Active)' if self.baseline == baseline else ''))
            answer += self.baseline_data(baseline)

        if not answer:
            answer = 'No baselines'
        self.__watcher.emit(signal_answer,answer)


    def check_baseline(self, baseline):
        _DEB('Function check_baseline for %s' % baseline)
        try:
            build, test_info =  self.__build_handler_client.fetch_baseline_test_info(baseline)
            return True
        except Exception as e:
            _INF('%s' % e)
            return False

    def activate_baseline(self,signal_answer, baseline):
        _DEB('Function activate_baseline for %s called via rtc_cli' % baseline)
        try:
            build, test_info =  self.__build_handler_client.fetch_baseline_test_info(baseline)
            self.__service_config['service_parameters']['base_release'] = baseline
            answer = 'EXECUTED'
            self.save_service_config()
        except Exception as e:
            _ERR('%s' % e)
            answer = 'ERROR: %s' % e

        self.__watcher.emit(signal_answer,answer)


    def add_baseline(self, signal_answer,build):
        _DEB('Function add_baseline for %s called via rtc_cli' % build)
        answer = 'EXECUTED'
        try:
            self.__build_handler_client.baseline_add(build)
        except Exception as e:
            _ERR('%s' % e)
            answer = 'ERROR: %s' % e

        self.__watcher.emit(signal_answer,answer)


    def del_baseline(self, signal_answer, baseline, clean=False, force=False):
        _DEB('Function del_baseline for %s called via rtc_cli' % baseline)
        answer = 'EXECUTED'
        if self.baseline == baseline:
            if force:
                answer = 'EXECUTED. WARNING: From now on there is not an active baseline'
                self.__service_config['service_parameters']['base_release'] = None
                self.save_service_config()
            else:
                answer = 'NOT EXECUTED: %s is the active baseline' % baseline
                self.__watcher.emit(signal_answer,answer)
                return

        try:
            self.__build_handler_client.baseline_del(baseline)
            if clean:
                release = 'HSS-%s' % baseline
                _INF('Clean all builds for %s release' % release)
                self.__build_handler_client.clean_build(release)
        except Exception as e:
                _ERR('%s' % e)
                answer = 'ERROR: %s' % e

        self.__watcher.emit(signal_answer,answer)


    def fetch_build_test_info(self,signal_answer,build_id):
        _DEB('Function fetch_build_test_info called via rtc_cli')
        try:
            answer = self.__build_handler_client.fetch_build(build_id)
        except Exception as e:
            answer = '%s build test_info not found' % build_id
            _WRN(answer)

        self.__watcher.emit(signal_answer,answer)

    def update_build_test_info(self,signal_answer, build_id, test_info, persist=False):
        _DEB('Function update_build_test_info called via rtc_cli')
        if not self.__service_paused:
            _WRN('Service shall be in paused state. No actions')
            answer= 'Service shall be in paused state. No actions'
            self.__watcher.emit(signal_answer,answer)
            return

        answer = self.__build_handler_client.update_build_test_info(build_id, test_info, persist)
        self.__watcher.emit(signal_answer,answer)

    def fetch_pending_build_list(self,signal_answer):
        _DEB('Function fetch_pending_build_list called via rtc_cli')
        try:
            answer = self.__build_handler_client.fetch_pending_build_list
            if not len(answer):
                answer = 'There is not pending builds'

        except Exception as e:
            _WRN('Problem in fetch_pending_build_list: %s' % e)
            answer='There is not pending builds'

        self.__watcher.emit(signal_answer,answer)

    def clean_build(self,signal_answer,wildcard):
        _DEB('Function clean_build called via rtc_cli')
        try:
            answer = self.__build_handler_client.clean_build(wildcard)
            if not len(answer):
                answer = 'There is not build to clean'

        except Exception as e:
            _INF('Problem in clean_build: %s' % e)
            answer='There is not build to clean'

        self.__watcher.emit(signal_answer,answer)


    def purge_build(self,signal_answer,wildcard):
        _DEB('Function purge_build called via rtc_cli')
        try:
            answer = self.__build_handler_client.purge_build(wildcard)
            if not len(answer):
                answer = 'There is not build to purge'

        except Exception as e:
            _INF('Problem in purge_build: %s' % e)
            answer='There is not build to purge'

        self.__watcher.emit(signal_answer,answer)

    def set_build_status(self,signal_answer,build,status):
        _DEB('Function set_build_status for %s build with %s status called via rtc_cli' % (build,status))
        answer = self.__build_handler_client.force_build_status(build,status)
        self.__watcher.emit(signal_answer,answer)


    def fetch_build_test_result(self,signal_answer,build_id):
        _DEB('Function fetch_build_test_result called via rtc_cli')
        try:
            answer = self.__build_handler_client.get_build_test_result(build_id)
            if not len(answer):
                answer = 'There is not test result for %s' % build_id

        except Exception as e:
            _INF('Problem in fetch_build_test_result: %s' % e)
            answer='There is not test result for %s' % build_id

        self.__watcher.emit(signal_answer,answer)


    def fetch_available_builds(self,signal_answer):
        _DEB('Function fetch_available_builds called via rtc_cli')
        try:
            answer = self.__build_handler_client.fetch_available_builds
            if answer == '':
                answer = 'There is not available builds for testing'

        except Exception as e:
            _INF('Problem in fetch_available_builds: %s' % e)
            answer='There is not available builds for testing'

        self.__watcher.emit(signal_answer,answer)


    def force_build(self,signal_answer,build,build_info=None,test_suite=None, high_priority=False):
        _DEB('Function force_build %s called via rtc_cli' % build)
        if not self.__service_paused:
            answer= 'Service shall be in paused state to force a build test. No actions'
            _WRN(answer)
            self.__watcher.emit(signal_answer,answer)
            return

        if not self.__service_config:
            answer = 'Service not configured yet'
            _WRN(answer)
            self.__watcher.emit(signal_answer,answer)
            return

        if self.ongoing_test:
            answer= 'There is an ongoing test. No actions'
            _WRN(answer)
            self.__watcher.emit(signal_answer,answer)
            return

        if build_info is None:
            try:
                build_info = self.__build_handler_client.fetch_build(build)
                if build_info is None:
                    answer = '%s build_info not available' % build
                    self.__watcher.emit(signal_answer,answer)
                    return

            except Exception as e:
                _WRN('Problem in force_build: %s' % e)
                answer = '%s build not available' % build
                self.__watcher.emit(signal_answer,answer)
                return
        else:
            try:
                with open(build_info) as json_data:
                    build_info = json.load(json_data)
            except Exception as e:
                answer = 'Error parsing json %s file: %s' % (cfg, e)
                _ERR(answer)
                self.__watcher.emit(signal_answer,answer)
                return

        if signal_answer is not None:
            answer= 'ORDERED'
            self.__watcher.emit(signal_answer,answer)

        self.__build_handler_client.priority_del(build,update_status=False)
        self.start_hss_rtc_execution(build,build_info=build_info,high_priority=high_priority,test_suite=test_suite)


    def pause(self,signal_answer):
        _DEB('Function pause called via rtc_cli')
        self.__service_paused = True
        self.__watcher.emit(signal_answer,'EXECUTED')


    def resume(self,signal_answer):
        _DEB('Function resume called via rtc_cli')
        if self.__service_config:
            answer= 'EXECUTED'
            try:
                with open(os.path.join(CONFIG_PATH,CFG_FILE)) as json_data:
                    self.__service_config = json.load(json_data)
                    self.__service_paused = False
                    self.__watcher.emit('rtc_check_priority_list')
            except Exception as e:
                answer = 'Error reading configuration file %s: %s' % (os.path.join(CONFIG_PATH,CFG_FILE), e)
                _ERR(answer)

            try:
                self.__build_handler_client.refresh_DBM_from_file()
            except Exception as e:
                answer = str(e)
                _ERR(answer)

        else:
            answer = 'Service not configured yet'

        self.__watcher.emit(signal_answer,answer)


