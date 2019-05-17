#!/usr/bin/env python3
# -*- coding:utf-8 -*

"""
@version: 
@author:
@contact:
@software: PyCharm Community Edition
@file: clientInterface.py
@time: 18-10-29 上午10:44
@description: 电子病历客户端数据接口
"""

import os
import sys
cur_path = os.path.abspath(os.path.dirname(__file__))
root_path = os.path.split(cur_path)[0]
sys.path.append(root_path)  # 项目路径添加到系统路径
from datetime import datetime
from Utils.MongoUtils import PullDataFromMDBUtils, PushDataFromMDBUtils
from Utils.loadingConfigure import Properties
from Utils.segmentWord import RunSegmentWord
# from Utils.regularInfo import RegularInfo
from Utils.socketConnect import SocketConnect
from suds.client import Client
from collections import OrderedDict
import json
if cur_path.endswith('Test'):
    from RecordClientTest.mainProgram import CheckMultiRecords
    from RecordClientTest.timedTask import HospitalServerInfo
else:
    from RecordClient.mainProgram import CheckMultiRecords
    from RecordClient.timedTask import HospitalServerInfo


class ClientInterface(object):

    def __init__(self, debug=False):
        self.debug = debug
        self.mongo_pull_utils = PullDataFromMDBUtils()
        self.mongo_push_utils = PushDataFromMDBUtils()
        self.segment = RunSegmentWord()
        self.parameters = Properties()
        self.regular_model = self.parameters.regular_model['环节']
        self.dept_list = self.parameters.dept.copy()
        self.dept_dict = self.parameters.dept_dict.copy()
        self.ward_dept = self.parameters.ward_dept.copy()
        self.run_regular = CheckMultiRecords(debug=True)
        self.run_regular.regular_model = self.parameters.regular_model['医生端']
        self.database_name = self.mongo_pull_utils.mongodb_database_name
        self.collection_name = self.mongo_pull_utils.mongodb_collection_name
        # 加载规则模型
        self.conf_dict = self.parameters.conf_dict.copy()
        self.hospital_code = self.parameters.properties.get('hospital_code')
        self.database_ip = self.parameters.properties.get('mongo_host', '')
        self.emr_record = self.parameters.getInfo('emr_transform.txt')
        self.collection_name_huanjie = self.mongo_pull_utils.mongodb_collection_name_huanjie
        self.collection_name_zhongmo = self.mongo_pull_utils.mongodb_collection_name_zhongmo

        self.hospitalServerInfo = HospitalServerInfo()
        if cur_path.endswith('Test'):
            self.collection_name_doctor = self.mongo_pull_utils.mongodb_collection_name_doctor + '_test'  # 医生端数据库
            self.mr_client_url = self.conf_dict['mr_url'].get(self.database_ip, dict()).get('test', '')
        else:
            self.collection_name_doctor = self.mongo_pull_utils.mongodb_collection_name_doctor
            self.mr_client_url = self.conf_dict['mr_url'].get(self.database_ip, dict()).get('release', '')

    def segmentRecord_new(self, json_file):
        """
        对应新版本json传入
        """
        result = dict()
        medical_record = dict()
        patient_id = json_file.get('binganshouye', dict()).get('patient_id', '')
        visit_id = json_file.get('binganshouye', dict()).get('visit_id', '')
        if not (patient_id and visit_id):
            return {'res_flag': False, 'error_info': 'no patient_id or visit_id in json file'}
        _id = '{}#{}#{}'.format(self.hospital_code, patient_id, visit_id)
        medical_record['_id'] = _id
        medical_record['patient_id'] = patient_id
        medical_record['visit_id'] = visit_id
        medical_record['doctor_name'] = json_file.get('yonghuxinxi', dict()).get('user_name', '')
        medical_record['doctor_id'] = json_file.get('yonghuxinxi', dict()).get('user_id', '')
        medical_record['doctor_dept'] = json_file.get('yonghuxinxi', dict()).get('user_dept', '')
        medical_record['education_title'] = json_file.get('yonghuxinxi', dict()).get('education_title', '')
        medical_record['role_id'] = json_file.get('yonghuxinxi', dict()).get('role_id', '')
        medical_record['role_name'] = json_file.get('yonghuxinxi', dict()).get('role_name', '')
        result.update(medical_record)  # 将id, patient_id, visit_id存入返回数据中
        # 组合病案首页信息
        binganshouye = dict()
        binganshouye['pat_info'] = dict()
        binganshouye['pat_visit'] = dict()
        binganshouye['pat_info']['sex_name'] = json_file.get('binganshouye', dict()).get('pat_info_sex_name', '')
        binganshouye['pat_visit']['age_value'] = json_file.get('binganshouye', dict()).get('pat_info_age_value', '')
        binganshouye['pat_visit']['age_value_unit'] = json_file.get('binganshouye', dict()).get('pat_info_age_value_unit', '')
        binganshouye['pat_visit']['marital_status_name'] = json_file.get('binganshouye', dict()).get('pat_info_marital_status_name', '')
        binganshouye['pat_visit']['inp_no'] = json_file.get('binganshouye', dict()).get('inp_no', '')
        binganshouye['pat_visit']['admission_time'] = json_file.get('binganshouye', dict()).get('admission_time', '')
        binganshouye['pat_visit']['discharge_time'] = json_file.get('binganshouye', dict()).get('discharge_time', '')
        binganshouye['pat_visit']['dept_admission_to_name'] = json_file.get('binganshouye', dict()).get('pat_visit_dept_admission_to_name', '')  # dept
        binganshouye['pat_visit']['dept_admission_to_code'] = json_file.get('binganshouye', dict()).get('pat_visit_dept_admission_to_code', '')  # code
        binganshouye['pat_visit']['senior_doctor_name'] = json_file.get('binganshouye', dict()).get('senior_doctor_name', '')  # 主任(副主任)医师姓名
        binganshouye['pat_visit']['attending_doctor_name'] = json_file.get('binganshouye', dict()).get('attending_doctor_name', '')  # 住院医师
        binganshouye['pat_visit']['inp_doctor_name'] = json_file.get('binganshouye', dict()).get('inp_doctor_name', '')  # code
        binganshouye['pat_visit']['drug_allergy_name'] = json_file.get('binganshouye', dict()).get('drug_allergy_name', '')
        binganshouye['pat_visit']['patient_id'] = patient_id
        binganshouye['pat_visit']['visit_id'] = visit_id
        result['binganshouye'] = binganshouye  # 将病案首页信息存入返回数据中

        # step.1 获取传过来的文书名称,
        if 'huanzheshouye' not in json_file:
            emr_code = json_file.get('wenshuxinxi', dict()).get('mr_class_code', '')
            if not emr_code:
                return {'res_flag': False, 'error_info': 'mr_class_code is empty...'}
            if emr_code not in self.emr_record:
                return {'res_flag': False, 'warn_info': '此文书无相关质控规则', 'emr_code': emr_code}
            record_name = self.emr_record[emr_code]
            record_name_cn = self.conf_dict['english_to_chinese'].get(record_name[0], '')
            if not record_name_cn:
                return {'res_flag': False, 'error_info': 'no record name corresponding to the emr_code', 'emr_code': emr_code, 'record_name': record_name[0]}
        else:
            record_name = ['binganshouye', '1']
            record_name_cn = '病案首页'
        # step.1 结束

        # step.2 获取其它文书，并将非传来文书所属规则置于未启用
        his_record = ['yizhu', 'hulitizhengyangli', 'jianchabaogao', 'jianyanbaogao']  # 需要在socket请求的数据, jianyaobaogao, huli未处理, jiancha分词处理
        his_request = set()
        regular_record = self.parameters.getInfo('regular_to_record.txt')
        if json_file.get('binganshouye', dict()).get('discharge_time', ''):  # 病案首页有出院时间用环节质控，没有则用医生端质控
            self.run_regular.regular_model = self.parameters.regular_model['环节']
        for regular_code, regular_model in self.run_regular.regular_model.items():
            if regular_model.get('record_name') != record_name_cn:
                regular_model['status'] = '未启用'
                continue
            if regular_model.get('code') in regular_record:
                code = regular_model.get('code')
                if isinstance(regular_record[code], str):
                    his_request.add(regular_record[code])
                elif isinstance(regular_record[code], list):
                    for record in regular_record[code]:
                        his_request.add(record)
        # 环节质控才定时跑
        if record_name[0] in his_request:
            his_request.remove(record_name[0])
        if his_request:
            socket_app = SocketConnect()
            for collection in his_request:
                # 从socket获取其它文书数据，并将其存入数据库，且放入result中
                if collection in his_record:
                    if collection == 'yizhu':
                        socket_result = socket_app.process(patient_id, visit_id, collection)
                    else:
                        socket_result = socket_app.process(patient_id, '', collection, start_time=binganshouye['pat_visit']['admission_time'])
                    if not socket_result.get('res_flag'):
                        continue
                        # return socket_result
                    if collection == 'jianchabaogao':
                        result[collection] = [{collection: {'exam_report': socket_result.get(collection, list())}}]
                        self.mongo_push_utils.pushData('mrq_jianchabaogao', {collection: {'exam_report': socket_result.get(collection, list())},
                                                                             '_id': _id,
                                                                             'patient_id': patient_id,
                                                                             'visit_id': visit_id,
                                                                             'batchno': datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')})
                    elif collection == 'jianyanbaogao':
                        result[collection] = [{collection: {'lab_report': socket_result.get(collection, list())}}]
                        self.mongo_push_utils.pushData('mrq_jianyanbaogao', {collection: {'lab_report': socket_result.get(collection, list())},
                                                                             '_id': _id,
                                                                             'patient_id': patient_id,
                                                                             'visit_id': visit_id,
                                                                             'batchno': datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')})
                    else:
                        result[collection] = [{collection: socket_result.get(collection, list())}]
                        self.mongo_push_utils.pushData('mrq_jianyanbaogao', {collection: socket_result.get(collection, list()),
                                                                             '_id': _id,
                                                                             'patient_id': patient_id,
                                                                             'visit_id': visit_id,
                                                                             'batchno': datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')})
                # 从MRQ库获取其它文书数据，放入result中
                else:
                    conn = self.mongo_push_utils.connectCollection(database_name=self.database_name, collection_name=collection)
                    mongo_result = conn.find_one({'_id': _id}) or dict()
                    if not mongo_result:
                        continue
                    else:
                        result[collection] = [mongo_result]
        # step.2 结束

        if 'huanzheshouye' in json_file:
            result['binganshouye'] = json_file.get('huanzheshouye', dict())
            result['shouyeshoushu'] = [{'shouyeshoushu': json_file.get('shouyeshoushu', list())}]
            result['shouyezhenduan'] = [{'shouyezhenduan': json_file.get('shouyezhenduan', list())}]
            self.mongo_push_utils.pushData('mrq_binganshouye', {'binganshouye': json_file.get('huanzheshouye', dict()),
                                                                '_id': _id,
                                                                'patient_id': patient_id,
                                                                'visit_id': visit_id,
                                                                'batchno': datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')})
            self.mongo_push_utils.pushData('mrq_shouyeshoushu', {'shouyeshoushu': json_file.get('shouyeshoushu', list()),
                                                                 '_id': _id,
                                                                 'patient_id': patient_id,
                                                                 'visit_id': visit_id,
                                                                 'batchno': datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')})
            self.mongo_push_utils.pushData('mrq_shouyezhenduan', {'shouyezhenduan': json_file.get('shouyezhenduan', list()),
                                                                  '_id': _id,
                                                                  'patient_id': patient_id,
                                                                  'visit_id': visit_id,
                                                                  'batchno': datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')})
            result['res_flag'] = True
            return result

        # step.3 获取质控文书分词结果
        wenshuxinxi = json_file.get('wenshuxinxi', dict())
        seg_result = self.segment.processHtml(**wenshuxinxi)
        if not seg_result.get('res_flag'):
            return seg_result
        if record_name[0] in seg_result:
            k_src = '{}_src'.format(record_name[0])
            conn_name = 'mrq_{}'.format(record_name[0])
            conn_name_src = '{}_src'.format(conn_name)
            record_id = wenshuxinxi.get('file_unique_id')
            # 存储原始文书及其分词结果
            if record_id:
                # 文书内容存储在 mrq_文书名称(_src) 中
                # 存储src
                conn_src = self.mongo_push_utils.connectCollection(database_name=self.database_name,
                                                                   collection_name=conn_name_src)
                record_id_result = conn_src.find_one({'_id': _id}) or dict()
                record_id_list = [value.get('file_unique_id', '') for value in record_id_result.get(record_name[0], list())]
                record_index = -1 if record_id not in record_id_list else record_id_list.index(record_id)  # 获取此次文书在src出现的位置，未出现过则为-1
                record_id_result.setdefault(record_name[0], list())
                record_id_result.setdefault('_id', _id)
                if record_index == -1:
                    record_id_result.get(record_name[0], list()).append(wenshuxinxi)
                else:
                    record_id_result.get(record_name[0], list())[record_index] = wenshuxinxi
                self.mongo_push_utils.pushData(conn_name_src, record_id_result)  # 分词前的src，单文书多文书存储方式一致

                # 存储分词结果
                if record_name[1] == '1':
                    self.mongo_push_utils.pushData(conn_name, {'_id': _id, record_name[0]: seg_result[record_name[0]]})  # 单个文件分词后的
                else:
                    conn = self.mongo_push_utils.connectCollection(database_name=self.database_name,
                                                                   collection_name=conn_name)
                    conn_result = conn.find_one({'_id': _id}) or dict()
                    conn_result.setdefault(record_name[0], list())
                    conn_result.setdefault('_id', _id)
                    if record_index == -1:
                        conn_result.get(record_name[0], list()).append(seg_result[record_name[0]])
                    else:
                        conn_result.get(record_name[0], list())[record_index] = seg_result[record_name[0]]
                    self.mongo_push_utils.pushData(conn_name, conn_result)
            # 结束：原始文书及其分词结果存储

            if 'mr_content_html' in wenshuxinxi:
                wenshuxinxi.pop('mr_content_html')
            if record_name[1] == '1':
                result[record_name[0]] = [{record_name[0]: seg_result[record_name[0]]}]
            else:
                result[record_name[0]] = [{record_name[0]: [seg_result[record_name[0]]]}]
            result[k_src] = [{record_name[0]: [wenshuxinxi]}]
            seg_result.pop(record_name[0])
            result.update(seg_result)
        else:
            return {'res_flag': False, 'error_info': '{} not in segment result'.format(record_name[0])}
        # step.3 结束
        result['res_flag'] = True
        return result

    def isTestAccount(self, doctor_name):
        """
        查看医生姓名用的是否是测试账号
        """
        test_flag = False
        for test_name in self.conf_dict.get('test_account'):  # 测试账号不存入数据库
            if test_name in doctor_name:
                test_flag = True
                break
        return test_flag

    def processJsonFile(self, json_file):
        """
        json_file为传过来的原始数据
        """
        if json_file.get('pageSource') == '1':
            return {'print_info': '您在下诊断，无法进行内涵质控'}
        if json_file.get('pageSource') == '2':
            return {'print_info': '目前为浏览病历，请点击“保存”用以质控病历'}
        if json_file.get('pageSource') == '6':
            return {'print_info': '您在下医嘱，无法进行内涵质控'}
        if json_file.get('pageSource') == '8':
            return {'print_info': '欢迎使用AI病历内涵质控'}
        if json_file.get('pageSource') != '0':
            return {'print_info': '非保存病历状态码'}
        # if json_file.get('huanzheshouye'):
        #     return self.processJsonFileBingan(json_file)
        json_result = self.segmentRecord_new(json_file)
        if not json_result.get('res_flag'):
            return json_result
        doctor_name = json_result.get('doctor_name', '')  # 记录医生姓名
        key = json_result.get('_id', '')

        # 先看连的是否是测试mongo库，如果是测试库，直接进行推送，否则再判断账号是否是测试账号
        push_flag = False
        if self.collection_name_doctor == self.mongo_pull_utils.mongodb_collection_name_doctor + '_test':
            push_flag = True
        else:
            # 如果不是测试账号, 则推送数据库
            if not self.isTestAccount(doctor_name):  
                push_flag = True

        # 保存电子病历端传输的原始数据
        if push_flag:
            patient_id = json_file.get('patient_id', '')
            if patient_id:
                original_collection = self.collection_name_doctor + '_original'  # 测试接口保存到测试库，正式接口保存到正式库
                ori_id = self.hospital_code + '#' + patient_id
                ori_json = {'_id': ori_id, 'info': json_file, 'batchno': datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')}
                self.run_regular.PushData.pushData(original_collection, ori_json)  # 保存原始json数据

        result = dict()
        if not json_result:
            return result
        self.run_regular.all_result = dict()
        for collection_name, collection_rule_func in self.conf_dict['func'].items():
            for func in collection_rule_func:
                if func not in self.run_regular.__dir__():
                    continue
                result = eval('self.run_regular.' + func)(collection_name, **json_result)  # 进行质控
        return self.multiControlPush(key, result, json_result, self.collection_name_doctor, push_flag)

    def multiControlPush(self, key, control_result, json_result, collection_name, push_flag):
        """
        存储多次质控结果, 医生端，环节质控结果传回EMR
        :param key: _id号
        :param control_result: 此次质控结果
        :param json_result: segmentRecord_new结果
        :param collection_name: 医生端 self.collection_name_doctor, 环节 self.collection_name_huanjie
        :param push_flag:
        :return:
        """
        doctor_name = json_result.get('doctor_name', '')  # 记录医生姓名
        doctor_id = json_result.get('doctor_id', '')  # 记录医生id
        doctor_dept = json_result.get('doctor_dept', '')  # 记录医生病区
        conn = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                       collection_name=collection_name)

        key_split = key.split('#')
        mrq_id = '#'.join(key_split[1:]) + '#' + key_split[0]
        mongo_result = conn.find_one({'_id': mrq_id})

        # 获取该患者环节端的删除列表
        del_code = self.getDelValue(mrq_id, self.collection_name_huanjie)

        # 此次质控有结果
        if control_result:
            pat_value = list()
            # 此前没有质控过
            if not mongo_result:
                push_data = control_result[key].copy()
                push_data['doctor_name'] = doctor_name
                push_data['doctor_id'] = doctor_id
                push_data['doctor_dept'] = doctor_dept
                push_data['modify_num'] = list()  # 第n次质控时有修改
                push_data['modify_details'] = list()  # 第n次质控时有修改
                push_data['control_date'] = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')  # 记录保存保存时间
                push_data['doctor_value_list'] = list()
                push_data['code_list'] = [value['code'] for value in control_result[key]['pat_value']]  # 记录出现过的 code
                push_data['increase_code'] = dict().fromkeys(push_data['code_list'], 0)
                push_data['decrease_code'] = dict().fromkeys(push_data['code_list'], 0)

                for one_record in push_data['pat_value']:
                    code = one_record.get('code')
                    # 不在删除列表的规则结果才存储在 pat_value 中
                    if code and code not in del_code:
                        one_record['doctor_name'] = doctor_name
                        one_record['doctor_id'] = doctor_id
                        one_record['doctor_dept'] = doctor_dept
                        pat_value.append(one_record)
                push_data.pop('pat_value')

            else:  # 有质控过
                push_data = mongo_result.copy()
                push_data['pat_info'] = control_result[key]['pat_info']  # 患者信息取最新一次的
                push_data['doctor_name'] = doctor_name
                push_data['doctor_id'] = doctor_id
                push_data['doctor_dept'] = doctor_dept
                push_data['control_date'] = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')  # 记录保存保存时间

                push_data.setdefault('doctor_value_list', list())

                for one_record in control_result[key]['pat_value']:
                    regular_code = one_record.get('code')

                    # 不在删除列表的规则结果才存储在 pat_value 中
                    if regular_code and regular_code not in del_code:
                        one_record['doctor_name'] = doctor_name
                        one_record['doctor_id'] = doctor_id  # 添加该次病历书写医生id与医生科室
                        one_record['doctor_dept'] = doctor_dept
                        pat_value.append(one_record)
                        # 更新 出现过的code 列表
                        if regular_code and regular_code not in push_data['code_list']:
                            push_data['code_list'].append(regular_code)
                        # 更新完毕

                last_value = [value['code'] for value in push_data['doctor_value_list'][-1] if 'code' in value]  # 上一次的质控结果
                this_value = [value['code'] for value in pat_value if 'code' in value]

                if set(last_value) != set(this_value):
                    diff_code = set(last_value).difference(set(this_value)) | set(this_value).difference(set(last_value))
                    push_data['modify_num'].append(len(push_data['doctor_value_list']))  # 第几次有修改 从0开始
                    if 'modify_details' in push_data:
                        push_data['modify_details'].append({'num': len(push_data['doctor_value_list']),
                                                            'details': list(diff_code)})  # 第几次有修改 从0开始
                    else:
                        push_data['modify_details'] = [{'num': len(push_data['doctor_value_list']),
                                                        'details': list(diff_code)}]  # 第几次有修改 从0开始

                for c in this_value:
                    if c not in last_value:
                        push_data['increase_code'].setdefault(c, 0)
                        push_data['increase_code'][c] += 1
                for c in last_value:
                    if c not in this_value:
                        push_data['decrease_code'].setdefault(c, 0)
                        push_data['decrease_code'][c] += 1

            if not pat_value:
                pat_value.append({'doctor_name': doctor_name,
                                  'doctor_id': doctor_id,
                                  'doctor_dept': doctor_dept})
            score = sum([data['score'] for data in pat_value if 'score' in pat_value])
            push_data['pat_info']['machine_score'] = score  # 更新质控分
            push_data['doctor_value_list'].append(pat_value)
            control_result[key]['problem_num'] = len(pat_value)
            control_result[key]['pat_value'] = pat_value
            control_result[key]['pat_info']['machine_score'] = score

            if push_flag:
                self.run_regular.PushData.pushData(collection_name, push_data)

            control_result[key]['file_correct'] = False
            control_result[key]['res_flag'] = True
            return control_result[key]

        # 此次质控无结果
        else:
            # 此前没有质控过
            if not mongo_result:
                _, push_data, _ = self.run_regular.get_patient_info(json_result, '')
                push_data['doctor_name'] = doctor_name
                push_data['doctor_id'] = doctor_id
                push_data['doctor_dept'] = doctor_dept
                push_data['modify_num'] = list()  # 第n次质控时有修改
                push_data['modify_details'] = list()  # 第n次质控时有修改
                push_data['control_date'] = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')  # 记录保存保存时间
                push_data['doctor_value_list'] = list()
                push_data['code_list'] = list()  # 记录出现过的 code
                push_data['increase_code'] = dict()
                push_data['decrease_code'] = dict()
                value = [{'creator_name': doctor_name,
                          'doctor_name': doctor_name,
                          'doctor_dept': doctor_dept,
                          'doctor_id': doctor_id,
                          'batchno': datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')}]
                push_data.pop('pat_value')

            # 此前质控过
            else:
                push_data = mongo_result.copy()
                _, patient_info, _ = self.run_regular.get_patient_info(json_result, '')
                push_data['pat_info'] = patient_info['pat_info']  # 患者信息取最新一次的
                push_data['doctor_name'] = doctor_name
                push_data['doctor_id'] = doctor_id
                push_data['doctor_dept'] = doctor_dept
                push_data['control_date'] = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')  # 记录保存保存时间
                last_value = [value['code'] for value in push_data['doctor_value_list'][-1] if 'code' in value]  # 上一次的质控结果
                if last_value:
                    push_data['modify_num'].append(len(push_data['doctor_value_list']))  # 第几次有修改 从0开始
                    if 'modify_details' in push_data:
                        push_data['modify_details'].append({'num': len(push_data['doctor_value_list']),
                                                            'details': last_value})  # 第几次有修改 从0开始
                    else:
                        push_data['modify_details'] = [{'num': len(push_data['doctor_value_list']),
                                                        'details': last_value}]  # 第几次有修改 从0开始
                for c in last_value:
                    push_data['decrease_code'].setdefault(c, 0)
                    push_data['increase_code'].setdefault(c, 0)
                    push_data['decrease_code'][c] += 1

                value = [{'creator_name': doctor_name,
                          'doctor_name': doctor_name,
                          'doctor_dept': doctor_dept,
                          'doctor_id': doctor_id,
                          'batchno': datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')}]
            score = sum([data['score'] for data in value if 'score' in value])
            push_data['pat_info']['machine_score'] = score  # 更新质控分
            push_data['doctor_value_list'].append(value)
            if push_flag:
                self.run_regular.PushData.pushData(collection_name, push_data)
            control_result['file_correct'] = True
            control_result['res_flag'] = True
            return control_result

    def getDelValue(self, _id, collection_name):
        """
        获取患者质控结果删除code列表
        :param _id:
        :param collection_name:
        :return:
        """
        conn = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                       collection_name=collection_name)
        mongo_result = conn.find_one({'_id': _id, 'del_value.code': {'$exists': True}}, {'del_value.code': 1}) or dict()
        del_code = list()
        del_value = mongo_result.get('del_value', list())
        for one_value in del_value:
            code = one_value.get('code')
            if code and code not in del_code:
                del_value.append(code)
        return del_code

    def getTransmitEMR(self, _id, collection_name):
        """
        获取回传给电子病历的机器质控结果
        :param _id:
        :param collection_name:
        :return:
        """
        conn = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                       collection_name=collection_name)
        mongo_result = conn.find_one({'_id': _id, 'transmit_code': {'$exists': True}}, {'transmit_code': 1}) or dict()
        transmit_code = mongo_result.get('transmit_code', list())
        return transmit_code
    
    def pushTransmitFlag(self, patient_id, visit_id, collection_name):
        """
        环节质控数据结果回传emr
        """
        mrq_id = '{}#{}#{}'.format(patient_id, visit_id, self.hospital_code)
        if collection_name == 'huanjie':
            conn = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                           collection_name=self.collection_name_huanjie)
            pipeline = [
                {'$match': {'_id': mrq_id}},
                {'$project': {'pat_value': {'$slice': ['$doctor_value_list', -1, 1]},
                              'del_value.code': 1}},
                {'$unwind': '$pat_value'},
                {'$project': {'pat_value.code': 1,
                              'del_value.code': 1}}
            ]
            mongo_result = conn.aggregate(pipeline, allowDiskUse=True)
        elif collection_name == 'zhongmo' or collection_name == 'jiwang':
            conn = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                           collection_name='{}_{}'.format(self.collection_name, collection_name))
            mongo_result = conn.find({'_id': mrq_id}, {'pat_value.code': 1, 'del_value.code': 1})
        else:
            return {'res_flag': False, 'info': 'error collection_name [{}]'.format(collection_name)}
        for data in mongo_result:
            del_code = [value['code'] for value in data.get('del_value', list()) if 'code' in value]
            pat_code = [value['code'] for value in data.get('pat_value', list()) if 'code' in value]
            transmit_code = list(set(pat_code) - set(del_code))
            conn.update({'_id': mrq_id}, {'$set': {'transmit_code': transmit_code}}, upsert=True)
        return {'res_flag': True}

    def modifyHuanjieResult(self, data_id, content, delete_list, doctor_name):
        conn = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                       collection_name=self.collection_name_huanjie)
        data = conn.find_one({'_id': data_id})
        if not data:
            return {'res_flag': False, 'info': 'no [{}] data in mongoDB'.format(data_id)}
        if delete_list:
            del_value = data.get('del_value', list())
            pat_value = data['doctor_value_list'][-1]
            machine_score = sum([value['score'] for value in pat_value if 'score' in value])
            for one_pat_value in pat_value:
                n = str(one_pat_value.get('num', 0))
                if n in delete_list:
                    one_pat_value['del_reason'] = delete_list.get(n, dict())
                    one_pat_value['del_batchno'] = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
                    one_pat_value['del_doctor_name'] = doctor_name
                    del_value.append(one_pat_value)
                    machine_score -= one_pat_value.get('score', 0)
                    continue
            conn.update({'_id': data_id}, {'$set': {'del_value': del_value}}, upsert=True)
            conn.update({'_id': data_id}, {'$set': {'pat_info.machine_score': machine_score}}, upsert=True)
            conn.update({'_id': data_id}, {'$set': {'record_quality_doctor': doctor_name}}, upsert=True)
        if content:
            artificial_score = sum([float(value['score']) for value in content if 'score' in value])
            content_exist = [(value.get('reg', ''), value.get('text', ''), value.get('score', ''), value.get('selectedTab', ''), value.get('selectedText', '')) for value in data.get('content', list())]
            push_content = list()
            for one_data in content:
                if (one_data.get('reg', ''), one_data.get('text', ''), one_data.get('score', ''), one_data.get('selectedTab', ''), one_data.get('selectedText', '')) not in content_exist:
                    if one_data.get('reg'):
                        one_data['batchno'] = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
                        one_data['doctor_name'] = doctor_name
                push_content.append(one_data)
            conn.update({'_id': data_id}, {'$set': {'content': push_content}}, upsert=True)
            conn.update({'_id': data_id}, {'$set': {'control_date': datetime.strftime(datetime.now(), '%Y-%m-%d')}}, upsert=True)
            conn.update({'_id': data_id}, {'$set': {'status': True}}, upsert=True)
            conn.update({'_id': data_id}, {'$set': {'pat_info.artificial_score': artificial_score}}, upsert=True)
            conn.update({'_id': data_id}, {'$set': {'record_quality_doctor': doctor_name}}, upsert=True)
        return {'res_flag': True}

    def showHuanjieDataResult(self, data_id):
        conn = self.mongo_push_utils.connectCollection(database_name=self.database_name,
                                                       collection_name=self.collection_name_huanjie)
        pipeline = [
            {'$match': {'_id': data_id}},
            {'$project': {'pat_value': {'$slice': ['$doctor_value_list', -1, 1]},
                          'pat_info': 1,
                          'content': 1,
                          'del_value.code': 1,
                          'record_quality_doctor': 1}},
            {'$unwind': '$pat_value'},
        ]
        mongo_result = conn.aggregate(pipeline, allowDiskUse=True)
        result = dict()
        for data in mongo_result:
            result['inp_no'] = data.get('pat_info', dict()).get('inp_no')
            result['patient_id'] = data.get('pat_info', dict()).get('patient_id')
            result['machine_score'] = data.get('pat_info', dict()).get('machine_score')
            result['artificial_score'] = data.get('pat_info', dict()).get('artificial_score')
            result['dept_discharge_from_name'] = data.get('pat_info', dict()).get('dept_discharge_from_name')
            result['control_doctor'] = data.get('record_quality_doctor', '')
            path_list = []
            for k, v in self.regular_model.items():
                if v.get('record_name') and v.get('chapter'):
                    if v.get('record_name') not in path_list:
                        path_list.append(v.get('record_name'))
                    if v.get('record_name') != v.get('chapter'):
                        path_name = '{}--{}'.format(v.get('record_name'), v.get('chapter'))
                        if path_name not in path_list:
                            path_list.append(path_name)
            value_list = data.get('pat_value', list()) + data.get('content', list())
            del_code = [value['code'] for value in data.get('del_value', list()) if 'code' in value]
            result['info'] = list()
            for path in path_list:
                for value in value_list:
                    value_path = value.get('path') or value.get('selectedTab')
                    if value_path != path:
                        continue
                    value_content = value.get('name') or value.get('reg')
                    value_score = value.get('score') or value.get('score')
                    value_reason = value.get('reason') or value.get('text')
                    if 'code' in value:
                        # 已人工删除的机器质控不展示
                        if value['code'] in del_code:
                            continue
                        value_flag = 'machine'
                    elif 'reg' in value:
                        value_flag = 'manual'
                    else:
                        value_flag = 'emr'
                    result['info'].append({'path': value_path,
                                           'content': value_content,
                                           'score': value_score,
                                           'reason': value_reason,
                                           'flag': value_flag})
        return result

    def inHospitalPat(self, ward_code='', in_hospital=True):
        """
        返回某一病区下病人id
        """
        web_service = Client(self.mr_client_url)
        if in_hospital:
            if not self.hospitalServerInfo.inhospital_pat_data.get(ward_code, dict()):
                mr_data = web_service.service.EmrInHospitalData(ward_code)
                mr_data = json.loads(mr_data)
                self.hospitalServerInfo.inhospital_pat_data[ward_code] = mr_data
                patient_info = mr_data.get('INHOSPITAL_PATIENT_INFO', list())
            else:
                patient_info = self.hospitalServerInfo.inhospital_pat_data.get(ward_code).get('INHOSPITAL_PATIENT_INFO', list())
        else:
            if not self.hospitalServerInfo.discharge_pat_data.get(ward_code, dict()):
                mr_data = web_service.service.EmrOutHospitalData(ward_code)
                mr_data = json.loads(mr_data)
                self.hospitalServerInfo.discharge_pat_data[ward_code] = mr_data
                patient_info = mr_data.get('DISCHARGE_PATIENT_INFO', list())
            else:
                patient_info = self.hospitalServerInfo.discharge_pat_data.get(ward_code).get('DISCHARGE_PATIENT_INFO', list())
        query_id = dict()
        for data in patient_info:
            patient = data.get('PATIENT_ID')
            visit = data.get('VISIT_ID')
            if patient and visit:
                key = patient + '#' + visit + '#' + self.hospital_code
                query_id.setdefault(key, dict())
                if data.get('ADMISSION_DATE_TIME'):
                    admission_date = datetime.strptime(data.get('ADMISSION_DATE_TIME'), '%Y-%m-%d %H:%M:%S')
                    query_id[key]['admission_time'] = datetime.strftime(admission_date, '%Y-%m-%d %H:%M:%S')  # 入院时间
                if data.get('DISCHARGE_DATE_TIME'):
                    discharge_date = datetime.strptime(data.get('ADMISSION_DATE_TIME'), '%Y-%m-%d %H:%M:%S')
                    query_id[key]['discharge_time'] = datetime.strftime(discharge_date, '%Y-%m-%d %H:%M:%S')  # 出院时间
        return query_id

    def doctorControlStats(self, ward_name='', record_name='', regular_name='', in_hospital=True, step='医生端'):
        """
        同比表格页
        每一份病历文书所有质控次检测出的规则code，并对code数计数，并对code修改计数
        """
        search_field = dict()
        regular_list = list()
        query_id = set()
        if ward_name == '全部' or ward_name == '医务处':
            for one_ward_name in self.ward_dept:
                ward_code = self.ward_to_code(one_ward_name)
                query_web = self.inHospitalPat(in_hospital=in_hospital, ward_code=ward_code)
                query_id.update(set(query_web.keys()))
        elif ward_name in self.ward_dept.values():
            for one_ward_name, dept in self.ward_dept.items():
                if ward_name == dept:
                    ward_code = self.ward_to_code(one_ward_name)
                    query_web = self.inHospitalPat(in_hospital=in_hospital, ward_code=ward_code)
                    query_id.update(set(query_web.keys()))
        else:
            ward_code = self.ward_to_code(ward_name)
            query_web = self.inHospitalPat(in_hospital=in_hospital, ward_code=ward_code)  # 获取在院或出院病人id号
            query_id = list(query_web.keys())
        query_id = list(query_id)
        query_id = list(set(query_id))
        search_field['_id'] = {'$in': query_id}  # 在院/出院 病人ID
        if record_name:
            regular_list = self.chooseRecordName(record=record_name).get('regular_name', list())
            if regular_list and '全部' in regular_list:
                regular_list.remove('全部')
        if not regular_name:
            regular_name = regular_list
        else:
            regular_name = [regular_name]
        res_tmp = dict()
        modify_tmp = dict()
        collection_doctor = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                                    collection_name=self.collection_name_doctor)
        mongo_result = collection_doctor.find(search_field, {'code_list': 1, '_id': 0, 'decrease_code': 1})
        for data in mongo_result:
            code_list = data.get('code_list', list())
            decrease_code = data.get('decrease_code', dict())
            for code_name in code_list:
                res_tmp.setdefault(code_name, 0)
                res_tmp[code_name] += 1
            for k, v in decrease_code.items():
                if not (k and v):
                    continue
                modify_tmp.setdefault(k, 0)
                modify_tmp[k] += 1
        sheet_info = [{'code': k,
                       'regular_name': self.regular_model[k].get('regular_classify', ''),
                       'regular_details': self.regular_model[k].get('regular_details', ''),
                       'value1': v,
                       'value2': modify_tmp.get(k, 0)} for k, v in res_tmp.items() if (regular_name and self.regular_model[k].get('regular_classify', '') in regular_name) or not regular_name]
        # regular_name, regular_details 从质控结果数据库中取得，必为已启用规则
        remind_num = 0
        sheet_info.sort(key=lambda x: x['value1'], reverse=True)
        regular_model = self.parameters.regular_model[step]
        for regular_code in regular_model:  # excel 中 step 表开启的规则
            regular_info = regular_model.get(regular_code)  # 规则导出列表信息
            if regular_info.get('status') == '启用':
                remind_num += 1
            else:
                continue
            if regular_code not in res_tmp:  # 规则启用且没有提醒过
                if (regular_name and regular_info.get('regular_classify') in regular_name) or not regular_name:  # 规则名称
                    sheet_info.append({'code': regular_code,
                                       'regular_name': regular_info.get('regular_classify'),
                                       'regular_details': regular_info.get('regular_details'),
                                       'value1': 0,
                                       'value2': 0})
        result = dict()
        result['sheet_info'] = sheet_info
        result['remind_num'] = remind_num
        result['pat_num'] = len(query_id)
        return result

    def chooseRecordName(self, record='', step='医生端'):
        """
        配置文件中运行的规则所选文书名称
        """
        result = dict()
        record_name = list()
        regular_name = list()
        regular_model = self.parameters.regular_model[step]
        for regular_code, value in regular_model.items():
            if value.get('status') != '启用':
                continue
            if not value.get('record_name'):
                continue
            name = value.get('record_name')
            if name not in record_name:
                record_name.append(name)
            if not value.get('regular_classify'):
                continue
            regular_classify = value.get('regular_classify')
            if regular_classify in regular_name:
                continue
            if (record and name == record) or not record:
                regular_name.append(regular_classify)
        result['record_name'] = record_name
        result['record_name'].insert(0, '全部')
        result['regular_name'] = regular_name
        result['regular_name'].insert(0, '全部')
        return result

    def record_to_regular(self, record='', step='医生端'):
        """
        文书名称所包含的规则名称
        """
        result = dict()
        regular_model = self.parameters.regular_model[step]
        for regular_code, value in regular_model.items():  # 从 regular_model.xlsx 中读取文书名称及规则名称
            if value.get('status') != '启用':
                continue
            if not value.get('record_name'):
                continue
            name = value.get('record_name')
            if record and record != name:
                continue
            # 获取文书名称
            # 文书名称作为 key 值
            result.setdefault(name, list())
            if not value.get('regular_classify'):
                continue
            regular_classify = value.get('regular_classify')
            if regular_classify not in result[name]:
                result[name].append(regular_classify)
        return result

    def code_to_regular(self, code='', step='医生端'):
        """
        规则代码所对应的规则名称
        """
        result = dict()
        regular_model = self.parameters.regular_model[step]
        for regular_code, value in regular_model.items():  # 从 regular_model.xlsx 中读取文书名称及规则名称
            # 获取文书名称
            if code and code != regular_code:
                continue
            if not value.get('regular_classify'):
                continue
            result[regular_code] = value.get('regular_classify')
        return result

    def code_to_record(self, code='', step='医生端'):
        """
        规则代码对应的文书名称
        """
        result = dict()
        regular_model = self.parameters.regular_model[step]
        for regular_code, value in regular_model.items():  # 从 regular_model.xlsx 中读取文书名称及规则名称
            # 获取文书名称
            if not value.get('record_name'):
                continue
            if code and regular_code != code:
                continue
            name = value.get('record_name')
            result[regular_code] = name
        return result

    def ward_to_code(self, ward_name):
        ward_code = ''
        if ward_name:
            if ward_name not in self.dept_dict:
                if ward_name in self.dept_dict.values():
                    for k, v in self.dept_dict.items():
                        if v == ward_name:
                            ward_code = k
                            break
            else:
                ward_code = ward_name
        return ward_code

    def recordModifySort(self, ward_name='', in_hospital=True):
        """
        文书问题修改频次排行
        """
        result = dict()
        search_field = dict()
        query_id = set()
        if ward_name == '全部' or ward_name == '医务处':
            for one_ward_name in self.ward_dept:
                ward_code = self.ward_to_code(one_ward_name)
                query_web = self.inHospitalPat(in_hospital=in_hospital, ward_code=ward_code)
                query_id.update(set(query_web.keys()))
        elif ward_name in self.ward_dept.values():
            for one_ward_name, dept in self.ward_dept.items():
                if ward_name == dept:
                    ward_code = self.ward_to_code(one_ward_name)
                    query_web = self.inHospitalPat(in_hospital=in_hospital, ward_code=ward_code)
                    query_id.update(set(query_web.keys()))
        else:
            ward_code = self.ward_to_code(ward_name)
            query_web = self.inHospitalPat(in_hospital=in_hospital, ward_code=ward_code)  # 获取在院或出院病人id号
            query_id = list(query_web.keys())
        total = len(query_id)
        conn = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                       collection_name=self.collection_name_doctor)
        if ward_name in self.ward_dept:
            if in_hospital:
                search_field = {'pat_info.district_admission_to_name': ward_name}
            else:
                search_field = {'pat_info.district_discharge_from_name': ward_name}
        elif ward_name in self.ward_dept.values():
            if in_hospital:
                search_field = {'pat_info.dept_admission_to_name': ward_name}
            else:
                search_field = {'pat_info.dept_discharge_from_name': ward_name}
        query_id = list(query_id)
        search_field['_id'] = {'$in': query_id}  # 在院/出院患者
        mongo_result = conn.find(search_field, {'_id': 0, 'increase_code': 1, 'decrease_code': 1}).batch_size(500)
        for data in mongo_result:
            tmp = dict()
            increase_code = data.get('increase_code', dict())
            decrease_code = data.get('decrease_code', dict())
            for code, value in increase_code.items():
                record_name = self.code_to_record(code).get(code, '')
                if value:
                    modify = 1
                else:
                    modify = 0
                if record_name:
                    tmp.setdefault(record_name, 0)
                    tmp[record_name] += modify
            for code, value in decrease_code.items():
                record_name = self.code_to_record(code).get(code, '')
                if value:
                    modify = 1
                else:
                    modify = 0
                if record_name:
                    tmp.setdefault(record_name, 0)
                    tmp[record_name] += modify
            for k, v in tmp.items():
                result.setdefault(k, dict())
                result[k].setdefault('modified', 0)
                result[k].setdefault('not_modified', 0)
                result[k].setdefault('num', 0)
                if v:
                    result[k]['modified'] += 1
                else:
                    result[k]['not_modified'] += 1
                result[k]['num'] += 1
        result_list = [{'record_name': k,
                        'modified': v['modified'],
                        'not_modified': v['not_modified'],
                        'total_num': total,  # 科室患者总数————电子病历服务器接口
                        'ratio': round(v['modified']/v['num'], 3)} for k, v in result.items()]
        result_list.sort(key=lambda x: x['ratio'], reverse=True)
        return result_list

    def freqHeatMap(self, record_name='', ward_name='', in_hospital=True):
        """
        热度图
        """
        result = dict()
        if not record_name:
            return result
        conn = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                       collection_name=self.collection_name_doctor)
        code_list = [k for k, value in self.code_to_record(step='医生端').items() if value == record_name]
        code_to_regular = dict()
        for i in code_list:
            code_to_regular.update(self.code_to_regular(i))
        if ward_name in self.ward_dept:
            if in_hospital:
                search_field = {'pat_info.district_admission_to_name': ward_name}
            else:
                search_field = {'pat_info.district_discharge_from_name': ward_name}
        elif ward_name in self.ward_dept.values():
            if in_hospital:
                search_field = {'pat_info.dept_admission_to_name': ward_name}
            else:
                search_field = {'pat_info.dept_discharge_from_name': ward_name}
        else:
            search_field = dict()
        query_id = set()
        if ward_name == '全部' or ward_name == '医务处':
            for one_ward_name in self.ward_dept:
                ward_code = self.ward_to_code(one_ward_name)
                query_web = self.inHospitalPat(in_hospital=in_hospital, ward_code=ward_code)
                query_id.update(set(query_web.keys()))
        elif ward_name in self.ward_dept.values():
            for one_ward_name, dept in self.ward_dept.items():
                if ward_name == dept:
                    ward_code = self.ward_to_code(one_ward_name)
                    query_web = self.inHospitalPat(in_hospital=in_hospital, ward_code=ward_code)
                    query_id.update(set(query_web.keys()))
        else:
            ward_code = self.ward_to_code(ward_name)
            query_web = self.inHospitalPat(in_hospital=in_hospital, ward_code=ward_code)  # 获取在院或出院病人id号
            query_id = list(query_web.keys())
        query_id = list(query_id)
        search_field['_id'] = {'$in': query_id}  # 在院/出院患者
        mongo_result = conn.find(search_field, {'_id': 0, 'increase_code': 1, 'decrease_code': 1, 'code_list': 1}).batch_size(500)
        tmp = dict()  # 修改计数
        tmp_total = dict()
        for data in mongo_result:
            if 'code_list' in data:
                for c in data['code_list']:
                    if c in code_to_regular:
                        tmp_total.setdefault(code_to_regular[c], 0)
                        tmp_total[code_to_regular[c]] += 1  # 分类问题数 +1
            increase_code = data.get('increase_code', dict())
            decrease_code = data.get('decrease_code', dict())
            for code, value in increase_code.items():
                if code in code_to_regular:
                    tmp.setdefault(code_to_regular[code], 0)
                    tmp[code_to_regular[code]] += value
            for code, value in decrease_code.items():
                if code in code_to_regular:
                    tmp.setdefault(code_to_regular[code], 0)
                    tmp[code_to_regular[code]] += value
        res_list = sorted(tmp.items(), key=lambda x: x[1], reverse=True)
        value = list()
        result['regular_name'] = [v[0] for v in res_list]
        axis_set = set()
        for r in tmp:
            axis_set.add(tmp_total[r])
        axis_x = sorted(axis_set)
        result['axis_x'] = axis_x
        for k, v in enumerate(res_list):
            value.append([axis_x.index(tmp_total[v[0]]), k, v[1]])
        result['value'] = value
        return result

    def regularModifySort(self, ward_name='', record_name='', regular_name='', in_hospital=True):
        """
        规则修改排行
        每个医生，每个规则修改了多少次
        左侧改为规则名称 1129
        """
        result = dict()
        search_field = dict()
        doctor_list = list()  # 调用少林接口获取医生列表
        web_service = Client(self.mr_client_url)
        if in_hospital:
            if not self.hospitalServerInfo.inhospital_pat_num:
                mr_data = web_service.service.EmrInHospitalPatNum()
                mr_data = json.loads(mr_data)
                self.hospitalServerInfo.inhospital_pat_num = mr_data
                doc_total = mr_data.get('DOC_TOTAL', list())  # 医生病人数
            else:
                doc_total = self.hospitalServerInfo.inhospital_pat_num.get('DOC_TOTAL', list())
            for data in doc_total:
                if ward_name == '全部' or ward_name == '医务处' or data['DEPT_NAME'] == ward_name or self.ward_dept.get(data['DEPT_NAME']) == ward_name:
                    if 'USER_NAME' in data:
                        doctor_list.append(data['USER_NAME'])
        else:
            if not self.hospitalServerInfo.discharge_pat_num:
                mr_data = web_service.service.EmrOutHospitalPatNum()
                mr_data = json.loads(mr_data)
                self.hospitalServerInfo.discharge_pat_num = mr_data
                doc_total = mr_data.get('DOC_TOTAL', list())
            else:
                doc_total = self.hospitalServerInfo.discharge_pat_num.get('DOC_TOTAL', list())
            for data in doc_total:
                if ward_name == '全部' or ward_name == '医务处' or data['DEPT_DISCHARGE_FROM_NAME'] == ward_name or self.ward_dept.get(data['DEPT_DISCHARGE_FROM_NAME']) == ward_name:
                    if 'DOCTOR_IN_CHARGE' in data:
                        doctor_list.append(data['DOCTOR_IN_CHARGE'])
        conn = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                       collection_name=self.collection_name_doctor)
        show_field = {'doctor_value_list.code': 1, 'doctor_value_list.creator_name': 1, 'doctor_value_list.name': 1}
        code_list = [k for k, value in self.code_to_record(step='医生端').items() if value == record_name or (not record_name)]
        code_to_regular = dict()
        for i in code_list:
            code_to_regular.update(self.code_to_regular(i))
        mongo_result = conn.find(search_field, show_field).batch_size(500)
        tmp = dict()
        for data in mongo_result:
            last_dict = dict()  # {医生姓名: 错误规则代码集合}
            for value in data['doctor_value_list']:
                # 第几次质控
                this_doctor = value[0].get('creator_name', 'x')  # todo 上多文书后改成doctor_name
                test_flag = self.isTestAccount(this_doctor)
                if test_flag:
                    continue

                doctor_name = value[0].get('creator_name')
                if not doctor_name:  # 没有医生姓名也跳过
                    continue

                if doctor_name not in doctor_list:  # 不在少林给的医生列表中的医生不统计
                    continue

                if doctor_name not in last_dict:  # 该医生不存在上一次质控记录
                    last_dict[doctor_name] = set([v['code'] for v in value if 'code' in v])
                    continue

                this_code = set([v['code'] for v in value if 'code' in v])  # 该医生本次质控记录
                if this_code == last_dict[doctor_name]:  # 无修改
                    continue
                else:
                    diff_code = last_dict[doctor_name].difference(this_code) | this_code.difference(last_dict[doctor_name])  # 上次与本次不同的规则码
                    for c in diff_code:
                        if regular_name:
                            if self.code_to_regular(c).get(c) != regular_name:
                                continue
                        key_regular = self.code_to_regular(c).get(c)
                        tmp.setdefault(key_regular, dict())
                        for one_doctor in doctor_list:
                            if one_doctor not in tmp[key_regular]:
                                tmp[key_regular][one_doctor] = 0
                        tmp[key_regular][doctor_name] += 1
                    last_dict[doctor_name] = this_code
        for k, v in tmp.items():  # tmp = {规则名称：{医生姓名：次数}}
            result.setdefault(k, dict())
            result[k]['total_num'] = sum(v.values())
            temp = sorted(v.items(), key=lambda x: x[0], reverse=True)  # 按医生姓名排序
            result[k]['doctor'] = [value[0] for value in temp]
            result[k]['num'] = [value[1] for value in temp]
        result = dict(sorted(result.items(), key=lambda x: x[1]['total_num'], reverse=True))
        return result

    def getPatientInfo(self, status_bool='all', dept_name='', show_num=10, page_num=0, patient_id='', visit_id='', name='', details='', record='', category='', isResult=False, in_hospital=True):
        """
        todo 环节质控列表展示
        只展示最后一次的质控结果
        问题条数：历史问题数
        修改数：修改条数
        未修改数：未修改条数
        dept_code: 病区名称或病区代码
        """
        collection = self.mongo_pull_utils.connection(collection_name=self.collection_name_huanjie)
        # collection_click = self.mongo_pull_utils.connection(collection_name=self.collection_name_doctor+'_click')
        result = dict()
        query_field = dict()
        # 获取全部分类的患者信息
        # todo 临时注释
        # query_id = set()
        # query_web = dict()
        # if ward_name == '全部' or ward_name == '医务处':
        #     for one_ward_name in self.ward_dept:
        #         ward_code = self.ward_to_code(one_ward_name)
        #         query_web = self.inHospitalPat(in_hospital=in_hospital, ward_code=ward_code)
        #         query_id.update(set(query_web.keys()))
        # elif ward_name in self.ward_dept.values():
        #     for one_ward_name, dept in self.ward_dept.items():
        #         if ward_name == dept:
        #             ward_code = self.ward_to_code(one_ward_name)
        #             query_web = self.inHospitalPat(in_hospital=in_hospital, ward_code=ward_code)
        #             query_id.update(set(query_web.keys()))
        # else:
        #     ward_code = self.ward_to_code(ward_name)
        #     query_web = self.inHospitalPat(in_hospital=in_hospital, ward_code=ward_code)  # 获取在院或出院病人id号
        #     query_id = list(query_web.keys())
        # query_id = list(query_id)
        # query_field['_id'] = {'$in': query_id}
        # 获取全部分类的患者信息
        if isResult != 'all':
            if isResult:
                # 是问题病历
                query_field['$or'] = [{'pat_info.machine_score': {'$ne': 0}}, {'pat_info.artificial_score': {'$ne': 0}}]
            else:
                # 不是问题病历
                query_field['pat_info.machine_score'] = 0
                query_field['pat_info.artificial_score'] = 0
        if status_bool == 'all':
            status_bool = {'$in': [True, False]}
        elif status_bool == 'zero':
            status_bool = True
            query_field['del_value'] = {'$size': {'$ne': 0}}
            query_field['pat_info.machine_score'] = 0
            query_field['pat_info.artificial_score'] = 0
        query_field['status'] = status_bool
        if in_hospital:
            query_field['pat_info.discharge_time'] = ''
        else:
            query_field['pat_info.discharge_time'] = {'$gt': ''}
        if dept_name:
            if in_hospital:
                query_field['pat_info.dept_admission_to_name'] = dept_name
            else:
                query_field['pat_info.dept_discharge_from_name'] = dept_name
        if patient_id and visit_id:
            query_field['_id'] = '{}#{}#{}'.format(patient_id, visit_id, self.hospital_code)
        else:
            if patient_id:
                query_field['pat_info.patient_id'] = patient_id
            if visit_id:
                query_field['pat_info.visit_id'] = visit_id
        if name:
            query_field['pat_value.name'] = name
        if details:
            query_field['pat_value.regular_details'] = details
        if isinstance(show_num, str):
            try:
                show_num = int(show_num)
            except:
                show_num = 10
        if isinstance(page_num, str):
            try:
                page_num = int(page_num)
            except:
                page_num = 0
        if record:
            query_field['pat_value.record_name'] = record
        if category and category != 'all':
            query_field['pat_category.{}'.format(category)] = True
        pipeline = [
                    {'$project': {'pat_value': {'$slice': ['$doctor_value_list', -1, 1]},
                                  'pat_info': 1,
                                  'content': 1,
                                  'doctor_name': 1,
                                  'doctor_id': 1,
                                  'doctor_dept': 1,
                                  'status': 1,
                                  'pat_category': 1,
                                  'del_value.code': 1,
                                  'code_list': 1,
                                  'modify_num': 1,
                                  'control_date': 1}},  # 查看是否修改
                    {'$unwind': '$pat_value'},
                    {'$match': query_field},
                    {'$sort': {'_id': 1}},
                    {'$skip': page_num*show_num},
                    {'$limit': show_num}
        ]
        query_result = collection.aggregate(pipeline, allowDiskUse=True)
        count_result = collection.aggregate([{'$project': {'pat_value': {'$slice': ['$doctor_value_list', -1, 1]},
                                                           'pat_info': 1,
                                                           'content': 1,
                                                           'doctor_name': 1,
                                                           'doctor_id': 1,
                                                           'doctor_dept': 1,
                                                           'status': 1,
                                                           'pat_category': 1,
                                                           'del_value.code': 1,
                                                           'code_list': 1,
                                                           'modify_num': 1,
                                                           'control_date': 1}},  # 查看是否修改
                                             {'$unwind': '$pat_value'},
                                             {'$match': query_field},
                                             {'$group': {'_id': True, 'value': {"$sum": 1}}}], allowDiskUse=True)
        for data in count_result:
            result['count'] = data.get('value', 0)
        result['page_num'] = page_num
        result['show_num'] = show_num
        result['info'] = list()
        for data_index, data_value in enumerate(query_result):
            data_value.setdefault('doctor_name', '')
            if data_value.get('transmit_code'):
                data_value['transmit_flag'] = True
            else:
                data_value['transmit_flag'] = False
            del_code = [value['code'] for value in data_value.get('del_value', list()) if 'code' in value]
            pat_value = list()
            for one_value in data_value.get('pat_value', list()):
                code = one_value.get('code')
                if code:
                    if code not in del_code:
                        if code in data_value.get('transmit_code', list()):
                            one_value['transmit_flag'] = True
                        else:
                            one_value['transmit_flag'] = False
                        pat_value.append(one_value)
                    continue
                pat_value.append(one_value)
            data_value['pat_value'] = pat_value
            data_value['problem_num'] = len(data_value.get('content', list())) + len(pat_value)  # 问题条数
            # # 点击数
            # data_value['click_count'] = 0
            # data_value['click_icon'] = 0
            # click_result = collection_click.find_one({'_id': data_value['pat_info']['patient_id']})
            # if click_result:
            #     if click_result.get('visit_id') == data_value['pat_info']['visit_id']:
            #         if data_value['pat_value'][0].get('doctor_name', '') and data_value['pat_value'][0].get('doctor_id', ''):
            #
            #             doctor_key = '{}#{}'.format(data_value['pat_value'][0].get('doctor_name', ''), data_value['pat_value'][0]['doctor_id'])
            #
            #             if doctor_key in click_result.get('click_info', dict()):
            #                 data_value['click_count'] = click_result['click_info'][doctor_key]
            #             if doctor_key in click_result.get('click_info_icon', dict()):
            #                 data_value['click_icon'] = click_result['click_info_icon'][doctor_key]
            result['info'].append(data_value)
        return result

    def getClickCount(self, patient_id, visit_id, doctor_name, doctor_id, loc=False):
        """
        点击计数
        """
        if not patient_id:
            return {'res_flag': False, 'error_info': 'No patient id...'}
        if not visit_id:
            return {'res_flag': False, 'error_info': 'No visit id...'}
        if not doctor_name:
            return {'res_flag': False, 'error_info': 'No doctor name...'}
        if not doctor_id:
            return {'res_flag': False, 'error_info': 'No doctor id...'}
        if loc:
            key = 'click_info_icon'
        else:
            key = 'click_info'
        inc_key = '{}.{}#{}'.format(key, doctor_name, doctor_id)
        conn_click = self.mongo_push_utils.connectCollection(database_name=self.database_name,
                                                             collection_name=self.collection_name_doctor+'_click')
        if conn_click.find_one({'_id': patient_id, 'visit_id': visit_id}, {}):
            result = conn_click.update({'_id': patient_id}, {"$inc": {inc_key: 1}}, upsert=True)
            if result and isinstance(result, dict) and 'updatedExisting' in result:
                return {'res_flag': True}
            else:
                return {'res_flag': False, 'error_info': 'update failed'}
        else:
            if loc:
                push_data = {'_id': patient_id,
                             'visit_id': visit_id,
                             'click_info': {},
                             key: {'{}#{}'.format(doctor_name, doctor_id): 1}}
            else:
                push_data = {'_id': patient_id,
                             'visit_id': visit_id,
                             'click_info_icon': {},
                             key: {'{}#{}'.format(doctor_name, doctor_id): 1}}
            result = self.run_regular.PushData.pushData(self.collection_name_doctor+'_click', push_data)
            if result:
                return {'res_flag': result}
            else:
                return {'res_flag': result, 'error_info': 'push data failed'}

    def getHuanjiePatientHtmlList(self, data_id):
        id_tmp = data_id.split('#')[:3]
        record_id = '{}#{}#{}'.format(id_tmp[2], id_tmp[0], id_tmp[1])
        conn = self.mongo_pull_utils.record_db.get_collection(name='binganshouye')
        bingan_data = conn.find_one({'_id': record_id}, {'binganshouye.pat_visit.mr_doctor_papt_status': 1}) or dict()
        # 3是签收，0是未签收，6是编目
        papt_status = bingan_data.get('binganshouye', dict()).get('pat_visit', dict()).get('mr_doctor_papt_status', '')
        papt_flag = False
        if papt_status == '0':
            papt_flag = True
        result = dict()
        for one_html in self.conf_dict['html_english_chinese']:
            if one_html in ['shouyezhenduan', 'shouyeshoushu', 'hulitizhengyangli']:
                continue
            else:
                collection_name = 'mrq_' + one_html
                if not papt_flag:
                    # 非未签收的，先看mrq表，再看春光表
                    conn = self.mongo_pull_utils.record_db.get_collection(name=collection_name)
                    if conn.find_one({'_id': record_id}, {}):
                        result[collection_name] = self.conf_dict['html_english_chinese'][one_html]
                    else:
                        conn = self.mongo_pull_utils.record_db.get_collection(name=one_html)
                        if conn.find_one({'_id': record_id}, {}):
                            result[one_html] = self.conf_dict['html_english_chinese'][one_html]
                else:
                    # 未签收的，先看春光表，再看mrq表
                    conn = self.mongo_pull_utils.record_db.get_collection(name=one_html)
                    if conn.find_one({'_id': record_id}, {}):
                        result[one_html] = self.conf_dict['html_english_chinese'][one_html]
                    else:
                        conn = self.mongo_pull_utils.record_db.get_collection(name=collection_name)
                        if conn.find_one({'_id': record_id}, {}):
                            result[collection_name] = self.conf_dict['html_english_chinese'][one_html]
        return result

    def getHuanjiePatientHtml(self, data_id, record_name=''):
        if not record_name:
            return {'res_flag': False, 'info': 'record_name is [{}]'.format(record_name)}
        id_tmp = data_id.split('#')[:3]
        record_id = '#'.join([id_tmp[2]]+id_tmp[0:2])
        query_field = {'_id': record_id}
        result = dict()
        result['html'] = OrderedDict()
        result['regular_name'] = list(set([regular_name['regular_classify'] for regular_name in self.regular_model.values() if regular_name.get('regular_classify')]))
        collection_name = record_name
        record_name = record_name if not record_name.startswith('mrq_') else record_name.replace('mrq_', '')
        if record_name == 'binganshouye':
            conn = self.mongo_pull_utils.record_db.get_collection(name=collection_name)
            if collection_name.startswith('mrq_'):
                conn_shouyeshoushu = self.mongo_pull_utils.record_db.get_collection(name='mrq_shouyeshoushu')
                conn_shouyezhenduan = self.mongo_pull_utils.record_db.get_collection(name='mrq_shouyezhenduan')
            else:
                conn_shouyeshoushu = self.mongo_pull_utils.record_db.get_collection(name='shouyeshoushu')
                conn_shouyezhenduan = self.mongo_pull_utils.record_db.get_collection(name='shouyezhenduan')
            query_result = conn.find_one(query_field) or dict()
            result_shouyeshoushu = conn_shouyeshoushu.find_one(query_field) or dict()
            result_shouyezhenduan = conn_shouyezhenduan.find_one(query_field) or dict()
            binganshouye = query_result.get('binganshouye', dict())
            shouyeshoushu = result_shouyeshoushu.get('shouyeshoushu', list())
            shouyezhenduan = result_shouyezhenduan.get('shouyezhenduan', list())
            binganshouye['shouyeshoushu'] = shouyeshoushu
            binganshouye['shouyezhenduan'] = list()
            for one_record in shouyezhenduan:
                if one_record.get('diagnosis_type_name') != '病理诊断':
                    binganshouye['shouyezhenduan'].append(one_record)
            result['html'][self.conf_dict['html_english_chinese'][record_name]] = [binganshouye]
        else:
            if record_name in ['yizhu', 'jianchabaogao', 'jianyanbaogao']:
                collection = self.mongo_pull_utils.record_db.get_collection(name=record_name)
                query_result = collection.find_one(query_field) or dict()
            else:
                collection_src_name = collection_name + '_src'
                collection = self.mongo_pull_utils.record_db.get_collection(name=collection_src_name)
                query_result = collection.find_one(query_field) or dict()
            if not query_result.get(record_name):
                return result
            if record_name == 'yizhu':
                result['html']['医嘱'] = self.processYizhuHtml(query_result)
                return result
            elif record_name == 'jianchabaogao':
                result['html']['检查报告'] = self.processJianchaHtml(query_result)
                return result
            elif record_name == 'jianyanbaogao':
                result['html']['检验报告'] = self.processJianyanHtml(query_result)
                return result
            html_tmp = list()
            for one_data in query_result[record_name]:
                html = one_data.get('MR_CONTENT_HTML', '') or one_data.get('mr_content_html', '')
                if not html:
                    continue
                caption_time = one_data.get('CAPTION_DATE_TIME', '') or one_data.get('caption_date_time', '')
                file_unique_id = one_data.get('FILE_UNIQUE_ID', '') or one_data.get('file_unique_id', '')
                html_tmp.append({'html': html, 'time': caption_time, 'file_unique_id': file_unique_id})
            if not html_tmp:
                return result
            html_tmp.sort(key=lambda x: x['time'])
            record_cn = self.conf_dict['html_english_chinese'][record_name]
            result['html'][record_cn] = list()
            for n, data in enumerate(html_tmp):
                data.update({'num': n, 'title': record_cn})
                result['html'][record_cn].append(data)
        return result

    @staticmethod
    def processYizhuHtml(query_result):
        """
        处理医嘱原文展示
        住院医嘱：医嘱类别名称、医嘱项名称、医嘱开始时间、医嘱结束时间、执行频次名称、持续时间值、持续时间单位、用药剂量、用药剂量单位、给药途径和方法/用途、出院带药标识
        result['html']['医嘱'] = {'类别1': [], '类别2': []}
        按医嘱开始时间排序分类
        """
        result = dict()
        for one_data in query_result.get('yizhu', list()):
            class_name = one_data.get('order_class_name')
            if not class_name:
                continue
            item_name = one_data.get('order_item_name')
            if not item_name:
                continue
            result.setdefault(class_name, list())
            result[class_name].append({
                'order_item_name': item_name,
                'order_class_name': one_data.get('order_class_name', ''),
                'order_properties_name': one_data.get('order_properties_name', ''),
                'order_begin_time': one_data.get('order_begin_time', ''),
                'order_end_time': one_data.get('order_end_time', ''),
                'frequency_name': one_data.get('frequency_name', ''),
                'duration_value': one_data.get('duration_value', ''),
                'duration_unit': one_data.get('duration_unit', ''),
                'dosage_value': one_data.get('dosage_value', ''),
                'dosage_value_unit': one_data.get('dosage_value_unit', ''),
                'pharmacy_way_name': one_data.get('pharmacy_way_name', ''),
                'discharge_medicine_indicator': one_data.get('discharge_medicine_indicator', ''),
            })
        result = dict(sorted(result.items(), key=lambda x: len(x[1]), reverse=True))
        for k, v in result.items():
            v.sort(key=lambda x: x['order_begin_time'])
        return result

    @staticmethod
    def processJianchaHtml(query_result):
        """
        检查报告：送检科室、报告回报时间、检查时间、检查类别名称、检查部位、检查类别细项、检查项目名称、检查所见、检查结论
        result['html']['检查报告'] = {'检查类别名称1': [], '检查类别名称2': []}
        """
        result = dict()
        jianyan_model = query_result.get('jianchabaogao', dict())
        for one_data in jianyan_model.get('exam_report', list()):
            exam_class_name = one_data.get('exam_class_name')
            if not exam_class_name:
                continue
            exam_sub_class = one_data.get('exam_sub_class', '')
            result.setdefault(exam_class_name, list())
            result[exam_class_name].append({
                'exam_sub_class': exam_sub_class,
                'apply_dept_name': one_data.get('apply_dept_name', ''),
                'exam_time': one_data.get('exam_time', ''),
                'exam_part': one_data.get('exam_part', ''),
                'exam_class_name': one_data.get('exam_class_name', ''),
                'exam_item_name': one_data.get('exam_item_name', ''),
                'exam_feature': one_data.get('exam_feature', ''),
                'exam_diag': one_data.get('exam_diag', ''),
            })
        result = dict(sorted(result.items(), key=lambda x: len(x[1])))
        for k, v in result.items():
            v.sort(key=lambda x: x['exam_time'])
        return result

    @staticmethod
    def processJianyanHtml(query_result):
        """
        检验报告：送检科室、标本类型、采样时间、报告时间、检验单名称、检验细项名称、检验定量结果值、检验定性结果、参考范围、检验定量结果值标志位
        result['html']['检验报告'] = {'检验项目1': [], '检验项目2': []}
        """
        result = dict()
        jianyan_model = query_result.get('jianyanbaogao', dict())
        for one_data in jianyan_model.get('lab_report', list()):
            lab_item_name = one_data.get('report_no', '')[:10] + one_data.get('lab_item_name', '')
            if not lab_item_name:
                continue
            lab_sub_item_name = one_data.get('lab_sub_item_name', '')
            result.setdefault(lab_item_name, list())
            result[lab_item_name].append({
                'lab_sub_item_name': lab_sub_item_name,
                'department': one_data.get('department', ''),
                'lab_item_name': one_data.get('lab_item_name', ''),
                'specimen': one_data.get('specimen', ''),
                'sample_time': one_data.get('sample_time', ''),
                'report_time': one_data.get('report_time', ''),
                'lab_result_value': one_data.get('lab_result_value', ''),
                'lab_qual_result': one_data.get('lab_qual_result', ''),
                'range': one_data.get('range', ''),
                'lab_result_value_indicator': one_data.get('lab_result_value_indicator', ''),
            })
        result = dict(sorted(result.items(), key=lambda x: x[0]))
        for k, v in result.items():
            v.sort(key=lambda x: x['sample_time'])
        return result

    def statisticDept(self, ward_name='', in_hospital=True):
        """
        统计各个科室问题病历数
        """
        ward_code = self.ward_to_code(ward_name)
        result = dict()
        match_field = dict()
        if in_hospital:
            query_field = {'_id': '$pat_info.district_admission_to_name', 'value': {"$sum": 1}}  # 在院
            if ward_name:
                match_field = {'pat_info.district_admission_to_name': ward_name}
        else:
            query_field = {'_id': '$pat_info.district_discharge_from_name', 'value': {"$sum": 1}}  # 出院
            if ward_name:
                match_field = {'pat_info.district_discharge_from_name': ward_name}
        match_field['doctor_value.code'] = {'$exists': True}
        match_field['pat_info.district_discharge_from_name'] = {'$ne': None}  # 出院病区不能为空
        query_web = self.inHospitalPat(in_hospital=in_hospital, ward_code=ward_code)
        query_id = list(query_web.keys())
        match_field['_id'] = {'$in': query_id}
        collection = self.mongo_pull_utils.connection(collection_name=self.collection_name_doctor)
        pipeline = [
                    {'$project': {'doctor_value': {'$slice': ['$doctor_value_list', -1, 1]},
                                  'pat_info': 1,
                                  'modify_num': 1}},
                    {'$unwind': '$doctor_value'},
                    {'$match': match_field},
                    {'$group': query_field},
        ]
        mongo_result = collection.aggregate(pipeline, allowDiskUse=True)
        for data in mongo_result:
            value = data.get('value')
            if not value:
                continue
            result.setdefault(data['_id'], 0)
            result[data['_id']] += value
        result_sort = dict(sorted(result.items(), key=lambda x: x[1], reverse=True))
        return result_sort

    @staticmethod
    def getDoctorInfo(doctor_json):
        if isinstance(doctor_json, dict):
            doctor_id = doctor_json.get('doctor_id', '')
            doctor_name = doctor_json.get('doctor_name', '')
            doctor_dept = doctor_json.get('doctor_dept', '')
            doctor_district = doctor_json.get('doctor_district', '')
            if doctor_id and doctor_name and doctor_dept and doctor_district:
                return {'status': True}
            else:
                return {'status': False,
                        'doctor_id': doctor_id,
                        'doctor_name': doctor_name,
                        'doctor_dept': doctor_dept,
                        'doctor_district': doctor_district}
        else:
            return {'status': False,
                    'message': 'no json file...'}

    def doctorWorkStat(self, ward_name='', in_hospital=True):
        """
        医生工作列表
        """
        result = dict()
        if not ward_name:
            return {}
        conn = self.mongo_pull_utils.connection(collection_name=self.collection_name_doctor)
        web_service = Client(self.mr_client_url)
        doctor_pat = dict()
        if in_hospital:
            if not self.hospitalServerInfo.inhospital_pat_num:
                mr_data = web_service.service.EmrInHospitalPatNum()
                mr_data = json.loads(mr_data)
                self.hospitalServerInfo.inhospital_pat_num = mr_data
                doc_total = mr_data.get('DOC_TOTAL', list())  # 医生病人数
            else:
                doc_total = self.hospitalServerInfo.inhospital_pat_num.get('DOC_TOTAL', list())
            for data in doc_total:
                if ward_name == '全部' or ward_name == '医务处' or data['DEPT_NAME'] == ward_name or self.ward_dept.get(data['DEPT_NAME']) == ward_name:
                    result.setdefault(data['USER_ID'], dict())  # {医生ID：{doctor_name：名称，ward：病区，pat_num：病人数}}
                    result[data['USER_ID']]['doctor_name'] = data['USER_NAME']
                    result[data['USER_ID']]['ward'] = data['DEPT_NAME']
                    result[data['USER_ID']].setdefault('pat_num', 0)
                    result[data['USER_ID']]['pat_num'] += float(data['DOC_NUM'])
                    result[data['USER_ID']].setdefault('record_num', 0)
                    result[data['USER_ID']].setdefault('modify_num', 0)
                    result[data['USER_ID']].setdefault('patient_mrq_num', 0)
            patient_info = list()
            if ward_name == '全部' or ward_name == '医务处':
                for one_ward_name in self.ward_dept:
                    ward_code = self.ward_to_code(one_ward_name)
                    if not self.hospitalServerInfo.inhospital_pat_data.get(ward_code, dict()):
                        mr_data = web_service.service.EmrInHospitalData(ward_code)
                        mr_data = json.loads(mr_data)
                        self.hospitalServerInfo.inhospital_pat_data[ward_code] = mr_data
                        patient_info += mr_data.get('INHOSPITAL_PATIENT_INFO', list())
                    else:
                        patient_info += self.hospitalServerInfo.inhospital_pat_data[ward_code].get('INHOSPITAL_PATIENT_INFO', list())
            elif ward_name in self.ward_dept.values():
                for one_ward_name, dept in self.ward_dept.items():
                    if ward_name == dept:
                        ward_code = self.ward_to_code(one_ward_name)
                        if not self.hospitalServerInfo.inhospital_pat_data.get(ward_code, dict()):
                            mr_data = web_service.service.EmrInHospitalData(ward_code)
                            mr_data = json.loads(mr_data)
                            self.hospitalServerInfo.inhospital_pat_data[ward_code] = mr_data
                            patient_info += mr_data.get('INHOSPITAL_PATIENT_INFO', list())
                        else:
                            patient_info += self.hospitalServerInfo.inhospital_pat_data[ward_code].get('INHOSPITAL_PATIENT_INFO', list())
            else:
                ward_code = self.ward_to_code(ward_name)
                if not self.hospitalServerInfo.inhospital_pat_data.get(ward_code, dict()):
                    mr_data = web_service.service.EmrInHospitalData(ward_code)
                    mr_data = json.loads(mr_data)
                    self.hospitalServerInfo.inhospital_pat_data[ward_code] = mr_data
                    patient_info += mr_data.get('INHOSPITAL_PATIENT_INFO', list())
                else:
                    patient_info += self.hospitalServerInfo.inhospital_pat_data[ward_code].get('INHOSPITAL_PATIENT_INFO', list())
            for data in patient_info:
                patient = data.get('PATIENT_ID')
                visit = data.get('VISIT_ID')
                doctor_id = data.get('REQUEST_USER_ID')
                if patient and visit:
                    key = patient + '#' + visit + '#' + self.hospital_code
                else:
                    continue
                if doctor_id:
                    if doctor_id not in result:
                        continue
                    doctor_pat.setdefault(doctor_id, set())
                    mongo_result = conn.find_one({'_id': key}, {'code_list': 1, 'modify_num': 1})
                    if not mongo_result:
                        continue
                    if len(mongo_result['code_list']) > 0:  # 有问题
                        if patient not in doctor_pat[doctor_id]:
                            result[doctor_id]['patient_mrq_num'] += 1  # 有问题患者数
                            doctor_pat[doctor_id].add(patient)
                        result[doctor_id]['record_num'] += 1  # 有问题病历数
                    if len(mongo_result['modify_num']) > 0:  # 有修改
                        result[doctor_id]['modify_num'] += 1  # 修改病历数
        else:
            if not self.hospitalServerInfo.discharge_pat_num:
                mr_data = web_service.service.EmrOutHospitalPatNum()
                mr_data = json.loads(mr_data)
                self.hospitalServerInfo.discharge_pat_num = mr_data
                doc_total = mr_data.get('DOC_TOTAL', list())
            else:
                doc_total = self.hospitalServerInfo.discharge_pat_num.get('DOC_TOTAL', list())
            for data in doc_total:
                if ward_name == '全部' or ward_name == '医务处' or data['DEPT_DISCHARGE_FROM_NAME'] == ward_name or self.ward_dept.get(data['DEPT_DISCHARGE_FROM_NAME']) == ward_name:
                    result.setdefault(data['DOCTOR_IN_CHARGE_ID'], dict())  # {医生ID：{doctor_name：名称，ward：病区，pat_num：病人数}}
                    result[data['DOCTOR_IN_CHARGE_ID']]['doctor_name'] = data['DOCTOR_IN_CHARGE']
                    result[data['DOCTOR_IN_CHARGE_ID']]['ward'] = data['DEPT_DISCHARGE_FROM_NAME']
                    result[data['DOCTOR_IN_CHARGE_ID']].setdefault('pat_num', 0)
                    result[data['DOCTOR_IN_CHARGE_ID']]['pat_num'] += float(data['DOC_TOTAL'])
                    result[data['DOCTOR_IN_CHARGE_ID']].setdefault('record_num', 0)
                    result[data['DOCTOR_IN_CHARGE_ID']].setdefault('modify_num', 0)
                    result[data['DOCTOR_IN_CHARGE_ID']].setdefault('patient_mrq_num', 0)
            patient_info = list()
            if ward_name == '全部' or ward_name == '医务处':
                for one_ward_name in self.ward_dept:
                    ward_code = self.ward_to_code(one_ward_name)
                    if not self.hospitalServerInfo.inhospital_pat_data.get(ward_code, dict()):
                        mr_data = web_service.service.EmrOutHospitalData(ward_code)
                        mr_data = json.loads(mr_data)
                        self.hospitalServerInfo.inhospital_pat_data[ward_code] = mr_data
                        patient_info += mr_data.get('DISCHARGE_PATIENT_INFO', list())
                    else:
                        patient_info += self.hospitalServerInfo.inhospital_pat_data[ward_code].get('DISCHARGE_PATIENT_INFO', list())
            elif ward_name in self.ward_dept.values():
                for one_ward_name, dept in self.ward_dept.items():
                    if ward_name == dept:
                        ward_code = self.ward_to_code(one_ward_name)
                        if not self.hospitalServerInfo.inhospital_pat_data.get(ward_code, dict()):
                            mr_data = web_service.service.EmrOutHospitalData(ward_code)
                            mr_data = json.loads(mr_data)
                            self.hospitalServerInfo.inhospital_pat_data[ward_code] = mr_data
                            patient_info += mr_data.get('DISCHARGE_PATIENT_INFO', list())
                        else:
                            patient_info += self.hospitalServerInfo.inhospital_pat_data[ward_code].get('DISCHARGE_PATIENT_INFO', list())
            else:
                ward_code = self.ward_to_code(ward_name)
                if not self.hospitalServerInfo.inhospital_pat_data.get(ward_code, dict()):
                    mr_data = web_service.service.EmrOutHospitalData(ward_code)
                    mr_data = json.loads(mr_data)
                    self.hospitalServerInfo.inhospital_pat_data[ward_code] = mr_data
                    patient_info += mr_data.get('DISCHARGE_PATIENT_INFO', list())
                else:
                    patient_info += self.hospitalServerInfo.inhospital_pat_data[ward_code].get('DISCHARGE_PATIENT_INFO', list())

            for data in patient_info:
                patient = data.get('PATIENT_ID')
                visit = data.get('VISIT_ID')
                doctor_id = data.get('REQUEST_USER_ID')
                if patient and visit:
                    key = patient + '#' + visit + '#' + self.hospital_code
                else:
                    continue
                if doctor_id:
                    if doctor_id not in result:
                        continue
                    doctor_pat.setdefault(doctor_id, set())
                    mongo_result = conn.find_one({'_id': key}, {'code_list': 1, 'modify_num': 1})
                    if not mongo_result:
                        continue
                    if len(mongo_result['code_list']) > 0:  # 有问题
                        if patient not in doctor_pat[doctor_id]:
                            result[doctor_id]['patient_mrq_num'] += 1  # 有问题患者数
                            doctor_pat[doctor_id].add(patient)
                        result[doctor_id]['record_num'] += 1  # 有问题病历数
                    if len(mongo_result['modify_num']) > 0:  # 有修改
                        result[doctor_id]['modify_num'] += 1  # 修改病历数
        return result

    def doctorModifySort(self, ward_name, in_hospital=True):
        """
        10.30原型图最后一张
        查看病区下有哪些医生，对医生规则修改情况进行统计
        """
        if not ward_name:
            return {}
        conn = self.mongo_pull_utils.connection(collection_name=self.collection_name_doctor)
        web_service = Client(self.mr_client_url)
        doctor_pat = dict()  # {医生: {规则1: {}}}
        if in_hospital:
            if not self.hospitalServerInfo.inhospital_pat_num:
                mr_data = web_service.service.EmrInHospitalPatNum()
                mr_data = json.loads(mr_data)
                self.hospitalServerInfo.inhospital_pat_num = mr_data
                doc_total = mr_data.get('DOC_TOTAL', list())  # 医生病人数
            else:
                doc_total = self.hospitalServerInfo.inhospital_pat_num.get('DOC_TOTAL', list())
            for data in doc_total:
                if ward_name == '全部' or ward_name == '医务处' or data['DEPT_NAME'] == ward_name or self.ward_dept.get(data['DEPT_NAME']) == ward_name:
                    doctor_pat.setdefault(data['USER_NAME'], dict())
        else:
            if not self.hospitalServerInfo.discharge_pat_num:
                mr_data = web_service.service.EmrOutHospitalPatNum()
                mr_data = json.loads(mr_data)
                self.hospitalServerInfo.discharge_pat_num = mr_data
                doc_total = mr_data.get('DOC_TOTAL', list())  # 医生病人数
            else:
                doc_total = self.hospitalServerInfo.discharge_pat_num.get('DOC_TOTAL', list())
            for data in doc_total:
                if ward_name == '全部' or ward_name == '医务处' or data['DEPT_DISCHARGE_FROM_NAME'] == ward_name or self.ward_dept.get(data['DEPT_DISCHARGE_FROM_NAME']) == ward_name:
                    doctor_pat.setdefault(data['DOCTOR_IN_CHARGE'], dict())
        query_id = set()
        if ward_name == '全部' or ward_name == '医务处':
            for one_ward_name in self.ward_dept:
                ward_code = self.ward_to_code(one_ward_name)
                query_web = self.inHospitalPat(in_hospital=in_hospital, ward_code=ward_code)
                query_id.update(set(query_web.keys()))
        elif ward_name in self.ward_dept.values():
            for one_ward_name, dept in self.ward_dept.items():
                if ward_name == dept:
                    ward_code = self.ward_to_code(one_ward_name)
                    query_web = self.inHospitalPat(in_hospital=in_hospital, ward_code=ward_code)
                    query_id.update(set(query_web.keys()))
        else:
            ward_code = self.ward_to_code(ward_name)
            query_web = self.inHospitalPat(in_hospital=in_hospital, ward_code=ward_code)  # 获取在院或出院病人id号
            query_id.update(set(query_web.keys()))
        query_id = list(query_id)
        query_field = {'_id': {'$in': query_id}}
        query_result = conn.find(query_field).batch_size(50)

        for data in query_result:
            tmp = dict()  # {医生: {modify: 修改的规则码-set, regular: 出过问题的规则码-set}}

            for doc_value in data['doctor_value_list']:
                if 'code' not in doc_value[0]:  # 本次质控的第一条结果
                    continue
                for value in doc_value:  # 遍历本次doc_value质控的每一条质控结果
                    creator_name = value.get('creator_name')  # todo 上多文书后改成doctor_name
                    if creator_name and creator_name in doctor_pat:
                        tmp.setdefault(creator_name, dict())
                        tmp[creator_name].setdefault('regular', set())
                        tmp[creator_name]['regular'].add(value['code'])

            if len(data.get('modify_num', list())) != 0:  # 如果有修改过
                for modify_num in data['modify_num']:
                    creator_name = data['doctor_value_list'][modify_num][0].get('creator_name')  # 看看修改者是谁
                    if creator_name and creator_name in doctor_pat:  # 修改者是该病区的医生
                        tmp.setdefault(creator_name, dict())
                        tmp[creator_name].setdefault('modify', set())
                        last_code = set([v['code'] for v in data['doctor_value_list'][modify_num-1] if 'code' in v])  # 上一次的code
                        this_code = set([v['code'] for v in data['doctor_value_list'][modify_num] if 'code' in v])  # 本次code
                        diff_code = last_code.difference(this_code) | this_code.difference(last_code)  # 修改的规则
                        tmp[creator_name]['modify'].update(diff_code)

            for creator_name, v in tmp.items():
                for kk, vv in v.items():
                    if kk == 'regular':
                        for code_name in vv:
                            regular_name = self.code_to_regular(code_name).get(code_name)
                            doctor_pat[creator_name].setdefault(regular_name, dict())
                            doctor_pat[creator_name][regular_name].setdefault('num', 0)
                            doctor_pat[creator_name][regular_name].setdefault('modify_num', 0)
                            doctor_pat[creator_name][regular_name]['num'] += 1
                    if kk == 'modify':
                        for code_name in vv:
                            regular_name = self.code_to_regular(code_name).get(code_name)
                            doctor_pat[creator_name].setdefault(regular_name, dict())
                            doctor_pat[creator_name][regular_name].setdefault('modify_num', 0)
                            doctor_pat[creator_name][regular_name]['modify_num'] += 1
        return doctor_pat

    def doctorRank(self, doctor_id='', dept=''):
        result = dict()
        conn = self.mongo_pull_utils.connection(collection_name=self.collection_name_doctor)
        today = datetime.now()
        this_month = datetime.strftime(today, '%Y-%m')
        year_right = today.year
        month_right = today.month
        year_left = year_right if month_right != 1 else year_right - 1
        month_left = month_right - 1 if month_right != 1 else 12
        month_left_left = month_left - 1 if month_left != 1 else 12
        year_left_left = year_left if month_left != 1 else year_left - 1
        last_month = datetime.strftime(datetime(year_left, month_left, 1), '%Y-%m')
        last_two_month = datetime.strftime(datetime(year_left_left, month_left_left, 1), '%Y-%m')

        # 上月书写病历数与上月书写问题病历数
        last_month_count = conn.find({'control_date': {"$gte": last_month, "$lt": this_month}, 'doctor_id': doctor_id}).count()
        last_month_problem = conn.aggregate([
            {'$match': {'control_date': {"$gte": last_month, "$lt": this_month}}},
            {'$project': {'doctor_value': {'$slice': ['$doctor_value_list', -1, 1]}}},  # 查看是否修改
            {'$unwind': '$doctor_value'},
            {'$match': {'doctor_value.code': {'$exists': True}, 'doctor_value.doctor_id': doctor_id}},
            {'$group': {'_id': True, 'value': {"$sum": 1}}}
        ], allowDiskUse=True)
        result['last_month_count'] = last_month_count  # 该医生上月总书写病历数
        for data in last_month_problem:
            result['last_month_problem_count'] = data.get('value', 0)  # 该医生上月问题病历数

        # 上月书写各文书问题占比，各文书问题数排序
        record_num = conn.aggregate([
            {'$match': {'control_date': {"$gte": last_month, "$lt": this_month}}},
            {'$project': {'doctor_value': {'$slice': ['$doctor_value_list', -1, 1]}}},
            {'$unwind': '$doctor_value'},
            {'$match': {'doctor_value.code': {'$exists': True}, 'doctor_value.doctor_id': doctor_id}},
            {'$unwind': '$doctor_value'},
            {'$group': {'_id': '$doctor_value.path', 'value': {"$sum": 1}}}
        ], allowDiskUse=True)
        tmp = dict()
        total = 0
        for data in record_num:
            record_name = data['_id'].split('--')[0]
            tmp.setdefault(record_name, 0)
            tmp[record_name] += data.get('value', 0)  # 上月各文书问题数
            total += data.get('value', 0)  # 所有文书问题总数
        sort_record = sorted(tmp.items(), key=lambda x: x[1], reverse=True)  # 文书按问题条数排序
        result['record_sorted'] = list()
        result['graph'] = list()
        for data in sort_record:
            if len(result['record_sorted']) < 5:
                result['record_sorted'].append({data[0]: data[1]})  # 文书按问题条数排序，只取前5,存入结果字典
            value = data[1]/total if total else 0
            result['graph'].append({data[0]: value})  # 环形图

        # 最易犯问题前3
        details_num = conn.aggregate([
            {'$match': {'control_date': {"$gte": last_month, "$lt": this_month}}},
            {'$project': {'doctor_value': {'$slice': ['$doctor_value_list', -1, 1]}}},
            {'$unwind': '$doctor_value'},
            {'$match': {'doctor_value.code': {'$exists': True}, 'doctor_value.doctor_id': doctor_id}},
            {'$unwind': '$doctor_value'},
            {'$group': {'_id': '$doctor_value.regular_details', 'value': {"$sum": 1}}},
            {'$sort': {'value': -1}},
            {'$limit': 3},
        ], allowDiskUse=True)
        result['regular_sort'] = list()
        for data in details_num:
            result['regular_sort'].append(data['_id'])  # 最易犯问题前3

        # 该科室上月各医生书写总数
        last_month_total = conn.aggregate([
            {'$match': {'control_date': {"$gte": last_month, "$lt": this_month}, 'doctor_dept': dept}},
            {'$group': {'_id': '$doctor_id', 'value': {"$sum": 1}}}
        ], allowDiskUse=True)
        # 该科室上月各医生书写问题病历数
        last_month_num = conn.aggregate([
            {'$match': {'control_date': {"$gte": last_month, "$lt": this_month}, 'doctor_dept': dept}},
            {'$project': {'doctor_id': 1, 'doctor_value': {'$slice': ['$doctor_value_list', -1, 1]}}},  # 查看是否修改
            {'$unwind': '$doctor_value'},
            {'$match': {'doctor_value.code': {'$exists': True}}},
            {'$group': {'_id': '$doctor_id', 'value': {"$sum": 1}}}
        ], allowDiskUse=True)
        tmp_total = dict()
        tmp_num = dict()
        tmp_ratio = dict()
        for data in last_month_total:
            tmp_total[data['_id']] = data['value']
        for data in last_month_num:
            tmp_num[data['_id']] = data['value']
        for k, v in tmp_total.items():
            if k in tmp_num:
                tmp_ratio[k] = tmp_num[k]/v if v else 0
        ratio_sort = sorted(tmp_ratio.items(), key=lambda x: x[1], reverse=True)
        doctor_total = len(ratio_sort)
        last_rank = 0
        result['rank_info'] = ''
        for n, data in enumerate(ratio_sort, 1):
            if data[0] == doctor_id:
                if n <= 3:
                    result['rank_info'] = '严重提示，您问题占比居于科室前三啦！'
                elif n < doctor_total/3:
                    result['rank_info'] = '遗憾，33%同僚与您携手触底'
                elif doctor_total/3 < n < doctor_total*2/3:
                    result['rank_info'] = '再接再厉，质量仅超过33%同僚'
                else:
                    result['rank_info'] = '优秀如您，质量超过66%同僚'
                last_rank = n
                break
        # 该科室上上月各医生书写总数
        last_two_total = conn.aggregate([
            {'$match': {'control_date': {"$gte": last_two_month, "$lt": last_month}, 'doctor_dept': dept}},
            {'$group': {'_id': '$doctor_id', 'value': {"$sum": 1}}}
        ], allowDiskUse=True)
        # 该科室上上月各医生书写问题病历数
        last_two_num = conn.aggregate([
            {'$match': {'control_date': {"$gte": last_month, "$lt": this_month}, 'doctor_dept': dept}},
            {'$project': {'doctor_id': 1, 'doctor_value': {'$slice': ['$doctor_value_list', -1, 1]}}},  # 查看是否修改
            {'$unwind': '$doctor_value'},
            {'$match': {'doctor_value.code': {'$exists': True}}},
            {'$group': {'_id': '$doctor_id', 'value': {"$sum": 1}}}
        ], allowDiskUse=True)
        tmp_two_total = dict()
        tmp_two_num = dict()
        tmp_two_ratio = dict()
        for data in last_two_total:
            tmp_two_total[data['_id']] = data['value']
        for data in last_two_num:
            tmp_two_num[data['_id']] = data['value']
        for k, v in tmp_two_total.items():
            if k in tmp_two_num:
                tmp_two_ratio[k] = tmp_two_num[k]/v if v else 0
        ratio_two_sort = sorted(tmp_two_ratio.items(), key=lambda x: x[1], reverse=True)
        result['rank_change'] = ''
        for n, data in enumerate(ratio_two_sort, 1):
            if data[0] == doctor_id:
                if n < last_rank:
                    result['rank_change'] = '较{}月排名下降'.format(month_left_left)
                else:
                    result['rank_change'] = '较{}月排名上升'.format(month_left_left)
                break
        return result

    def problemNameAndCode(self, regular_name='', in_hospital=True):
        result = dict()
        if in_hospital:
            regular_model = self.parameters.regular_model['医生端']
        else:
            regular_model = self.parameters.regular_model['环节']
        for k, v in regular_model.items():
            if v.get('status') == '启用' and v.get('regular_classify'):
                regular_classify = v.get('regular_classify')
                result.setdefault(regular_classify, list())
                if v.get('regular_details') and v.get('regular_details') not in result[regular_classify]:
                    result[regular_classify].append(v.get('regular_details').strip())
        code_list = ['全部']
        for v in result.values():
            code_list.extend(v)
        regular_list = list(result.keys())
        regular_list.insert(0, '全部')
        if regular_name and regular_name != '全部':
            return result[regular_name]
        elif regular_name == '全部':
            return code_list
        else:
            return {'regular_list': regular_list,
                    'code_list': code_list}

    def allDistrict(self, ward_name=''):
        """
        始终返回所有科室，输入科室返回该科室病区
        """
        result = dict()
        result['dept'] = self.dept_list.copy()
        result['dept'].insert(0, '全部')
        if ward_name == '医务处' or ward_name == '全部':
            result['district'] = list(self.ward_dept.keys())
            result['district'].insert(0, '全部')
        elif ward_name in self.ward_dept.values():
            result['district'] = list()
            for k, v in self.ward_dept.items():
                if v == ward_name:
                    result['district'].append(k)
            result['district'].insert(0, '全部')
        return result

    def showJsonFile(self, patient_id, visit_id):
        """
        环节列表展示原始数据
        """
        result = dict()
        original_collection = self.collection_name_doctor + '_original'
        conn = self.mongo_pull_utils.connection(collection_name=original_collection)
        original_id = self.hospital_code + '#' + patient_id
        search_field = {'_id': original_id}
        query_result = conn.find_one(search_field)
        if not query_result:
            return result
        original_info = query_result.get('info', dict())
        if original_info.get('visit_id') != visit_id:
            return result
        for record_name, tab_name in self.conf_dict['english_to_chinese'].items():
            if not original_info.get(record_name):  # json数据中没有 english_to_chinese 中的 english 字段的数据
                continue
            if record_name == 'ruyuanjilu':  # 文书名称是ruyuanjilu且json数据中有ruyuanjilu
                if not isinstance(original_info[record_name], list):  # 入院记录不是list, 跳过
                    continue
                for info in original_info[record_name]:  # 遍历json数据中ruyuanjilu的内容
                    if info.get('key') and info['key'] in self.conf_dict['ruyuanjilu_segment']:
                        result.setdefault(tab_name, dict())
                        result[tab_name][info['key']] = info.get('value', '')
                if 'binglizhenduan' in original_info and isinstance(original_info.get('binglizhenduan'), list):  # 初步诊断在 binglizhenduan 中
                    diagnosis_name = list()
                    for info in original_info['binglizhenduan']:
                        if info.get('diagnosis_type_name') == '初步诊断' and info.get('diagnosis_name'):
                            diagnosis_name.append(info['diagnosis_name'])
                    diagnosis_src = '、'.join(diagnosis_name)
                    if diagnosis_name:
                        result.setdefault(tab_name, dict())
                        result[tab_name]['初步诊断'] = diagnosis_src
            else:  # html 病历原文
                if record_name == 'shouyeshoushu' or record_name == 'shouyezhenduan':
                    continue
                if isinstance(original_info[record_name], list):  # 可重复文书
                    for info in original_info[record_name]:
                        if not info.get('mr_content_html'):
                            continue
                        result.setdefault(tab_name, list())
                        result[tab_name].append(info['mr_content_html'])
        return result

    def demoData(self):
        collection_name = self.collection_name + '_show'
        conn = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                       collection_name=collection_name)
        mongo_result = conn.aggregate([{'$sample': {'size': 1}}])
        result = dict()
        for data in mongo_result:
            if data['_id'].startswith('BJDXDSYY'):
                result['patient_id'] = data['patient_id']
                result['visit_id'] = data['visit_id']
                result['person_name'] = data['binganshouye']['pat_info'].get('person_name', '')
                result['sex_name'] = data['binganshouye']['pat_info'].get('sex_name', '')
                result['age_value'] = data['binganshouye']['pat_visit'].get('age_value', '')
                result['age_value_unit'] = data['binganshouye']['pat_visit'].get('age_value_unit', '')
                result['allergy_indicator'] = data['ruyuanjilu']['ruyuanjilu'].get('history_of_past_illness', dict()).get('allergy_indicator', '否')
                result['dept'] = data['binganshouye']['pat_visit'].get('dept_discharge_from_name', '') or data['binganshouye']['pat_visit'].get('dept_admission_to_name', '')
                result['chief_complaint'] = data['ruyuanjilu']['ruyuanjilu'].get('chief_complaint', dict()).get('src', '')
                result['history_of_present_illness'] = data['ruyuanjilu']['ruyuanjilu'].get('history_of_present_illness', dict()).get('src', '')
                result['history_of_past_illness'] = data['ruyuanjilu']['ruyuanjilu'].get('history_of_past_illness', dict()).get('src', '')
                result['social_history'] = data['ruyuanjilu']['ruyuanjilu'].get('social_history', dict()).get('src', '')
                result['menstrual_and_obstetrical_histories'] = data['ruyuanjilu']['ruyuanjilu'].get('menstrual_and_obstetrical_histories', dict()).get('src', '')
                result['history_of_family_member_diseases'] = data['ruyuanjilu']['ruyuanjilu'].get('history_of_family_member_diseases', dict()).get('src', '')
                result['physical_examination'] = data['ruyuanjilu']['ruyuanjilu'].get('physical_examination', dict()).get('src', '')
                result['auxiliary_examination'] = data['ruyuanjilu']['ruyuanjilu'].get('auxiliary_examination', dict()).get('src', '')
                result['special_examination'] = data['ruyuanjilu']['ruyuanjilu'].get('special_examination', dict()).get('src', '')
                result['diagnosis_name'] = data['ruyuanjilu']['ruyuanjilu'].get('diagnosis_name_src', '')
                result['pat_value'] = data['result'].get('pat_value', list())
                result['shoushujilu'] = ''
            else:
                result = data
        return result

    def runDemo(self, json_file):
        if json_file.get('shoushujilu'):
            return json_file.get('pat_value', list())
        medical_record = dict()
        result = dict()
        medical_record['patient_id'] = json_file['patient_id']
        medical_record['visit_id'] = json_file['visit_id']
        medical_record['_id'] = '{}#{}#{}'.format('BJDXDSYY', json_file['patient_id'], json_file['visit_id'])
        result.update(medical_record)
        # 组合病案首页信息
        binganshouye = dict()
        binganshouye['pat_info'] = dict()
        binganshouye['pat_visit'] = dict()
        binganshouye['pat_info']['sex_name'] = json_file.get('sex_name', '')
        binganshouye['pat_info']['person_name'] = json_file.get('person_name', '')
        binganshouye['pat_visit']['age_value'] = json_file.get('age_value', '')
        binganshouye['pat_visit']['age_value_unit'] = json_file.get('age_value_unit', '')
        binganshouye['pat_visit']['dept_discharge_from_name'] = json_file.get('dept', '')
        result['binganshouye'] = binganshouye
        ruyuanjilu = [
            {'key': 'ryjl_zs', 'value': json_file.get('chief_complaint', ''), 'chapter_name': 'chief_complaint'},
            {'key': 'ryjl_tgjc', 'value': json_file.get('physical_examination', ''), 'chapter_name': 'physical_examination'},
            {'key': 'ryjl_xbs', 'value': json_file.get('history_of_present_illness', ''), 'chapter_name': 'history_of_present_illness'},
            {'key': 'ryjl_jws', 'value': json_file.get('history_of_past_illness', ''), 'chapter_name': 'history_of_past_illness'},
            {'key': 'ryjl_grs', 'value': json_file.get('social_history', ''), 'chapter_name': 'social_history'},
            {'key': 'ryjl_yjhys', 'value': json_file.get('menstrual_and_obstetrical_histories', ''), 'chapter_name': 'menstrual_and_obstetrical_histories'},
            {'key': 'ryjl_jzs', 'value': json_file.get('history_of_family_member_diseases', ''), 'chapter_name': 'history_of_family_member_diseases'},
            {'key': 'ryjl_cbzd', 'value': json_file.get('special_examination', ''), 'chapter_name': 'special_examination'}
        ]
        segment_result = self.segment.process(ruyuanjilu)
        file_flag = False
        if segment_result:
            file_flag = True  # 有有效文书
            result['ruyuanjilu'] = [{'ruyuanjilu': segment_result}]
            result['ruyuanjilu'][0].update(medical_record)
        if not file_flag:
            return {}
        if result.get('ruyuanjilu', list()):
            if 'ruyuanjilu' in result['ruyuanjilu'][0]:
                result['ruyuanjilu'][0]['ruyuanjilu'].setdefault('history_of_past_illness', dict())
                result['ruyuanjilu'][0]['ruyuanjilu']['history_of_past_illness']['allergy_indicator'] = json_file.get('allergy_indicator', '否')

        res = dict()
        self.run_regular.all_result = dict()
        self.run_regular.debug = False
        self.run_regular.regular_model = self.parameters.regular_model['终末']
        # 只质控病案首页相关规则，非病案首页规则置为未启用
        for regular_code, regular_model in self.run_regular.regular_model.items():
            if regular_model.get('record_name') == '入院记录':
                regular_model['status'] = '启用'
            else:
                regular_model['status'] = '未启用'
        for collection_name, collection_rule_func in self.conf_dict['func'].items():
            for func in collection_rule_func:
                if func not in self.run_regular.__dir__():
                    continue
                res = eval('self.run_regular.' + func)(collection_name, **result)
        if res:
            return res.get(medical_record['_id'], dict()).get('pat_value', list())
        else:
            return ['病历正确']


if __name__ == '__main__':
    app = ClientInterface()
    with open('./123.json', 'r', encoding='utf8') as f:
        dt = json.load(f)
    t1 = datetime.now()
    r = app.getHuanjiePatientHtml('000558687900#1#BJDXDSYY', 'binganshouye')
    t = (datetime.now()-t1).total_seconds()
    print(json.dumps(r, ensure_ascii=False, indent=4))
    print('函数运行消耗 {0} 秒'.format(t))