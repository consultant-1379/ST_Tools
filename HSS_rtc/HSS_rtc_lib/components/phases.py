#!/usr/bin/env python
#

import sys
import os
import os.path
import time
import filecmp
import signal


import hss_utils.st_command as st_command
import hss_utils.connection as connection
import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning

from HSS_rtc_lib.shared import *
from . import ExecutionConfigurationError
from . import ExecutionStartError
from . import ExecutionRunError
from . import steps

class Phase(object):
    def __init__(self, config , id, user_config, rtc_data):

        self.__rtc_data = rtc_data
        self.__user_config = user_config
        self.__config = config['phases'][id]
        self.__id = id
        self.__working_path = os.path.join(rtc_data.root_path, id)
        self.__tcname = rtc_data.id


    @property
    def id(self):
        return self.__id

    @property
    def user_config(self):
        return self.__user_config

    @property
    def rtc_data(self):
        return self.__rtc_data

    @property
    def summary(self):
        return self.rtc_data.TestCase.summary

    @property
    def config(self):
        return self.__config

    @property
    def working_path(self):
        return self.__working_path

    @property
    def tcname(self):
        return self.__tcname 

    def run(self):

        if self.__config['enable']:
            _INF('')
            _INF('Start %s phase' % self.id )
            if not os.path.exists(self.working_path):
                os.makedirs(self.working_path)

            try:
                for step in self.__config['steps']:
                    if self.rtc_data.exit_test_case:
                        _WRN('%s Exit from Test case order has been received' % self.id)
                        break

                    try:
                        enable = step["enable"]
                        if isinstance(enable,str) or isinstance(enable,unicode):
                            enable = self.rtc_data.get_macro_value(enable)
                            enable = (enable == 'true')
                    except KeyError:
                        _WRN('Missing "enable" field in step definition')
                        continue

                    if enable:
                        step = steps.Step(step, self.user_config, self.id, self.working_path, self.rtc_data)
                        step.run()

            except (ExecutionConfigurationError,ExecutionRunError), e:
                error_info = '%s %s' % (self.id, str(e))
                _ERR(error_info)
                raise e

class CLEAN(Phase):

    def __init__(self, config , user_config, rtc_data):

        Phase.__init__(self, config , 'CLEAN', user_config, rtc_data)

class PRE(Phase):

    def __init__(self, config , user_config, rtc_data):

        Phase.__init__(self, config , 'PRE', user_config, rtc_data)

class POST(Phase):

    def __init__(self, config , user_config, rtc_data):

        Phase.__init__(self, config , 'POST', user_config, rtc_data)

class COLLECT(Phase):

    def __init__(self, config , user_config, rtc_data):

        Phase.__init__(self, config , 'COLLECT', user_config, rtc_data)


