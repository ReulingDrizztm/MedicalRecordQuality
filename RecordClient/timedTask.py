#!/usr/bin/env python3
# -*- coding:utf-8 -*

"""
@version: 
@author:
@contact:
@software: PyCharm
@file: timedTask.py
@time: 18-11-27 下午1:58
@description: 
"""
import os
import sys
cur_path = os.path.abspath(os.path.dirname(__file__))
root_path = os.path.split(cur_path)[0]
sys.path.append(root_path)  # 项目路径添加到系统路径
import json
import traceback
from suds.client import Client
from Utils.LogUtils import LogUtils
from Utils.loadingConfigure import Properties
from Utils.MongoUtils import PullDataFromMDBUtils
from datetime import datetime, timedelta


class HospitalServerInfo(object):
    # 是否初始化
    is_init = False

    def __init__(self):
        if not HospitalServerInfo.is_init:
            self.inhospital_pat_data = dict()
            self.inhospital_pat_num = dict()
            self.discharge_pat_data = dict()
            self.discharge_pat_num = dict()
            self.ward_code_list = list()

            self.mongo_pull_utils = PullDataFromMDBUtils()
            self.logger = LogUtils().getLogger('backend')

            self.parameters = Properties()
            self.conf_dict = self.parameters.conf_dict.copy()
            self.dept_dict = self.parameters.dept_dict.copy()
            self.ward_dept = self.parameters.ward_dept.copy()
            self.hospital_code = self.parameters.properties.get('hospital_code')
            self.database_ip = self.parameters.properties.get('mongo_host')
            if cur_path.endswith('Test'):
                self.mr_client_url = self.conf_dict['mr_url'].get(self.database_ip, dict()).get('test', '')
                self.collection_name_doctor = self.mongo_pull_utils.mongodb_collection_name_doctor + '_test'  # 医生端数据库
            else:
                self.mr_client_url = self.conf_dict['mr_url'].get(self.database_ip, dict()).get('release', '')
                self.collection_name_doctor = self.mongo_pull_utils.mongodb_collection_name_doctor
            if not self.ward_code_list:
                self.ward_code_list = self.get_ward_code()
            HospitalServerInfo.is_init = True

    def __new__(cls, *args, **kwargs):
        """
        单例模式
        """
        if not hasattr(cls, 'instance'):
            cls.instance = super(HospitalServerInfo, cls).__new__(cls)
        return cls.instance

    def get_ward_code(self):
        result = list()
        for k, v in self.dept_dict.items():
            if v in self.ward_dept:
                result.append(k)
        return result

    def get_inhospitalpatdata(self):
        """
        获取所有病区在院患者信息
        """
        web_service = Client(self.mr_client_url)
        for ward_code in self.ward_code_list:
            mr_data = web_service.service.EmrInHospitalData(ward_code)
            self.inhospital_pat_data[ward_code] = json.loads(mr_data)
        return self.inhospital_pat_data

    def get_dischargepatdata(self):
        """
        获取所有病区出院患者信息，并更新doctor库的质控信息
        """
        conn = self.mongo_pull_utils.connection(collection_name=self.collection_name_doctor)
        web_service = Client(self.mr_client_url)
        for ward_code in self.ward_code_list:
            mr_data = web_service.service.EmrOutHospitalData(ward_code)
            self.discharge_pat_data[ward_code] = json.loads(mr_data)
            patient_info = self.discharge_pat_data[ward_code].get('DISCHARGE_PATIENT_INFO', list())
            for data in patient_info:  # 通过电子病历服务器数据更新mongo中的医生端质控数据
                key = data.get('PATIENT_ID', '') + '#' + data.get('VISIT_ID', '') + '#' + self.hospital_code

                mongo_data = conn.find_one({'_id': key}, {'pat_info': 1})
                if not mongo_data:  # 没有质控数据则跳过
                    continue
                if data.get('ADMISSION_DATE_TIME') and data.get('ADMISSION_DATE_TIME') != mongo_data.get('pat_info', dict()).get('admission_time'):
                    conn.update({'_id': key}, {'$set': {'pat_info.admission_time': data.get('ADMISSION_DATE_TIME')}}, upsert=True)  # 更新入院时间

                if data.get('DISCHARGE_DATE_TIME') and data.get('DISCHARGE_DATE_TIME') != mongo_data.get('pat_info', dict()).get('discharge_time'):
                    conn.update({'_id': key}, {'$set': {'pat_info.discharge_time': data.get('DISCHARGE_DATE_TIME')}}, upsert=True)  # 更新出院时间

                if data.get('DEPT_ADMISSION_TO_NAME') and data.get('DEPT_ADMISSION_TO_NAME') != mongo_data.get('pat_info', dict()).get('district_admission_to_name'):  # dept 和 district 反了
                    ward = data.get('DEPT_ADMISSION_TO_NAME')
                    conn.update({'_id': key}, {'$set': {'pat_info.district_admission_to_name': ward}}, upsert=True)  # 更新入院病区
                    conn.update({'_id': key}, {'$set': {'pat_info.dept_admission_to_name': self.ward_dept.get(ward)}}, upsert=True)  # 更新入院科室

                if data.get('DEPT_DISCHARGE_FROM_NAME') and data.get('DEPT_DISCHARGE_FROM_NAME') != mongo_data.get('pat_info', dict()).get('dept_discharge_from_name'):
                    ward = data.get('DEPT_DISCHARGE_FROM_NAME')
                    conn.update({'_id': key}, {'$set': {'pat_info.district_discharge_from_name': ward}}, upsert=True)  # 更新出院病区
                    conn.update({'_id': key}, {'$set': {'pat_info.dept_discharge_from_name': self.ward_dept.get(ward)}}, upsert=True)  # 更新出院科室

        return self.discharge_pat_data

    def get_inhospitalpatnum(self):
        """
        获取所有病区医生在院病人数
        """
        web_service = Client(self.mr_client_url)
        mr_data = web_service.service.EmrInHospitalPatNum()
        self.inhospital_pat_num = json.loads(mr_data)
        return self.inhospital_pat_num

    def get_dischargepatnum(self):
        """
        获取所有病区医生出院病人数
        """
        web_service = Client(self.mr_client_url)
        mr_data = web_service.service.EmrOutHospitalPatNum()
        self.discharge_pat_num = json.loads(mr_data)
        return self.discharge_pat_num

    def get_artificial_data(self, patient_id='', visit_id=''):
        """
        根据patient_id和visit_id获取该患者病历文书人工质控结果，并存入终末质控
        """
        web_service = Client(self.mr_client_url)
        mr_data = web_service.service.EmrArtificialQCData(patient_id, visit_id)
        result = json.loads(mr_data)
        if not result:
            return result
        try:
            one_record = result.get('DISCHARGE_PATIENT_INFO', list())[0]
            if not isinstance(one_record, dict):
                return {}
        except:
            self.logger.error(traceback.format_exc())
            return result
        conn = self.mongo_pull_utils.connection()
        key = patient_id + '#' + visit_id + '#' + self.hospital_code
        if not conn.find_one({'_id': key}, {'_id': 1}):  # 规则质控中无该文书质控信息
            push_data = {'_id': key}
            push_data['pat_info'] = dict()
            push_data['pat_info']['patient_id'] = patient_id
            push_data['pat_info']['visit_id'] = visit_id
            push_data['pat_info']['machine_score'] = 0
            push_data['pat_info']['person_name'] = one_record.get('姓名', '')
            push_data['pat_info']['district_admission_to_name'] = one_record.get('入院病区', '')
            push_data['pat_info']['district_discharge_from_name'] = one_record.get('出院病区', '')
            push_data['pat_info']['dept_admission_to_name'] = self.ward_dept.get(one_record.get('入院病区', ''), '')
            push_data['pat_info']['dept_discharge_from_name'] = self.ward_dept.get(one_record.get('出院病区', ''), '')
            push_data['pat_info']['admission_time'] = one_record.get('入院时间', '')
            push_data['pat_info']['discharge_time'] = one_record.get('出院时间', '')
            push_data['pat_info']['html'] = list()
            push_data['pat_value'] = list()
            push_data['del_value'] = list()
            push_data['content'] = list()
        else:
            push_data = conn.find_one({'_id': key})
            if push_data.get('pat_info', dict()).get('district_admission_to_name') != one_record.get('入院病区', ''):
                push_data['pat_info']['district_admission_to_name'] = one_record.get('入院病区', '')
                push_data['pat_info']['dept_admission_to_name'] = self.ward_dept.get(one_record.get('入院病区', ''), '')
            if push_data.get('pat_info', dict()).get('district_discharge_from_name') != one_record.get('出院病区', ''):
                push_data['pat_info']['district_discharge_from_name'] = one_record.get('出院病区', '')
                push_data['pat_info']['dept_discharge_from_name'] = self.ward_dept.get(one_record.get('出院病区', ''), '')
            if push_data.get('pat_info', dict()).get('admission_time') != one_record.get('入院时间', ''):
                push_data['pat_info']['admission_time'] = one_record.get('入院时间', '')
            if push_data.get('pat_info', dict()).get('discharge_time') != one_record.get('出院时间', ''):
                push_data['pat_info']['discharge_time'] = one_record.get('出院时间', '')
        push_data['arti_control_date'] = one_record.get('质控日期', '')  # 人工质控日期
        push_data['record_quality_doctor'] = one_record.get('质控医生姓名', '')
        push_data['status'] = True
        push_data['artificial_value'] = result.get('DISCHARGE_PATIENT_INFO', list())
        save_status = conn.update({'_id': key}, {"$set": push_data}, upsert=True)
        if save_status and isinstance(save_status, dict) and 'updatedExisting' in save_status:
            return result
        else:
            self.logger.error('update id {0} in {2} failed\n\t{1}'.format(key, save_status, self.mongo_pull_utils.mongodb_collection_name))
            return {}

    def get_auto_data(self, patient_id='', visit_id=''):
        """
        根据patient_id和visit_id获取该患者病历文书自动质控结果，并存入终末质控
        """
        web_service = Client(self.mr_client_url)
        mr_data = web_service.service.EmrAutoQCData(patient_id, visit_id)
        result = json.loads(mr_data)
        if not result:
            return result
        try:
            one_record = result.get('AUTO_QC_DATA', list())[0]
            if not isinstance(one_record, dict):
                return {}
        except:
            self.logger.error(traceback.format_exc())
            return result
        conn = self.mongo_pull_utils.connection()
        key = patient_id + '#' + visit_id + '#' + self.hospital_code
        if not conn.find_one({'_id': key}, {'_id': 1}):  # 规则质控中无该文书质控信息
            push_data = {'_id': key}
            push_data['pat_info'] = dict()
            push_data['pat_info']['patient_id'] = patient_id
            push_data['pat_info']['visit_id'] = visit_id
            push_data['pat_info']['machine_score'] = 0
            push_data['pat_info']['person_name'] = one_record.get('NAME', '')
            push_data['pat_info']['html'] = list()
            push_data['pat_value'] = list()
            push_data['del_value'] = list()
            push_data['content'] = list()
        else:
            push_data = conn.find_one({'_id': key})
        push_data['status'] = True
        push_data['auto_value'] = result.get('AUTO_QC_DATA', list())
        save_status = conn.update({'_id': key}, {"$set": push_data}, upsert=True)
        if save_status and isinstance(save_status, dict) and 'updatedExisting' in save_status:
            return result
        else:
            self.logger.error('update id {0} in {2} failed\n\t{1}'.format(key, save_status, self.mongo_pull_utils.mongodb_collection_name))
            return {}

    def get_finalQC_id(self):
        """
        定时请求增量数据表，获取增量数据id
        """
        yesterday = datetime.now() - timedelta(days=1)
        suffix = yesterday.strftime("%Y%m%d")
        collection_name = 'hzlb_listlsb' + suffix
        conn = self.mongo_pull_utils.connection(collection_name=collection_name)
        query_result = conn.find({}, {'_id': 1})
        result = set()
        for data in query_result:
            if len(data.get('_id', '').split('#')) < 3:
                continue
            pivid = data.get('_id', '').split('#')[:2]
            result.add((pivid[0], pivid[1]))
        return result

    def calc_doctor_stat(self):
        """
        定时计算医生端上月统计数据
        """
        conn = self.mongo_pull_utils.connection(collection_name=self.collection_name_doctor)  # 医生端数据库


if __name__ == '__main__':
    app = HospitalServerInfo()
    r = app.get_finalQC_id()
    print(r)
