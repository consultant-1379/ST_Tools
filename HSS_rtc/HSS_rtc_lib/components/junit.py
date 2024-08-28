import xml.etree.ElementTree as ET
import os
import re
import sys

import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning


class JunitFile(object):
    def __init__(self, name):
        self.name = name
        self.tree = None
        self.testsuites = []

    def __repr__(self):
        rep = ""
        for suite in self.testsuites:
            rep = rep + suite.name + " " + str(suite.get_time())  + "\n"
            for case in suite.test_cases:
                rep = rep + "    " + case.name + "\n"
                rep = rep + "    " + str(case.time ) + "\n"

        return rep

    def display(self):
        for suite in self.testsuites:
            suite.display()

    def get_info(self):
        info=''
        for suite in self.testsuites:
            info += suite.get_info()
        return info

    def load(self):
        if not os.path.isfile(self.name):
            self.testsuites = []
            return

        self.tree = ET.parse(self.name)
        root = self.tree.getroot()
        if self.testsuites is None:
            self.testsuites = []

        for suite_node in root:
            suite = self.get_suite_class(suite_node)
            for case_node in suite_node:
                suite.add_testcase(self.get_testcase_obj(case_node))

            self.testsuites.append(suite)


    def dump(self):
        xml_element = self.to_xml_element()
        xml_file = open(self.name, 'w')
        tree = ET.ElementTree(xml_element)
        tree.write(xml_file, encoding="utf-8")


    def get_suite_class(self, suite_node):
        suite_name = suite_node.get("name")
        suite = TestSuite(suite_name)
        return suite

    def get_testcase_obj(self, testcase_node):
        case_name = testcase_node.get("name")
        case_log = testcase_node.get("log")
        case_time = testcase_node.get("time")
        case_classname = testcase_node.get("classname")
        case = TestCase(case_name, time=float(case_time), class_name=case_classname, log=case_log)
        if testcase_node.find("failure") is not None:
            case.set_failure(testcase_node.find("failure").text)

        elif testcase_node.find("skipped") is not None:
            case.set_skipped(testcase_node.find("skipped").text)

        if testcase_node.find("error") is not None:
            case.set_error(testcase_node.find("error").text)

        return case

    def to_xml_element(self):
        xml_element = ET.Element("testsuites")
        for suite in self.testsuites:
            xml_element.append(suite.to_xml_element())
        return xml_element

    def add_testcase(self, testcase, suitename):
        suite_exists = False
        for suite in self.testsuites:
            if suite.name == suitename:
                suite_exists = True
                suite.add_testcase(testcase)

        if not suite_exists:
            suite = TestSuite(suitename,[testcase])
            if self.testsuites is None:
                self.testsuites = []

            self.testsuites.append(suite)

class TestSuite(object):
    def __init__(self, name, test_cases=None):
        self.name = name
        self.test_cases = test_cases

    def add_testcase(self, test_case):
        if self.test_cases is None:
            self.test_cases = []

        self.test_cases.append(test_case)

    def set_test_cases(self, test_cases):
        self.test_cases = test_cases

    def get_num_failures(self):
        return len([c for c in self.test_cases if c.is_failure()])

    def get_num_errors(self):
        return len([c for c in self.test_cases if c.is_failure()])

    def get_num_skipped(self):
        return len([c for c in self.test_cases if c.is_skipped()])

    def get_num_tests(self):
        return len(self.test_cases)

    def get_time(self):
        return sum(c.time for c in self.test_cases if c.time)

    def to_xml_element(self):
        test_suite_attributes = dict()
        test_suite_attributes['name'] = self.name
        test_suite_attributes['failures'] = \
            str(len([c for c in self.test_cases if c.is_failure()]))
        test_suite_attributes['errors'] = \
            str(len([c for c in self.test_cases if c.is_error()]))
        test_suite_attributes['skipped'] = \
            str(len([c for c in self.test_cases if c.is_skipped()]))
        test_suite_attributes['time'] = \
            str(sum(c.time for c in self.test_cases if c.time))
        test_suite_attributes['tests'] = str(len(self.test_cases))

        xml_element = ET.Element("testsuite", test_suite_attributes)

        for case in self.test_cases:
            xml_element.append(case.to_xml_element())
        return xml_element

    def display(self):
        _INF('')
        _INF(' Test Suite :  %s' % self.name)
        for test_case in self.test_cases:
            test_case.display()

    def get_info(self):
        info = '\n'
        info +=' Test Suite :  %s\n' % self.name
        for test_case in self.test_cases:
            info += test_case.get_info()
        return info

