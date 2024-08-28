#!/usr/bin/env python
# -*- coding: utf-8 -*-

import e3utils.log as logging
_DEB = logging.internal_debug
_WRN = logging.internal_warning
_ERR = logging.internal_error
_INF = logging.internal_info


import hss_utils.dbus.services
from hss_utils.dbus.services import remote

RTC_BUILD_HANDLER_SERVICE_OBJ = 'com.ericsson.rtc.build_handler'
RTC_BUILD_HANDLER_SERVICE_PATH = '/com/ericsson/rtc/build_handler'
RTC_CONTROLLER_SERVICE_OBJ = 'com.ericsson.rtc.controller'
RTC_CONTROLLER_SERVICE_PATH = '/com/ericsson/rtc/controller'
RTC_GATEWAY_SERVICE_OBJ = 'com.ericsson.rtc.gateway'
RTC_GATEWAY_SERVICE_PATH = '/com/ericsson/rtc/gateway'


class Build_handler_Client(hss_utils.dbus.services.Client):
    def __init__(self):
        super(Build_handler_Client, self).__init__(RTC_BUILD_HANDLER_SERVICE_OBJ,
                                     RTC_BUILD_HANDLER_SERVICE_PATH)


    @remote
    def refresh_DBM_from_file(self):
        pass

    @remote
    def build_info_add(self, build, info):
        pass

    @remote
    def build_info_update(self, build, info):
        pass

    @remote
    def priority_add(self, build):
        pass

    @remote
    def priority_del(self, build, update_status):
        pass

    @remote
    def priority_increase (self, build):
        pass

    @remote
    def baseline_add (self, build):
        pass

    @remote
    def baseline_del (self, baseline):
        pass

    @remote
    def get_release (self, build):
        pass

    @remote
    def get_project (self, build):
        pass

    @remote
    def clean_build(self, wildcard, exclude):
        pass

    @remote
    def purge_build(self, wildcard):
        pass

    @property
    @remote
    def baseline_list(self):
        pass

    @property
    @remote
    def get_build(self):
        pass

    @remote
    def fetch_build(self, build):
        pass

    @remote
    def update_build_test_info(self, build, test_info, persist):
        pass

    @property
    @remote
    def is_there_build_to_test(self):
        pass

    @property
    @remote
    def fetch_pending_build_list(self):
        pass

    @property
    @remote
    def fetch_available_builds(self):
        pass

    @remote
    def fetch_baseline_test_info(self,baseline):
        pass

    @remote
    def add_build_test_result(self, build, test_result):
        pass

    @remote
    def get_build_test_result(self,build):
        pass

    @remote
    def update_build_status(self, build, status):
        pass

    @remote
    def force_build_status(self, build, status):
        pass


    @remote
    def get_build_status(self, build):
        pass