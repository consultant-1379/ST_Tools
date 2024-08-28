#!/usr/bin/env python
# -*- coding: utf-8 -*-


import json
import os
from distutils.version import LooseVersion
import pprint

import e3utils.log
_INF = e3utils.log.info
_DEB = e3utils.log.debug
_ERR = e3utils.log.error
_WRN = e3utils.log.warning

import hss_utils.dbus.services
from hss_utils.dbus.clients import RTC_BUILD_HANDLER_SERVICE_OBJ
from hss_utils.dbus.clients import RTC_BUILD_HANDLER_SERVICE_PATH

class FaultyAction(Exception):
    def __init__(self, cause='unknown cause'):
        self.__err = cause

    def __str__(self):
        return 'FAILED. %s' % self.__err

DB_PATH='/var/lib/rtc_build_handler'
DB_FILE= 'db.json'

class Handler(hss_utils.dbus.services.Service):
    def __init__(self):
        super(Handler, self).__init__(RTC_BUILD_HANDLER_SERVICE_OBJ,
                                      RTC_BUILD_HANDLER_SERVICE_PATH)

        self.__db = {'priority':{},'build_info':{},'baselines':{}}
        try:
            with open(os.path.join(DB_PATH,DB_FILE)) as json_data:
                self.__db = json.load(json_data)
        except IOError as e:
            _INF('Missing DB. %s' % e)
            self.update_db()
        except Exception as e:
            _ERR('Error parsing json %s file: %s' % (os.path.join(DB_PATH,DB_FILE), e))
            raise e


    def refresh_DBM_from_file(self):
        _DEB('Function refresh_DBM_from_file')
        try:
            with open(os.path.join(DB_PATH,DB_FILE)) as json_data:
                self.__db = json.load(json_data)
        except IOError as e:
            _ERR('Missing DB. %s' % e)
            raise e
        except Exception as e:
            _ERR('Error parsing json %s file: %s' % (os.path.join(DB_PATH,DB_FILE), e))
            raise e

    def get_project(self, build):
        return '.'.join(build.split('.')[:3])

    def get_release(self, build):
        return '.'.join(build.split('.')[:2])

    def clean_priority(self):
        _DEB('Function clean_priority')
        for key, value in self.__db['priority'].items():
            if len(value['pending']) == 0 and value['high_priority'] is None:
                del self.__db['priority'][key]


    def build_info_add(self, build, info):
        _DEB('Function build_info_add for %s' % build)
        if build in self.__db['build_info'].keys():
            error = '%s already exists in DB.' % build
            _WRN('%s No actions' % error)
            raise FaultyAction(error)

        self.__db['build_info'].update({build:{'test_info':info,'test_result':[], 'status':'NOT_TESTED'}})

        self.update_db()
        return True


    def build_info_update(self, build, info):
        _DEB('Function build_info_update for %s' % build)
        if build not in self.__db['build_info'].keys():
            error = '%s does not exists in DB. No actions' % build
            _ERR(error)
            raise FaultyAction(error)

        if not self.__db['build_info'][build]['test_info']:
            error = 'Test info for %s build does not exists in DB. No actions' % build
            _ERR(error)
            raise FaultyAction(error)

        try:
            if info['packages']:
                self.__db['build_info'][build]['test_info'].update({'packages':info['packages']})
        except KeyError as e:
            _DEB('%s Build info not updated' % e)

        try:
            if info['GIT_repos']:
                self.__db['build_info'][build]['test_info'].update({'GIT_repos':info['GIT_repos']})
        except KeyError as e:
            _DEB('%s Build info not updated' % e)


        self.update_db()
        return True


    def priority_add(self, build):
        _DEB('Function priority_add for %s' % build)
        if build not in self.__db['build_info'].keys():
            error = '%s does not exists in DB. No actions' % build
            _ERR(error)
            raise FaultyAction(error)

        project=self.get_project(build)
        try:
            if build not in self.__db['priority'][project]['pending']:
                self.__db['priority'][project]['pending'].append(build)
        except KeyError:
            self.__db['priority'].update({project:{'pending':[build],'high_priority':None}})

        self.clean_priority()
        self.update_db()
        return True


    def priority_del(self, build, update_status):
        _DEB('Function priority_del for %s' % build)
        project=self.get_project(build)
        try:
            if build in self.__db['priority'][project]['pending']:
                self.__db['priority'][project]['pending'].remove(build)
            elif self.__db['priority'][project]['high_priority'] == build:
                self.__db['priority'][project]['high_priority'] = None
        except (ValueError, KeyError) as e:
            _INF('%s build not found. %s' % (build, e))
            return

        if update_status:
            try:
                if self.__db['build_info'][build]['status'] == 'NOT_TESTED':
                    self.__db['build_info'][build]['status'] = 'SKIPPED'

            except (ValueError, KeyError) as e:
                _INF('Changing status. %s build not found. %s' % (build, e))
                return

        self.clean_priority()
        self.update_db()


    def priority_increase (self, build):
        _DEB('Function priority_increase for %s' % build)
        project=self.get_project(build)
        was_pending = False
        try:
            if build in self.__db['priority'][project]['pending']:
                index = self.__db['priority'][project]['pending'].index(build)
                self.__db['priority'][project]['pending'] = self.__db['priority'][project]['pending'][index+1:]
                self.__db['priority'][project]['high_priority'] = build
                was_pending = True
            else:
                info = '%s build not pending.' % build
                _INF(info)
        except (ValueError, KeyError) as e:
            info = '%s build not found. %s' % (build, e)
            _INF(info)
            raise FaultyAction(info)

        self.clean_priority()
        self.update_db()
        return was_pending


    def fetch_baseline_test_info(self, baseline):
        _DEB('Function fetch_baseline_test_info for %s' % baseline)
        try:
            build = self.__db['baselines'][baseline]
        except KeyError:
            error = 'Not build found for %s baseline' % baseline
            _ERR(error)
            raise FaultyAction(error)
        try:
            return build, self.__db['build_info'][build]['test_info']
        except KeyError:
            error = 'Not test info for %s' % build
            _ERR(error)
            raise FaultyAction(error)


    def baseline_add (self, build):
        _DEB('Function baseline_add for %s' % build)
        if build not in self.__db['build_info'].keys():
            error = '%s does not exists in DB. No actions' % build
            _ERR(error)
            raise FaultyAction(error)

        release = self.get_release(build)
        baseline = release.split('-')[-1]
        try:
            self.__db['baselines'].update({baseline:build})
        except KeyError:
            self.__db.update({'baselines':{baseline:build}})

        self.update_db()
        return '%s build is set as baseline for %s' % (build,baseline)


    def baseline_del (self, baseline):
        _DEB('Function baseline_del for %s' % baseline)
        try:
            del self.__db['baselines'][baseline]
        except KeyError:
            _WRN('%s baseline does not exist in DB. No actions' % baseline)
        self.update_db()

    @property
    def baseline_list(self):
        _DEB('Function baseline_list')
        return self.__db['baselines'].keys()


    def add_build_test_result(self, build, test_result):
        _DEB('Function add_build_test_result for %s' % build)
        try:
            if self.__db['build_info'][build]['status'] == 'TEST_ONGOING':
                self.__db['build_info'][build]['status'] = 'TESTED'
            self.__db['build_info'][build]['test_result'].append(test_result)
            self.update_db()
        except KeyError as e:
            _WRN('Build to update result %s not found. %s' % (build, e))
            return


    def get_build_test_result(self, build):
        _DEB('Function get_build_test_result for %s' % build)
        try:
            return self.__db['build_info'][build]['test_result']
        except KeyError as e:
            _INF('Build to get result %s not found. %s' % (build, e))
            return []


    def find_next_build(self,extract=True):
        _DEB('Function find_next_build')
        project_list = sorted(self.__db['priority'].keys(), key=LooseVersion)
        for project in project_list:
            rc = self.__db['priority'][project]['high_priority']
            if rc is None:
                continue
            else:
                if extract:
                    self.__db['priority'][project]['high_priority'] = None
                return (rc,True)

        project_list.reverse()
        for project in project_list:
            pending = self.__db['priority'][project]['pending']
            if pending:
                if extract:
                    build = self.__db['priority'][project]['pending'].pop()
                    return (build,False)
                else:
                    return (self.__db['priority'][project]['pending'][-1],False)
            else:
                continue

        return (None,False)


    def update_build_status(self, build, status):
        _DEB('Function update_build_status of %s to %s status' % (build, status))
        if status not in ['TEST_ONGOING','CANCELLED','SKIPPED','TESTED','NOT_TESTED','TEST_FAULTY']:
            _WRN('%s build status not allowed' % status)
            return
        try:
            self.__db['build_info'][build]['status'] = status
            self.update_db()
        except KeyError:
            _WRN('Build to update %s not found' % build)

    def force_build_status(self, build, status):
        _DEB('Function force_build_status of %s to %s status' % (build, status))
        allowed_values = ['CANCELLED','SKIPPED','TESTED','TEST_FAULTY']
        if status not in allowed_values:
            info = '%s build status not valid. Allowed values are: %s' % (status,' '.join(allowed_values))
            _WRN(info)
            return info
        try:
            self.__db['build_info'][build]['status'] = status
            self.update_db()
            info = '%s build status updated to %s' % (build, status)
            _INF(info)
            return info
        except KeyError:
            info = 'Build to update %s not found' % build
            _WRN(info)
            return info


    def get_build_status(self, build):
        _DEB('Function get_build_status of %s' % build)
        try:
            return self.__db['build_info'][build]['status']
        except KeyError:
            return 'NOT FOUND'


    @property
    def is_there_build_to_test(self):
        _DEB('Function is_there_build_to_test')
        build, rc = self.find_next_build(extract=False)
        return build is not None


    @property
    def get_build(self):
        _DEB('Function get_build')
        build, rc = self.find_next_build()
        if build is None:
            return (None,None,False)

        else:
            self.update_db()
            return (build, self.__db['build_info'][build]['test_info'],rc)


    def clean_build(self, wildcard, exclude=''):
        _DEB('Function clean_build wildcard:%s  exclude:%s' % (wildcard,exclude))
        counter = 0
        for key in self.__db['build_info'].keys():
            if key.startswith(wildcard) and key != exclude:

                if self.__db['build_info'][key]['status'] == 'TEST_ONGOING':
                    _WRN('There is an ongoing test for %s build. Do not clean' % key)
                    continue

                _INF('Cleaning %s' % key)
                self.priority_del(key,update_status=False)
                if key in self.__db['baselines'].values():
                    _INF('The %s build is a baseline, Test info will be kept only test_result will be removed' % key)
                    self.__db['build_info'][key]['test_result'] = []
                else:
                    del self.__db['build_info'][key]
                counter += 1

        self.clean_priority()
        self.update_db()
        return ' %s builds cleaned from db' % counter


    def purge_build(self, wildcard):
        _DEB('Function purge_build')
        counter = 0
        for key in self.__db['build_info'].keys():
            if key.startswith(wildcard):
                if len(self.__db['build_info'][key]['test_result']) > 1:
                    self.__db['build_info'][key]['test_result'] = [self.__db['build_info'][key]['test_result'][-1]]
                    counter += 1

        self.clean_priority()
        self.update_db()
        return ' %s builds purged from db' % counter


    def fetch_build(self, build):
        _DEB('Function fetch_build')
        return self.__db['build_info'][build]['test_info']


    def update_build_test_info(self, build, test_info, persist):
        _DEB('Function update_build_info')
        try:
            self.__db['build_info'][build]['test_info'] = test_info
        except KeyError:
            answer = '%s build not found' % build
        answer =  'EXECUTED'

        if persist:
            self.update_db()
        return answer


    @property
    def fetch_pending_build_list(self):
        _DEB('Function fetch_pending_build_list')
        build_list = []
        project_list = sorted(self.__db['priority'].keys(), key=LooseVersion)
        for project in project_list:
            rc = self.__db['priority'][project]['high_priority']
            if rc is None:
                continue
            else:
                build_list.append((rc,True))

        project_list.reverse()
        for project in project_list: 
            pending = list(reversed(self.__db['priority'][project]['pending']))
            if pending:
                build_list += [(x,False) for x in pending]
            else:
                continue

        return build_list

    @property
    def fetch_available_builds(self):
        _DEB('Function fetch_available_builds')
        info = ''
        for build in sorted(self.__db['build_info'].keys(), key=LooseVersion):
            info += '  %s\t%s\n' % (build, self.__db['build_info'][build]['status'])

        return info


    def update_db(self):
        _DEB('Function update_db')
        if not os.path.exists(DB_PATH):
            os.makedirs(DB_PATH)

        with open(os.path.join(DB_PATH, DB_FILE), 'w') as fp:
            json.dump(self.__db, fp, indent=4)