class TestCase(object):
    def __init__(self, name, time=None, class_name=None, log=None):
        self.name       = name
        self.time       = time
        self.class_name = class_name
        self.log        = log

        self.skipped_message = None
        self.error_message   = None
        self.failure_message = None

    def _clean_illegal_xml_chars(self, string_to_clean):
        illegal_unichrs = [
            (0x00, 0x08), (0x0B, 0x1F), (0x7F, 0x84), (0x86, 0x9F),
            (0xD800, 0xDFFF), (0xFDD0, 0xFDDF), (0xFFFE, 0xFFFF),
            (0x1FFFE, 0x1FFFF), (0x2FFFE, 0x2FFFF), (0x3FFFE, 0x3FFFF),
            (0x4FFFE, 0x4FFFF), (0x5FFFE, 0x5FFFF), (0x6FFFE, 0x6FFFF),
            (0x7FFFE, 0x7FFFF), (0x8FFFE, 0x8FFFF), (0x9FFFE, 0x9FFFF),
            (0xAFFFE, 0xAFFFF), (0xBFFFE, 0xBFFFF), (0xCFFFE, 0xCFFFF),
            (0xDFFFE, 0xDFFFF), (0xEFFFE, 0xEFFFF), (0xFFFFE, 0xFFFFF),
            (0x10FFFE, 0x10FFFF)]

        illegal_ranges = ["%s-%s" % (unichr(low), unichr(high))
                          for (low, high) in illegal_unichrs
                          if low < sys.maxunicode]

        illegal_xml_re = re.compile('[%s]' % ''.join(illegal_ranges))
        return illegal_xml_re.sub('', string_to_clean)

    def set_failure(self, message):
        self.failure_message = self._clean_illegal_xml_chars(message)

    def set_skipped(self, message):
        self.skipped_message = self._clean_illegal_xml_chars(message)

    def set_error(self, message):
        self.error_message = self._clean_illegal_xml_chars(message)

    def is_skipped(self):
        return self.skipped_message != None

    def is_failure(self):
        return self.failure_message != None

    def is_error(self):
        return self.error_message != None

    def display(self):
        if self.is_skipped():
            _WRN('')
            _WRN(' Test Case name :  %s' % self.name)
            _WRN(' Result         :  SKIPPED')
            _WRN('                   %s' % self.skipped_message)
            _WRN('')

        elif self.is_failure():
            _ERR('')
            _ERR(' Test Case name :  %s' % self.name)
            _ERR(' Execution time :  %f seconds' % self.time)
            _ERR(' Log            :  %s' % self.log)
            _ERR(' Result         :  FAILED')
            if self.is_failure():
                for error in self.failure_message.split(';'):
                    if error != '':
                        _ERR('                   %s' % error)
            _ERR('')

        else:
            _INF('')
            _INF(' Test Case name :  %s' % self.name)
            _INF(' Execution time :  %f seconds' % self.time)
            _INF(' Log            :  %s' % self.log)
            _INF(' Result         :  SUCCESS' )
            _INF('')

    def get_info(self):
        info = '\n'
        if self.is_skipped():
            info += ' Test Case name :  %s\n' % self.name
            info += ' Result         :  SKIPPED\n'
            info += '                   %s\n' % self.skipped_message
            info += '\n'

        elif self.is_failure():
            info += ' Test Case name :  %s\n' % self.name
            info += ' Execution time :  %f seconds\n' % self.time
            info += ' Log            :  %s\n' % self.log
            info += ' Result         :  FAILED\n'
            if self.is_failure():
                for error in self.failure_message.split(';'):
                    if error != '':
                        info += '                   %s\n' % error
            info += '\n'

        else:
            info += ' Test Case name :  %s\n' % self.name
            info += ' Execution time :  %f seconds\n' % self.time
            info += ' Log            :  %s\n' % self.log
            info += ' Result         :  SUCCESS\n' 
            info += '\n'

        return info

    def to_xml_element(self):
        test_case_attributes = dict()
        test_case_attributes['name'] = self.name
        test_case_attributes['time'] = "%f" % self.time

        if self.class_name is not None:
            test_case_attributes['classname'] = self.class_name
        if self.log is not None:
            test_case_attributes['log'] = self.log

        test_case_element = ET.Element("testcase", test_case_attributes)
        if self.is_failure():
            attrs = {'type': 'failure'}
            #attrs['message'] = self.failure_message
            element = ET.Element("failure", attrs)
            element.text = self.failure_message
            test_case_element.append(element)

        if self.is_skipped():
            attrs = {'type': 'skipped'}
            #attrs['message'] = self.skipped_message
            element = ET.Element("skipped", attrs)
            element.text = self.skipped_message
            test_case_element.append(element)

        if self.is_error():
            attrs = {'type': 'error'}
            #attrs['message'] = self.error_message
            element = ET.Element("error", attrs)
            element.text = self.error_message
            test_case_element.append(element)

        return test_case_element

