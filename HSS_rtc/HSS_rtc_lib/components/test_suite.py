#!/usr/bin/env python
# -*- coding: utf-8 -*-

import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning


import json
import pprint
import time
import os.path
from hss_utils.st_command import real_path

class TestSuite(object):
    def __init__(self, name=None, data={}, report_path=''):
        #self.__name = name

        if data:
            self.__data = {'name':data['name'],'status':data['status'],
                           'testCases':[TestCase(data=x) for x in data['testCases']]}

        else:
            self.__data = {'name':name,'testCases':[],
                        'status':'SUCCESS'}
            self.__current_text_case = -1

        self.report_path = report_path


    @property
    def _as_dict(self):
        return {'name':self.__data['name'],'status':self.status,
                'testCases':[x._as_dict for x in self.__data['testCases']]}

    @property
    def name(self):
        return self.__data['name']

    def add_test_case(self,json_file,macro_files, mandatory=True):
        self.__data['testCases'].append(TestCase(json_file,macro_files,mandatory=mandatory))

    def next_text_case(self):
        if self.__current_text_case < len(self.__data['testCases']) - 1:
            self.__current_text_case += 1
            return self.__data['testCases'][self.__current_text_case]

        return None

    def repeat_test_case(self):
        self.__data['testCases'].insert(self.__current_text_case+1,
                                        self.__data['testCases'][self.__current_text_case].clone())

    def get_last_epm(self, id):
        for testcase in reversed(self.__data['testCases'][:self.__current_text_case]):
            if id == testcase.epm.get('id',''):
                return (testcase.name , testcase.epm)

        return None, None

    @property
    def next_test_case_is_optional(self):
        if self.__current_text_case < len(self.__data['testCases']) - 1:
            return self.__data['testCases'][self.__current_text_case + 1].is_optional

        return False

    @property
    def current_text_case(self):
        return self.__data['testCases'][self.__current_text_case]

    @property
    def nof_tcs(self):
        return len(self.__data['testCases'])

    @property
    def nof_mandatory_tcs(self):
        number = 0
        for testcase in self.__data['testCases']:
            if testcase.is_mandatory:
                number += 1
        return number

    @property
    def nof_optional_tcs(self):
        number = 0
        for testcase in self.__data['testCases']:
            if testcase.is_optional:
                number += 1
        return number

    @property
    def nof_mandatory_tcs_exec(self):
        number = 0
        for testcase in self.__data['testCases']:
            if testcase.is_mandatory and testcase.status not in ['not executed','running']:
                number += 1
        return number

    @property
    def nof_optional_tcs_exec(self):
        number = 0
        for testcase in self.__data['testCases']:
            if testcase.is_optional and testcase.status not in ['not executed','running']:
                number += 1
        return number


    def get_summary(self, test_case):
        for testcase in self.__data['testCases']:
            if testcase.name == test_case and testcase.summary is not None:
                return '%s' % testcase.summary
        return 'summary for %s not found' % test_case

    @property
    def status(self):
        for testcase in self.__data['testCases']:
            if testcase.report_not_valid:
                return 'FAILED'
        return 'SUCCESS'

    def set_test_suite_execution_status(self, status, force = False):
        if force:
            for testcase in self.__data['testCases']:
                if testcase.status in ['finished','not finished']:
                    testcase.report_not_valid = (status == 'FAILED')
        else:
            self.current_text_case.report_not_valid = (status == 'FAILED')


    def save_report(self):
        report_file = os.path.join(self.report_path,'TestSuite_%s.report' % self.name)
        with open(report_file , "w") as text_file:
            text_file.write(str(self))


    def __str__(self):
        info = '\n'
        info +=' Test Suite     :  %s\n' % self.name
        for test_case in self.__data['testCases']:
            info += str(test_case)
        return info


class TestCase(object):
    def __init__(self, json_file=None, macro_files=None ,mandatory=True, data={}):
        self.__data = {'status':'not executed','mandatory':mandatory,
                       'failure_messages':[],'skipped_message':'',
                       'start_time':None,'stop_time':None,
                       'start_date':None,'stop_date':None,
                       'root_path':'','name':'','reexecution':False}

        self.__repeat = False
        self.__report_not_valid = False
        self.__summary = None
        self.__nof_payloads = -1
        self.__epm = {}

        if data:
            self.__data = data

        else:
            self.__json_file = real_path(json_file)
            self.__macro_files = []
            if not os.path.isfile(self.__json_file):
                error_info = 'Configuration file %s not found' % self.__json_file
                raise TypeError(error_info)

            try:
                with open(self.__json_file) as json_data:
                    self.__config_data = json.load(json_data)
                    self.__data['name'] = self.__config_data['name']

            except Exception, e:
                error_info = 'Error parsing json %s file: %s' % (self.__json_file, str(e))
                raise TypeError(error_info)

            if macro_files:
                for macro_file in macro_files.split(','):
                    macro_file = real_path(macro_file)
                    if not os.path.isfile(macro_file):
                        error_info = 'Macro file %s not found' % macro_file
                        raise TypeError(error_info)

                    self.__macro_files.append(macro_file)

    def clone(self):
        _INF('Cloning Test case %s' % self.__data['name'])
        if self.macro_files:
            macro_files = ','.join(self.macro_files)
        else:
            macro_files = None
        cloned_test_case = TestCase(json_file=self.__json_file, macro_files=macro_files ,mandatory=self.is_mandatory)
        cloned_test_case.nof_retries = self.nof_retries - 1
        cloned_test_case.reexecution = True
        self.__report_not_valid = False
        return cloned_test_case


    @property
    def nof_payloads(self):
        return self.__nof_payloads

    @nof_payloads.setter
    def nof_payloads(self, value):
        self.__nof_payloads = value

    @property
    def epm(self):
        return self.__epm 

    def update_epm(self, value):
        assert(isinstance(value, dict))
        self.__epm.update(value)

    @property
    def epm_enabled(self):
        try:
            return self.__config_data['phases']['EXECUTION']['configuration']['diaproxy_reports']['latency']['enable']
        except KeyError:
            return False

    @property
    def epm_samples(self):
        try:
            return int(self.__config_data['phases']['EXECUTION']['configuration']['diaproxy_reports']['latency']['samples'])
        except KeyError:
            return -1

    @property
    def report_not_valid(self):
        return self.__report_not_valid

    @report_not_valid.setter
    def report_not_valid(self, value):
        self.__report_not_valid = value

    @property
    def nof_retries(self):
        return self.__config_data.get('nof_retries',0)

    @nof_retries.setter
    def nof_retries(self, value):
        self.__config_data['nof_retries'] = value

    @property
    def repeat(self):
        return self.__repeat

    @repeat.setter
    def repeat(self, value):
        self.__repeat |= value

    @property
    def shall_repeat(self):
        return self.nof_retries and self.repeat

    @property
    def _as_dict(self):
        return self.__data

    @property
    def name(self):
        return self.__data['name']

    @name.setter
    def name(self, name):
        self.__data['name'] = name

    @property
    def reexecution(self):
        return self.__data['reexecution']

    @reexecution.setter
    def reexecution(self, value):
        self.__data['reexecution'] = value

    @property
    def summary(self):
        return self.__summary

    @property
    def json_file(self):
        return self.__json_file

    @property
    def config_data(self):
        return self.__config_data

    @property
    def macro_files(self):
        return self.__macro_files


    @property
    def is_mandatory(self):
        return self.__data['mandatory']

    @property
    def is_optional(self):
        return not self.__data['mandatory']

    @property
    def status(self):
        return self.__data['status']

    @property
    def failure_messages(self):
        return self.__data['failure_messages']

    @failure_messages.setter
    def failure_messages(self, message):
        self.__data['failure_messages'].append(message)

    @property
    def skipped_message(self):
        return self.__data['skipped_message']

    @skipped_message.setter
    def skipped_message(self, message):
        self.__data['skipped_message'] = message

    @property
    def root_path(self):
        return self.__data['root_path']

    @root_path.setter
    def root_path(self, root_path):
        self.__data['root_path'] = root_path

    @property
    def start_time(self):
        return self.__data['start_time']

    @property
    def stop_time(self):
        return self.__data['stop_time']

    @property
    def start_date(self):
        return self.__data['start_date']

    @property
    def stop_date(self):
        return self.__data['stop_date']

    @property
    def time(self):
        return self.stop_time - self.start_time

    def update_status(self,status,message='',root_path=None,repeat=False,test_case_path=None):
        if status == 'running' and self.__data['status'] == 'not executed':

            self.__data['start_date'] = time.strftime("%Y%m%d-%H%M%S")
            self.__data['name'] = '%s_%s' % (self.__data['name'], self.__data['start_date'])
            if test_case_path:
                self.__data['root_path'] = test_case_path
            else:
                self.__data['root_path'] = os.path.abspath(os.path.join(root_path,self.__data['name']))
            self.__data['start_time'] = time.time()
            self.__summary = Summary(self.root_path)
            self.__data['status'] = status

        elif status == 'skipped' and self.__data['status'] == 'not executed':
            self.skipped_message = message
            self.__data['status'] = status

        elif status in ['finished','not finished' ] and self.__data['status'] == 'running':
            self.__data['stop_time'] = time.time()
            self.__data['stop_date'] = time.strftime("%Y%m%d-%H%M%S")
            if message != '':
                self.failure_messages = message
                self.repeat = repeat

            self.__data['status'] = status
            self.summary.save()

        else:
            _WRN('Received %s state is not valid in %s current state' % (status,self.__data['status']))


    def __str__(self):
        info = '\n'
        if self.status == 'not executed':
            info += ' Test Case name :  %s%s\n' % (self.name, (' (Re-execution)' if self.reexecution else ''))
            info += ' Type           :  %s\n' % ('MANDATORY' if self.is_mandatory else 'OPTIONAL')
            info += ' State          :  NOT EXECUTED\n'
            info += '\n'

        elif self.status == 'running':
            info += ' Test Case name :  %s%s\n' % (self.name, (' (Re-execution)' if self.reexecution else ''))
            info += ' Type           :  %s\n' % ('MANDATORY' if self.is_mandatory else 'OPTIONAL')
            info += ' State          :  RUNNING\n'
            info += ' Start          :  %s\n' % self.start_date
            info += '\n'

        elif self.status == 'skipped':
            info += ' Test Case name :  %s%s\n' % (self.name, (' (Re-execution)' if self.reexecution else ''))
            info += ' Type           :  %s\n' % ('MANDATORY' if self.is_mandatory else 'OPTIONAL')
            info += ' Result         :  SKIPPED\n'
            info += '                   %s\n' % self.skipped_message
            info += '\n'

        elif self.status == 'not finished':
            info += ' Test Case name :  %s%s\n' % (self.name, (' (Re-execution)' if self.reexecution else ''))
            info += ' Type           :  %s\n' % ('MANDATORY' if self.is_mandatory else 'OPTIONAL')
            info += ' Start          :  %s\n' % self.start_date
            info += ' Stop           :  %s\n' % self.stop_date
            info += ' Execution time :  %f seconds\n' % self.time
            info += ' Log            :  %s\n' % self.root_path
            info += ' Result         :  NOT FINISHED\n'
            for error in self.failure_messages:
                if error != '':
                    info += '                   %s\n' % error
            info += '\n'

        elif self.status == 'finished':
            info += ' Test Case name :  %s%s\n' % (self.name, (' (Re-execution)' if self.reexecution else ''))
            info += ' Type           :  %s\n' % ('MANDATORY' if self.is_mandatory else 'OPTIONAL')
            info += ' Start          :  %s\n' % self.start_date
            info += ' Stop           :  %s\n' % self.stop_date
            info += ' Execution time :  %f seconds\n' % self.time
            info += ' Log            :  %s\n' % self.root_path
            if self.failure_messages:
                info += ' Result         :  FAILED\n'
                for error in self.failure_messages:
                    if error != '':
                        info += '                   %s\n' % error
                info += '\n'

            else:
                info += ' Result         :  SUCCESS\n' 

            info += '\n'

        return info


class Summary(object):
    def __init__(self, root_path):

        self.__filename = os.path.join(root_path, 'summary.txt')
        self.__additional_info = []
        self.__faulty_steps = []
        self.__action_results = []
        self.__action_info = {}

    def add_faulty_step(self, message):
        self.__faulty_steps.append(message)

    def add_action_result(self, message):
        self.__action_results.append(message)

    def add_action_info(self, action_id, message):
        try:
            self.__action_info[action_id] += message + '\n'
        except KeyError:
            self.__action_info.update({action_id:message + '\n'})

    def add_to_report(self, level, message, add_timestamp=False):
        timestamp = ''
        if add_timestamp:
            timestamp = '%s :' % datetime.now()

        self.__additional_info.append('%s%s' % (timestamp, message))

        if level == 'info':
            _INF(message)
        elif level == 'error':
            _ERR(message)
        elif level == 'warning':
            _WRN(message)

    def save(self):
        try:
            with open(self.__filename , "w") as text_file:
                text_file.write('%s' % self)
        except IOError as e:
            _WRN('Problem creating summary file: %s' % e)

    def __str__(self):
        info = []
        if self.__faulty_steps:
            info += ['FAULTY STEPs CMDs:']
            info += ['------------------']
            for message in self.__faulty_steps:
                info += ['%s' %message]
            info += ['']

        if self.__action_results:
            info += ['ACTIONS results:']
            info += ['----------------']
            for message in self.__action_results:
                info += ['%s' %message]
            info += ['']

        if self.__action_results:
            info += ['ACTIONS info:']
            info += ['-------------']
            for key, value in self.__action_info.iteritems():
                info += ['%-*s:\n' % (15,key)]
                for line in value.splitlines():
                    info += ['%-*s %s' % (15, ' ',line)]
                info += ['']

            info += ['']

        if self.__additional_info:
            info += ['CHECKs:']
            info += ['-------']
            info += self.__additional_info

        if info:
            return '\n' + '\n'.join(info) + '\n'
        else:
            return ' There is not information to be included in the summary\n'

