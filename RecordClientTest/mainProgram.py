#!/usr/bin/env python3
# -*- coding:utf-8 -*

"""
@version: v1.0
@author:
@contact:
@software: PyCharm Community Edition
@file: main_program.py
@time: 18-6-26 下午4:10
@description:
"""
import os
import sys
cur_path = os.path.abspath(os.path.dirname(__file__))
root_path = os.path.split(cur_path)[0]
sys.path.append(root_path)  # 项目路径添加到系统路径
import re
import traceback
from Utils.gainMongoInfo import GainMongoInfo
from Utils.MongoUtils import PushDataFromMDBUtils
from Utils.loadingConfigure import Properties
from Utils.LogUtils import LogUtils
from Utils.gainESSearch import GainESSearch
from datetime import datetime


class CheckMultiRecords(object):

    def __init__(self, debug=False):
        self.debug = debug
        self.gain_info = GainMongoInfo()
        self.PushData = PushDataFromMDBUtils()
        self.parameters = Properties()
        self.app_es = GainESSearch()
        self.logger = LogUtils().getLogger("record_info")
        self.logger_info = LogUtils().getLogger("run_info")
        self.logger_error = LogUtils().getLogger("mainProgram")
        self.logger_print = LogUtils().getLogger("out_info")
        self.all_result = dict()
        self.conf_dict = self.parameters.conf_dict.copy()
        self.hospital_code = self.parameters.properties.get('hospital_code')
        self.version = self.parameters.properties.get('version', '')
        self.regular_model = self.parameters.regular_model['医生端'].copy()
        t = self.conf_dict.get('time_limits', dict()).copy()
        self.time_limits = t if isinstance(t, dict) else dict()
        self.repeat = dict()
        self.processed = set()

    def enable_regular(self, regular_code):
        try:
            if regular_code == 'all':
                for k in self.regular_model:
                    self.regular_model[k]['status'] = '启用'
            else:
                self.regular_model.get(regular_code, dict())['status'] = '启用'
        except:
            self.logger_error.error(traceback.format_exc())

    def disable_regular(self, regular_code):
        try:
            if regular_code == 'all':
                for k in self.regular_model:
                    self.regular_model[k]['status'] = '未启用'
            else:
                self.regular_model.get(regular_code, dict())['status'] = '未启用'
        except:
            self.logger_error.error(traceback.format_exc())

    def enable_config_regular(self):
        self.disable_regular('all')
        for regular_code in self.conf_dict['regular_code']:
            self.enable_regular(regular_code)
            
    def filter_dept(self, regular_code, binganshouye_data=''):
        """
        返回True，科室符合要求，继续运行规则，返回False，不符合要求，跳过
        """
        if self.regular_model.get(regular_code, dict()).get('status', '') != '启用':
            return False
        if isinstance(binganshouye_data, dict):
            if 'menzhenshuju' in binganshouye_data:
                dept_discharge = binganshouye_data.get('menzhenshuju', dict()).get('pat_visit', dict()).get('dept_discharge_from_name')
                dept_admission = binganshouye_data.get('menzhenshuju', dict()).get('pat_visit', dict()).get('dept_admission_to_name')
                dept = dept_discharge or dept_admission
            else:
                dept_discharge = binganshouye_data.get('binganshouye', dict()).get('pat_visit', dict()).get('dept_discharge_from_name')
                dept_admission = binganshouye_data.get('binganshouye', dict()).get('pat_visit', dict()).get('dept_admission_to_name')
                dept = dept_discharge or dept_admission
            if dept:
                for k, v in self.regular_model[regular_code].get('dept', dict()).items():
                    if k == '$in':
                        if dept in v:
                            return True
                    if k == '$nin':
                        if dept not in v:
                            return True
            return False
        return True

    def get_patient_info(self, bingan_data, collection_name):
        collection_data = dict()
        if collection_name and (collection_name in bingan_data):
            if isinstance(bingan_data[collection_name], list) and len(bingan_data[collection_name]) > 0:  # 为list且不为空
                collection_data = bingan_data[collection_name][0]
            elif isinstance(bingan_data[collection_name], dict):
                collection_data = bingan_data[collection_name]
        mq_id = bingan_data['_id']
        if mq_id in self.all_result:
            patient_result = self.all_result[bingan_data['_id']]
            num = len(patient_result['pat_value']) + 1
        else:
            num = 1
            patient_result = self.gain_info._gain_bingan_info(cursor=bingan_data)
            patient_id, visit_id = mq_id.split('#')[1:]
            patient_result['_id'] = '#'.join([patient_id, visit_id, self.hospital_code])
            patient_result['status'] = False
            patient_result['content'] = list()
            patient_result['del_value'] = list()
            patient_result['control_date'] = ''
            patient_result['record_quality_doctor'] = ''
            patient_result['version'] = self.version
        return collection_data, patient_result, num

    def supplementErrorInfo(self, error_info, **kwargs):
        try:
            if error_info['code'] in self.regular_model:
                code = error_info['code']
                error_info['name'] = self.regular_model[code].get('regular_classify', '')
                error_info['regular_details'] = self.regular_model[code].get('regular_details', '')
                error_info['classification'] = self.regular_model[code].get('classification_flag', '')  # 类别标识
                error_info['score'] = self.regular_model[code].get('score', '')
                record_name = self.regular_model[code].get('record_name', '')
                chapter = self.regular_model[code].get('chapter') or record_name
                error_info['record_name'] = record_name
                error_info['chapter'] = chapter
                error_info['path'] = '{}--{}'.format(record_name, chapter) if chapter != record_name else record_name
                error_info['test_status'] = False
            error_info['creator_name'] = kwargs.get('creator_name', '')
            error_info['html'] = kwargs.get('collection_name', '')
            error_info['file_time_value'] = kwargs.get('file_time_value', '')
            error_info['last_modify_date_time'] = kwargs.get('last_modify_date_time', '')  # 文书最后修改时间时间
            error_info['del_reason'] = ''
            error_info['test_content'] = {'fenci': '', 'cibiao': '', 'guize': '', 'zhengque': ''}
        except:
            self.logger_error.error(traceback.format_exc())
        return error_info

    def check_chief_time(self, collection_name, **json_file):
        """
        collection = ruyuanjilu
        检查主诉时间缺失
        RYJLZS0001
        """
        if json_file and self.filter_dept('RYJLZS0001', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if collection_name not in collection_data:
                    continue
                chief_time, flag = self.gain_info._gain_chief_time(collection_data.get(collection_name, dict()).get('chief_complaint', dict()))
                chief_src = self.gain_info._gain_src(cursor=collection_data,
                                                     collection_name=collection_name,
                                                     chapter_name='chief_complaint')
                if not collection_data.get(collection_name, dict()).get('chief_complaint', dict()):
                    continue
                word_filter = self.conf_dict['check_chief_time']
                if word_filter.findall(chief_src):  # 含有配置词的 src过滤
                    continue
                batchno = collection_data.get('batchno', '')
                chief_time_copy = chief_time.copy()
                for content_name in chief_time_copy:
                    if content_name not in chief_src:
                        chief_time.pop(content_name)
                creator_name = collection_data.get(collection_name, dict()).get('creator_name', '')
                last_modify_date_time = collection_data.get(collection_name, dict()).get('last_modify_date_time', '')
                file_time_value = collection_data.get(collection_name, dict()).get('file_time_value', '')
                if chief_time and (not flag):  # 有内容没有时间, flag为True, chief_time必有内容
                    k = list(chief_time.keys())
                    # 演示用，测试时间需要去掉
                    # if re.findall('[1-9]', chief_src):
                    #     continue
                    reason = '主诉中<{0}>没有时间'.format(k[0])
                    if patient_result['pat_info'].get('dept_discharge_from_name', '') == '妇产科':
                        collection_ruyuanjilu = self.PushData.connectCollection(database_name=self.PushData.mongodb_database_name,
                                                                                collection_name=collection_name)
                        if re.findall('\d*次', chief_src):
                            continue
                        if collection_ruyuanjilu.find_one({'_id': data['_id'],
                                                           'ruyuanjilu.chief_complaint.symptom.freq': {'$exists': True},
                                                           'ruyuanjilu.chief_complaint.disease.disease_frequency': {'$exists': True}}):
                            continue
                elif flag:  # 有时间有内容或者无内容
                    continue
                else:
                    reason = '书写错误，未检出信息'  # 10.24 修改 未提取出主诉内容信息 修改为 书写错误未检出信息
                    # continue  # /todo 未提取内容不显示
                # if reason != '未提取出主诉内容信息':  # /TODO 只检测 未提取出主诉内容信息 数据时启用
                #     continue
                if self.debug:
                    self.logger.info('\n主诉缺失时间ZS0001:\n\tid: {0}\n\tchapter: {1}\n\treason: {2}\n\tbatchno: {3}\n'.
                                     format(data['_id'],
                                            collection_data[collection_name]['chief_complaint'],
                                            reason,
                                            batchno))
                error_info = {'code': 'RYJLZS0001',
                              'num': num,
                              'chief_src': chief_src,
                              'reason': reason}
                error_info = self.supplementErrorInfo(error_info=error_info,
                                                      creator_name=creator_name,
                                                      file_time_value=file_time_value,
                                                      last_modify_date_time=last_modify_date_time,
                                                      collection_name=collection_name)
                if 'score' in error_info:
                    patient_result['pat_info']['machine_score'] += error_info['score']
                patient_result['pat_value'].append(error_info)
                mq_id = data['_id']
                patient_result['pat_info'].setdefault('html', list())
                if collection_name not in patient_result['pat_info']['html']:
                    patient_result['pat_info']['html'].append(collection_name)
                self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_chief_present(self, collection_name, **json_file):
        """
        collection = ruyuanjilu
        内容(RYJLXBS0001),
        要求主诉所有时间在现病史中(RYJLXBS0005),
        RYJLXBS0001, RYJLXBS0005, RYJLZS0005
        主诉所有时间要在现病史中，主诉有一条内容在现病史中就OK
        """
        regular_code = ['RYJLXBS0001', 'RYJLXBS0005', 'RYJLZS0005']
        regular_boolean = list()
        for i in regular_code:
            if self.regular_model.get(i, dict()).get('status', '') != '启用':
                regular_boolean.append(True)
            else:
                regular_boolean.append(False)
        if all(regular_boolean):
            return self.all_result
        if json_file:
            mongo_result = [json_file]
        else:
            return self.all_result

        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if collection_name not in collection_data:
                    continue
                chief_time, chief_flag = self.gain_info._gain_chief_time(collection_data.get(collection_name, dict()).get('chief_complaint', dict()))
                chief_src = self.gain_info._gain_src(cursor=collection_data,
                                                     collection_name=collection_name,
                                                     chapter_name='chief_complaint')
                batchno = collection_data.get('batchno', '')
                if not chief_time:
                    continue
                chief_time_copy = chief_time.copy()
                chief_shoushu_flag = False
                for content_name in chief_time_copy:
                    if content_name not in chief_src:
                        chief_time.pop(content_name)
                    if (not chief_shoushu_flag) and '术后' in content_name:
                        chief_shoushu_flag = True
                creator_name = collection_data.get(collection_name, dict()).get('creator_name', '')
                last_modify_date_time = collection_data.get(collection_name, dict()).get('last_modify_date_time', '')
                file_time_value = collection_data.get(collection_name, dict()).get('file_time_value', '')

                error_info = dict()
                if 'history_of_present_illness' not in collection_data[collection_name]:
                    if len(self.regular_model.get('RYJLXBS0001', list())) > 6 and self.regular_model['RYJLXBS0001'][6] == '启用' and self.filter_dept('RYJLXBS0001', data):
                        reason = '没有现病史章节'
                        error_info = {'code': 'RYJLXBS0001',
                                      'num': num,
                                      'chief_src': chief_src,
                                      'reason': reason}
                        error_info = self.supplementErrorInfo(error_info=error_info,
                                                              creator_name=creator_name,
                                                              file_time_value=file_time_value,
                                                              last_modify_date_time=last_modify_date_time,
                                                              collection_name=collection_name)
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                else:
                    present_src = self.gain_info._gain_src(cursor=collection_data,
                                                           collection_name=collection_name,
                                                           chapter_name='history_of_present_illness')  # 现病史 src
                    # RYJLZS0005
                    if len(self.regular_model.get('RYJLZS0005', list())) > 6 and self.regular_model['RYJLZS0005'][6] == '启用' and self.filter_dept('RYJLZS0005', data):
                        present_symptom = set()
                        symptom_field = [collection_name+'.history_of_present_illness.time.symptom.symptom_name']
                        for route in symptom_field:
                            present_symptom.update(self.gain_info.getField({'_id': data['_id']}, route))
                        if present_symptom:
                            present_symptom_num = dict()
                            for s in present_symptom:
                                present_symptom_num.setdefault(present_src.count(s), set())
                                present_symptom_num[present_src.count(s)].add(s)
                            max_symptom = present_symptom_num[max(present_symptom_num.keys())]
                            if not self.gain_info._gain_same_content(chief_time.keys(), max_symptom):
                                reason = '现病史反复出现<{0}>，主诉未描述'.format('/'.join(max_symptom))
                                error_info = {'code': 'RYJLZS0005',
                                              'num': num,
                                              'chief_src': chief_src,
                                              'present_src': present_src,
                                              'reason': reason}
                                error_info = self.supplementErrorInfo(error_info=error_info,
                                                                      creator_name=creator_name,
                                                                      file_time_value=file_time_value,
                                                                      last_modify_date_time=last_modify_date_time,
                                                                      collection_name=collection_name)
                                if 'score' in error_info:
                                    patient_result['pat_info']['machine_score'] += error_info['score']
                                patient_result['pat_value'].append(error_info)
                                num += 1
                                
                    present_chapter = collection_data.get(collection_name, dict()).get('history_of_present_illness', dict())
                    present_time, present_flag = self.gain_info._gain_present_time(present_chapter)
                    present_only_time = self.gain_info._gain_present_time_value(present_chapter)

                    if present_time or present_only_time:  # 如果现病史有时间节点模型

                        present_time_copy = present_time.copy()
                        present_shoushu_flag = False
                        for content_name in present_time_copy:
                            if content_name not in present_src:
                                present_time.pop(content_name)
                            if (not present_shoushu_flag) and '术' in content_name:
                                present_shoushu_flag = True

                        chief_content = list(chief_time.keys())
                        present_content = list(present_time.keys())
                        # {现病史中的词：主诉中的词}  找同义词,找present_content的父节点
                        same_flag = self.gain_info._gain_same_content(present_content, chief_content)
                        
                        if not same_flag:  # or set(chief_content).difference(set(same_flag.values())):
                            # 主诉内容匹配src
                            src_flag = False
                            for item in chief_content:
                                if item in present_src:
                                    src_flag = True
                                    break
                            if not src_flag:
                                if not (chief_shoushu_flag and present_shoushu_flag):
                                    if self.filter_dept('RYJLXBS0001', data):
                                        reason = '主诉中<{0}>不在现病史中'.format('，'.join(set(chief_content).difference(set(same_flag.values()))))
                                        if self.debug:
                                            self.logger.info('\n现病史缺失主诉内容XBS0001:\n\tid: {0}\n\t主诉: {1}\n\t现病史: {2}\n\tbatchno: {3}\n'.
                                                             format(data['_id'],
                                                                    collection_data[collection_name]['chief_complaint'],
                                                                    present_chapter,
                                                                    batchno))
                                        error_info = {'code': 'RYJLXBS0001',
                                                      'num': num,
                                                      'chief_src': chief_src,
                                                      'present_src': present_src,
                                                      'chief_content': '，'.join(chief_content),
                                                      'present_content': '，'.join(present_content),
                                                      'reason': reason}
                                        error_info = self.supplementErrorInfo(error_info=error_info,
                                                                              creator_name=creator_name,
                                                                              file_time_value=file_time_value,
                                                                              last_modify_date_time=last_modify_date_time,
                                                                              collection_name=collection_name)
                                        if 'score' in error_info:
                                            patient_result['pat_info']['machine_score'] += error_info['score']
                                        patient_result['pat_value'].append(error_info)
                                        num += 1
                        # else:
                        #     part_flag = False
                        #     part_info = dict()  # {主诉内容 : { 主诉部位: xxx, 现病史部位: xxx}}
                        #     reason = ''
                        #     for present, chief in same_flag.items():
                        #         for value in chief_time.get(chief):
                        #             if len(value) < 2:
                        #                 continue
                        #             if value[1] != '部位':
                        #                 continue
                        #             part_info[chief] = {'主诉部位': value[0]}
                        #         for value in present_time.get(present):
                        #             if len(value) < 2:
                        #                 continue
                        #             if value[1] != '部位':
                        #                 continue
                        #             part_info[chief] = {'现病史部位': value[0]}
                        #     if part_info:
                        #         for k, values in part_info.items():
                        #             if ('左' in values.get('主诉部位', '') and '左' not in values.get('现病史部位', '')) or ('右' in values.get('主诉部位', '') and '右' not in values.get('现病史部位', '')):
                        #                 part_flag = True
                        #                 reason = '主诉现病史相同内容{}，但是部位不同。'.format(k)
                        #                 break
                        #     if part_flag:
                        #         error_info = {'code': 'RYJLXBS0001',
                        #                       'num': num,
                        #                       'chief_src': chief_src,
                        #                       'present_src': present_src,
                        #                       'chief_content': '，'.join(chief_content),
                        #                       'present_content': '，'.join(present_content),
                        #                       'reason': reason}
                        #         error_info = self.supplementErrorInfo(error_info=error_info,
                        #                                               creator_name=creator_name,
                        #                                               file_time_value=file_time_value,
                        #                                               last_modify_date_time=last_modify_date_time,
                        #                                               collection_name=collection_name)
                        #         if 'score' in error_info:
                        #             patient_result['pat_info']['machine_score'] += error_info['score']
                        #         patient_result['pat_value'].append(error_info)
                        #         num += 1
                        if self.filter_dept('RYJLXBS0005', data):  # 妇产科不检
                            if patient_result['pat_info'].get('dept_discharge_from_name', '') == '妇产科':  # /TODO 妇产科暂时不检
                                continue
                            word_filter = self.conf_dict['check_chief_present']
                            if word_filter.findall(chief_src):
                                continue
                            chief_all_time = set()
                            present_all_time = set()
                            for content, content_time in chief_time.items():
                                chief_all_time.update(content_time)
                            for content, content_time in present_time.items():
                                present_all_time.update(content_time)
                            present_all_time.update(present_only_time)
                            only_time = present_all_time.copy()
                            for t in only_time:
                                if len(t) == 2:
                                    if t[1] == '具体日期' and file_time_value != '':
                                        if '月' in t[0] and '年' not in t[0]:
                                            trans_date = self.gain_info._calc_time(file_time_value[:4]+'年'+t[0], file_time_value)
                                        else:
                                            trans_date = self.gain_info._calc_time(t[0], file_time_value)
                                        present_all_time.update(trans_date)
                                    elif t[1] == '天':
                                        present_all_time.add((t[0], '日'))

                            if '出生时' in present_src:
                                age = data.get('binganshouye', dict()).get('pat_visit', dict()).get('age_value', 0)  # 取年龄
                                if age and data.get('binganshouye', dict()).get('pat_visit', dict()).get('age_value_unit', '') == '岁':
                                    present_all_time.add((int(age), '年'))
                                    
                            common_all_time = chief_all_time & present_all_time  # 所有时间的交集
                            diff_time = chief_all_time.difference(common_all_time)
                            diff_time_copy = diff_time.copy()
                            for time_item in diff_time_copy:
                                if len(time_item) == 1:
                                    continue
                                else:
                                    if time_item[1] != '具体日期':
                                        s = str(time_item[0]) + time_item[1]
                                    else:
                                        s = str(time_item[0])
                                if s in present_src and (time_item in diff_time):
                                    diff_time.remove(time_item)
                                    if time_item[1] == '年' and ((time_item[0]*12, '月') in diff_time):
                                        diff_time.remove((time_item[0]*12, '月'))
                                    elif time_item[1] == '日' and ((time_item[0], '天') in diff_time):
                                        diff_time.remove((time_item[0], '天'))
                            if diff_time:  # 主诉时间减去交集时间，不为空，则主诉有时间不在现病史中，检出
                                for time_item in diff_time_copy:
                                    if len(time_item) == 1:
                                        continue
                                    if time_item[1] == '部位':
                                        diff_time.remove(time_item)
                                    if str(time_item[0]) not in chief_src:
                                        if (not str(time_item[0]).endswith('.5')) and (len(diff_time) > 1) and (time_item in diff_time):
                                            diff_time.remove(time_item)
                                    if time_item[1] == '年' and ((time_item[0]*12, '月') in diff_time):
                                        diff_time.remove((time_item[0]*12, '月'))
                                    elif time_item[1] == '日' and ((time_item[0], '天') in diff_time):
                                        diff_time.remove((time_item[0], '天'))
                            if diff_time:
                                reason = '主诉时间<{0}>不存在于现病史时间中'.format(diff_time)
                                if self.debug:
                                    self.logger.info('\n现病史缺失主诉时间XBS0005:\n\tid: {0}\n\t主诉: {1}\n\t现病史: {2}\n\tbatchno: {3}\n'.
                                                     format(data['_id'],
                                                            collection_data[collection_name]['chief_complaint'],
                                                            present_chapter,
                                                            batchno))
                                error_info = {'code': 'RYJLXBS0005',
                                                      'num': num,
                                                      'chief_src': chief_src,
                                                      'present_src': present_src,
                                                      'reason': reason}
                                error_info = self.supplementErrorInfo(error_info=error_info,
                                                                      creator_name=creator_name,
                                                                      file_time_value=file_time_value,
                                                                      last_modify_date_time=last_modify_date_time,
                                                                      collection_name=collection_name)
                                if 'score' in error_info:
                                    patient_result['pat_info']['machine_score'] += error_info['score']
                                patient_result['pat_value'].append(error_info)
                                num += 1
                    else:
                        if self.filter_dept('RYJLXBS0001', data):
                            reason = '现病史章节无时间节点模型'
                            error_info = {'code': 'RYJLXBS0001',
                                          'num': num,
                                          'chief_src': chief_src,
                                          'present_src': present_src,
                                          'reason': reason}
                            error_info = self.supplementErrorInfo(error_info=error_info,
                                                                  creator_name=creator_name,
                                                                  file_time_value=file_time_value,
                                                                  last_modify_date_time=last_modify_date_time,
                                                                  collection_name=collection_name)
                            if 'score' in error_info:
                                patient_result['pat_info']['machine_score'] += error_info['score']
                            patient_result['pat_value'].append(error_info)
                if error_info:
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_present_time(self, collection_name, **json_file):
        """
        collection = ruyuanjilu
        <时间节点N>不应在<时间节点N+1>前，时间未按照顺序描述
        RYJLXBS0004
        """
        if json_file and self.filter_dept('RYJLXBS0004', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data.get(collection_name, dict()).get('history_of_present_illness', dict()).get('time', ''):
                    continue
                creator_name = collection_data.get(collection_name, dict()).get('creator_name', '')
                last_modify_date_time = collection_data.get(collection_name, dict()).get('last_modify_date_time', '')
                file_time_value = collection_data.get(collection_name, dict()).get('file_time_value', '')
                present_src = self.gain_info._gain_src(cursor=collection_data,
                                                       collection_name=collection_name,
                                                       chapter_name='history_of_present_illness')  # 现病史 src
                batchno = collection_data.get('batchno', '')
                time_transform = {'年': 4, '月': 3, '周': 2, '天': 1, '日': 1}
                time_last = 0
                unit_last = 0
                flag = False
                for time_model in collection_data[collection_name]['history_of_present_illness']['time']:
                    if 'time_value' not in time_model:
                        continue
                    time_value = self.gain_info._load_time(time_model['time_value'])
                    if len(time_value) != 2:  # 会出现没有时间单位的情况
                        continue
                    if time_value[1] in time_transform:
                        unit_current = time_transform[time_value[1]]
                    else:
                        continue
                    time_current = time_value[0]
                    if not time_last:
                        time_last = time_current
                        unit_last = unit_current
                        continue
                    if unit_current > unit_last:
                        if unit_last == 3:
                            time_last_calc = time_last * 30
                        elif unit_last == 2:
                            time_last_calc = time_last * 7
                        else:
                            time_last_calc = time_last
                        if unit_current == 4:
                            time_current_calc = time_current * 365
                        elif unit_current == 3:
                            time_current_calc = time_current * 30
                        else:
                            time_current_calc = time_current * 7
                        if time_last_calc < time_current_calc:
                            flag = True
                            break
                        else:
                            time_last = time_current
                            unit_last = unit_current
                    elif unit_current < unit_last:
                        unit_last = unit_current
                        time_last = time_current
                    else:
                        if time_current <= time_last:
                            time_last = time_current
                        else:
                            flag = True
                            break
                if flag:
                    if self.debug:
                        self.logger.info('\n现病史时间顺序颠倒XBS0004:\n\tid: {0}\n\t现病史时间节点: {1}\n\tbatchno: {2}\n'.
                                         format(data['_id'],
                                                collection_data[collection_name]['history_of_present_illness']['time'],
                                                batchno))
                    reason = '现病史时间节点未按照顺序描述'
                    error_info = {'code': 'RYJLXBS0004',
                                  'num': num,
                                  'present_src': present_src,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_present_past(self, collection_name, **json_file):
        """
        collection = ruyuanjilu
        现病史-时间节点-疾病诊断-诊断名称==既往史-疾病-疾病名称 -->检出
        RYJLJWS0003
        """
        if json_file and self.filter_dept('RYJLJWS0003', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                creator_name = collection_data.get(collection_name, dict()).get('creator_name', '')
                last_modify_date_time = collection_data.get(collection_name, dict()).get('last_modify_date_time', '')
                file_time_value = collection_data.get(collection_name, dict()).get('file_time_value', '')
                present_src = self.gain_info._gain_src(cursor=collection_data,
                                                       collection_name=collection_name,
                                                       chapter_name='history_of_present_illness')  # 现病史 src
                past_src = self.gain_info._gain_src(cursor=collection_data,
                                                    collection_name=collection_name,
                                                    chapter_name='history_of_past_illness')
                batchno = collection_data.get('batchno', '')
                
                if not collection_data.get(collection_name, dict()).get('history_of_past_illness', dict()).get('disease', ''):
                    continue
                past_dis = self.gain_info._gain_disease_name(collection_data[collection_name]['history_of_past_illness']['disease'])
                
                if not collection_data.get(collection_name, dict()).get('history_of_present_illness', dict()).get('time', ''):
                    continue
                present_dia = set()
                for time_model in collection_data[collection_name]['history_of_present_illness']['time']:
                    if 'diagnose' in time_model:
                        if 'diagnosis_name' in time_model['diagnose']:
                            present_dia.add(time_model['diagnose']['diagnosis_name'])
                
                common_dis = past_dis & present_dia
                if common_dis:
                    if self.debug:
                        self.logger.info('\n既往史重复现病史疾病JWS0003:\n\tid: {0}\n\t现病史: {1}\n\t既往史: {2}\n\tbatchno: {3}\n'.
                                         format(data['_id'],
                                                present_dia,
                                                past_dis,
                                                batchno))
                    reason = '现病史{0}已描述，不需在既往史中再次提及'.format('，'.join(common_dis))
                    error_info = {'code': 'RYJLJWS0003',
                                  'num': num,
                                  'present_src': present_src,
                                  'past_src': past_src,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_past_diagnosis(self, collection_name, **json_file):
        """
        collection = ruyuanjilu
        初步诊断--疾病名称 不包含 既往史--疾病名称（只限高血压、糖尿病、冠心病、***癌、***瘤）and
        (本就诊次含手术记录 or (医嘱日期==入院日期 and 医嘱项名称/通用名)==西药层级表高血压药/降血糖药)(RYJLJWS0001)
        初步诊断第一疾病 and 既往史中含有该疾病(RYJLJWS0005)
        RYJLJWS0001, RYJLJWS0005
        """
        regular_code = ['RYJLJWS0001', 'RYJLJWS0005']
        regular_boolean = list()
        for i in regular_code:
            if self.regular_model.get(i, dict()).get('status', dict()) != '启用':
                regular_boolean.append(True)
            else:
                regular_boolean.append(False)
        if all(regular_boolean):
            return self.all_result
        if json_file:
            mongo_result = [json_file]
        else:
            return self.all_result
        collection_shoushu = self.PushData.connectCollection(database_name=self.PushData.mongodb_database_name,
                                                             collection_name='shoushujilu')
        collection_yizhu = self.PushData.connectCollection(database_name=self.PushData.mongodb_database_name,
                                                           collection_name='yizhu')
        for data in mongo_result:
            try:
                admission_time = data.get('binganshouye', dict()).get('pat_visit', dict()).get('admission_time', '')
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                creator_name = collection_data.get(collection_name, dict()).get('creator_name', '')
                last_modify_date_time = collection_data.get(collection_name, dict()).get('last_modify_date_time', '')
                file_time_value = collection_data.get(collection_name, dict()).get('file_time_value', '')

                if not collection_data.get(collection_name, dict()).get('history_of_past_illness', dict()).get('disease', ''):
                    continue
                past_dis = self.gain_info._gain_disease_name(collection_data[collection_name]['history_of_past_illness']['disease'])
                past_src = self.gain_info._gain_src(cursor=collection_data,
                                                    collection_name=collection_name,
                                                    chapter_name='history_of_past_illness')
                batchno = collection_data.get('batchno', '')
                if not past_dis:
                    continue
                past_dis_copy = past_dis.copy()
                for i in past_dis_copy:  # 发现疾病，检查后未见疾病
                    target = '未见' + i
                    if target in past_src:
                        past_dis.remove(i)
                error_info = dict()
                if 'diagnosis_name' not in collection_data[collection_name]:
                    if len(self.regular_model.get('RYJLJWS0001', list())) > 6 and self.regular_model['RYJLJWS0001'][6] != '启用' and self.filter_dept('RYJLJWS0001', data):
                        continue
                    if self.debug:
                        self.logger.info('\n初步诊断缺失JWS0001:\n\tid: {0}\n\tchapter_names: {1}\n\tbatchno: {2}\n'.
                                         format(data['_id'],
                                                list(collection_data[collection_name].keys()),
                                                batchno))
                    reason = '未获取到初步诊断'
                    error_info = {'code': 'RYJLJWS0001',
                                  'num': num,
                                  'past_src': past_src,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                else:
                    diagnosis_dis = self.gain_info._gain_diagnosis_name(collection_data[collection_name]['diagnosis_name'])
                    detect_dis = list()
                    shu_flag = False
                    for dis in past_dis:
                        if self.gain_info._gain_same_content(['高血压'], [dis]):
                            detect_dis.append('高血压')
                        elif self.gain_info._gain_same_content(['糖尿病'], [dis]):
                            detect_dis.append('糖尿病')
                        elif self.gain_info._gain_same_content(['冠心病'], [dis]):
                            detect_dis.append('冠心病')
                        # elif self.gain_info._gain_same_content(['癌'], [dis]):
                        #     detect_dis.append(dis)
                        #     if re.findall('(?<!否认手)术', past_src) and (not re.findall('手术史', past_src)):
                        #         shu_flag = True
                        # elif self.gain_info._gain_same_content(['瘤'], [dis]):
                        #     detect_dis.append(dis)
                        #     if re.findall('(?<!否认手)术', past_src) and (not re.findall('手术史', past_src)):
                        #         shu_flag = True
                    past_dis_sub = set(detect_dis)
                    if shu_flag:
                        past_dis_sub.add('术后')
                    flag = False
                    lost_dis = ''
                    for i in past_dis_sub:
                        if (i == '糖尿病') or (i == '高血压') or (i == '术后'):
                            if not self.gain_info._gain_same_content([i], diagnosis_dis):
                                flag = True
                                if i == '术后':
                                    lost_dis = '肿瘤手术'
                                else:
                                    lost_dis = i
                                break
                        else:
                            if not shu_flag:
                                if not self.gain_info._gain_same_content([i], diagnosis_dis):
                                    flag = True
                                    lost_dis = i
                                    break
                    if flag and len(self.regular_model.get('RYJLJWS0001', list())) > 6 and (self.regular_model['RYJLJWS0001'][6] == '启用') and self.filter_dept('RYJLJWS0001', data):
                        final_flag = False
                        shoushu_result = collection_shoushu.find_one({'_id': data['_id']}, {})
                        if shoushu_result:
                            final_flag = True
                        else:
                            yizhu_result = collection_yizhu.find_one({'_id': data['_id']}, {'yizhu.order_time': 1,
                                                                                            'yizhu.order_item_name': 1,
                                                                                            'yizhu.china_approved_drug_name': 1})
                            if yizhu_result:
                                yizhu = yizhu_result.get('yizhu', list())
                                jiangyayao = self.gain_info._gain_jiangya_medicine()
                                for one_record in yizhu:
                                    if one_record.get('order_time', '')[:10] == admission_time[:10]:
                                        if one_record.get('order_item_name', ''):
                                            if self.gain_info._gain_same_content([one_record.get('order_item_name', '')], jiangyayao):
                                                final_flag = True
                                                break
                                        if one_record.get('china_approved_drug_name', ''):
                                            if self.gain_info._gain_same_content([one_record.get('china_approved_drug_name', '')], jiangyayao):
                                                final_flag = True
                                                break
                        if final_flag:
                            if self.debug:
                                self.logger.info('\n初步诊断缺失既往史疾病JWS0001:\n\tid: {0}\n\t既往史: {1}\n\t初步诊断: {2}\n\tbatchno: {3}\n'.
                                                 format(data['_id'],
                                                        '，'.join(past_dis_sub),
                                                        '，'.join(diagnosis_dis),
                                                        batchno))
                            if '高血压' == lost_dis or '糖尿病' == lost_dis:
                                reason = '患者含手术或药物治疗，既往史中<{0}>等疾病未在初步诊断中找到'.format(lost_dis)
                            else:
                                reason = '既往史中<{0}>等疾病未在初步诊断中找到'.format(lost_dis)
                            error_info = {'code': 'RYJLJWS0001',
                                          'num': num,
                                          'past_src': past_src,
                                          'diagnosis_name': '，'.join(diagnosis_dis),
                                          'reason': reason}
                            error_info = self.supplementErrorInfo(error_info=error_info,
                                                                  creator_name=creator_name,
                                                                  file_time_value=file_time_value,
                                                                  last_modify_date_time=last_modify_date_time,
                                                                  collection_name=collection_name)
                            if 'score' in error_info:
                                patient_result['pat_info']['machine_score'] += error_info['score']
                            patient_result['pat_value'].append(error_info)
                            num += 1

                    first_dis = ''
                    for dis in collection_data[collection_name]['diagnosis_name']:
                        if 'diagnosis_name' in dis:
                            first_dis = dis['diagnosis_name']
                            break

                    if first_dis and (first_dis in past_dis) and len(self.regular_model.get('RYJLJWS0005', list())) > 6 and self.regular_model['RYJLJWS0005'][6] == '启用' and self.filter_dept('RYJLJWS0005', data):
                        if self.debug:
                            self.logger.info('\n既往史含初步诊断首要诊断JWS0005:\n\tid: {0}\n\t既往史: {1}\n\t初步诊断: {2}\n\tbatchno: {3}\n'.
                                             format(data['_id'],
                                                    '，'.join(past_dis),
                                                    first_dis,
                                                    batchno))
                        reason = '既往史含初步诊断首要诊断<{0}>'.format(first_dis)
                        error_info = {'code': 'RYJLJWS0005',
                                      'num': num,
                                      'past_src': past_src,
                                      'first_disease': first_dis,
                                      'reason': reason}
                        error_info = self.supplementErrorInfo(error_info=error_info,
                                                              creator_name=creator_name,
                                                              file_time_value=file_time_value,
                                                              last_modify_date_time=last_modify_date_time,
                                                              collection_name=collection_name)
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)

                if error_info:
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_past_deny(self, collection_name, **json_file):
        """
        collection = ruyuanjilu
        既往史--疾病--疾病名称 == 否认的项目 and 既往史--手术--手术名称 == 否认的项目（否认手术史）(RYJLJWS0006)
        RYJLJWS0006
        """
        if json_file and self.filter_dept('RYJLJWS0006', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if collection_name not in collection_data:
                    continue
                creator_name = collection_data.get(collection_name, dict()).get('creator_name', '')
                last_modify_date_time = collection_data.get(collection_name, dict()).get('last_modify_date_time', '')
                file_time_value = collection_data.get(collection_name, dict()).get('file_time_value', '')
                past_src = self.gain_info._gain_src(cursor=collection_data,
                                                    collection_name=collection_name,
                                                    chapter_name='history_of_past_illness')
                past_chapter = collection_data.get(collection_name, dict()).get('history_of_past_illness', dict())
                batchno = collection_data.get('batchno', '')
                deny = past_chapter.get('deny', '').split(' ')
                past_content = set()
                if 'disease' in past_chapter:
                    past_content = self.gain_info._gain_disease_name(past_chapter.get('disease', list()))
                same_flag = self.gain_info._gain_same_content(past_content, deny)
                reason = ''
                if same_flag:
                    for k in same_flag:
                        reason = '既往史疾病<{0}>与否认疾病<{1}>同时存在'.format(k, same_flag[k])
                        break
                elif 'operation' in past_chapter and '手术史' in deny:
                    reason = '既往史中有手术史与否认手术史同时存在'
                if reason:
                    if self.debug:
                        self.logger.info('\n既往史与否认同时存在JWS0006:\n\tid: {0}\n\t既往史: {1}\n\t否认项: {2}\n\tbatchno: {3}\n'.
                                         format(data['_id'],
                                                '，'.join(past_content),
                                                '，'.join(deny),
                                                batchno))
                    error_info = {'code': 'RYJLJWS0006',
                                  'num': num,
                                  'past_src': past_src,
                                  'deny': past_chapter.get('deny', ''),
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_past_guominshi(self, collection_name, **json_file):
        """
        collection = ruyuanjilu
        既往史--(有无过敏史、过敏)均==NULL or (传染病史)==NULL or (有无输血史、输血次数)均==NULL
        暂时不检测输血史
        RYJLJWS0007
        """
        if json_file and self.filter_dept('RYJLJWS0007', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data.get(collection_name, dict()).get('history_of_past_illness', dict()):
                    continue
                dept = patient_result.get('pat_info', dict()).get('dept_discharge_from_name', '') or patient_result.get('pat_info', dict()).get('dept_admission_to_name', '')
                person_name = data.get('binganshouye', dict()).get('pat_info', dict()).get('person_name', '')
                creator_name = collection_data.get(collection_name, dict()).get('creator_name', '')
                last_modify_date_time = collection_data.get(collection_name, dict()).get('last_modify_date_time', '')
                file_time_value = collection_data.get(collection_name, dict()).get('file_time_value', '')
                past_src = self.gain_info._gain_src(cursor=collection_data,
                                                    collection_name=collection_name,
                                                    chapter_name='history_of_past_illness')
                # 科室==眼科 and 既往史src只含“屈光不正史”不检出；
                # 科室==儿科 and person_name含“***之女/之子/之大子/之大女/之小女/之小子”不检出
                if dept == '眼科' and self.conf_dict['check_past_guominshi'][dept].findall(past_src):
                    continue
                elif dept == '儿科' and self.conf_dict['check_past_guominshi'][dept].findall(person_name):
                    continue
                if '过敏史' in past_src:
                    continue
                batchno = collection_data.get('batchno', '')
                lost_content = set()
                if 'allergy' not in collection_data[collection_name]['history_of_past_illness']:
                    lost_content.add('过敏史')
                # if 'blood_transfusion_times' not in collection_data[collection_name]['history_of_past_illness']:
                #     lost_content.add('输血史')
                if 'deny' in collection_data[collection_name]['history_of_past_illness']:
                    if ('过敏' in collection_data[collection_name]['history_of_past_illness']['deny']) and ('过敏史' in lost_content):
                        lost_content.remove('过敏史')
                    # elif ('输血' in collection_data[collection_name]['history_of_past_illness']['deny']) and ('输血史' in lost_content):
                    #     lost_content.remove('输血史')
                if lost_content:
                    if self.debug:
                        self.logger.info('\n既往史缺失过敏史JWS0007:\n\tid: {0}\n\t既往史: {1}\n\t缺失: {2}\n\tbatchno: {3}\n'.
                                         format(data['_id'],
                                                collection_data[collection_name]['history_of_past_illness'],
                                                '，'.join(lost_content),
                                                batchno))
                    reason = '既往史缺失<{0}>'.format('/'.join(lost_content))
                    error_info = {'code': 'RYJLJWS0007',
                                  'num': num,
                                  'past_src': past_src,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_past_guominyuan(self, collection_name, **json_file):
        """
        collection = ruyuanjilu
        既往史--有无过敏==有 and
        既往史--过敏--是否药物过敏==是 and
        既往史--过敏--过敏原名称 不等于 病案首页--就诊信息--过敏药物 or
        （既往史--过敏--是否皮试==是 and
        皮试值==阳性 and
        皮试原名称 不等于 病案首页--就诊信息--过敏药物） -->检出
        RYJLJWS0010
        """
        return self.all_result
        if json_file and self.filter_dept('RYJLJWS0010', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if collection_data.get(collection_name, dict()).get('history_of_past_illness', dict()).get('allergy_indicator', '') != '是':
                    continue
                if not collection_data.get(collection_name, dict()).get('history_of_past_illness', dict()).get('allergy', ''):
                    continue
                creator_name = collection_data.get(collection_name, dict()).get('creator_name', '')
                last_modify_date_time = collection_data.get(collection_name, dict()).get('last_modify_date_time', '')
                file_time_value = collection_data.get(collection_name, dict()).get('file_time_value', '')
                batchno = collection_data.get('batchno', '')
                allergy = set()
                for a in collection_data[collection_name]['history_of_past_illness']['allergy']:
                    if a.get('drug_allergy', '') == '是' and a.get('allergy_name', ''):
                        allergy.add(a['allergy_name'])
                    if a.get('skin_test', '') == '是' and a.get('skin_test_value') == '阳性' and a.get('skin_test_name', ''):
                        allergy.add(a['skin_test_name'])
                if not allergy:
                    continue
                flag = False
                # diff_allergy = set()
                if data['binganshouye']['pat_visit'].get('drug_allergy_name'):
                    for a in allergy:
                        if a not in data['binganshouye']['pat_visit']['drug_allergy_name']:
                            flag = True
                            # diff_allergy.add(a)
                    reason = '过敏史<{0}>与病案首页<{1}>不符'.format('，'.join(allergy), data['binganshouye']['pat_visit']['drug_allergy_name'])
                else:
                    flag = True
                    # diff_allergy = allergy
                    reason = '过敏史<{0}>与病案首页<null>不符'.format('，'.join(allergy))
                if flag:
                    if self.debug:
                        self.logger.info('\n过敏史与病案首页不符JWS0010:\n\tid: {0}\n\treason: {1}\n\tbatchno: {2}\n'.
                                         format(data['_id'],
                                                reason,
                                                batchno))
                    error_info = {'code': 'RYJLJWS0010',
                                  'num': num,
                                  'allergy': '，'.join(allergy),
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_present_past_operation(self, collection_name, **json_file):
        """
        collection = ruyuanjilu
        现病史--手术--手术名称==非NULL and 既往史--否认的项目（否认手术史） -->检出
        RYJLJWS0008
        """
        if json_file and self.filter_dept('RYJLJWS0008', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if '手术史' not in collection_data.get(collection_name, dict()).get('history_of_past_illness', dict()).get('deny', ''):
                    continue
                creator_name = collection_data.get(collection_name, dict()).get('creator_name', '')
                last_modify_date_time = collection_data.get(collection_name, dict()).get('last_modify_date_time', '')
                file_time_value = collection_data.get(collection_name, dict()).get('file_time_value', '')
                batchno = collection_data.get('batchno', '')
                present_src = self.gain_info._gain_src(cursor=collection_data,
                                                       collection_name=collection_name,
                                                       chapter_name='history_of_present_illness')
                past_src = self.gain_info._gain_src(cursor=collection_data,
                                                    collection_name=collection_name,
                                                    chapter_name='history_of_past_illness')
                operation_name = set()
                if not collection_data.get(collection_name, dict()).get('history_of_present_illness', dict()).get('time', ''):
                    continue
                for t in collection_data[collection_name]['history_of_present_illness']['time']:
                    if 'operation' in t:
                        for o in t['operation']:
                            if 'operation_name' in o:
                                operation_name.add(o['operation_name'])
                if not operation_name:
                    continue
                if self.debug:
                    self.logger.info('\n现病史含手术, 既往史否认手术史JWS0008:\n\tid: {0}\n\t现病史: {1}\n\t既往史否认项: {2}\n\tbatchno: {3}\n'.
                                     format(data['_id'],
                                            '，'.join(operation_name),
                                            collection_data[collection_name]['history_of_past_illness'].get('deny', ''),
                                            batchno))
                reason = '现病史含手术<{0}>，既往史否认手术史'.format('/'.join(operation_name))
                error_info = {'code': 'RYJLJWS0008',
                              'num': num,
                              'present_src': present_src,
                              'past_src': past_src,
                              'reason': reason}
                error_info = self.supplementErrorInfo(error_info=error_info,
                                                      creator_name=creator_name,
                                                      file_time_value=file_time_value,
                                                      last_modify_date_time=last_modify_date_time,
                                                      collection_name=collection_name)
                if 'score' in error_info:
                    patient_result['pat_info']['machine_score'] += error_info['score']
                patient_result['pat_value'].append(error_info)
                mq_id = data['_id']
                patient_result['pat_info'].setdefault('html', list())
                if collection_name not in patient_result['pat_info']['html']:
                    patient_result['pat_info']['html'].append(collection_name)
                self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_repeat(self, collection_name, **json_file):
        """
        collection = ruyuanjilu
        具有相同src，文书时间相差1年以上，RYJLXBS0006以就诊次为准
        RYJLZS0003, RYJLXBS0006, RYJLJWS0009, RYJLJWS0011, RYJLGRS0001
        """
        regular_code = ['RYJLZS0003', 'RYJLXBS0006', 'RYJLJWS0009', 'RYJLJWS0011', 'RYJLGRS0001']
        regular_boolean = list()
        for i in regular_code:
            if self.regular_model.get(i, dict()).get('status') != '启用':
                regular_boolean.append(True)
            else:
                regular_boolean.append(False)
        if all(regular_boolean):
            return self.all_result
        detect_id = ''
        if json_file:
            patient_id = json_file.get('patient_id', '')
            visit_id = json_file.get('visit_id', '')
            if patient_id and visit_id:
                detect_id = self.hospital_code + '#' + patient_id + '#' + visit_id
            if not detect_id:
                return self.all_result
            expression = [
                            [
                                {"field": "患者标识", "exp": "=", "flag": "or", "unit": "", "values": [patient_id]}
                            ],
                            [
                                {"field": "入院记录_文档src", "exp": "!=", "flag": "or", "unit": "", "values": ["111"]}
                            ]
                        ]
            es_result = self.app_es.getId(expression)
            if es_result.get('res_flag') and es_result.get('count'):
                key = '{}#{}'.format(self.hospital_code, patient_id)
                id_result = {key: list()}
                for i in es_result.get('result', set()):
                    past_vid = i.split('#')[-1]
                    id_result[key].append(past_vid)
                if id_result[key]:
                    id_result[key].append(visit_id)
                else:
                    return self.all_result
                id_result[key].sort(key=lambda l: int(l))
            else:
                return self.all_result
            # for v in id_result.values():
            #     v.append(visit_id)
            #     v.sort(key=lambda l: int(l))
        else:
            return self.all_result

        # collection_bingan = self.PushData.connectCollection(database_name=self.PushData.mongodb_database_name,
        #                                                     collection_name='binganshouye')
        # collection_ruyuanjilu = self.PushData.connectCollection(database_name=self.PushData.mongodb_database_name,
        #                                                         collection_name=collection_name)
        start_date = self.time_limits.get('binganshouye.pat_visit.discharge_time', dict()).get('$gte', '')
        end_date = self.time_limits.get('binganshouye.pat_visit.discharge_time', dict()).get('$lt', '')
        for data in id_result:
            try:
                id_list = [data+'#'+i for i in id_result[data]]
                chief_list = list()
                present_list = list()
                past_list = list()
                allergy_list = list()
                smoke_list = list()
                time_list = list()
                creator_list = list()
                create_time = list()
                patient_list = list()
                num_list = list()
                detect_flag = False  # 检测目标id是否在 id_list 中，不在则中止规则查询
                id_list_copy = id_list.copy()
                for _id in id_list_copy:
                    if json_file and _id == detect_id:
                        patient_bingan = dict()
                        if '_id' in json_file:
                            patient_bingan['_id'] = json_file['_id']
                        if 'binganshouye' in json_file:
                            patient_bingan['binganshouye'] = json_file['binganshouye']
                    else:
                        if _id in self.processed:
                            continue
                        condition = dict()
                        condition['_id'] = _id
                        # condition.update(time_limits)
                        if not self.hospital_code == _id.split('#')[0]:
                            continue
                        patient_id, visit_id = _id.split('#')[1:]
                        patient_bingan = self.app_es.getRecordQuickly(patient_id, visit_id, 'binganshouye')
                        if not patient_bingan:
                            id_list.remove(_id)
                            if detect_id not in id_list:
                                detect_flag = True
                                break
                            continue
                        # patient_bingan = collection_bingan.find_one(condition,
                        #                                             {'binganshouye.pat_info.person_name': 1,
                        #                                              'binganshouye.pat_visit': 1})
                        self.processed.add(_id)
                    if not patient_bingan:
                        id_list.remove(_id)
                        if detect_id not in id_list:
                            detect_flag = True
                            break
                        continue
                    # collection_data = patient_bingan['binganshouye']
                    _, patient_result, num = self.get_patient_info(patient_bingan, collection_name)
                    if json_file and _id == detect_id:
                        patient_ruyuan = dict()
                        if collection_name in json_file:
                            patient_ruyuan = json_file[collection_name][0]
                    else:
                        patient_ruyuan = self.app_es.getRecordQuickly(patient_id, visit_id, 'ruyuanjilu')
                        # patient_ruyuan = collection_ruyuanjilu.find_one({'_id': _id,
                        #                                                  '$or': [{collection_name+'.chief_complaint': {'$exists': True}},
                        #                                                          {collection_name+'.history_of_present_illness': {'$exists': True}},
                        #                                                          {collection_name+'.social_history': {'$exists': True}},
                        #                                                          {collection_name+'.history_of_past_illness.allergy.allergy_name': {'$exists': True}},
                        #                                                          {collection_name+'.history_of_past_illness.disease': {'$exists': True}}]},
                        #                                                 {collection_name+'.chief_complaint.src': 1,
                        #                                                  collection_name+'.history_of_present_illness.src': 1,
                        #                                                  collection_name+'.social_history.smoke_indicator': 1,
                        #                                                  collection_name+'.history_of_past_illness.disease': 1,
                        #                                                  collection_name+'.history_of_past_illness.allergy.allergy_name': 1,
                        #                                                  collection_name+'.creator_name': 1,
                        #                                                  collection_name+'.last_modify_date_time': 1})
                    if not patient_ruyuan:
                        id_list.remove(_id)
                        if detect_id not in id_list:
                            detect_flag = True
                            break
                        continue
                    chief_src = self.gain_info._gain_src(patient_ruyuan, collection_name, 'chief_complaint')
                    present_src = self.gain_info._gain_src(patient_ruyuan, collection_name, 'history_of_present_illness')
                    past_chapter = patient_ruyuan.get(collection_name, dict()).get('history_of_past_illness', dict())
                    past_dis = set()
                    allergy = set()
                    if 'history_of_past_illness' in patient_ruyuan[collection_name]:
                        if 'disease' in past_chapter:
                            past_dis = self.gain_info._gain_disease_name(past_chapter.get('disease', list()))
                        if 'allergy' in past_chapter:
                            for a in past_chapter.get('allergy', list()):
                                if 'allergy_name' in a:
                                    allergy.add(a['allergy_name'])
                    if 'social_history' in patient_ruyuan[collection_name] and 'smoke_indicator' in patient_ruyuan[collection_name]['social_history']:
                        smoke_list.append(True)
                    else:
                        smoke_list.append(False)
                    creator_name = patient_ruyuan.get(collection_name, dict()).get('creator_name', '')
                    last_modify_date_time = patient_ruyuan.get(collection_name, dict()).get('last_modify_date_time', '')
                    file_time_value = patient_ruyuan.get(collection_name, dict()).get('file_time_value', '')
                    chief_list.append(chief_src)
                    present_list.append(present_src)
                    past_list.append(past_dis)
                    allergy_list.append(allergy)
                    time_list.append(last_modify_date_time)
                    creator_list.append(creator_name)
                    patient_list.append(patient_result)
                    num_list.append(num)
                    create_time.append(file_time_value)

                if detect_flag:  # 如果要查询的 visit_id 不在 id_list 中，则跳过此患者的查询
                    continue

                if self.filter_dept('RYJLJWS0009', json_file):
                    if any(past_list) and len(past_list) > 1:  # RYJLJWS0009
                        for index in range(1, len(past_list)):
                            if detect_id and id_list[index] != detect_id:  # 如果有目标 id，那么只检测目标 id
                                continue
                            if not (start_date < patient_list[index]['pat_info'].get('discharge_time', '') < end_date) and (not json_file):
                                continue
                            if self.gain_info._gain_same_content(['高血压'], past_list[index-1]):  # 前次就诊既往史中有高血压
                                if not self.gain_info._gain_same_content(['高血压'], past_list[index]):  # 本次就诊既往史中没有高血压
                                    if self.debug:
                                        self.logger.info('\n多个就诊次既往史高血压JWS0009：\n\tid: {0}\n\tlast_disease: {1}\n\tthis_disease: {2}\n'.
                                                         format(id_list[index],
                                                                '/'.join(past_list[index-1]),
                                                                '/'.join(past_list[index])))
                                    reason = '前次既往史中“高血压”未出现在本次既往史中'
                                    error_info = {'code': 'RYJLJWS0009',
                                                  'num': num_list[index],
                                                  'last_id': id_list[index-1],
                                                  'reason': reason}
                                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                                          creator_name=creator_list[index],
                                                                          file_time_value=create_time[index],
                                                                          last_modify_date_time=time_list[index],
                                                                          collection_name=collection_name)
                                    if 'score' in error_info:
                                        patient_list[index]['pat_info']['machine_score'] += error_info['score']
                                    patient_list[index]['pat_value'].append(error_info)
                                    patient_list[index]['pat_info'].setdefault('html', list())
                                    if collection_name not in patient_list[index]['pat_info']['html']:
                                        patient_list[index]['pat_info']['html'].append(collection_name)
                                    num_list[index] += 1
                                    self.all_result[id_list[index]] = patient_list[index]

                if self.filter_dept('RYJLJWS0011', json_file):
                    if any(allergy_list) and len(allergy_list) > 1:  # RYJLJWS0011
                        for index in range(1, len(allergy_list)):
                            if detect_id and id_list[index] != detect_id:  # 如果有目标 id，那么只检测目标 id
                                continue
                            if not (start_date < patient_list[index]['pat_info'].get('discharge_time', '') < end_date) and (not json_file):
                                continue
                            same_allergy = self.gain_info._gain_same_content(allergy_list[index-1], allergy_list[index])  # 前一次和这一次比
                            if len(same_allergy) != len(allergy_list[index-1]):
                                lost_allergy = allergy_list[index-1].difference(set(same_allergy.keys()))
                                reason = '前次就诊次过敏史<{0}>不存在于本次过敏史<{1}>中'.format('，'.join(lost_allergy), '，'.join(allergy_list[index]))
                                if not allergy_list[index]:
                                    reason = '前次就诊次过敏史<{0}>不存在于本次过敏史<null>中'.format('，'.join(lost_allergy))
                                if self.debug:
                                    self.logger.info('\n多个就诊次既往史过敏JWS0011：\n\tid: {0}\n\tlast_allergy: {1}\n\tthis_allergy: {2}\n'.
                                                     format(id_list[index],
                                                            '/'.join(allergy_list[index-1]),
                                                            '/'.join(allergy_list[index])))
                                error_info = {'code': 'RYJLJWS0011',
                                              'num': num_list[index],
                                              'last_id': id_list[index-1],
                                              'reason': reason}
                                error_info = self.supplementErrorInfo(error_info=error_info,
                                                                      creator_name=creator_list[index],
                                                                      file_time_value=create_time[index],
                                                                      last_modify_date_time=time_list[index],
                                                                      collection_name=collection_name)
                                if 'score' in error_info:
                                    patient_list[index]['pat_info']['machine_score'] += error_info['score']
                                patient_list[index]['pat_value'].append(error_info)
                                patient_list[index]['pat_info'].setdefault('html', list())
                                if collection_name not in patient_list[index]['pat_info']['html']:
                                    patient_list[index]['pat_info']['html'].append(collection_name)
                                num_list[index] += 1
                                self.all_result[id_list[index]] = patient_list[index]

                if self.filter_dept('RYJLGRS0001', json_file):
                    if any(smoke_list) and len(smoke_list) > 1:  # RYJLGRS0001
                        for index in range(1, len(smoke_list)):
                            dept = patient_list[index]['pat_info'].get('dept_discharge_from_name', '') or patient_list[index]['pat_info'].get('dept_admission_to_name', '')
                            if dept not in ['心血管科', '心脏外科', '呼吸科', '老年病内科', '胸外科', '肿瘤化疗与放射病科', '肿瘤放疗科']:
                                continue
                            if detect_id and id_list[index] != detect_id:  # 如果有目标 id，那么只检测目标 id
                                continue
                            if not (start_date < patient_list[index]['pat_info'].get('discharge_time', '') < end_date) and (not json_file):
                                continue
                            if not smoke_list[index]:
                                if smoke_list[index-1]:
                                    reason = '前次吸烟史未在本次吸烟史中记录'
                                    error_info = {'code': 'RYJLGRS0001',
                                                  'num': num_list[index],
                                                  'last_id': id_list[index-1],
                                                  'reason': reason}
                                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                                          creator_name=creator_list[index],
                                                                          file_time_value=create_time[index],
                                                                          last_modify_date_time=time_list[index],
                                                                          collection_name=collection_name)
                                    if 'score' in error_info:
                                        patient_list[index]['pat_info']['machine_score'] += error_info['score']
                                    patient_list[index]['pat_value'].append(error_info)
                                    patient_list[index]['pat_info'].setdefault('html', list())
                                    if collection_name not in patient_list[index]['pat_info']['html']:
                                        patient_list[index]['pat_info']['html'].append(collection_name)
                                    num_list[index] += 1
                                    self.all_result[id_list[index]] = patient_list[index]
                # 查看是否有重复src内容, 返回重复内容的序列号, 双重list
                if self.filter_dept('RYJLZS0003', json_file):
                    repeat_index = self.gain_info._check_repeat_content(chief_list)
                    if repeat_index:
                        repeat_res = list()
                        for idx_list in repeat_index:  # repeat_index = [[x, y]], idx_list = [x, y]
                            if detect_id:  # 如果目标 id 的index 不在重复的id序号 idx_list中，则跳过不检测
                                if id_list.index(detect_id) not in idx_list:
                                    continue
                            repeat = list()
                            for idx_idx in range(1, len(idx_list)):
                                if len(time_list[idx_list[idx_idx-1]]) < 10 or len(time_list[idx_list[idx_idx]]) < 10:  # 有时间为空的情况
                                    continue
                                visit_date_1 = datetime.strptime(time_list[idx_list[idx_idx-1]][:10], '%Y-%m-%d')
                                visit_date_2 = datetime.strptime(time_list[idx_list[idx_idx]][:10], '%Y-%m-%d')
                                if abs((visit_date_1-visit_date_2).days) >= 365:
                                    if idx_list[idx_idx-1] not in repeat:
                                        repeat.append(idx_list[idx_idx-1])
                                        repeat.append(idx_list[idx_idx])
                                    else:
                                        repeat.append(idx_list[idx_idx])
                            if repeat:
                                repeat_res.append(repeat)  # 保存时间相隔一年以上的重复文书的序号

                        if repeat_res:
                            for idx_list in repeat_res:
                                for idx in idx_list:
                                    repeat_file = list()
                                    for repeat_id in id_list:
                                        if id_list.index(repeat_id) == idx:
                                            continue
                                        if id_list.index(repeat_id) not in idx_list:
                                            continue
                                        repeat_file.append({'_id': repeat_id,
                                                            'last_modify_date_time': time_list[id_list.index(repeat_id)],
                                                            'chief_src': chief_list[id_list.index(repeat_id)],
                                                            'creator_name': creator_list[id_list.index(repeat_id)]})
                                    if not (start_date < patient_list[idx]['pat_info'].get('discharge_time', '') < end_date) and (not json_file):
                                        continue
                                    if self.conf_dict['check_repeat'].findall(chief_list[idx]):  # 过滤含特定词的src
                                        continue
                                    reason = '同一病人病历文书时间间隔一年以上，主诉内容相同'
                                    error_info = {'code': 'RYJLZS0003',
                                                  'num': num_list[idx],
                                                  'chief_src': chief_list[idx],
                                                  'error_file': repeat_file,
                                                  'reason': reason}
                                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                                          creator_name=creator_list[idx],
                                                                          file_time_value=create_time[idx],
                                                                          last_modify_date_time=time_list[idx],
                                                                          collection_name=collection_name)
                                    if 'score' in error_info:
                                        patient_list[idx]['pat_info']['machine_score'] += error_info['score']
                                    patient_list[idx]['pat_value'].append(error_info)
                                    patient_list[idx]['pat_info'].setdefault('html', list())
                                    if collection_name not in patient_list[idx]['pat_info']['html']:
                                        patient_list[idx]['pat_info']['html'].append(collection_name)
                                    num_list[idx] += 1
                                    self.all_result[id_list[idx]] = patient_list[idx]

                if self.filter_dept('RYJLXBS0006', json_file):
                    repeat_index = self.gain_info._check_repeat_content(present_list)
                    if repeat_index:
                        repeat_res = list()
                        for idx_list in repeat_index:  # repeat_index = [[x, y]], idx_list = [x, y]
                            if detect_id:  # 如果目标 id 的index 不在重复的id序号 idx_list中，则跳过不检测
                                if id_list.index(detect_id) not in idx_list:
                                    continue
                            repeat = list()
                            for idx_idx in range(1, len(idx_list)):
                                if idx_list[idx_idx] - idx_list[idx_idx] == 1:  # 现病史为相邻就诊次相同就检测出
                                    if idx_list[idx_idx-1] not in repeat:
                                        repeat.append(idx_list[idx_idx-1])
                                        repeat.append(idx_list[idx_idx])
                                    else:
                                        repeat.append(idx_list[idx_idx])
                            if repeat:
                                repeat_res.append(repeat)  # 保存时间相隔一年以上的重复文书的序号

                        if repeat_res:
                            for idx_list in repeat_res:
                                for idx in idx_list:
                                    repeat_file = list()
                                    for repeat_id in id_list:
                                        if id_list.index(repeat_id) == idx:
                                            continue
                                        if id_list.index(repeat_id) not in idx_list:
                                            continue
                                        repeat_file.append({'_id': repeat_id,
                                                            'last_modify_date_time': time_list[id_list.index(repeat_id)],
                                                            'creator_name': creator_list[id_list.index(repeat_id)]})
                                    if not (start_date < patient_list[idx]['pat_info'].get('discharge_time', '') < end_date) and (not json_file):
                                        continue
                                    reason = '同一病人相邻就诊次，现病史内容相同'
                                    error_info = {'code': 'RYJLXBS0006',
                                                  'num': num_list[idx],
                                                  'present_src': present_list[idx],
                                                  'error_file': repeat_file,
                                                  'reason': reason}
                                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                                          creator_name=creator_list[idx],
                                                                          file_time_value=create_time[idx],
                                                                          last_modify_date_time=time_list[idx],
                                                                          collection_name=collection_name)
                                    if 'score' in error_info:
                                        patient_list[idx]['pat_info']['machine_score'] += error_info['score']
                                    patient_list[idx]['pat_value'].append(error_info)
                                    patient_list[idx]['pat_info'].setdefault('html', list())
                                    if collection_name not in patient_list[idx]['pat_info']['html']:
                                        patient_list[idx]['pat_info']['html'].append(collection_name)
                                    num_list[idx] += 1
                                    self.all_result[id_list[idx]] = patient_list[idx]
            except:
                self.logger_error.error(data)
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_present_tigejiancha(self, collection_name, **json_file):
        """
        collection = ruyuanjilu
        现病史含“偏瘫”字段，体格检查含“四肢活动自如” or 现病史含“昏迷”字段，体格检查含神志清/查体合作/语音震颤任一个 -->检出
        RYJLTGJC0002
        """
        if json_file and self.filter_dept('RYJLTGJC0002', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                creator_name = collection_data.get(collection_name, dict()).get('creator_name', '')
                last_modify_date_time = collection_data.get(collection_name, dict()).get('last_modify_date_time', '')
                file_time_value = collection_data.get(collection_name, dict()).get('file_time_value', '')
                batchno = collection_data.get('batchno', '')
                admission_time = data['binganshouye'].get('pat_visit', dict()).get('admission_time', '')
                if not collection_data.get(collection_name, dict()).get('diagnosis_name', ''):
                    continue
                diagnosis_name = self.gain_info._gain_diagnosis_name(collection_data[collection_name]['diagnosis_name'])
                physical_examination_src = self.gain_info._gain_src(cursor=collection_data,
                                                                    collection_name=collection_name,
                                                                    chapter_name='physical_examination')
                present_word = ''
                physical_examination_word = ''
                if self.gain_info._gain_same_content(['偏瘫'], diagnosis_name) and ('四肢活动自如' in physical_examination_src):
                    present_word = '偏瘫'
                    physical_examination_word = '四肢活动自如'
                elif self.gain_info._gain_same_content(['昏迷'], diagnosis_name):
                    present_word = '昏迷'
                    if not admission_time:
                        continue
                    if (datetime.strptime(file_time_value[:10], '%Y-%m-%d') - datetime.strptime(admission_time[:10], '%Y-%m-%d')).days > 3:
                        continue
                    if '神志清' in physical_examination_src:
                        physical_examination_word = '神志清'
                    elif '查体合作' in physical_examination_src:
                        physical_examination_word = '查体合作'
                    elif '语音震颤' in physical_examination_src:
                        physical_examination_word = '语音震颤'
                    else:
                        continue
                if present_word:
                    if self.debug:
                        self.logger.info('\n初步诊断与体格检查矛盾TGJC0002:\n\tid: {0}\n\t初步诊断: {1}\n\t体格检查: {2}\n\tbatchno: {3}\n'.
                                         format(data['_id'],
                                                '，'.join(diagnosis_name),
                                                physical_examination_src,
                                                batchno))
                    reason = '现病史含<{0}>，体格检查不应含<{1}>'.format(present_word, physical_examination_word)
                    error_info = {'code': 'RYJLTGJC0002',
                                  'num': num,
                                  'diagnosis_name': '，'.join(diagnosis_name),
                                  'physical_examination_src': physical_examination_src,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_diagnosis_xinjie(self, collection_name, **json_file):
        """
        collection = ruyuanjilu
        初步诊断--疾病名称含“心界”字段，专科查体不含“心界”字段
        RYJLZKJC0002
        """
        if json_file and self.filter_dept('RYJLZKJC0002', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data.get(collection_name, dict()).get('diagnosis_name', ''):
                    continue
                diagnosis_name = self.gain_info._gain_diagnosis_name(collection_data[collection_name]['diagnosis_name'])
                if '心界' not in diagnosis_name:
                    continue
                if collection_data.get(collection_name, dict()).get('special_examination', dict()).get('heart_border', ''):
                    continue
                if '心界' in collection_data.get(collection_name, dict()).get('special_examination', dict()).get('src', ''):
                    continue
                creator_name = collection_data.get(collection_name, dict()).get('creator_name', '')
                last_modify_date_time = collection_data.get(collection_name, dict()).get('last_modify_date_time', '')
                file_time_value = collection_data.get(collection_name, dict()).get('file_time_value', '')
                reason = '初步诊断含<心界>，专科查体不含<心界>检查'
                error_info = {'code': 'RYJLZKJC0002',
                              'num': num,
                              'diagnosis_name': '，'.join(diagnosis_name),
                              'reason': reason}
                error_info = self.supplementErrorInfo(error_info=error_info,
                                                      creator_name=creator_name,
                                                      file_time_value=file_time_value,
                                                      last_modify_date_time=last_modify_date_time,
                                                      collection_name=collection_name)
                if 'score' in error_info:
                    patient_result['pat_info']['machine_score'] += error_info['score']
                patient_result['pat_value'].append(error_info)
                mq_id = data['_id']
                patient_result['pat_info'].setdefault('html', list())
                if collection_name not in patient_result['pat_info']['html']:
                    patient_result['pat_info']['html'].append(collection_name)
                self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_diagnosis_fangchan(self, collection_name, **json_file):
        """
        collection = ruyuanjilu
        （初步诊断含“房颤”字段 and 体格检查--心率 < 脉搏） or （初步诊断不含“房颤”字段 and 心率 ≠ 脉搏） -->检出
        RYJLTGJC0003
        """
        if json_file and self.filter_dept('RYJLTGJC0003', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result

        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data.get(collection_name, dict()).get('diagnosis_name', ''):
                    continue
                if not collection_data.get(collection_name, dict()).get('physical_examination', dict()).get('heart_rate', ''):
                    continue
                if not collection_data.get(collection_name, dict()).get('physical_examination', dict()).get('pulse', ''):
                    continue
                creator_name = collection_data.get(collection_name, dict()).get('creator_name', '')
                last_modify_date_time = collection_data.get(collection_name, dict()).get('last_modify_date_time', '')
                file_time_value = collection_data.get(collection_name, dict()).get('file_time_value', '')
                in_flag = False
                for diag_name in collection_data[collection_name]['diagnosis_name']:
                    if '房颤' in diag_name.get('diagnosis_name', ''):
                        in_flag = True
                        break
                heart_rate = int(re.search('\d+', collection_data[collection_name]['physical_examination']['heart_rate']).group())
                pulse = int(re.search('\d+', collection_data[collection_name]['physical_examination']['pulse']).group())
                if in_flag and (heart_rate < pulse):
                    reason = '初步诊断含<房颤>，体格检查<心率>小于<脉搏>'
                elif (not in_flag) and (heart_rate != pulse):
                    reason = '初步诊断不含<房颤>，体格检查<心率>不等于<脉搏>'
                else:
                    continue
                error_info = {'code': 'RYJLTGJC0003',
                              'num': num,
                              'reason': reason}
                error_info = self.supplementErrorInfo(error_info=error_info,
                                                      creator_name=creator_name,
                                                      file_time_value=file_time_value,
                                                      last_modify_date_time=last_modify_date_time,
                                                      collection_name=collection_name)
                if 'score' in error_info:
                    patient_result['pat_info']['machine_score'] += error_info['score']
                patient_result['pat_value'].append(error_info)
                mq_id = data['_id']
                patient_result['pat_info'].setdefault('html', list())
                if collection_name not in patient_result['pat_info']['html']:
                    patient_result['pat_info']['html'].append(collection_name)
                self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_zhuankejiancha_tanhuan(self, collection_name, **json_file):
        """
        collection = ruyuanjilu
        初步诊断--疾病名称含“瘫痪/Frankel A/Frankel B/Frankel C/ASIA A/ASIA B/ASIA C”字段 and
        专科检查--骨科专科检查--所有运动系统检查左上肢/右上肢/左下肢/右下肢** （enum）值均==5 (29-68)-->检出
        RYJLZKJC0003
        """
        if json_file and self.filter_dept('RYJLZKJC0003', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data.get(collection_name, dict()).get('diagnosis_name', ''):
                    continue
                creator_name = collection_data.get(collection_name, dict()).get('creator_name', '')
                last_modify_date_time = collection_data.get(collection_name, dict()).get('last_modify_date_time', '')
                file_time_value = collection_data.get(collection_name, dict()).get('file_time_value', '')
                diagnosis_name = self.gain_info._gain_diagnosis_name(collection_data[collection_name]['diagnosis_name'])
                target_name = ['瘫痪', 'FrankelA', 'FrankelB', 'FrankelC', 'ASIAA', 'ASIAB', 'ASIAC']
                same_flag = self.gain_info._gain_same_content(target_name, diagnosis_name)
                reason_name = list(same_flag.keys())
                if not reason_name:
                    continue
                else:
                    exam_grade = collection_data.get(collection_name, dict()).get('special_examination', dict()).get('orthopedic_exam', dict())
                    target_grade = {
                        'l_levator_scapulae_strength': 'V',
                        'r_levator_scapulae_strength': 'V',
                        'l_deltoid_strength': 'V',
                        'r_deltoid_strength': 'V',
                        'l_bicep_strength': 'V',
                        'r_bicep_strength': 'V',
                        'l_tricep_strength': 'V',
                        'r_tricep_strength': 'V',
                        'l_extensor_carpi_strength': 'V',
                        'r_extensor_carpi_strength': 'V',
                        'l_flexor_carpi_strength': 'V',
                        'r_flexor_carpi_strength': 'V',
                        'l_trapezius_strength': 'V',
                        'r_trapezius_strength': 'V',
                        'l_brachioradialis_strength': 'V',
                        'r_brachioradialis_strength': 'V',
                        'l_extensor_finger_strength': 'V',
                        'r_extensor_finger_strength': 'V',
                        'l_flexor_finger_strength': 'V',
                        'r_flexor_finger_strength': 'V',
                        'l_abductor_minim_strength': 'V',
                        'r_abductor_minim_strength': 'V',
                        'l_grip_strength': 'V',
                        'r_grip_strength': 'V',
                        'l_iliopsoas_strength': 'V',
                        'r_iliopsoas_strength': 'V',
                        'l_quadriceps_femoris_strength': 'V',
                        'r_quadriceps_femoris_strength': 'V',
                        'l_hamstring_strength': 'V',
                        'r_hamstring_strength': 'V',
                        'l_tibialis_anterior_strength': 'V',
                        'r_tibialis_anterior_strength': 'V',
                        'l_triceps_surae_strength': 'V',
                        'r_triceps_surae_strength': 'V',
                        'l_extensor_digitorum_strength': 'V',
                        'r_extensor_digitorum_strength': 'V',
                        'l_peroneus_strength': 'V',
                        'r_peroneus_strength': 'V',
                        'l_thumb_extensor_strength': 'V',
                        'r_thumb_extensor_strength': 'V',
                    }
                    flag = False
                    for k, v in target_grade.items():
                        if exam_grade.get(k, '') != v:
                            flag = True
                            break
                    if flag:
                        continue
                reason = '初步诊断含<{0}>，专科检查运动系统检查上下肢值全部为5'.format('，'.join(reason_name))
                error_info = {'code': 'RYJLZKJC0003',
                              'num': num,
                              'reason': reason}
                error_info = self.supplementErrorInfo(error_info=error_info,
                                                      creator_name=creator_name,
                                                      file_time_value=file_time_value,
                                                      last_modify_date_time=last_modify_date_time,
                                                      collection_name=collection_name)
                if 'score' in error_info:
                    patient_result['pat_info']['machine_score'] += error_info['score']
                patient_result['pat_value'].append(error_info)
                mq_id = data['_id']
                patient_result['pat_info'].setdefault('html', list())
                if collection_name not in patient_result['pat_info']['html']:
                    patient_result['pat_info']['html'].append(collection_name)
                self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_yuejingshi(self, collection_name, **json_file):
        """
        collection = ruyuanjilu
        病案首页-基本信息-性别名称==“女” and 住院首页手术-手术与操作名称==非NULL
        入院记录-月经婚育史-初潮年龄、行经期天数、38行至71行绝经后异常症状全部==NULL -->检出
        RYJLHY0001
        """
        if json_file and self.filter_dept('RYJLHY0001', json_file):
            if json_file.get('binganshouye', dict()).get('pat_info', dict()).get('sex_name') != '女':
                return self.all_result
            if (int(json_file.get('binganshouye', dict()).get('pat_visit', dict()).get('age_value', 0)) < 14) and json_file.get('binganshouye', dict()).get('pat_visit', dict()).get('age_value_unit', '') == '岁':  # 年龄过滤
                return self.all_result
            mongo_result = [json_file]
        else:
            return self.all_result

        for data in mongo_result:
            try:
                shouyeshoushu_result_list = data.get('shouyeshoushu', list())  # 获取首页手术
                shouyeshoushu_result = dict()
                if shouyeshoushu_result_list:
                    shouyeshoushu_result = shouyeshoushu_result_list[0]
                if not shouyeshoushu_result:
                    continue
                if (int(data.get('binganshouye', dict()).get('pat_visit', dict()).get('age_value', 0)) < 14) and data.get('binganshouye', dict()).get('pat_visit', dict()).get('age_value_unit', '') == '岁':
                    continue
                if not shouyeshoushu_result.get('shouyeshoushu', dict()).get('operation_name'):
                    continue
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                dept = patient_result.get('pat_info', dict()).get('dept_discharge_from_name', '') or patient_result.get('pat_info', dict()).get('dept_admission_to_name', '')
                if not dept:
                    continue
                if dept == '眼科' or dept == '儿科':
                    continue
                menstrual_chapter = collection_data.get(collection_name, dict()).get('menstrual_and_obstetrical_histories', dict())
                if not menstrual_chapter:
                    continue
                exam_list = ['age_of_menarche', 'menstrual_days', 'menstrual_days_min', 'menstrual_days_max',
                             'menstrual_cycle', 'menstrual_cycle_min', 'menstrual_cycle_max', 'menstrual_cycle_regular',
                             'last_menstrual_period', 'last_menstrual_period_describe', 'menstrual_blood_volume',
                             'menstrual_color', 'menstrual_blood_clots', 'recent_menstrual_volume',
                             'recent_menstrual_cycle', 'menstrual_abnormal_cause', 'menstrual_abnormal_description',
                             'amenorrhea', 'amenorrhea_duration', 'dysmenorrhea', 'menopause_indicator', 'menopause_age',
                             'menopause_vaginal_abnormal', 'menopause_duration_describe', 'menopause_duration',
                             'menopause_symptom', 'obstetrics_and_gynecology_operation']
                for item in exam_list:
                    if item in menstrual_chapter:
                        continue
                creator_name = collection_data.get(collection_name, dict()).get('creator_name', '')
                last_modify_date_time = collection_data.get(collection_name, dict()).get('last_modify_date_time', '')
                file_time_value = collection_data.get(collection_name, dict()).get('file_time_value', '')
                src = self.gain_info._gain_src(cursor=collection_data,
                                               collection_name=collection_name,
                                               chapter_name='menstrual_and_obstetrical_histories')
                reason = '入院记录未记录月经史'
                error_info = {'code': 'RYJLHY0001',
                              'num': num,
                              'src': src,
                              'reason': reason}
                error_info = self.supplementErrorInfo(error_info=error_info,
                                                      creator_name=creator_name,
                                                      file_time_value=file_time_value,
                                                      last_modify_date_time=last_modify_date_time,
                                                      collection_name=collection_name)
                if 'score' in error_info:
                    patient_result['pat_info']['machine_score'] += error_info['score']
                patient_result['pat_value'].append(error_info)
                mq_id = data['_id']
                patient_result['pat_info'].setdefault('html', list())
                if collection_name not in patient_result['pat_info']['html']:
                    patient_result['pat_info']['html'].append(collection_name)
                self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_hypokalemia(self, collection_name, **json_file):
        """
        collection = ruyuanjilu
        检查低钾血症, 高钾血症, 低钠血症, 高钠血症, 贫血, 低白蛋白
        RYJLFZJC0002, RYJLFZJC0004, RYJLFZJC0005, RYJLFZJC0006, RYJLFZJC0007, RYJLFZJC0008
        """
        regular_code = ['RYJLFZJC0002', 'RYJLFZJC0004', 'RYJLFZJC0005', 'RYJLFZJC0006', 'RYJLFZJC0007', 'RYJLFZJC0008']
        regular_boolean = list()
        for i in regular_code:
            if self.regular_model.get(i, dict()).get('status') == '启用':
                regular_boolean.append(False)
            else:
                regular_boolean.append(True)
        if all(regular_boolean):
            return self.all_result
        if json_file:
            mongo_result = [json_file]
        else:
            return self.all_result

        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data.get(collection_name, dict()).get('auxiliary_examination', dict()).get('lab', ''):
                    continue
                creator_name = collection_data.get(collection_name, dict()).get('creator_name', '')
                last_modify_date_time = collection_data.get(collection_name, dict()).get('last_modify_date_time', '')
                file_time_value = collection_data.get(collection_name, dict()).get('file_time_value', '')
                file_time = data.get('binganshouye', dict()).get('pat_visit', dict()).get('admission_time', '')  # 获取入院时间
                if not file_time:
                    continue
                get_item = self.conf_dict['lab_check_hypokalemia']
                lab_model = collection_data[collection_name]['auxiliary_examination']['lab']
                lab_info = self.gain_info._gain_lab_info(lab_model, get_item)
                flag = {'lower_k': False,
                        'high_k': False,
                        'lower_na': False,
                        'high_na': False,
                        'low_blood': False,
                        'low_albumin': False}  # 低钾血，高钾血，低钠血，高钠血，贫血，低白蛋白
                for i in lab_info:
                    if 'lab_result_value' not in i:
                        continue
                    v = re.findall('[\d]+\.?[\d]*', i.get('lab_result_value', ''))
                    if not v:
                        continue
                    else:
                        v = v[0]
                    if 'lab_sub_item_name' in i:
                        if '钾' in i['lab_sub_item_name']:
                            if (i.get('report_time', '')[:10] == file_time[:10]) and (float(v) < 3.5):
                                flag['lower_k'] = True
                            elif (i.get('report_time', '')[:10] == file_time[:10]) and (float(v) >= 5.3):
                                flag['high_k'] = True
                        if '钠' in i['lab_sub_item_name']:
                            if (i.get('report_time', '')[:10] == file_time[:10]) and (float(v) < 137):
                                flag['lower_na'] = True
                            elif (i.get('report_time', '')[:10] == file_time[:10]) and (float(v) >= 147):
                                flag['high_na'] = True
                        if '血红蛋白' in i['lab_sub_item_name']:
                            if (i.get('report_time', '')[:10] == file_time[:10]) and (float(v) < 120):
                                flag['low_blood'] = True
                        if '白蛋白' in i['lab_sub_item_name']:
                            if (i.get('report_time', '')[:10] == file_time[:10]) and (float(v) < 30):
                                flag['low_albumin'] = True
                    if 'lab_sub_item_en_name' in i:
                        if 'k' == i['lab_sub_item_en_name'].lower():
                            if (i.get('report_time', '')[:10] == file_time[:10]) and (float(v) < 3.5):
                                flag['lower_k'] = True
                            elif (i.get('report_time', '')[:10] == file_time[:10]) and (float(v) >= 5.3):
                                flag['high_k'] = True
                        if 'na' == i['lab_sub_item_en_name'].lower():
                            if (i.get('report_time', '')[:10] == file_time[:10]) and (float(v) < 137):
                                flag['lower_na'] = True
                            elif (i.get('report_time', '')[:10] == file_time[:10]) and (float(v) >= 147):
                                flag['high_na'] = True
                        if 'hb' == i['lab_sub_item_en_name'].lower():
                            if (i.get('report_time', '')[:10] == file_time[:10]) and (float(v) < 120):
                                flag['low_blood'] = True

                push_flag = False
                if flag['lower_k'] and self.filter_dept('RYJLFZJC0002', json_file):
                    error_info = dict()
                    if 'diagnosis_name' in collection_data[collection_name]:
                        diagnosis_name = self.gain_info._gain_diagnosis_name(collection_data[collection_name]['diagnosis_name'])
                        same_flag = self.gain_info._gain_same_content(['低钾血症'], diagnosis_name)
                        if not same_flag:  # 没有低钾血症的话
                            reason = '初步诊断缺少检验中含有的低钾血症'
                            error_info = {'code': 'RYJLFZJC0002',
                                          'num': num,
                                          'diagnosis_name': '，'.join(diagnosis_name),
                                          'reason': reason}
                    else:
                        reason = '初步诊断缺少检验中含有的低钾血症'
                        error_info = {'code': 'RYJLFZJC0002',
                                      'num': num,
                                      'reason': reason}
                    if error_info:
                        push_flag = True
                        error_info = self.supplementErrorInfo(error_info=error_info,
                                                              creator_name=creator_name,
                                                              file_time_value=file_time_value,
                                                              last_modify_date_time=last_modify_date_time,
                                                              collection_name=collection_name)
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        num += 1

                if flag['high_k'] and self.filter_dept('RYJLFZJC0004', json_file):
                    error_info = dict()
                    if 'diagnosis_name' in collection_data[collection_name]:
                        diagnosis_name = self.gain_info._gain_diagnosis_name(collection_data[collection_name]['diagnosis_name'])
                        same_flag = self.gain_info._gain_same_content(['高钾血症'], diagnosis_name)
                        if not same_flag:
                            reason = '初步诊断缺少检验中含有的高钾血症'
                            error_info = {'code': 'RYJLFZJC0004',
                                          'num': num,
                                          'diagnosis_name': '，'.join(diagnosis_name),
                                          'reason': reason}
                    else:
                        reason = '初步诊断缺少检验中含有的高钾血症'
                        error_info = {'code': 'RYJLFZJC0004',
                                      'num': num,
                                      'reason': reason}
                    if error_info:
                        push_flag = True
                        error_info = self.supplementErrorInfo(error_info=error_info,
                                                              creator_name=creator_name,
                                                              file_time_value=file_time_value,
                                                              last_modify_date_time=last_modify_date_time,
                                                              collection_name=collection_name)
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        num += 1

                if flag['lower_na'] and self.filter_dept('RYJLFZJC0005', json_file):
                    error_info = dict()
                    if 'diagnosis_name' in collection_data[collection_name]:
                        diagnosis_name = self.gain_info._gain_diagnosis_name(collection_data[collection_name]['diagnosis_name'])
                        same_flag = self.gain_info._gain_same_content(['低钠血症'], diagnosis_name)
                        if not same_flag:
                            reason = '初步诊断缺少检验中含有的低钠血症'
                            error_info = {'code': 'RYJLFZJC0005',
                                          'num': num,
                                          'diagnosis_name': '，'.join(diagnosis_name),
                                          'reason': reason}
                    else:
                        reason = '初步诊断缺少检验中含有的低钠血症'
                        error_info = {'code': 'RYJLFZJC0005',
                                      'num': num,
                                      'reason': reason}
                    if error_info:
                        push_flag = True
                        error_info = self.supplementErrorInfo(error_info=error_info,
                                                              creator_name=creator_name,
                                                              file_time_value=file_time_value,
                                                              last_modify_date_time=last_modify_date_time,
                                                              collection_name=collection_name)
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        num += 1

                if flag['high_na'] and self.filter_dept('RYJLFZJC0006', json_file):
                    error_info = dict()
                    if 'diagnosis_name' in collection_data[collection_name]:
                        diagnosis_name = self.gain_info._gain_diagnosis_name(collection_data[collection_name]['diagnosis_name'])
                        same_flag = self.gain_info._gain_same_content(['高钠血症'], diagnosis_name)
                        if not same_flag:
                            reason = '初步诊断缺少检验中含有的高钠血症'
                            error_info = {'code': 'RYJLFZJC0006',
                                          'num': num,
                                          'diagnosis_name': '，'.join(diagnosis_name),
                                          'reason': reason}
                    else:
                        reason = '初步诊断缺少检验中含有的高钠血症'
                        error_info = {'code': 'RYJLFZJC0006',
                                      'num': num,
                                      'reason': reason}
                    if error_info:
                        push_flag = True
                        error_info = self.supplementErrorInfo(error_info=error_info,
                                                              creator_name=creator_name,
                                                              file_time_value=file_time_value,
                                                              last_modify_date_time=last_modify_date_time,
                                                              collection_name=collection_name)
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        num += 1

                if flag['low_blood'] and self.filter_dept('RYJLFZJC0007', json_file):
                    error_info = dict()
                    if 'diagnosis_name' in collection_data[collection_name]:
                        diagnosis_name = self.gain_info._gain_diagnosis_name(collection_data[collection_name]['diagnosis_name'])
                        same_flag = self.gain_info._gain_same_content(['贫血'], diagnosis_name)
                        if not same_flag:
                            reason = '初步诊断缺少检验中含有的贫血'
                            error_info = {'code': 'RYJLFZJC0007',
                                          'num': num,
                                          'diagnosis_name': '，'.join(diagnosis_name),
                                          'reason': reason}
                    else:
                        reason = '初步诊断缺少检验中含有的贫血'
                        error_info = {'code': 'RYJLFZJC0007',
                                      'num': num,
                                      'reason': reason}
                    if error_info:
                        push_flag = True
                        error_info = self.supplementErrorInfo(error_info=error_info,
                                                              creator_name=creator_name,
                                                              file_time_value=file_time_value,
                                                              last_modify_date_time=last_modify_date_time,
                                                              collection_name=collection_name)
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        num += 1

                if flag['low_albumin'] and self.filter_dept('RYJLFZJC0008', json_file):
                    error_info = dict()
                    if 'diagnosis_name' in collection_data[collection_name]:
                        diagnosis_name = self.gain_info._gain_diagnosis_name(collection_data[collection_name]['diagnosis_name'])
                        same_flag = self.gain_info._gain_same_content(['低蛋白血症'], diagnosis_name)
                        if not same_flag:
                            reason = '初步诊断缺少检验中含有的低蛋白血症'
                            error_info = {'code': 'RYJLFZJC0008',
                                          'num': num,
                                          'diagnosis_name': '，'.join(diagnosis_name),
                                          'reason': reason}
                    else:
                        reason = '初步诊断缺少检验中含有的低蛋白血症'
                        error_info = {'code': 'RYJLFZJC0008',
                                      'num': num,
                                      'reason': reason}
                    if error_info:
                        push_flag = True
                        error_info = self.supplementErrorInfo(error_info=error_info,
                                                              creator_name=creator_name,
                                                              file_time_value=file_time_value,
                                                              last_modify_date_time=last_modify_date_time,
                                                              collection_name=collection_name)
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        num += 1

                if push_flag:
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_shoushujilu_chafang(self, collection_name, **json_file):
        """
        collection = shoushujilu
        手术记录--主刀医师、手术时间 and 手术时间前住院上级医师查房录src--TOPIC 不含有 该主刀医师名称 -->检出
        RCBC0017
        """
        if json_file and self.filter_dept('RCBC0017', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        # collection_shangjichafang = self.PushData.connectCollection(database_name=self.PushData.mongodb_database_name,
        #                                                             collection_name='shangjiyishichafanglu_src')
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                creator_name = ''
                last_modify_date_time = ''
                file_time_value = ''
                operation_time = ''
                surgeon = list()
                shoushujilu_model = collection_data.get(collection_name, list())
                for one_record in shoushujilu_model:
                    if 'operation_time' in one_record:
                        creator_name = one_record.get('creator_name', '')
                        last_modify_date_time = one_record.get('last_modify_date_time', '')
                        file_time_value = one_record.get('file_time_value', '')

                        # 获取所有手术中，手术时间较早的那一个
                        if not operation_time:
                            operation_time = one_record['operation_time']
                        else:
                            operation_time = one_record['operation_time'] if operation_time > one_record['operation_time'] else operation_time

                        # 获取手术时间较早的那次的 surgeon
                        if operation_time == one_record['operation_time']:
                            if one_record.get('surgeon', '') == '术':
                                continue
                            surgeon = one_record.get('surgeon', '').split('、')
                if not (operation_time and surgeon):
                    continue
                if not all(surgeon):
                    continue
                bingcheng_src_list = data.get('shangjiyishishoucibingchengjilu_src', list())
                bingcheng = dict()
                if bingcheng_src_list:
                    bingcheng = bingcheng_src_list[0]
                reason = ''
                if bingcheng:
                    in_flag = False
                    for one_record in bingcheng.get('shangjiyishishoucibingchengjilu', list()):
                        caption_date_time = one_record.get('caption_date_time', '')[:10]
                        if not caption_date_time:
                            continue
                        # 手术那天之后查房，跳过，手术当天不跳过
                        if caption_date_time > operation_time:
                            continue
                        if 'topic' not in one_record:
                            continue
                        for one_surgeon in surgeon:
                            if not one_surgeon:
                                continue
                            if one_surgeon in one_record['topic']:
                                in_flag = True
                                break
                        if in_flag:
                            break
                    if not in_flag:
                        reason = '手术患者缺失第一手术者查房记录'
                if not reason:
                    chafang_src_list = data.get('shangjiyishichafanglu_src', list())
                    chafang_src = dict()
                    if chafang_src_list:
                        chafang_src = chafang_src_list[0]
                    if not chafang_src:
                        continue
                    # chafang_src = collection_shangjichafang.find_one({'_id': data['_id'],
                    #                                                   'shangjiyishichafanglu.TOPIC': {'$exists': True},
                    #                                                   'shangjiyishichafanglu.CAPTION_DATE_TIME': {'$lt': operation_time}},  # 查房时间
                    #                                                  {'shangjiyishichafanglu.TOPIC': 1,
                    #                                                   'shangjiyishichafanglu.CAPTION_DATE_TIME': 1})
                    if not chafang_src:
                        reason = '手术时间前无查房记录'
                    else:
                        if 'shangjiyishichafanglu' not in chafang_src:
                            continue
                        in_flag = False
                        for one_record in chafang_src['shangjiyishichafanglu']:
                            caption_date_time = one_record.get('caption_date_time', '')[:10]
                            if not caption_date_time:
                                continue
                            # 手术那天之后查房，跳过，手术当天不跳过
                            if caption_date_time > operation_time:
                                continue
                            if 'topic' not in one_record:
                                continue
                            for one_surgeon in surgeon:
                                if not one_surgeon:
                                    continue
                                if one_surgeon in one_record['topic']:
                                    in_flag = True
                                    break
                            if in_flag:
                                break
                        if not in_flag:
                            reason = '手术患者缺失第一手术者查房记录'
                if reason:
                    error_info = {'code': 'RCBC0017',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    if 'shangjiyishichafanglu' not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append('shangjiyishichafanglu')
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_yizhu_shuxue(self, collection_name, **json_file):
        """
        collection = yizhu
        RCBC0018, RCBC0019
        """
        if self.regular_model.get('RCBC0018', dict()).get('status') != '启用' and self.regular_model.get('RCBC0019', dict()).get('status') != '启用':
            return self.all_result
        if json_file:
            mongo_result = [json_file]
        else:
            return self.all_result
        # collection_shangjichafang = self.PushData.connectCollection(database_name=self.PushData.mongodb_database_name,
        #                                                             collection_name='shangjiyishichafanglu_src')
        # collection_richangbingcheng = self.PushData.connectCollection(database_name=self.PushData.mongodb_database_name,
        #                                                               collection_name='richangbingchengjilu_src')
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                order_time = ''
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                for one_record in collection_data[collection_name]:
                    if ('order_class_name' in one_record) and one_record['order_class_name'] == '输血类':
                        if 'order_time' in one_record:
                            if not order_time:
                                order_time = one_record['order_time']
                            else:
                                order_time = one_record['order_time'] if order_time > one_record['operation_time'] else order_time
                if not order_time:
                    continue
                chafang_src_list = data.get('shangjiyishichafanglu_src', list())
                chafang_src = dict()
                if chafang_src_list:
                    chafang_src = chafang_src_list[0]
                # chafang_src = collection_shangjichafang.find_one({'_id': data['_id'],
                #                                                   'shangjiyishichafanglu.TOPIC': {'$exists': True},
                #                                                   'shangjiyishichafanglu.CAPTION_DATE_TIME': {'$gt': order_time}},
                #                                                  {'shangjiyishichafanglu.TOPIC': 1,
                #                                                   'shangjiyishichafanglu.CAPTION_DATE_TIME': 1,
                #                                                   'shangjiyishichafanglu.CREATOR_NAME': 1})
                if chafang_src and len(self.regular_model.get('RCBC0018', list())) > 6 and self.regular_model['RCBC0018'][6] == '启用' and self.filter_dept('RCBC0018', json_file):
                    flag = False
                    error_file = list()
                    for one_record in chafang_src.get('shangjiyishichafanglu', list()):
                        if 'caption_date_time' not in one_record:
                            continue
                        if one_record['caption_date_time'] < order_time:
                            continue
                        if 'topic' not in one_record:
                            continue
                        error_file.append({'file_time_value': one_record['caption_date_time'],
                                           'last_modify_date_time': one_record['last_modify_date_time'],
                                           'creator_name': one_record.get('creator_name', '')})
                        if one_record['topic'] == '输血病程' or one_record['topic'] == '输血记录':
                            flag = True
                            break
                    if not flag:
                        reason = '输血患者缺失输血记录'
                        error_info = {'code': 'RCBC0018',
                                      'error_file': error_file,
                                      'num': num,
                                      'reason': reason}
                        error_info = self.supplementErrorInfo(error_info=error_info,
                                                              collection_name='shangjiyishichafanglu')
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        mq_id = data['_id']
                        patient_result['pat_info'].setdefault('html', list())
                        if 'shangjiyishichafanglu' not in patient_result['pat_info']['html']:
                            patient_result['pat_info']['html'].append('shangjiyishichafanglu')
                        self.all_result[mq_id] = patient_result
                        num += 1

                richangbingcheng_src_list = data.get('richangbingchengjilu_src', list())
                richangbingcheng_src = dict()
                if richangbingcheng_src_list:
                    richangbingcheng_src = chafang_src_list[0]
                # richangbingcheng_src = collection_richangbingcheng.find_one({'_id': data['_id'],
                #                                                              'richangbingchengjilu.TOPIC': {'$exists': True},
                #                                                              'richangbingchengjilu.LAST_MODIFY_DATE_TIME': {'$gt': order_time}},
                #                                                             {'richangbingchengjilu.TOPIC': 1,
                #                                                              'richangbingchengjilu.CAPTION_DATE_TIME': 1,
                #                                                              'richangbingchengjilu.LAST_MODIFY_DATE_TIME': 1})
                if richangbingcheng_src and len(self.regular_model.get('RCBC0019', list())) > 6 and self.regular_model['RCBC0019'][6] == '启用' and self.filter_dept('RCBC0019', json_file):
                    flag = False
                    error_file = list()
                    for one_record in richangbingcheng_src.get('richangbingchengjilu', list()):
                        if 'caption_date_time' not in one_record:
                            continue
                        if one_record['caption_date_time'] < order_time:
                            continue
                        if 'topic' not in one_record:
                            continue
                        error_file.append({'last_modify_date_time': one_record['last_modify_date_time'],
                                           'file_time_value': one_record['caption_date_time'],
                                           'creator_name': one_record.get('creator_name', '')})
                        if one_record['topic'] == '输血病程' or one_record['topic'] == '输血记录':
                            flag = True
                            break
                    if not flag:
                        reason = '输血患者缺失输血记录'
                        error_info = {'code': 'RCBC0019',
                                      'error_file': error_file,
                                      'num': num,
                                      'reason': reason}
                        error_info = self.supplementErrorInfo(error_info=error_info,
                                                              collection_name='richangbingchengjilu')
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        mq_id = data['_id']
                        patient_result['pat_info'].setdefault('html', list())
                        if 'richangbingchengjilu' not in patient_result['pat_info']['html']:
                            patient_result['pat_info']['html'].append('richangbingchengjilu')
                        self.all_result[mq_id] = patient_result
                        num += 1
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_repeat_shangjichafang(self, collection_name, **json_file):
        """
        collection = shangjiyishichafanglu
        本次就诊次上级医师查房记录连续两天内容相同（src相同）
        RCBC0005
        """
        if json_file and self.filter_dept('RCBC0005', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                chafang_record = collection_data[collection_name]
                chafang_record.sort(key=lambda l: l['file_time_value'])
                flag = False
                creator_name = ''
                last_modify_date_time = ''
                file_time_value = ''
                for index in range(1, len(chafang_record)):
                    last_data = chafang_record[index-1]
                    if last_data.get('src', '').strip() and 'file_time_value' in last_data:
                        last_src = last_data['src']
                        last_time = last_data['file_time_value']
                    else:
                        continue
                    this_data = chafang_record[index]
                    if this_data.get('src', '').strip() and 'file_time_value' in this_data:
                        this_src = this_data['src']
                        this_time = this_data['file_time_value']
                    else:
                        continue
                    if (datetime.strptime(this_time[:10], '%Y-%m-%d')-datetime.strptime(last_time[:10], '%Y-%m-%d')).days == 1:
                        if re.sub("[，。,、]+", "", last_src) == re.sub("[，。,、]+", "", this_src):
                            flag = True
                            creator_name = this_data.get('creator_name', '')
                            last_modify_date_time = this_data.get('last_modify_date_time', '')
                            file_time_value = this_data.get('file_time_value', '')
                            break
                if flag:
                    reason = '上级医师查房记录连续两天内容相同'
                    error_info = {'code': 'RCBC0005',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_repeat_richangbingcheng(self, collection_name, **json_file):
        """
        collection = richangbingchengjilu
        本次就诊次日常病程记录连续两天内容相同（src相同） -->检出
        RCBC0006
        """
        if json_file and self.filter_dept('RCBC0006', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                chafang_record = collection_data.get(collection_name, list())
                chafang_record.sort(key=lambda l: l['file_time_value'])
                flag = False
                creator_name = ''
                last_modify_date_time = ''
                file_time_value = ''
                for index in range(1, len(chafang_record)):
                    last_data = chafang_record[index-1]
                    if last_data.get('src', '').strip() and 'file_time_value' in last_data:
                        last_src = last_data['src']
                        last_time = last_data['file_time_value']
                    else:
                        continue
                    this_data = chafang_record[index]
                    if this_data.get('src', '').strip() and 'file_time_value' in this_data:
                        this_src = this_data['src']
                        this_time = this_data['file_time_value']
                    else:
                        continue
                    if (datetime.strptime(this_time[:10], '%Y-%m-%d')-datetime.strptime(last_time[:10], '%Y-%m-%d')).days == 1:
                        if re.sub("[，。,、]+", "", last_src) == re.sub("[，。,、]+", "", this_src):
                            flag = True
                            creator_name = this_data.get('creator_name', '')
                            last_modify_date_time = this_data.get('last_modify_date_time', '')
                            file_time_value = this_data.get('file_time_value', '')
                            break
                if flag:
                    reason = '日常病程记录连续两天内容相同'
                    error_info = {'code': 'RCBC0006',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_repeat_shuhoubingcheng(self, collection_name, **json_file):
        """
        collection = shuhoubingchengjilu
        本次就诊次术后病程记录连续两天内容相同（src相同） -->检出
        SHBC0002
        """
        if json_file and self.filter_dept('SHBC0002', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                chafang_record = collection_data[collection_name]
                chafang_record.sort(key=lambda l: l['file_time_value'])
                flag = False
                creator_name = ''
                file_time_value = ''
                last_modify_date_time = ''
                for index in range(1, len(chafang_record)):
                    last_data = chafang_record[index-1]
                    if last_data.get('src', '').strip() and 'file_time_value' in last_data:
                        last_src = last_data['src']
                        last_time = last_data['file_time_value']
                    else:
                        continue
                    this_data = chafang_record[index]
                    if this_data.get('src', '').strip() and 'file_time_value' in this_data:
                        this_src = this_data['src']
                        this_time = this_data['file_time_value']
                    else:
                        continue
                    if (datetime.strptime(this_time[:10], '%Y-%m-%d')-datetime.strptime(last_time[:10], '%Y-%m-%d')).days == 1:
                        if re.sub("[，。,、]+", "", last_src) == re.sub("[，。,、]+", "", this_src):
                            flag = True
                            creator_name = this_data.get('creator_name', '')
                            file_time_value = this_data.get('file_time_value', '')
                            last_modify_date_time = this_data.get('last_modify_date_time', '')
                            break
                if flag:
                    reason = '术后病程记录连续两天内容相同'
                    error_info = {'code': 'SHBC0002',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_chatirepeat_shangjichafang(self, collection_name, **json_file):
        """
        collection = shangjiyishichafanglu
        上级医师首次病程记录--当前病情记录--查体--（心率、血压） and
        所有上级医师查房记录--当前病情记录--查体--（心率、血压）连续两次查房记录相同 -->检出
        RCBC0014
        """
        if json_file and self.filter_dept('RCBC0014', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                chati_list = list()
                shoucibingcheng_list = data.get('shangjiyishishoucibingchengjilu', list())
                shoucibingcheng = dict()
                if shoucibingcheng_list:
                    shoucibingcheng = shoucibingcheng_list[0]
                # shoucibingcheng = collection_shouci.find_one({'_id': data['_id'],
                #                                               'shangjiyishishoucibingchengjilu': {'$exists': True},
                #                                               '$or': [{'shangjiyishishoucibingchengjilu.problem_list.physical_examination.heart_rate': {'$exists': True}},
                #                                                       {'shangjiyishishoucibingchengjilu.problem_list.physical_examination.blood_pressure': {'$exists': True}}]},
                #                                              {'shangjiyishishoucibingchengjilu.problem_list.physical_examination.heart_rate': 1,
                #                                               'shangjiyishishoucibingchengjilu.problem_list.physical_examination.blood_pressure': 1,
                #                                               'shangjiyishishoucibingchengjilu.problem_list.physical_examination.creator_name': 1,
                #                                               'shangjiyishishoucibingchengjilu.problem_list.physical_examination.file_time_value': 1,
                #                                               'shangjiyishishoucibingchengjilu.problem_list.physical_examination.last_modify_date_time': 1,
                #                                               })
                if shoucibingcheng:
                    one_record = shoucibingcheng.get('shangjiyishishoucibingchengjilu', dict())
                    if 'file_time_value' in one_record:
                        heart_rate = one_record.get('problem_list', dict()).get('physical_examination', dict()).get('heart_rate', '')
                        blood_pressure = one_record.get('problem_list', dict()).get('physical_examination', dict()).get('blood_pressure', '')
                        creator_name = one_record.get('creator_name', '')
                        last_modify_date_time = one_record.get('last_modify_date_time', '无文书时间')
                        if heart_rate or blood_pressure:
                            chati_list.append((heart_rate, blood_pressure, one_record['file_time_value'], creator_name, last_modify_date_time))
                for one_record in collection_data[collection_name]:
                    if 'file_time_value' in one_record:
                        heart_rate = one_record.get('problem_list', dict()).get('physical_examination', dict()).get('heart_rate', '')
                        blood_pressure = one_record.get('problem_list', dict()).get('physical_examination', dict()).get('blood_pressure', '')
                        creator_name = one_record.get('creator_name', '')
                        last_modify_date_time = one_record.get('last_modify_date_time', '无文书时间')
                        if heart_rate or blood_pressure:
                            chati_list.append((heart_rate, blood_pressure, one_record['file_time_value'], creator_name, last_modify_date_time))
                if not chati_list:
                    continue
                chati_list.sort(key=lambda l: l[2])
                repeat_item = list()
                last_modify_date_time = ''
                creator_name = ''
                file_time_value = ''
                for index in range(1, len(chati_list)):
                    if chati_list[index][0] == chati_list[index-1][0] and chati_list[index][0] != '':
                        repeat_item.append('心率')
                    if chati_list[index][1] == chati_list[index-1][1] and chati_list[index][1] != '':
                        repeat_item.append('血压')
                    if repeat_item:
                        file_time_value = chati_list[index][2]
                        creator_name = chati_list[index][3]
                        last_modify_date_time = chati_list[index][4]
                        break
                if repeat_item:
                    reason = '上级医师查房记录中<{0}>连续两次以上相同'.format('/'.join(repeat_item))
                    error_info = {'code': 'RCBC0014',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_chatirepeat_richangbingcheng(self, collection_name, **json_file):
        """
        collection = richangbingchengjilu
        所有日常病程记录--当前病情记录--查体--（心率、血压）连续两次病程记录相同 -->检出
        RCBC0015
        """
        if json_file and self.filter_dept('RCBC0015', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                chati_list = list()
                for one_record in collection_data[collection_name]:
                    if 'file_time_value' in one_record:
                        heart_rate = one_record.get('problem_list', dict()).get('physical_examination', dict()).get('heart_rate', '')
                        blood_pressure = one_record.get('problem_list', dict()).get('physical_examination', dict()).get('blood_pressure', '')
                        creator_name = one_record.get('creator_name', '')
                        last_modify_date_time = one_record.get('last_modify_date_time', '无文书时间')
                        if heart_rate or blood_pressure:
                            chati_list.append((heart_rate, blood_pressure, one_record['file_time_value'], creator_name, last_modify_date_time))
                if not chati_list:
                    continue
                chati_list.sort(key=lambda l: l[2])
                repeat_item = list()
                last_modify_date_time = ''
                creator_name = ''
                file_time_value = ''
                for index in range(1, len(chati_list)):
                    if chati_list[index][0] == chati_list[index-1][0] and chati_list[index][0] != '':
                        repeat_item.append('心率')
                    if chati_list[index][1] == chati_list[index-1][1] and chati_list[index][1] != '':
                        repeat_item.append('血压')
                    if repeat_item:
                        file_time_value = chati_list[index][2]
                        creator_name = chati_list[index][3]
                        last_modify_date_time = chati_list[index][4]
                        break
                if repeat_item:
                    reason = '日常病程记录中<{0}>连续两次以上相同'.format('/'.join(repeat_item))
                    error_info = {'code': 'RCBC0015',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_chatirepeat_shuhoubingcheng(self, collection_name, **json_file):
        """
        collection = shuhoubingchengjilu
        所有术后病程记录--当前病情记录--查体--（心率、血压）连续两次术后病程记录相同 -->检出
        SHBC0007
        """
        if json_file and self.filter_dept('SHCB0007', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                chati_list = list()
                for one_record in collection_data[collection_name]:
                    if 'file_time_value' in one_record:
                        heart_rate = one_record.get('problem_list', dict()).get('physical_examination', dict()).get('heart_rate', '')
                        blood_pressure = one_record.get('problem_list', dict()).get('physical_examination', dict()).get('blood_pressure', '')
                        creator_name = one_record.get('creator_name', '')
                        last_modify_date_time = one_record.get('last_modify_date_time', '无文书时间')
                        if heart_rate or blood_pressure:
                            chati_list.append((heart_rate, blood_pressure, one_record['file_time_value'], creator_name, last_modify_date_time))
                if not chati_list:
                    continue
                chati_list.sort(key=lambda l: l[2])
                repeat_item = list()
                last_modify_date_time = ''
                creator_name = ''
                file_time_value = ''
                for index in range(1, len(chati_list)):
                    if chati_list[index][0] == chati_list[index-1][0] and chati_list[index][0] != '':
                        repeat_item.append('心率')
                    if chati_list[index][1] == chati_list[index-1][1] and chati_list[index][1] != '':
                        repeat_item.append('血压')
                    if repeat_item:
                        file_time_value = chati_list[index][2]
                        creator_name = chati_list[index][3]
                        last_modify_date_time = chati_list[index][4]
                        break
                if repeat_item:
                    reason = '术后病程记录中<{0}>连续两次以上相同'.format('/'.join(repeat_item))
                    error_info = {'code': 'SHBC0007',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_exist_shangjichafang(self, collection_name, **json_file):
        """
        collection = shangjiyishichafanglu
        上级医师查房记录--src==NULL
        RCBC0008
        """
        if json_file and self.filter_dept('RCBC0008', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                flag = False
                creator_name = ''
                last_modify_date_time = ''
                file_time_value = ''
                for one_record in collection_data[collection_name]:
                    if 'src' not in one_record:
                        flag = True
                        creator_name = one_record.get('creator_name', '')
                        file_time_value = one_record.get('file_time_value', '')
                        last_modify_date_time = one_record.get('last_modify_date_time', '')
                        break
                    elif len(one_record['src']) <= 3:
                        flag = True
                        creator_name = one_record.get('creator_name', '')
                        file_time_value = one_record.get('file_time_value', '')
                        last_modify_date_time = one_record.get('last_modify_date_time', '')
                        break
                if flag:
                    reason = '上级医师查房记录为空'
                    error_info = {'code': 'RCBC0008',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_exist_richangbingcheng(self, collection_name, **json_file):
        """
        collection = richangbingchengjilu
        日常病程记录--src==NULL -->检出
        RCBC0007
        """
        if json_file and self.filter_dept('RCBC0007', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                flag = False
                creator_name = ''
                file_time_value = ''
                last_modify_date_time = ''
                for one_record in collection_data[collection_name]:
                    if 'src' not in one_record:
                        flag = True
                        creator_name = one_record.get('creator_name', '')
                        file_time_value = one_record.get('file_time_value', '')
                        last_modify_date_time = one_record.get('last_modify_date_time', '')
                        break
                    elif len(one_record['src']) <= 3:
                        flag = True
                        creator_name = one_record.get('creator_name', '')
                        file_time_value = one_record.get('file_time_value', '')
                        last_modify_date_time = one_record.get('last_modify_date_time', '')
                        break
                if flag:
                    reason = '日常病程记录为空'
                    error_info = {'code': 'RCBC0007',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_exist_shangjishoucibingcheng(self, collection_name, **json_file):
        """
        collection = shangjiyishishoucibingchengjilu
        上级医师首次病程记录--src==NULL -->检出
        RCBC0009
        """
        if json_file and self.filter_dept('RCBC0009', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                flag = False
                creator_name = ''
                file_time_value = ''
                last_modify_date_time = ''
                one_record = collection_data[collection_name]
                if len(one_record.get('src', '')) <= 3:
                    flag = True
                    creator_name = one_record.get('creator_name', '')
                    file_time_value = one_record.get('file_time_value', '')
                    last_modify_date_time = one_record.get('last_modify_date_time', '')
                if flag:
                    reason = '上级医师首次病程记录为空'
                    error_info = {'code': 'RCBC0009',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result
    
    def check_exist_shuhoushoucichafang(self, collection_name, **json_file):
        """
        collection = shuhoushoucishangjiyishichangfangjilu
        术后首次上级医师查房记录--src==NULL -->检出
        RCBC0010
        """
        if json_file and self.filter_dept('RCBC0010', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                flag = False
                creator_name = ''
                file_time_value = ''
                last_modify_date_time = ''
                for one_record in collection_data[collection_name]:
                    if 'src' not in one_record:
                        flag = True
                        creator_name = one_record.get('creator_name', '')
                        file_time_value = one_record.get('file_time_value', '')
                        last_modify_date_time = one_record.get('last_modify_date_time', '')
                        break
                    elif len(one_record['src']) <= 3:
                        flag = True
                        creator_name = one_record.get('creator_name', '')
                        file_time_value = one_record.get('file_time_value', '')
                        last_modify_date_time = one_record.get('last_modify_date_time', '')
                        break
                if flag:
                    reason = '术后首次上级医师查房记录为空'
                    error_info = {'code': 'RCBC0010',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_exist_shuhoubingcheng(self, collection_name, **json_file):
        """
        collection = shuhoubingchengjilu
        术后病程记录--src==NULL -->检出
        SHBC0004
        """
        if json_file and self.filter_dept('SHBC0004', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                flag = False
                creator_name = ''
                file_time_value = ''
                last_modify_date_time = ''
                for one_record in collection_data[collection_name]:
                    if 'src' not in one_record:
                        flag = True
                        creator_name = one_record.get('creator_name', '')
                        file_time_value = one_record.get('file_time_value', '')
                        last_modify_date_time = one_record.get('last_modify_date_time', '')
                        break
                    elif len(one_record['src']) <= 3:
                        flag = True
                        creator_name = one_record.get('creator_name', '')
                        file_time_value = one_record.get('file_time_value', '')
                        last_modify_date_time = one_record.get('last_modify_date_time', '')
                        break
                if flag:
                    reason = '术后病程记录为空'
                    error_info = {'code': 'SHBC0004',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_exist_shuhoushoucibingcheng(self, collection_name, **json_file):
        """
        collection = shuhoushoucibingchengjilu
        术后首次病程记录--src==NULL -->检出
        SHBC0005
        """
        if json_file and self.filter_dept('SHBC0005', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                flag = False
                creator_name = ''
                file_time_value = ''
                last_modify_date_time = ''
                for one_record in collection_data[collection_name]:
                    if 'src' not in one_record:
                        flag = True
                        creator_name = one_record.get('creator_name', '')
                        file_time_value = one_record.get('file_time_value', '')
                        last_modify_date_time = one_record.get('last_modify_date_time', '')
                        break
                    elif len(one_record['src']) <= 3:
                        flag = True
                        creator_name = one_record.get('creator_name', '')
                        file_time_value = one_record.get('file_time_value', '')
                        last_modify_date_time = one_record.get('last_modify_date_time', '')
                        break
                if flag:
                    reason = '术后首次病程记录为空'
                    error_info = {'code': 'SHBC0005',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
                # else:
                #     shoushujilu_list = data.get('shoushujilu', list())
                #     shoushu_result = dict()
                #     if shoushujilu_list:
                #         shoushu_result = shoushujilu_list[0]
                #     if not shoushu_result:
                #         continue
                #     if not shoushu_result.get('shoushujilu', list()):
                #         continue
                #     operation_time = shoushu_result.get('shoushujilu', list())[0].get('operation_time')
                #     if not operation_time:
                #         continue
                #     operation_date = operation_time[:10] if len(operation_time) > 10 else ''
                #     if not operation_date:
                #         continue
                #     shuhoubingchengjilu_list = data.get('shuhoubingchengjilu', list())
                #     shuhou_result = dict()
                #     if shuhoubingchengjilu_list:
                #         shuhou_result = shuhoubingchengjilu_list[0]
                #     if not shuhou_result:
                #         flag = True
                #     else:
                #         for one_record in shuhou_result.get('shuhoubingchengjilu', list()):
                #             if 'file_time_value' in one_record:
                #                 if len(one_record['file_time_value']) > 10:
                #                     if one_record['file_time_value'][:10] == operation_date or datetime.strptime(operation_date, '%Y-%m-%d') + timedelta(1) == datetime.strptime(one_record['file_time_value'][:10], '%Y-%m-%d'):
                #                         if not one_record.get('src'):
                #                             flag = True
                #                             creator_name = one_record.get('creator_name', '')
                #                             file_time_value = one_record.get('file_time_value', '')
                #                             last_modify_date_time = one_record.get('last_modify_date_time', '')
                #                         else:
                #                             flag = False
                #     if flag:
                #         reason = '手术日期后术后病程记录为空'
                #         error_info = {'code': 'SHBC0005',
                #                       'num': num,
                #                       'reason': reason}
                #         error_info = self.supplementErrorInfo(error_info=error_info,
                #                                               creator_name=creator_name,
                #                                               file_time_value=file_time_value,
                #                                               last_modify_date_time=last_modify_date_time,
                #                                               collection_name=collection_name)
                #         if 'score' in error_info:
                #             patient_result['pat_info']['machine_score'] += error_info['score']
                #         patient_result['pat_value'].append(error_info)
                #         mq_id = data['_id']
                #         patient_result['pat_info'].setdefault('html', list())
                #         if collection_name not in patient_result['pat_info']['html']:
                #             patient_result['pat_info']['html'].append(collection_name)
                #         self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_chati_shangjichafang(self, collection_name, **json_file):
        """
        collection = shangjiyishichafanglu
        上级医师查房记录--当前病情记录--查体--（体温、脉搏、心率、血压）任一为0 -->检出
        RCBC0012
        """
        if json_file and self.filter_dept('RCBC0012', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                creator_name = ''
                file_time_value = ''
                last_modify_date_time = ''
                items = set()
                for one_record in collection_data[collection_name]:
                    if 'problem_list' not in one_record:
                        continue
                    if 'physical_examination' not in one_record['problem_list']:
                        continue
                    if one_record['problem_list']['physical_examination'].get('temperature', '') == '0':
                        items.add('体温')
                    if one_record['problem_list']['physical_examination'].get('pulse', '') == '0':
                        items.add('脉搏')
                    if one_record['problem_list']['physical_examination'].get('breath', '') == '0':
                        items.add('呼吸')
                    if one_record['problem_list']['physical_examination'].get('systolic_pressure', '') == '0':
                        items.add('血压')
                    elif one_record['problem_list']['physical_examination'].get('diastolic_pressure', '') == '0':
                        items.add('血压')
                    if items:
                        creator_name = one_record.get('creator_name', '')
                        file_time_value = one_record.get('file_time_value', '')
                        last_modify_date_time = one_record.get('last_modify_date_time', '')
                if items:
                    reason = '上级医师查房记录中<{0}>为0'.format('/'.join(items))
                    error_info = {'code': 'RCBC0012',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_chati_shuhoushoucichafang(self, collection_name, **json_file):
        """
        collection = shuhoushoucishangjiyishichangfangjilu
        术后首次上级医师查房记录--当前病情记录--查体--（体温、脉搏、心率、血压）任一为0 -->检出
        RCBC0013
        """
        if json_file and self.filter_dept('RCBC0013', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                creator_name = ''
                file_time_value = ''
                last_modify_date_time = ''
                items = set()
                for one_record in collection_data[collection_name]:
                    if 'problem_list' not in one_record:
                        continue
                    if 'physical_examination' not in one_record['problem_list']:
                        continue
                    if one_record['problem_list']['physical_examination'].get('temperature', '') == '0':
                        items.add('体温')
                    if one_record['problem_list']['physical_examination'].get('pulse', '') == '0':
                        items.add('脉搏')
                    if one_record['problem_list']['physical_examination'].get('breath', '') == '0':
                        items.add('呼吸')
                    if one_record['problem_list']['physical_examination'].get('systolic_pressure', '') == '0':
                        items.add('血压')
                    elif one_record['problem_list']['physical_examination'].get('diastolic_pressure', '') == '0':
                        items.add('血压')
                    if items:
                        creator_name = one_record.get('creator_name', '')
                        file_time_value = one_record.get('file_time_value', '')
                        last_modify_date_time = one_record.get('last_modify_date_time', '')
                if items:
                    reason = '术后首次上级医师查房记录中<{0}>为0'.format('/'.join(items))
                    error_info = {'code': 'RCBC0013',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_chati_richangbingcheng(self, collection_name, **json_file):
        """
        collection = richangbingchengjilu
        日常病程记录--当前病情记录--查体--（体温、脉搏、心率、血压）任一为0 -->检出
        RCBC0011
        """
        if json_file and self.filter_dept('RCBC0011', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                creator_name = ''
                file_time_value = ''
                last_modify_date_time = ''
                items = set()
                for one_record in collection_data[collection_name]:
                    if '死亡' in one_record.get('src', ''):
                        continue
                    if 'problem_list' not in one_record:
                        continue
                    if 'physical_examination' not in one_record['problem_list']:
                        continue
                    if one_record['problem_list']['physical_examination'].get('temperature', '') == '0':
                        items.add('体温')
                    if one_record['problem_list']['physical_examination'].get('pulse', '') == '0':
                        items.add('脉搏')
                    if one_record['problem_list']['physical_examination'].get('breath', '') == '0':
                        items.add('呼吸')
                    if one_record['problem_list']['physical_examination'].get('systolic_pressure', '') == '0':
                        items.add('血压')
                    elif one_record['problem_list']['physical_examination'].get('diastolic_pressure', '') == '0':
                        items.add('血压')
                    if items:
                        creator_name = one_record.get('creator_name', '')
                        file_time_value = one_record.get('file_time_value', '')
                        last_modify_date_time = one_record.get('last_modify_date_time', '')
                if items:
                    reason = '日常病程记录中<{0}>为0'.format('/'.join(items))
                    error_info = {'code': 'RCBC0011',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_chati_shuhoubingcheng(self, collection_name, **json_file):
        """
        collection = shuhoubingchengjilu
        术后病程记录--当前病情记录--查体--（体温、脉搏、心率、血压）任一为0 -->检出
        SHBC0006
        """
        if json_file and self.filter_dept('SHBC0006', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                creator_name = ''
                file_time_value = ''
                last_modify_date_time = ''
                items = set()
                for one_record in collection_data[collection_name]:
                    if 'problem_list' not in one_record:
                        continue
                    if 'physical_examination' not in one_record['problem_list']:
                        continue
                    if one_record['problem_list']['physical_examination'].get('temperature', '') == '0':
                        items.add('体温')
                    if one_record['problem_list']['physical_examination'].get('pulse', '') == '0':
                        items.add('脉搏')
                    if one_record['problem_list']['physical_examination'].get('breath', '') == '0':
                        items.add('呼吸')
                    if one_record['problem_list']['physical_examination'].get('systolic_pressure', '') == '0':
                        items.add('血压')
                    elif one_record['problem_list']['physical_examination'].get('diastolic_pressure', '') == '0':
                        items.add('血压')
                    if items:
                        creator_name = one_record.get('creator_name', '')
                        file_time_value = one_record.get('file_time_value', '')
                        last_modify_date_time = one_record.get('last_modify_date_time', '')
                if items:
                    reason = '术后病程记录中<{0}>为0'.format('/'.join(items))
                    error_info = {'code': 'SHBC0006',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_shoushu_shuhoubingcheng(self, collection_name, **json_file):
        """
        collection = shoushujilu
        手术后第一天第二天有术后病程记录，没有则检出
        external = shuhoubingchengjilu
        SHBC0008
        """
        if json_file and self.filter_dept('SHBC0008', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                one_record = collection_data['shoushujilu'][0]
                operation_time = one_record.get('operation_time', '')
                if not operation_time:
                    continue
                discharge_time = patient_result['pat_info'].get('discharge_time', '')
                if not discharge_time:
                    continue
                creator_name = one_record.get('creator_name', '')
                last_modify_date_time = one_record.get('last_modify_date_time', '')
                file_time_value = one_record.get('file_time_value', '')
                operation_date = datetime.strptime(operation_time[:10], '%Y-%m-%d')
                discharge_date = datetime.strptime(discharge_time[:10], '%Y-%m-%d')
                if (discharge_date-operation_date).days >= 2:
                    day_flag = 2
                else:
                    day_flag = 1
                flag = False
                shuhoubingcheng_list = data.get('shuhoubingchengjilu', list())
                if shuhoubingcheng_list:
                    shuhoubingcheng = shuhoubingcheng_list[0]
                else:
                    shuhoubingcheng = dict()
                # shuhoubingcheng = collection_shuhou.find_one({'_id': data['_id'],
                #                                               'shuhoubingchengjilu.file_time_value': {'$exists': True}},
                #                                              {'shuhoubingchengjilu.file_time_value': 1})
                reason = ''
                if not shuhoubingcheng:
                    flag = True
                    reason = '未找到患者该就诊次有效术后病程记录'
                else:
                    file_time = [value.get('file_time_value') for value in shuhoubingcheng['shuhoubingchengjilu']]
                    file_time.sort()
                    if day_flag == 1:
                        one_flag = True
                        reason = '手术患者缺失术后第一天病程记录'
                        for t in file_time:
                            if not t:
                                continue
                            bingcheng_date = datetime.strptime(t[:10], '%Y-%m-%d')
                            if (bingcheng_date-operation_date).days == 1:
                                one_flag = False
                                break
                        flag = one_flag

                    elif day_flag == 2:
                        two_flag = True
                        one_flag = False
                        reason = '手术患者缺失术后第一天病程记录'
                        for t in file_time:
                            if not t:
                                continue
                            bingcheng_date = datetime.strptime(t[:10], '%Y-%m-%d')
                            if (bingcheng_date-operation_date).days == 1:
                                one_flag = True
                                reason = '手术患者缺失术后第二天病程记录'
                            elif one_flag and (bingcheng_date-operation_date).days == 2:
                                two_flag = False
                        flag = two_flag
                if flag:
                    error_info = {'code': 'SHBC0008',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_shoushu_creator(self, collection_name, **json_file):
        """
        collection = shoushujilu
        手术记录--主刀医师名称 不等于 手术记录--creator_name -->检出(永久起搏器植入之类的手术未检测)
        SSJL0004
        """
        if json_file and self.filter_dept('SSJL0004', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                one_record = collection_data['shoushujilu'][0]
                surgeon = one_record.get('surgeon', '')
                creator_name = one_record.get('creator_name', '')
                file_time_value = one_record.get('file_time_value', '')
                last_modify_date_time = one_record.get('last_modify_date_time', '')
                first_assistant = one_record.get('first_assistant', '')
                if (surgeon in creator_name) or (first_assistant in creator_name) or (creator_name in surgeon) or (creator_name in first_assistant):
                    if surgeon or surgeon == '术':
                        continue
                    else:
                        reason = '无主刀医师记录'
                else:
                    reason = '手术记录者不是主刀医师'
                error_info = {'code': 'SSJL0004',
                              'num': num,
                              'reason': reason}
                error_info = self.supplementErrorInfo(error_info=error_info,
                                                      creator_name=creator_name,
                                                      file_time_value=file_time_value,
                                                      last_modify_date_time=last_modify_date_time,
                                                      collection_name=collection_name)
                if 'score' in error_info:
                    patient_result['pat_info']['machine_score'] += error_info['score']
                patient_result['pat_value'].append(error_info)
                patient_result['pat_info'].setdefault('html', list())
                if collection_name not in patient_result['pat_info']['html']:
                    patient_result['pat_info']['html'].append(collection_name)
                self.all_result[data['_id']] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_yizhu_baguan(self, collection_name, **json_file):
        """
        collection = yizhu
        医嘱order_item_name里面找拔管记录 同日日常病程src里找TOPIC=拔管记录
        RCBC0002
        """
        if json_file and self.filter_dept('RCBC0002', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                record_list = list()
                for yizhu in collection_data[collection_name]:
                    if 'order_item_name' in yizhu:
                        if ('拔' in yizhu['order_item_name']) and ('管' in yizhu['order_item_name']):
                            if 'order_begin_time' in yizhu:
                                record_list.append(yizhu['order_begin_time'])
                if not record_list:
                    continue
                richang_src_list = data.get('richangbingchengjilu_src', list())
                if richang_src_list:
                    richang_src_data = richang_src_list[0]
                else:
                    richang_src_data = dict()
                # richang_src_data = collection_richang_src.find_one({'_id': data['_id'],
                #                                                     'richangbingchengjilu.TOPIC': '拔管记录'},
                #                                                    {'richangbingchengjilu.TOPIC': 1,
                #                                                     'richangbingchengjilu.LAST_MODIFY_DATE_TIME': 1})
                if not richang_src_data:
                    continue
                flag = False
                last_modify_date_time = ''
                file_time_value = ''
                creator_name = ''
                for richang_one in richang_src_data:
                    if 'caption_date_time' not in richang_one:
                        continue
                    if 'topic' not in richang_one:
                        continue
                    if richang_one['topic'] == '拔管记录':
                        for yizhu_time in record_list:
                            if richang_one['caption_date_time'][:10] == yizhu_time:
                                last_modify_date_time = richang_one.get('last_modify_date_time', '')
                                file_time_value = richang_one.get('caption_date_time', '')
                                flag = True
                                break
                    if flag:
                        break
                if not flag:
                    reason = '医嘱中有拔管记录，日常病程中无拔管记录'
                    error_info = {'code': 'RCBC0002',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if 'yizhu' not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append('yizhu')
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_baguanjilu(self, collection_name, **json_file):
        """
        collection = richangbingchengjilu
        日常病程记录文档模型中拔管模型的检测
        RCBC0003
        """
        if json_file and self.filter_dept('RCBC0003', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                extubation_num = 0
                for one_data in collection_data[collection_name]:
                    if 'extubation' in one_data:
                        extubation_num += 1
                if extubation_num <= 1:
                    continue
                for one_data in collection_data:
                    if 'extubation' not in one_data:
                        continue
                    reason = list()
                    flag = False
                    creator_name = one_data.get('creator_name', '')
                    file_time_value = one_data.get('file_time_value', '')
                    last_modify_date_time = one_data.get('last_modify_date_time', '')
                    if 'extubation_type' not in one_data['extubation']:
                        flag = True
                        reason.append('缺失拔管类型')
                    if 'extubation_position' not in one_data['extubation']:
                        flag = True
                        reason.append('缺失拔管位置')
                    if 'drainage_situation' in one_data['extubation']:
                        if 'drainage_volume' not in one_data['extubation']['drainage_situation']:
                            flag = True
                            reason.append('缺失拔管引流量')
                        elif 'drainage_desc' not in one_data['extubation']['drainage_situation']:
                            flag = True
                            reason.append('缺失拔管引流性状描述')
                    else:
                        reason.append('缺失拔管引流量，缺失拔管引流性状描述')
                    if flag:
                        reason = '，'.join(reason)
                        error_info = {'code': 'RCBC0003',
                                      'num': num,
                                      'reason': reason}
                        error_info = self.supplementErrorInfo(error_info=error_info,
                                                              creator_name=creator_name,
                                                              file_time_value=file_time_value,
                                                              last_modify_date_time=last_modify_date_time,
                                                              collection_name=collection_name)
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        num += 1
                        mq_id = data['_id']
                        patient_result['pat_info'].setdefault('html', list())
                        if collection_name not in patient_result['pat_info']['html']:
                            patient_result['pat_info']['html'].append(collection_name)
                        self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_operation_hematoma(self, collection_name, **json_file):
        """
        collection = shoushujilu
        判断患者为非第一次手术,该患者本次VISIT-1次术后病程记录 含“血肿”字样  本次就诊次术前小结/手术记录-术前诊断无“血肿”-->检出
        无术前小结
        SSJL0003
        """
        if json_file and self.filter_dept('SSJL0003', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        # 非第一次手术，且preoperative_diagnosis术前诊断存在
        # collection_shuhou = self.PushData.connectCollection(database_name=self.PushData.mongodb_database_name,
        #                                                     collection_name='shuhoubingchengjilu')
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                flag = False
                creator_name = ''
                file_time_value = ''
                last_modify_date_time = ''
                for one_data in collection_data[collection_name]:
                    if 'first_operation' not in one_data:
                        continue
                    if (one_data['first_operation'] != 'false') or (one_data['first_operation'] != '否') or one_data['first_operation']:
                        continue
                    if 'preoperative_diagnosis' not in one_data:
                        continue
                    if '血肿' not in one_data['preoperative_diagnosis']:
                        continue
                    flag = True
                    creator_name = one_data.get('creator_name', '')
                    file_time_value = one_data.get('file_time_value', '')
                    last_modify_date_time = one_data.get('last_modify_date_time', '')
                    break
                if not flag:  # flag == True 时表示非第一次手术，且术前诊断没有血肿
                    continue
                patient_id = patient_result['pat_info']['patient_id']
                visit_id = patient_result['pat_info']['visit_id']
                visit_id_pre = int(visit_id)-1
                while visit_id_pre > 0:
                    expression = [
                        [
                            {"field": "患者标识", "exp": "=", "flag": "or", "unit": "", "values": [patient_id]}
                        ],
                        [
                            {"field": "住院病案首页_就诊信息_就诊次数", "exp": "=", "flag": "or", "unit": "", "values": [str(visit_id_pre)]}
                        ]
                    ]
                    es_result = self.app_es.getId(expression)
                    if es_result.get('res_flag') and es_result.get('count', 0):
                        break
                    visit_id_pre -= 1
                if not visit_id_pre:
                    continue
                expression = [
                    [
                        {"field": "患者标识", "exp": "=", "flag": "or", "unit": "", "values": [patient_id]}
                    ],
                    [
                        {"field": "住院病案首页_就诊信息_就诊次数", "exp": "=", "flag": "or", "unit": "", "values": [str(visit_id_pre)]}
                    ],
                    [
                        {"field": "住院术后病程记录_当前病情记录_疾病名称", "exp": "=", "flag": "or", "unit": "", "values": ['血肿']}
                    ]
                ]
                es_result = self.app_es.getId(expression)
                if not es_result.get('res_flag'):
                    continue
                reason = '无前次手术术后疾病"血肿"。'
                error_info = {'code': 'SSJL0003',
                              'num': num,
                              'reason': reason}
                error_info = self.supplementErrorInfo(error_info=error_info,
                                                      creator_name=creator_name,
                                                      file_time_value=file_time_value,
                                                      last_modify_date_time=last_modify_date_time,
                                                      collection_name=collection_name)
                if 'score' in error_info:
                    patient_result['pat_info']['machine_score'] += error_info['score']
                patient_result['pat_value'].append(error_info)
                mq_id = data['_id']
                patient_result['pat_info'].setdefault('html', list())
                if collection_name not in patient_result['pat_info']['html']:
                    patient_result['pat_info']['html'].append(collection_name)
                self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_operation_tube(self, collection_name, **json_file):
        """
        collection = shoushujilu
        住院出院记录--出院注意事项不含“带管出院”字段 and 手术记录--置管个数 ≠ 手术日期后拔管记录--拔管数 -->检出
        SSJL0001
        """
        if json_file and self.filter_dept('SSJL0001', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                chuyuan_result_list = data.get('chuyuanjilu', list())
                chuyuan_result = dict()
                if chuyuan_result_list:
                    chuyuan_result = chuyuan_result_list[0]
                # chuyuan_result = collection_chuyuan.find_one({'_id': data['_id'],
                #                                               'chuyuanjilu.discharge_note': {'$regex': '带管出院'}})
                if not chuyuan_result:
                    continue
                discharge_note = chuyuan_result.get('chuyuanjilu', dict()).get('discharge_note', '')
                if '带管出院' not in discharge_note:
                    continue
                operation_tube = list()
                for one_record in collection_data[collection_name]:
                    if 'procedure' not in one_record:
                        continue
                    if 'tube' not in one_record['procedure']:
                        continue
                    if 'file_time_value' not in one_record:
                        continue
                    creator_name = one_record.get('creator_name', '')
                    last_modify_date_time = one_record.get('last_modify_date_time', '')
                    file_time_value = one_record.get('file_time_value', '')
                    tube_num = 0
                    for t in one_record['procedure']['tube']:
                        if 'cathetering_num' in t:
                            if not isinstance(t['cathetering_num'], int):
                                try:
                                    tube_num += int(t['cathetering_num'])
                                except ValueError:
                                    tube_num += float(t['cathetering_num'])
                            else:
                                try:
                                    tube_num += t['cathetering_num']
                                except ValueError:
                                    tube_num += 1
                        else:
                            tube_num += 1
                    if tube_num:
                        operation_tube.append((tube_num, file_time_value, creator_name, last_modify_date_time))
                if not operation_tube:
                    continue
                operation_tube.sort(key=lambda l: l[1])
                bingcheng_result_list = data.get('richangbingchengjilu', list())
                bingcheng_result = dict()
                if bingcheng_result_list:
                    bingcheng_result = bingcheng_result_list[0]
                if not bingcheng_result:
                    continue
                # bingcheng_result = collection_richang.find_one({'_id': data['_id'],
                #                                                 'richangbingchengjilu.extubation': {'$exists': True}},
                #                                                {'richangbingchengjilu.extubation': 1,
                #                                                 'richangbingchengjilu.file_time_value': 1})
                reason = ''
                creator_name = ''
                file_time_value = ''
                last_modify_date_time = ''
                if bingcheng_result:
                    bingcheng_extubation = list()
                    for one_record in bingcheng_result['richangbingchengjilu']:
                        if 'extubation' not in one_record:
                            continue
                        if 'file_time_value' not in one_record:
                            continue
                        if 'extubation_num' in one_record['extubation']:
                            if not isinstance(one_record['extubation']['extubation_num'], int):
                                try:
                                    extubation_num = int(one_record['extubation']['extubation_num'])
                                except ValueError:
                                    extubation_num = float(one_record['extubation']['extubation_num'])
                            else:
                                try:
                                    extubation_num = one_record['extubation']['extubation_num']
                                except ValueError:
                                    extubation_num = 1
                        else:
                            extubation_num = 1
                        bingcheng_extubation.append((extubation_num, one_record['file_time_value']))
                    if not bingcheng_extubation:
                        reason = '日常病程无拔管记录数'
                    else:
                        bingcheng_extubation.sort(key=lambda l: l[1])
                        start_index = 0
                        for operation_record in operation_tube:
                            index = start_index
                            bingcheng_total = 0
                            for bingcheng_record in bingcheng_result[index:]:
                                if operation_record[1] > bingcheng_record[1]:
                                    start_index += 1
                                    continue
                                bingcheng_total += bingcheng_record[0]
                            if operation_record[0] != bingcheng_total:
                                reason = '手术记录中的置管个数<{0}>不等于手术日期后拔管记录数<{1}>'.format(operation_record[0], bingcheng_total)
                                creator_name = operation_record[2]
                                file_time_value = operation_record[1]
                                last_modify_date_time = operation_record[3]
                                break
                else:
                    reason = '日常病程无拔管记录数'
                if reason:
                    error_info = {'code': 'SSJL0001',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    mq_id = data['_id']
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_huli_tiwen(self, collection_name, **json_file):
        """
        collection = hulitizhengyangli
        持续两天及以上体温值（vital_sign_value）大于38.5，最后一次日期病程记录无体温及值  -->检出
        HL0002
        external = richangbingchengjilu
        """
        if json_file and self.filter_dept('HL0002', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                temp_list = list()
                for yangli_one in collection_data[collection_name]:
                    if yangli_one.get('vital_type_name', '') == '体温':
                        v = re.findall('[\d]+\.?[\d]*', yangli_one.get('vital_sign_value', '0'))
                        if not v:
                            continue
                        else:
                            v = v[0]
                        temperature = float(v)
                        measuring_time = yangli_one.get('measuring_time', '')[:10]
                        if temperature and measuring_time:
                            temp_list.append((temperature, measuring_time))
                temp_list.sort(key=lambda l: l[-1])  # 按时间顺序排序
                flag = False  # 上一次体温测量 大于 38.5 度
                res_flag = False
                date = ''
                for t in temp_list:
                    if t[0] <= 38.5:
                        flag = False
                        continue
                    if not flag:
                        flag = True
                        date = datetime.strptime(t[-1], '%Y-%m-%d')
                        continue
                    d = datetime.strptime(t[-1], '%Y-%m-%d')
                    if (d-date).days == 0:
                        date = d
                        continue
                    elif (d-date).days == 1:
                        res_flag = True
                        break
                if not res_flag:
                    continue
                richang_data_list = data.get('richangbingchengjilu', list())
                richang_data = dict()
                if richang_data_list:
                    richang_data = richang_data_list[0]
                # richang_data = collection_richang.find_one({'_id': data['_id']},
                #                                            {'richangbingchengjilu.problem_list.physical_examination.temperature': 1,
                #                                             'richangbingchengjilu.last_modify_date_time': 1,
                #                                             'richangbingchengjilu.creator_name': 1})
                if not richang_data:
                    continue
                if 'richangbingchengjilu' not in richang_data:
                    continue
                chapter_richang = richang_data['richangbingchengjilu']
                chapter_richang.sort(key=lambda l: l['file_time_value'] if 'file_time_value' in l else '')
                last_data = chapter_richang[-1]
                if 'problem_list' in last_data:
                    if 'physical_examination' in last_data['problem_list']:
                        if 'temperature' in last_data['problem_list']['physical_examination']:
                            continue
                reason = '体温连续两天高于38.5，病程未记录'
                error_info = {'code': 'HL0002',
                                      'num': num,
                                      'reason': reason}
                creator_name = last_data.get('creator_name', '')
                file_time_value = last_data.get('file_time_value', '')
                last_modify_date_time = last_data.get('last_modify_date_time', '')
                error_info = self.supplementErrorInfo(error_info=error_info,
                                                      creator_name=creator_name,
                                                      file_time_value=file_time_value,
                                                      last_modify_date_time=last_modify_date_time,
                                                      collection_name=collection_name)
                if 'score' in error_info:
                    patient_result['pat_info']['machine_score'] += error_info['score']
                patient_result['pat_value'].append(error_info)
                mq_id = data['_id']
                patient_result['pat_info'].setdefault('html', list())
                if 'hulitizhengyangli' not in patient_result['pat_info']['html']:
                    patient_result['pat_info']['html'].append('hulitizhengyangli')
                self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_gender(self, collection_name, **json_file):
        """
        collection = binganshouye
        住院病案首页-基本信息-证件号码 判断是否为18位，如是，倒数第二位为奇数 and 住院病案首页-基本信息-性别名称==女
        住院病案首页-基本信息-证件号码 判断是否为18位，如是，倒数第二位为偶数 and 住院病案首页-基本信息-性别名称==男
        SY0001
        """
        if json_file and self.filter_dept('SY0001', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        # search_field = {collection_name+'.pat_info.id_card_no': {'$exists': True},
        #                 collection_name+'.pat_info.sex_name': {'$exists': True}}
        # search_field.update(time_limits)
        # mongo_result = self.gain_info.collection_bingan.find(search_field).batch_size(50)
        for data in mongo_result:
            try:
                _, patient_result, num = self.get_patient_info(data, '')
                id_card_no = data.get(collection_name, dict()).get('pat_info', dict()).get('id_card_no', dict())
                if not id_card_no:
                    continue
                if len(id_card_no) != 18:
                    continue
                sex_name = data.get(collection_name, dict()).get('pat_info', dict()).get('sex_name', dict())
                if not sex_name:
                    continue
                if ((int(id_card_no[-2]) % 2) and sex_name == '男') or ((int(id_card_no[-2]) % 2 == 0) and sex_name == '女'):
                    continue
                reason = '病案首页病人信息性别有误'
                error_info = {'code': 'SY0001',
                              'num': num,
                              'id_card_no': id_card_no,
                              'sex_name': sex_name,
                              'reason': reason}
                error_info = self.supplementErrorInfo(error_info=error_info,
                                                      collection_name=collection_name)
                if 'score' in error_info:
                    patient_result['pat_info']['machine_score'] += error_info['score']
                patient_result['pat_value'].append(error_info)
                mq_id = data['_id']
                patient_result['pat_info'].setdefault('html', list())
                if collection_name not in patient_result['pat_info']['html']:
                    patient_result['pat_info']['html'].append(collection_name)
                self.all_result[mq_id] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_chuyuan_diagnosis(self, collection_name, **json_file):
        """
        collection = jianyanbaogao
        检查低钾血症, 高钾血症, 低钠血症, 高钠血症, 贫血, 低白蛋白
        CYJL0002, CYJL0003, CYJL0004, CYJL0005, CYJL0006, CYJL0007
        external = chuyuanjilu, binganshouye
        """
        regular_code = ['CYJL0002', 'CYJL0003', 'CYJL0004', 'CYJL0005', 'CYJL0006', 'CYJL0007']
        regular_boolean = list()
        for i in regular_code:
            if self.regular_model.get(i, dict()).get('status') == '启用':
                regular_boolean.append(False)
            else:
                regular_boolean.append(True)
        if all(regular_boolean):
            return self.all_result
        if json_file:
            if not ('chuyuanjilu' in json_file and 'binganshouye' in json_file):  # 出院记录-出院诊断，src-出院时间
                return self.all_result
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                chuyuan_data_list = data.get('chuyuanjilu', list())
                chuyuan_data = dict()
                if chuyuan_data_list:
                    chuyuan_data = chuyuan_data_list[0]
                # chuyuan_data = collection_chuyuan.find_one({'_id': data['_id'],
                #                                             'chuyuanjilu.discharge_diagnosis.diagnosis_name': {'$exists': True}},
                #                                            {'chuyuanjilu.discharge_diagnosis.diagnosis_name': 1,
                #                                             'chuyuanjilu.last_modify_date_time': 1,
                #                                             'chuyuanjilu.creator_name': 1})
                if not chuyuan_data:
                    continue
                if 'chuyuanjilu' not in chuyuan_data:
                    continue
                if 'discharge_diagnosis' not in chuyuan_data['chuyuanjilu']:
                    continue
                creator_name = chuyuan_data['chuyuanjilu'].get('creator_name', '')
                file_time_value = chuyuan_data['chuyuanjilu'].get('file_time_value', '')
                last_modify_date_time = chuyuan_data['chuyuanjilu'].get('last_modify_date_time', '')
                file_time = data.get('binganshouye', dict()).get('pat_visit', dict()).get('discharge_time', '')  # 获取出院时间
                if not file_time:
                    continue
                diagnosis_name = self.gain_info._gain_diagnosis_name(chuyuan_data['chuyuanjilu']['discharge_diagnosis'])
                if not diagnosis_name:
                    continue
                get_item = self.conf_dict['lab_check_hypokalemia']
                lab_model = collection_data[collection_name].get('lab_report')
                if not lab_model:
                    continue
                lab_info = self.gain_info._gain_lab_info(lab_model, get_item)
                if not lab_info:
                    continue
                flag = {'lower_k': False,
                        'high_k': False,
                        'lower_na': False,
                        'high_na': False,
                        'low_blood': False,
                        'low_albumin': False}  # 低钾血，高钾血，低钠血，高钠血，贫血，低白蛋白
                for i in lab_info:
                    if 'lab_result_value' not in i:
                        continue
                    v = re.findall('[\d]+\.?[\d]*', i.get('lab_result_value', ''))
                    if not v:
                        continue
                    else:
                        v = v[0]
                    if 'lab_sub_item_name' in i:
                        if '钾' in i['lab_sub_item_name']:
                            if (i.get('report_time', '')[:10] == file_time[:10]) and (float(v) < 3.5):
                                flag['lower_k'] = True
                            elif (i.get('report_time', '')[:10] == file_time[:10]) and (float(v) >= 5.3):
                                flag['high_k'] = True
                        if '钠' in i['lab_sub_item_name']:
                            if (i.get('report_time', '')[:10] == file_time[:10]) and (float(v) < 137):
                                flag['lower_na'] = True
                            elif (i.get('report_time', '')[:10] == file_time[:10]) and (float(v) >= 147):
                                flag['high_na'] = True
                        if '血红蛋白' in i['lab_sub_item_name']:
                            if (i.get('report_time', '')[:10] == file_time[:10]) and (float(v) < 120):
                                flag['low_blood'] = True
                        if '白蛋白' in i['lab_sub_item_name']:
                            if (i.get('report_time', '')[:10] == file_time[:10]) and (float(v) < 30):
                                flag['low_albumin'] = True
                    if 'lab_sub_item_en_name' in i:
                        if 'k' == i['lab_sub_item_en_name'].lower():
                            if (i.get('report_time', '')[:10] == file_time[:10]) and (float(v) < 3.5):
                                flag['lower_k'] = True
                            elif (i.get('report_time', '')[:10] == file_time[:10]) and (float(v) >= 5.3):
                                flag['high_k'] = True
                        if 'na' == i['lab_sub_item_en_name'].lower():
                            if (i.get('report_time', '')[:10] == file_time[:10]) and (float(v) < 137):
                                flag['lower_na'] = True
                            elif (i.get('report_time', '')[:10] == file_time[:10]) and (float(v) >= 147):
                                flag['high_na'] = True
                        if 'hb' == i['lab_sub_item_en_name'].lower():
                            if (i.get('report_time', '')[:10] == file_time[:10]) and (float(v) < 120):
                                flag['low_blood'] = True
                push_flag = False
                if flag['lower_k'] and self.filter_dept('CYJL0002', json_file):
                    error_info = dict()
                    same_flag = self.gain_info._gain_same_content(['低钾血症'], diagnosis_name)
                    if not same_flag:  # 没有低钾血症的话
                        reason = '出院诊断缺少检验中含有的低钾血症'
                        error_info = {'code': 'CYJL0002',
                                      'num': num,
                                      'diagnosis_name': '，'.join(diagnosis_name),
                                      'reason': reason}
                    if error_info:
                        push_flag = True
                        error_info = self.supplementErrorInfo(error_info=error_info,
                                                              creator_name=creator_name,
                                                              file_time_value=file_time_value,
                                                              last_modify_date_time=last_modify_date_time,
                                                              collection_name='chuyuanjilu')
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        num += 1

                if flag['high_k'] and self.filter_dept('CYJL0003', json_file):
                    error_info = dict()
                    same_flag = self.gain_info._gain_same_content(['高钾血症'], diagnosis_name)
                    if not same_flag:
                        reason = '出院诊断缺少检验中含有的高钾血症'
                        error_info = {'code': 'CYJL0003',
                                      'num': num,
                                      'diagnosis_name': '，'.join(diagnosis_name),
                                      'reason': reason}
                    if error_info:
                        push_flag = True
                        error_info = self.supplementErrorInfo(error_info=error_info,
                                                              creator_name=creator_name,
                                                              file_time_value=file_time_value,
                                                              last_modify_date_time=last_modify_date_time,
                                                              collection_name='chuyuanjilu')
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        num += 1

                if flag['lower_na'] and self.filter_dept('CYJL0004', json_file):
                    error_info = dict()
                    same_flag = self.gain_info._gain_same_content(['低钠血症'], diagnosis_name)
                    if not same_flag:
                        reason = '出院诊断缺少检验中含有的低钠血症'
                        error_info = {'code': 'CYJL0004',
                                      'num': num,
                                      'diagnosis_name': '，'.join(diagnosis_name),
                                      'reason': reason}
                    if error_info:
                        push_flag = True
                        error_info = self.supplementErrorInfo(error_info=error_info,
                                                              creator_name=creator_name,
                                                              file_time_value=file_time_value,
                                                              last_modify_date_time=last_modify_date_time,
                                                              collection_name='chuyuanjilu')
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        num += 1

                if flag['high_na'] and self.filter_dept('CYJL0005', json_file):
                    error_info = dict()
                    same_flag = self.gain_info._gain_same_content(['高钠血症'], diagnosis_name)
                    if not same_flag:
                        reason = '出院诊断缺少检验中含有的高钠血症'
                        error_info = {'code': 'CYJL0005',
                                      'num': num,
                                      'diagnosis_name': '，'.join(diagnosis_name),
                                      'reason': reason}
                    if error_info:
                        push_flag = True
                        error_info = self.supplementErrorInfo(error_info=error_info,
                                                              creator_name=creator_name,
                                                              file_time_value=file_time_value,
                                                              last_modify_date_time=last_modify_date_time,
                                                              collection_name='chuyuanjilu')
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        num += 1

                if flag['low_blood'] and self.filter_dept('CYJL0006', json_file):
                    error_info = dict()
                    same_flag = self.gain_info._gain_same_content(['贫血'], diagnosis_name)
                    if not same_flag:
                        reason = '出院诊断缺少检验中含有的贫血'
                        error_info = {'code': 'CYJL0006',
                                      'num': num,
                                      'diagnosis_name': '，'.join(diagnosis_name),
                                      'reason': reason}
                    if error_info:
                        push_flag = True
                        error_info = self.supplementErrorInfo(error_info=error_info,
                                                              creator_name=creator_name,
                                                              file_time_value=file_time_value,
                                                              last_modify_date_time=last_modify_date_time,
                                                              collection_name='chuyuanjilu')
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        num += 1

                if flag['low_albumin'] and self.filter_dept('CYJL0007', json_file):
                    error_info = dict()
                    same_flag = self.gain_info._gain_same_content(['低蛋白血症'], diagnosis_name)
                    if not same_flag:
                        reason = '出院诊断缺少检验中含有的低蛋白血症'
                        error_info = {'code': 'CYJL0007',
                                      'num': num,
                                      'diagnosis_name': '，'.join(diagnosis_name),
                                      'reason': reason}
                    if error_info:
                        push_flag = True
                        error_info = self.supplementErrorInfo(error_info=error_info,
                                                              creator_name=creator_name,
                                                              file_time_value=file_time_value,
                                                              last_modify_date_time=last_modify_date_time,
                                                              collection_name='chuyuanjilu')
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        num += 1

                if push_flag:
                    patient_result['pat_info'].setdefault('html', list())
                    if 'chuyuanjilu' not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append('chuyuanjilu')
                    self.all_result[data['_id']] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result
    
    def check_chuyuan_chuyuandaiyao(self, collection_name, **json_file):
        """
        collection = chuyuanjilu
        出院记录有出院带药名称--(给药途径和方法 and 用药剂量 均为 NULL) or
        (医嘱日期==出院日期 and 医嘱给药途径=='出院带药' and (医嘱项名称/药品通用名!=出院带药药品名称 or 医嘱用药剂量!=出院用药剂量)) -->检出
        CYJL0008, CYJL0009
        external = yizhu
        """
        if self.regular_model.get('CYJL0008', dict()).get('status') != '启用' and self.regular_model.get('CYJL0009', dict()).get('status') != '启用':
            return self.all_result
        if json_file:
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                medicine_model = collection_data.get(collection_name, dict()).get('medicine', list())
                if not medicine_model:
                    continue
                creator_name = collection_data.get(collection_name, dict()).get('creator_name', '')
                last_modify_date_time = collection_data.get(collection_name, dict()).get('last_modify_date_time', '')
                file_time_value = collection_data.get(collection_name, dict()).get('file_time_value', '')
                flag = False
                chuyuan_medicine = dict()  # {'药品名称': {用量}}
                for one_record in medicine_model:
                    if one_record.get('medicine_name', ''):
                        chuyuan_medicine.setdefault(one_record['medicine_name'], set())
                        if 'route' in one_record:
                            flag = True
                        if 'dosage' in one_record:
                            chuyuan_medicine[one_record['medicine_name']].add(one_record['dosage'])
                            flag = True
                if not flag and len(self.regular_model.get('CYJL0008', list())) > 6 and self.regular_model['CYJL0008'][6] == '启用' and self.filter_dept('CYJL0008', json_file):
                    reason = '出院带药未描述用法、用量'
                    error_info = {'code': 'CYJL0008',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                else:
                    # 查医嘱出院带药和出院记录出院是否一致
                    # search_field = {'_id': data['_id']}
                    # show_field = {'yizhu.order_time': 1,
                    #               'yizhu.dosage_value': 1,
                    #               'yizhu.pharmacy_way_name': 1,
                    #               'yizhu.order_item_name': 1,
                    #               'yizhu.china_approved_drug_name': 1}
                    # yizhu_result = collection_yizhu.find_one(search_field, show_field)
                    yizhu_result_list = data.get('yizhu', list())
                    yizhu_result = dict()
                    if yizhu_result_list:
                        yizhu_result = yizhu_result_list[0]
                    if not yizhu_result:
                        continue
                    if 'yizhu' not in yizhu_result:
                        continue
                    yizhu_medicine = dict()
                    for one_record in yizhu_result['yizhu']:
                        if one_record.get('order_time', '')[:10] == file_time_value[:10]:  # and one_record.get('pharmacy_way_name', '') == '出院带药':
                            if one_record.get('order_item_name', ''):
                                yizhu_medicine.setdefault(one_record['order_item_name'], set())
                            if one_record.get('china_approved_drug_name', ''):
                                yizhu_medicine.setdefault(one_record['china_approved_drug_name'], set())
                            if one_record.get('dosage_value', ''):
                                yizhu_medicine[one_record['china_approved_drug_name']].add(one_record['dosage_value'])
                    chuyuan_content = list(chuyuan_medicine.keys())
                    yizhu_content = list(yizhu_medicine.keys())
                    same_content = self.gain_info._gain_same_content(chuyuan_content, yizhu_content)
                    if not same_content and self.filter_dept('CYJL0009', json_file):
                        reason = '医嘱中不含出院记录的出院带药'
                        error_info = {'code': 'CYJL0009',
                                      'num': num,
                                      'reason': reason}
                        error_info = self.supplementErrorInfo(error_info=error_info,
                                                              creator_name=creator_name,
                                                              file_time_value=file_time_value,
                                                              last_modify_date_time=last_modify_date_time,
                                                              collection_name=collection_name)
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        patient_result['pat_info'].setdefault('html', list())
                        if collection_name not in patient_result['pat_info']['html']:
                            patient_result['pat_info']['html'].append(collection_name)
                        self.all_result[data['_id']] = patient_result
                    else:
                        for k in same_content:
                            chuyuan_dosage = chuyuan_medicine[k]
                            yizhu_dosage = yizhu_medicine[same_content[k]]
                            same_dosage = chuyuan_dosage & yizhu_dosage
                            if not same_dosage and self.filter_dept('CYJL0009', json_file):
                                reason = '医嘱中与出院记录中相同药品用量不一致'
                                error_info = {'code': 'CYJL0009',
                                              'num': num,
                                              'reason': reason}
                                error_info = self.supplementErrorInfo(error_info=error_info,
                                                                      creator_name=creator_name,
                                                                      file_time_value=file_time_value,
                                                                      last_modify_date_time=last_modify_date_time,
                                                                      collection_name=collection_name)
                                if 'score' in error_info:
                                    patient_result['pat_info']['machine_score'] += error_info['score']
                                patient_result['pat_value'].append(error_info)
                                patient_result['pat_info'].setdefault('html', list())
                                if collection_name not in patient_result['pat_info']['html']:
                                    patient_result['pat_info']['html'].append(collection_name)
                                self.all_result[data['_id']] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_shouyeshoushu_shangjichafang(self, collection_name, **json_file):
        """
        collection = shangjiyishichafanglu
        含住院首页手术 and
        住院首页手术--手术名称不为空 and
        住院首页手术--手术与操作时间以前的上级医师查房记录文书名称不含“住院首页手术--术者”名称字样 -->检出
        external = shouyeshoushu
        RCBC0021
        """
        if json_file and self.filter_dept('RCBC0021', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                shouyeshoushu_list = data.get('shouyeshoushu', list())
                shouyeshoushu = dict()
                if shouyeshoushu_list:
                    shouyeshoushu = shouyeshoushu_list[0]
                if not shouyeshoushu:
                    continue
                if 'shouyeshoushu' not in shouyeshoushu:
                    continue
                operation_info = dict()  # {手术时间：手术人}
                for one_record in shouyeshoushu['shouyeshoushu']:
                    if 'operation_name' not in one_record:
                        continue
                    if 'operation_date' not in one_record:
                        continue
                    if 'operator' not in one_record:
                        continue
                    operation_info[one_record['operation_date']] = one_record['operator']
                if not operation_info:
                    continue
                flag = False
                last_modify_date_time = ''
                creator_name = ''
                file_time_value = ''
                for one_record in collection_data[collection_name]:
                    if 'creator_name' not in one_record:
                        continue
                    if 'file_time_value' not in one_record:
                        continue
                    creator_name = one_record.get('creator_name', '')
                    file_time_value = one_record.get('file_time_value', '')
                    last_modify_date_time = one_record.get('last_modify_date_time', '')
                    for k, v in operation_info.items():
                        if one_record['file_time_value'] < k and (v in one_record['creator_name']):  # 手术以前的上级医师查房, 术者名称在查房记录书写者中
                            flag = True
                            break
                    if flag:  # 查房者中有手术记录者，不检出
                        break
                if not flag:
                    reason = '手术前无术者查房记录'
                    error_info = {'code': 'RCBC0021',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_shouyeshoushu_richangbingcheng(self, collection_name, **json_file):
        """
        collection = richangbingchengjilu
        含住院首页手术 and
        住院首页手术--手术名称不为空 and
        住院首页手术--手术与操作时间以前的日常病程记录文书名称不含“住院首页手术--术者”名称字样 -->检出
        external = shouyeshoushu
        RCBC0020
        """
        if json_file and self.filter_dept('RCBC0020', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                shouyeshoushu_list = data.get('shouyeshoushu', list())
                shouyeshoushu = dict()
                if shouyeshoushu_list:
                    shouyeshoushu = shouyeshoushu_list[0]
                if not shouyeshoushu:
                    continue
                if 'shouyeshoushu' not in shouyeshoushu:
                    continue
                operation_info = dict()  # {手术时间：手术人}
                for one_record in shouyeshoushu['shouyeshoushu']:
                    if 'operation_name' not in one_record:
                        continue
                    if 'operation_date' not in one_record:
                        continue
                    if 'operator' not in one_record:
                        continue
                    operation_info[one_record['operation_date']] = one_record['operator']
                if not operation_info:
                    continue
                flag = False
                last_modify_date_time = ''
                creator_name = ''
                file_time_value = ''
                for one_record in collection_data[collection_name]:
                    if 'creator_name' not in one_record:
                        continue
                    if 'file_time_value' not in one_record:
                        continue
                    creator_name = one_record.get('creator_name', '')
                    last_modify_date_time = one_record.get('last_modify_date_time', '')
                    file_time_value = one_record.get('file_time_value', '')
                    for k, v in operation_info.items():
                        if one_record['file_time_value'] < k and (v in one_record['creator_name']):  # 手术以前的上级医师查房, 术者名称在查房记录书写者中
                            flag = True
                            break
                    if flag:  # 查房者中有手术记录者，不检出
                        break
                if not flag:
                    reason = '手术前无术者查房记录'
                    error_info = {'code': 'RCBC0020',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info,
                                                          creator_name=creator_name,
                                                          file_time_value=file_time_value,
                                                          last_modify_date_time=last_modify_date_time,
                                                          collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_shoushu_buwei(self, collection_name, **json_file):
        """
        collection = shoushujilu
        （手术记录-手术名称含“左” and 手术记录--手术经过procedure 含除“右侧卧位”的“右”字样） or
        （手术记录-手术名称含“右” and 手术记录--手术经过procedure 含除“左侧卧位”的“左”字样）
        有问题
        SSJL0005
        """
        if json_file and self.filter_dept('SSJL0005', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                one_record = collection_data[collection_name][0]
                creator_name = one_record.get('creator_name', '')
                file_time_value = one_record.get('file_time_value', '')
                last_modify_date_time = one_record.get('last_modify_date_time', '')
                operation_name = one_record.get('operation_name')
                if not operation_name:
                    continue
                if '双' in operation_name:
                    continue
                procedure_src = one_record.get('procedure', dict()).get('src')
                if not procedure_src:
                    continue
                if '左眼' in operation_name and '右眼' not in operation_name:
                    operation_location = '左眼'
                    re_info = '右眼'
                elif '右眼' in operation_name and '左眼' not in operation_name:
                    operation_location = '右眼'
                    re_info = '左眼'
                else:
                    continue
                procedure = re.findall(re_info, procedure_src)
                if not procedure:
                    continue
                reason = '手术名称含<{0}>，手术部位含<{1}>'.format(operation_location, procedure[0])
                error_info = {'code': 'SSJL0005',
                              'num': num,
                              'operation_name': operation_name,
                              'procedure': procedure_src,
                              'reason': reason}
                error_info = self.supplementErrorInfo(error_info=error_info,
                                                      creator_name=creator_name,
                                                      file_time_value=file_time_value,
                                                      last_modify_date_time=last_modify_date_time,
                                                      collection_name=collection_name)
                if 'score' in error_info:
                    patient_result['pat_info']['machine_score'] += error_info['score']
                patient_result['pat_value'].append(error_info)
                patient_result['pat_info'].setdefault('html', list())
                if collection_name not in patient_result['pat_info']['html']:
                    patient_result['pat_info']['html'].append(collection_name)
                self.all_result[data['_id']] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_birth_weight(self, collection_name, **json_file):
        """
        collection = shouyezhenduan
        首页诊断--诊断类型==出院诊断--诊断编码含 Z37 新生儿出生体重 ==NULL
        SY0003
        """
        if json_file and self.filter_dept('SY0003', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if not collection_data:
                    continue
                if collection_name not in collection_data:
                    continue
                flag = False
                for one_record in collection_data[collection_name]:
                    if one_record.get('diagnosis_type_name', '') == '出院诊断':
                        if 'Z37' in one_record.get('diagnosis_code', ''):
                            flag = True
                            break
                if not flag:
                    continue
                if data.get('binganshouye', dict()).get('pat_info', dict()).get('baby_birth_weight'):
                    continue
                reason = '未写婴儿出生体重'
                error_info = {'code': 'SY0003',
                              'num': num,
                              'reason': reason}
                error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                if 'score' in error_info:
                    patient_result['pat_info']['machine_score'] += error_info['score']
                patient_result['pat_value'].append(error_info)
                patient_result['pat_info'].setdefault('html', list())
                if collection_name not in patient_result['pat_info']['html']:
                    patient_result['pat_info']['html'].append(collection_name)
                self.all_result[data['_id']] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_admission_weight(self, collection_name, **json_file):
        """
        collection = binganshouye
        患者年龄≤28天 and 新生儿入院体重==NULL -->检出
        SY0004
        """
        if json_file and self.filter_dept('SY0004', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                _, patient_result, num = self.get_patient_info(data, collection_name)
                age_unit = data.get(collection_name, dict()).get('pat_visit', dict()).get('age_value_unit')
                if age_unit != '天':
                    continue
                age = data.get(collection_name, dict()).get('pat_visit', dict()).get('age_value')
                try:
                    age = float(age)
                except:
                    self.logger.info('\n新生儿年龄问题SY0004:\n\tid: {0}\n\tage: {1}\n'. format(data['_id'], age))
                    continue
                if age <= 28:
                    if not data.get('binganshouye', dict()).get('pat_info', dict()).get('baby_admin_weight'):
                        reason = '出生未满28天婴儿未写入院体重'
                        error_info = {'code': 'SY0004',
                                      'num': num,
                                      'age': '{}{}'.format(age, age_unit),
                                      'reason': reason}
                        error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        patient_result['pat_info'].setdefault('html', list())
                        if collection_name not in patient_result['pat_info']['html']:
                            patient_result['pat_info']['html'].append(collection_name)
                        self.all_result[data['_id']] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_marital_status(self, collection_name, **json_file):
        """
        collection = ruyuanjilu
        病案首页--就诊信息--婚姻状况名称不等于“入院记录--既往史--月经婚育史--婚姻状态”-->检出
        SY0005
        """
        if json_file and self.filter_dept('SY0005', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                filter_condition = {'未婚', '已婚', '其他', '其它'}
                ruyuan_status = collection_data.get(collection_name, dict()).get('menstrual_and_obstetrical_histories', dict()).get('marriage_status')
                if not ruyuan_status:
                    continue
                elif ruyuan_status not in filter_condition:
                    continue
                bingan_status = data.get('binganshouye', dict()).get('pat_visit', dict()).get('marital_status_name')
                if not bingan_status:
                    continue
                elif bingan_status not in filter_condition:
                    continue
                if bingan_status == ruyuan_status:
                    continue
                creator_name = collection_data.get(collection_name, dict()).get('creator_name', '')
                last_modify_date_time = collection_data.get(collection_name, dict()).get('last_modify_date_time', '')
                file_time_value = collection_data.get(collection_name, dict()).get('file_time_value', '')
                reason = '入院记录与病案首页婚姻状态不一致'
                error_info = {'code': 'SY0005',
                              'num': num,
                              'ruyuanjilu_status': ruyuan_status,
                              'binganshouye_status': bingan_status,
                              'reason': reason}
                error_info = self.supplementErrorInfo(error_info=error_info,
                                                      creator_name=creator_name,
                                                      file_time_value=file_time_value,
                                                      last_modify_date_time=last_modify_date_time,
                                                      collection_name=collection_name)
                if 'score' in error_info:
                    patient_result['pat_info']['machine_score'] += error_info['score']
                patient_result['pat_value'].append(error_info)
                patient_result['pat_info'].setdefault('html', list())
                if collection_name not in patient_result['pat_info']['html']:
                    patient_result['pat_info']['html'].append(collection_name)
                self.all_result[data['_id']] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_items_shouyeshoushu(self, collection_name, **json_file):
        """
        collection = shouyeshoushu
        SY0006: 首页手术--手术与操作名称 or 手术与操作编码 or 手术与操作时间 存在两个及以上相同-->检出
        SY0007: 含有手术记录 and
                ((同一条数据 首页手术--手术级别名称包含“术” and 该“术”条无“手术或操作手术编码/手术与操作时间/术者”任一为空) or
                 (同一条数据 首页手术--手术级别名称包含“术” and 手术切口愈合等级==NULL))-->检出
        external = shoushujilu
        SY0009: 首页手术--手术与操作时间 < 病案首页--就诊信息--就诊时间 or 首页手术--手术与操作时间 > 病案首页--就诊信息--出院时间 -->检出
        SY0011: 首页手术--切口等级名称不等于“无”and 首页手术--愈合等级名称==NULL-->检出
        SY0012: 首页手术--切口等级名称==“Ⅰ”and 首页手术--愈合等级名称==“丙”-->检出
        SY0006, SY0007, SY0009, SY0011, SY0012
        """
        regular_code = ['SY0006', 'SY0007', 'SY0009', 'SY0011', 'SY0012']
        regular_boolean = list()
        for i in regular_code:
            if self.regular_model.get(i, dict()).get('status') == '启用':
                regular_boolean.append(False)
            else:
                regular_boolean.append(True)
        if all(regular_boolean):
            return self.all_result
        if json_file:
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                shoushujilu_result = data.get('shoushujilu', list())
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if collection_name not in collection_data:
                    continue
                admission_time = data.get('binganshouye', dict()).get('pat_visit', dict()).get('admission_time')
                discharge_time = data.get('binganshouye', dict()).get('pat_visit', dict()).get('discharge_time')
                repeat_items = set()  # SY0006
                reason_repeat = set()  # SY0006  reason
                lack_items = set()  # SY0007
                reason_time = ''  # SY0009
                reason_healing = ''  # SY0011
                reason_wound = ''  # SY0012
                for one_record in collection_data[collection_name]:

                    operation_name = one_record.get('operation_name')  # 手术与操作名称
                    operation_code = one_record.get('operation_code')  # 手术与操作编码
                    operation_date = one_record.get('operation_date')  # 手术与操作时间
                    operation_type = one_record.get('operation_type')  # 手术与操作类型
                    operator = one_record.get('operator')  # 术者
                    operation_grade_name = one_record.get('operation_grade_name')  # 手术级别名称
                    wound_grade_name = one_record.get('wound_grade_name')  # 切口等级名称
                    healing_grade_name = one_record.get('healing_grade_name')  # 愈合等级

                    if self.filter_dept('SY0006', data):
                        one_item = (operation_code, operation_name, operation_date)
                        if operation_name and operation_code:
                            if one_item in repeat_items:
                                reason_repeat.add('手术与操作名称/手术与操作编码/手术与操作时间')
                            else:
                                repeat_items.add(one_item)

                    if shoushujilu_result and self.filter_dept('SY0007', data) and not lack_items:
                        if operation_name and '术' in operation_name and operation_type == '手术':
                            if not operation_code:
                                lack_items.add('手术与操作编码')
                            if not operation_date:
                                lack_items.add('手术与操作时间')
                            if not operator:
                                lack_items.add('术者')
                        if operation_grade_name and '术' in operation_grade_name and not wound_grade_name:
                            lack_items.add('切口等级名称')

                    if self.filter_dept('SY0009', data) and operation_date and not reason_time:
                        if admission_time:
                            if operation_date[:10] < admission_time[:10]:
                                reason_time = '手术与操作时间早于入院时间'
                        if discharge_time:
                            if operation_date[:10] > discharge_time[:10]:
                                reason_time = '手术与操作时间晚于出院时间'

                    if self.filter_dept('SY0011', data) and wound_grade_name and not reason_healing:
                        if wound_grade_name != '无':
                            if not healing_grade_name:
                                reason_healing = '切口等级为{0}，愈合等级未填写'.format(wound_grade_name)

                    if self.filter_dept('SY0012', data) and wound_grade_name == 'I' and healing_grade_name == '丙' and not reason_wound:
                        reason_wound = "切口等级为'I'，愈合等级为'丙'"
                for item in repeat_items:
                    if '会诊' in item:
                        reason_repeat.clear()
                if reason_repeat:
                    reason = '<{0}>存在相同数据'.format('/'.join(reason_repeat))
                    error_info = {'code': 'SY0006',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
                if lack_items:
                    reason = '首页手术<{0}>未填写'.format('/'.join(lack_items))
                    error_info = {'code': 'SY0007',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
                if reason_time:
                    error_info = {'code': 'SY0009',
                                  'num': num,
                                  'reason': reason_time}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
                if reason_healing:
                    error_info = {'code': 'SY0011',
                                  'num': num,
                                  'reason': reason_healing}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
                if reason_wound:
                    error_info = {'code': 'SY0012',
                                  'num': num,
                                  'reason': reason_healing}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result
    
    def check_code_shouyezhenduan(self, collection_name, **json_file):
        """
        collection = shouyezhenduan
        SY0014: “入院记录--初步诊断”不等于“首页诊断--诊断类型==门(急)诊诊断--诊断名称”-->检出
        external: ruyuanjilu
        SY0015: 首页诊断--诊断类型==门(急)诊诊断--诊断编码首字母含"V" or "W" or “X" or "Y" -->检出
        SY0016: 首页诊断--诊断类型==出院诊断--诊断编码==“C00~C97”、“D00~D48” and 含病理报告 and 首页诊断--诊断类型==病理诊断--诊断名称==NULL -->检出
        external: jianchabaogao
        SY0017: （首页诊断--诊断类型==出院诊断--诊断编码不等于“C00~C97”or“D00~D48”） and 病理诊断不为空 -->检出
        SY0018: 首页诊断--诊断类型==第一条出院诊断--诊断编码==“D00~D09” and 病理诊断不等于“M****/2” -->检出
        SY0019: 首页诊断--诊断类型==出院诊断--诊断编码含“M******/*" or “M80" or 首字母含（"V" or "W" or “X" or "Y" ）-->检出
        SY0020: 首页诊断--诊断类型==出院诊断--诊断编码含（“O80~O84”and“O00~O08”）and 不含“Z37”-->检出
        SY0021: 就诊类型名称==“医疗保险” and 首页诊断--诊断类型==出院诊断--诊断编码首字母含“F”-->检出
        SY0022: 病案首页--就诊信息--就诊次数==1 and 首页诊断--诊断类型==出院诊断--诊断编码首字母含“Z”-->检出
        SY0023: 首页诊断--诊断类型==出院诊断--诊断编码含“Z37” and 病案首页--就诊信息--出院科室名称不等于“产科” -->检出
        SY0041: 首页诊断--诊断类型==出院诊断--首个诊断编码==“S01~S06” and 病案首页--就诊信息--颅脑损伤患者入院前昏迷时间==NULL or 病案首页--就诊信息--颅脑损伤患者入院后昏迷时间==NULL
        SY0047: 首页诊断--诊断类型==出院诊断--诊断编码首字母含“M” -->检出
        SY0048: 首页诊断--诊断类型==门(急)诊诊断--诊断编码首字母含“M” -->检出
        SY0049: 首页诊断--诊断类型==门(急)诊诊断--诊断编码含“P10~P15” and 病案首页--就诊信息--就诊时间 减去  病案首页--基本信息--出生日期 大于28天 -->检出
        SY0051: 首页诊断--诊断类型==门(急)诊诊断--诊断编码含“J40” and 病案首页--就诊信息--出院科室名称==“儿科”-->检出
        SY0053: 首页诊断--诊断类型==第一条出院诊断--诊断编码==“C77~C80” and 病理诊断不等于“M****/6” -->检出
        SY0054: 首页诊断--诊断类型==第一条出院诊断--诊断编码==“C00~C76” and 病理诊断不等于“M****/3” -->检出
        SY0055: 首页诊断--诊断类型==第一条出院诊断--诊断编码==“D10~D36” and 病理诊断不等于“M****/0” -->检出
        SY0056: 首页诊断--诊断类型==第一条出院诊断--诊断编码==“D37~D48” and 病理诊断不等于“M****/1” -->检出
        SY0050: 首页诊断--诊断类型==出院诊断--诊断编码含“P10~P15” and 病案首页--就诊信息--就诊时间 减去  病案首页--基本信息--出生日期 大于28天 -->检出
        SY0052: 首页诊断--诊断类型==出院诊断--诊断编码含“J40” and 病案首页--就诊信息--出院科室名称==“儿科”-->检出
        SY0014, SY0015, SY0016, SY0017, SY0018, SY0019, SY0020, SY0021, SY0022, SY0023, SY0047, SY0048, SY0049
        SY0051, SY0053, SY0054, SY0055, SY0056, SY0050, SY0052
        """
        regular_code = ['SY0014', 'SY0015', 'SY0016', 'SY0017', 'SY0018', 'SY0019', 'SY0020', 'SY0021', 'SY0022', 'SY0023',
                        'SY0047', 'SY0048', 'SY0049', 'SY0050', 'SY0051', 'SY0052', 'SY0053', 'SY0054', 'SY0055', 'SY0056', ]
        regular_boolean = list()
        for i in regular_code:
            if self.regular_model.get(i, dict()).get('status') == '启用':
                regular_boolean.append(False)
            else:
                regular_boolean.append(True)
        if all(regular_boolean):
            return self.all_result
        if json_file:
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                collection_data, patient_result, num = self.get_patient_info(data, collection_name)
                if collection_name not in collection_data:
                    continue
                # SY0014
                ruyuanjilu_diag = set()
                if self.filter_dept('SY0014', data) and False:
                    ruyuanjilu_data = dict()
                    if data.get('ruyuanjilu', list()):
                        ruyuanjilu_data = data['ruyuanjilu'][0]
                    if 'ruyuanjilu' in ruyuanjilu_data:
                        diag_list = ruyuanjilu_data['ruyuanjilu'].get('diagnosis_name', list())
                        for diag in diag_list:
                            if diag.get('diagnosis_name'):
                                ruyuanjilu_diag.add(diag.get('diagnosis_name'))

                # SY0016
                binglibaogao_data = False
                if self.filter_dept('SY0016', data):
                    if data.get('jianchabaogao', list()):
                        jianchabaogao_data = data['jianchabaogao'][0]
                        for one_record in jianchabaogao_data.get('jianchabaogao', dict()).get('exam_report', list()):
                            if '病理' in one_record.get('exam_item_name', ''):
                                binglibaogao_data = True
                                break
                # SY0021
                yiliaobaoxian_flag = False
                if self.filter_dept('SY0021', data):
                    if data.get('binganshouye', dict()).get('pat_visit', dict()).get('visit_type_name') == '医疗保险':
                        yiliaobaoxian_flag = True
                        
                # SY0022
                first_visit = False
                if self.filter_dept('SY0022', data):
                    if data.get('binganshouye', dict()).get('pat_visit', dict()).get('visit_id') == '1':
                        first_visit = True
                        
                # SY0023
                chanke_flag = False  # 规则不启用，为False，后续不再判断诊断编码
                if self.filter_dept('SY0023', data):
                    dept = data.get('binganshouye', dict()).get('pat_visit', dict()).get('dept_discharge_from_name')
                    if not dept:
                        district = data.get('binganshouye', dict()).get('pat_visit', dict()).get('district_discharge_from_name', '')
                        dept = self.parameters.ward_dept.get(district, '')
                    if dept == '产科':
                        chanke_flag = False  # 科室为产科，后续不再判断诊断编码
                    else:
                        chanke_flag = True  # 科室不为产科，后续需要再判断诊断编码

                first_flag = False
                first_letter = ''  # SY0015
                shouyezhenduan_diag = set()  # SY0014
                binglizhenduan_flag = False  # SY0016
                binglizhenduan_flag2 = False  # SY0017
                binglizhenduan_content = set()  # SY0016, SY0017
                sy0018_flag = False  # SY0018  等于1时，表示第1次出院诊断已经出现，等于2时表示第一条出院诊断编码为D00-D09
                sy0018_bingli = False  # SY0018 病理诊断不等于“M****/2” True
                sy0019_flag = False  # SY0019
                sy0020_flag = False  # SY0020
                z37_flag = False
                sy0021_flag = False  # SY0021
                sy0022_flag = False  # SY0022
                sy0023_flag = False  # SY0023
                sy0041_flag = False
                sy0047_flag = False
                sy0048_flag = False
                sy0049_flag = False
                sy0050_flag = False
                sy0051_flag = False
                sy0052_flag = False
                sy0053_flag = False
                sy0053_bingli = False
                sy0054_flag = False
                sy0054_bingli = False
                sy0055_flag = False
                sy0055_bingli = False
                sy0056_flag = False
                sy0056_bingli = False
                for one_record in collection_data[collection_name]:
                    
                    diagnosis_code = one_record.get('diagnosis_code', '')
                    diagnosis_type_name = one_record.get('diagnosis_type_name')
                    diagnosis_name = one_record.get('diagnosis_name')
                    diagnosis_num = one_record.get('diagnosis_num')

                    if 'M' in diagnosis_code:
                        if (diagnosis_type_name == '门(急)诊诊断' or diagnosis_type_name == '门诊诊断') and self.filter_dept('SY0048', data) and False:
                            sy0048_flag = True
                        elif diagnosis_type_name == '出院诊断' and self.filter_dept('SY0047', data) and False:
                            sy0047_flag = True

                    if diagnosis_type_name == '出院诊断':
                        if diagnosis_code:
                            if re.findall('^(C[0-8][0-9]|C[9][0-7])', diagnosis_code) or re.findall('^(D[0-3][0-9]|D[4][0-8])', diagnosis_code):
                                # SY0016
                                if len(diagnosis_code) > 3 and binglibaogao_data and not binglizhenduan_flag and diagnosis_num == '1':
                                    binglizhenduan_flag = True
                                # SY0017
                                if self.filter_dept('SY0017', data) and diagnosis_num == '1':
                                    if not binglizhenduan_flag2:  # 诊断编码不等于 “C00~C97”or“D00~D48”
                                        binglizhenduan_flag2 = True

                            # SY0018
                            if self.filter_dept('SY0018', data):
                                if len(diagnosis_code) > 3 and re.findall('^D0[0-9]$', diagnosis_code) and not first_flag:  # 第一条出院诊断
                                    sy0018_flag = True

                            # SY0019
                            if self.filter_dept('SY0019', data) and not sy0019_flag:
                                if isinstance(diagnosis_code, str):
                                    if 'M80' in diagnosis_code or re.findall('^[VWXY]', diagnosis_code) or re.findall('^M.*/.$', diagnosis_code):
                                        sy0019_flag = True

                            # SY0020
                            if self.filter_dept('SY0020', data):
                                if isinstance(diagnosis_code, str):
                                    if re.findall('O8[0-4]', diagnosis_code) or re.findall('O0[0-8]', diagnosis_code):
                                        sy0020_flag = True
                                    if 'Z37' in diagnosis_code:
                                        z37_flag = True
                            # SY0021
                            if yiliaobaoxian_flag and diagnosis_num == '1':
                                if isinstance(diagnosis_code, str) and diagnosis_code.startswith('F'):
                                    sy0021_flag = True

                            # SY0022
                            if first_visit and not diagnosis_num == '1':
                                if isinstance(diagnosis_code, str) and diagnosis_code.startswith('Z'):
                                    sy0022_flag = True

                            # SY0023
                            if chanke_flag:
                                if isinstance(diagnosis_code, str) and 'Z37' in diagnosis_code:
                                    sy0023_flag = True

                            # SY0041
                            if self.filter_dept('SY0041', data) and not sy0041_flag:
                                if isinstance(diagnosis_code, str) and re.findall('^S0[1-6]$', diagnosis_code) and not first_flag:
                                    if not (data.get('binganshouye', dict()).get('pat_visit', dict()).get('before_coma_time') and data.get('binganshouye', dict()).get('pat_visit', dict()).get('in_coma_time')):
                                        sy0041_flag = True

                            # SY0050
                            if self.filter_dept('SY0050', data) and not sy0050_flag:
                                match_result = re.findall('P1[0-5]', diagnosis_code)
                                if match_result:
                                    admission_time = data.get(collection_name, dict()).get('pat_visit', dict()).get('admission_time', '')
                                    date_of_birth = data.get(collection_name, dict()).get('pat_info', dict()).get('date_of_birth', '')
                                    if admission_time and date_of_birth:
                                        age_baby = (datetime.strptime(admission_time, '%Y-%m-%d %H:%M:%S') - datetime.strptime(date_of_birth, '%Y-%m-%d %H:%M:%S')).days
                                        if age_baby >= 28:
                                            sy0050_flag = True

                            # SY0052
                            if self.filter_dept('SY0052', data) and not sy0052_flag:
                                discharge_dept = data.get(collection_name, dict()).get('pat_visit', dict()).get('dept_discharge_from_name', '')
                                if 'J40' in diagnosis_code and discharge_dept == '儿科':
                                    sy0052_flag = True
                            
                            # SY0053
                            if self.filter_dept('SY0053', data) and not sy0053_flag:
                                if isinstance(diagnosis_code, str) and re.findall('^(C7[7-9]|C80)$', diagnosis_code) and not first_flag:
                                    sy0053_flag = True
                                    
                            # SY0054
                            if self.filter_dept('SY0054', data) and not sy0054_flag:
                                if isinstance(diagnosis_code, str) and re.findall('^(C[0-6][0-9]|C7[0-6])$', diagnosis_code) and not first_flag:
                                    sy0054_flag = True

                            # SY0055
                            if self.filter_dept('SY0055', data) and not sy0055_flag:
                                if isinstance(diagnosis_code, str) and re.findall('^(D[1-2][0-9]|D3[0-6])$', diagnosis_code) and not first_flag:
                                    sy0055_flag = True

                            # SY0056
                            if self.filter_dept('SY0056', data) and not sy0056_flag:
                                if isinstance(diagnosis_code, str) and re.findall('^(D3[7-9]|D4[0-8])$', diagnosis_code) and not first_flag:
                                    sy0056_flag = True

                        # 第一条出院诊断已出现
                        if not first_flag:  # 第一条出院诊断
                            first_flag = True  # 不是第一条出院诊断

                    if diagnosis_type_name == '病理诊断':
                        # SY0016, SY0017
                        binglizhenduan_content.add(diagnosis_name)
                        
                        # SY0018
                        if not re.findall('^M.*/2$', diagnosis_code) and sy0018_flag:
                            sy0018_bingli = True

                        # SY0053
                        if not re.findall('^M.*/6$', diagnosis_code) and sy0053_flag:
                            sy0053_bingli = True

                        # SY0054
                        if not re.findall('^M.*/3$', diagnosis_code) and sy0054_flag:
                            sy0054_bingli = True
                            
                        # SY0055
                        if not re.findall('^M.*/0$', diagnosis_code) and sy0055_flag:
                            sy0055_bingli = True
                            
                        # SY0056
                        if not re.findall('^M.*/1$', diagnosis_code) and sy0056_flag:
                            sy0056_bingli = True

                    if diagnosis_type_name == '门(急)诊诊断' or diagnosis_type_name == '门诊诊断':
                        # SY0014
                        if ruyuanjilu_diag:
                            if one_record.get('diagnosis_name'):
                                shouyezhenduan_diag.add(diagnosis_name)

                        # SY0015
                        if self.filter_dept('SY0015', data):
                            match_result = re.findall('^[VWXY]', diagnosis_code)
                            if match_result:
                                first_letter = match_result[0]

                        # SY0049
                        if self.filter_dept('SY0049', data) and not sy0049_flag:
                            match_result = re.findall('P1[0-5]', diagnosis_code)
                            if match_result:
                                admission_time = data.get(collection_name, dict()).get('pat_visit', dict()).get('admission_time', '')
                                date_of_birth = data.get(collection_name, dict()).get('pat_info', dict()).get('date_of_birth', '')
                                if admission_time and date_of_birth:
                                    age_baby = (datetime.strptime(admission_time, '%Y-%m-%d %H:%M:%S') - datetime.strptime(date_of_birth, '%Y-%m-%d %H:%M:%S')).days
                                    if age_baby >= 28:
                                        sy0049_flag = True

                        # SY0051
                        if self.filter_dept('SY0051', data) and not sy0051_flag:
                            discharge_dept = data.get(collection_name, dict()).get('pat_visit', dict()).get('dept_discharge_from_name', '')
                            if 'J40' in diagnosis_code and discharge_dept == '儿科':
                                sy0051_flag = True
                                        
                if shouyezhenduan_diag and False:
                    diff_diag = ruyuanjilu_diag.difference(shouyezhenduan_diag)  # 入院诊断都在门急诊诊断中就可以
                    if diff_diag:
                        reason = '入院记录初步诊断不等于病案首页门急诊诊断'
                        error_info = {'code': 'SY0014',
                                      'num': num,
                                      'reason': reason}
                        error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        patient_result['pat_info'].setdefault('html', list())
                        if collection_name not in patient_result['pat_info']['html']:
                            patient_result['pat_info']['html'].append(collection_name)
                        self.all_result[data['_id']] = patient_result
                        num += 1
                if first_letter:
                    reason = '门急诊诊断编码含<{0}>'.format(first_letter)
                    error_info = {'code': 'SY0015',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
                if binglizhenduan_flag and not binglizhenduan_content:
                    reason = '含病理报告且出院诊断编码含“C00~C97/D00~D48”，病理诊断却为空'
                    error_info = {'code': 'SY0016',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
                if (not binglizhenduan_flag2) and binglizhenduan_content:
                    reason = '非肿瘤类疾病，病理诊断不为空'
                    error_info = {'code': 'SY0017',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
                if sy0018_bingli:
                    reason = '出院首要诊断编码含“D00~D09”，病理诊断不为“M****/2”'
                    error_info = {'code': 'SY0018',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
                if sy0019_flag:
                    reason = '出院诊断编码含“M******/*、M80”或含“V\W\X\Y”'
                    error_info = {'code': 'SY0019',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
                if sy0020_flag:  # 诊断编码含（“O80~O84”and“O00~O08”）
                    if not z37_flag:  # 不含“Z37”
                        reason = '出院诊断编码含“O80~O84\O00~O08”却不含诊断编码“Z37”'
                        error_info = {'code': 'SY0020',
                                      'num': num,
                                      'reason': reason}
                        error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        patient_result['pat_info'].setdefault('html', list())
                        if collection_name not in patient_result['pat_info']['html']:
                            patient_result['pat_info']['html'].append(collection_name)
                        self.all_result[data['_id']] = patient_result
                        num += 1
                if sy0021_flag:
                    reason = '医保患者出院诊断编码含“F”'
                    error_info = {'code': 'SY0021',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
                if sy0022_flag:
                    reason = '首次入院患者出院诊断编码含“Z”'
                    error_info = {'code': 'SY0022',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
                if sy0023_flag:
                    reason = '诊断编码为“Z37”，出院科室不为产科'
                    error_info = {'code': 'SY0023',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
                if sy0041_flag:
                    reason = '出院主诊断编码“S01~S06”，颅脑损伤患者入院前/后昏迷时间为空'
                    error_info = {'code': 'SY0041',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
                if sy0047_flag:
                    reason = '出院诊断出现含“M”的诊断编码'
                    error_info = {'code': 'SY0047',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
                if sy0048_flag:
                    reason = '门急诊诊断出现含“M”的诊断编码'
                    error_info = {'code': 'SY0048',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
                if sy0049_flag:
                    reason = '门急诊诊断出现“P10~P15”诊断编码，但年龄却大于28天'
                    error_info = {'code': 'SY0049',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
                if sy0050_flag:
                    reason = '出院诊断出现“P10~P15”诊断编码，但年龄却大于28天'
                    error_info = {'code': 'SY0050',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
                if sy0051_flag:
                    reason = '门急诊诊断出现“J40”诊断编码，出院科室却为儿科'
                    error_info = {'code': 'SY0051',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
                if sy0052_flag:
                    reason = '出院诊断出现“J40”诊断编码，出院科室却为儿科'
                    error_info = {'code': 'SY0052',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
                if sy0053_bingli:
                    reason = '出院首要诊断编码含“C77~C80”，病理诊断不为“M****/6”'
                    error_info = {'code': 'SY0053',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
                if sy0054_bingli:
                    reason = '出院首要诊断编码含“C00~C76”，病理诊断不为“M****/3”'
                    error_info = {'code': 'SY0054',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
                if sy0055_bingli:
                    reason = '出院首要诊断编码含“D10~D36”，病理诊断不为“M****/0”'
                    error_info = {'code': 'SY0055',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
                if sy0056_bingli:
                    reason = '出院首要诊断编码含“D37~D48”，病理诊断不为“M****/1”'
                    error_info = {'code': 'SY0056',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
                    num += 1
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_info_binganshouye(self, collection_name, **json_file):
        """
        collection = binganshouye
        SY0032: 病案首页--就诊信息--年龄值>120岁 -->检出
        SY0033: 病案首页--就诊信息--年龄值>15岁 -->检出
        SY0034: 病案首页--就诊信息--联系人与患者关系==夫妻 and 病案首页--就诊信息--婚姻状态名称==未婚 -->检出
        SY0035: 病案首页--就诊信息--男性年龄<22 or 女性年龄>20 and  病案首页--就诊信息--婚姻状态名称==已婚 -->检出
        SY0036: 病案首页--就诊信息--6<年龄<14 and 病案首页--就诊信息--职业名称不等于“学生” or 病案首页--就诊信息--职业名称 不等于 “入院记录--个人史--现职业” -->检出
        SY0037: 病案首页--就诊信息--就诊时间 ≤ 病案首页--就诊信息--出院时间 -->检出
        SY0039: 病案首页--就诊信息--邮编  值位数 不等于 6 -->检出
        SY0042: (住院医嘱--医嘱项名称==出院 and 病案首页--就诊信息--出院方式 不等于医嘱离院)  or (住院死亡记录 不为空 and 病案首页--就诊信息--出院方式 不等于死亡) -->检出
        external = siwangjilu, ruyuanjilu, yizhu
        SY0043: 病案首页--就诊信息--是否有出院31天内再住院计划==2 and 病案首页--就诊信息--再住院目的==NULL  -->检出
        SWJL0000: 病案首页--就诊信息--离院方式==5 and 住院死亡记录==NULL  -->检出
        external = siwangjilu
        SY0059: 病案首页--就诊信息--ICU天数+CCU天数之和 不等于 病案首页--就诊信息--特级护理天数 -->检出
        SY0060: 病案首页--就诊信息--入ICU时间 ＜ 病案首页--就诊信息--就诊时间  -->检出
        SY0061: 病案首页--就诊信息--入ICU时间 ＞ 病案首页--就诊信息--出院时间 -->检出
        SY0062: 病案首页--就诊信息--出ICU时间 ＜ 病案首页--就诊信息--入ICU时间 -->检出
        SY0063: 病案首页--就诊信息--出ICU时间 ＞ 病案首页--就诊信息--出院时间 -->检出
        SY0064: 病案首页--就诊信息--ICU天数+CCU天数 不等于 病案首页--就诊信息--出ICU时间 - 入ICU时间  -->检出
        """
        regular_code = ['SY0032', 'SY0033', 'SY0034', 'SY0035', 'SY0036', 'SY0037', 'SY0039', 'SY0042', 'SY0043', 'SWJL0000',
                        'SY0059', 'SY0060', 'SY0061', 'SY0062', 'SY0063', 'SY0064']
        regular_boolean = list()
        for i in regular_code:
            if self.regular_model.get(i, dict()).get('status') == '启用':
                regular_boolean.append(False)
            else:
                regular_boolean.append(True)
        if all(regular_boolean):
            return self.all_result
        if json_file:
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                _, patient_result, num = self.get_patient_info(data, collection_name)
                # 病案首页无文书时间及文书作者
                # SY0032, SY0033, SY0035, SY0036  要获取年龄
                if self.filter_dept('SY0032', data) or self.filter_dept('SY0033', data) or self.filter_dept('SY0035', data) or self.filter_dept('SY0036', data):
                    age_unit = data.get(collection_name, dict()).get('pat_visit', dict()).get('age_value_unit')
                    if age_unit == '岁':
                        age = data.get(collection_name, dict()).get('pat_visit', dict()).get('age_value')
                        try:
                            age = float(age)
                        except:
                            self.logger.info('\n病案首页年龄问题:\n\tid: {0}\n\tage: {1}\n'.format(data['_id'], age))
                            age = 'error_age'
                        if age != 'error_age':
                            # SY0032
                            if self.filter_dept('SY0032', data) and age > 120:
                                reason = '年龄书写有误'
                                error_info = {'code': 'SY0032',
                                              'num': num,
                                              'age': '{}{}'.format(age, age_unit),
                                              'reason': reason}
                                error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                                if 'score' in error_info:
                                    patient_result['pat_info']['machine_score'] += error_info['score']
                                patient_result['pat_value'].append(error_info)
                                patient_result['pat_info'].setdefault('html', list())
                                if collection_name not in patient_result['pat_info']['html']:
                                    patient_result['pat_info']['html'].append(collection_name)
                                self.all_result[data['_id']] = patient_result
                                num += 1
                            # SY0033
                            if self.filter_dept('SY0033', data) and age > 15:
                                reason = '儿科年龄书写有误'
                                error_info = {'code': 'SY0033',
                                              'num': num,
                                              'age': '{}{}'.format(age, age_unit),
                                              'reason': reason}
                                error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                                if 'score' in error_info:
                                    patient_result['pat_info']['machine_score'] += error_info['score']
                                patient_result['pat_value'].append(error_info)
                                patient_result['pat_info'].setdefault('html', list())
                                if collection_name not in patient_result['pat_info']['html']:
                                    patient_result['pat_info']['html'].append(collection_name)
                                self.all_result[data['_id']] = patient_result
                                num += 1
                            # SY0035
                            if self.filter_dept('SY0035', data):
                                sex_name = data.get(collection_name, dict()).get('pat_info', dict()).get('sex_name', '')
                                marital_status_name = data.get(collection_name, dict()).get('pat_visit', dict()).get('marital_status_name', '')
                                if marital_status_name == '已婚':
                                    if (sex_name == '男' and age < 22) or (sex_name == '女' and age < 20):
                                        reason = '患者年龄与婚姻状态不相符'
                                        error_info = {'code': 'SY0035',
                                                      'num': num,
                                                      'age': '{}{}'.format(age, age_unit),
                                                      'sex_name': sex_name,
                                                      'marital_status': marital_status_name,
                                                      'reason': reason}
                                        error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                                        if 'score' in error_info:
                                            patient_result['pat_info']['machine_score'] += error_info['score']
                                        patient_result['pat_value'].append(error_info)
                                        patient_result['pat_info'].setdefault('html', list())
                                        if collection_name not in patient_result['pat_info']['html']:
                                            patient_result['pat_info']['html'].append(collection_name)
                                        self.all_result[data['_id']] = patient_result
                                        num += 1
                            # SY0036
                            if self.filter_dept('SY0036', data):
                                if 6 < age < 14:
                                    occupation_name = data.get(collection_name, dict()).get('pat_visit', dict()).get('occupation_name', '')
                                    if occupation_name and occupation_name != '学生':
                                        personal_his = dict()
                                        if data.get('ruyuanjilu', list()):
                                            personal_his = data['ruyuanjilu'][0]
                                        if personal_his:
                                            current_occupation = personal_his.get('ruyuanjilu', dict()).get('social_history', dict()).get('current_occupation', '')
                                            if current_occupation != occupation_name:
                                                reason = '病案首页职业信息与入院记录个人史职业信息不相符'
                                                error_info = {'code': 'SY0036',
                                                              'num': num,
                                                              'age': '{}{}'.format(age, age_unit),
                                                              'occupation_name': occupation_name,
                                                              'current_occupation': current_occupation,
                                                              'reason': reason}
                                                error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                                                if 'score' in error_info:
                                                    patient_result['pat_info']['machine_score'] += error_info['score']
                                                patient_result['pat_value'].append(error_info)
                                                patient_result['pat_info'].setdefault('html', list())
                                                if collection_name not in patient_result['pat_info']['html']:
                                                    patient_result['pat_info']['html'].append(collection_name)
                                                self.all_result[data['_id']] = patient_result
                                                num += 1
                # SY0034
                if self.filter_dept('SY0034', data):
                    relationship = data.get(collection_name, dict()).get('pat_visit', dict()).get('relationship_name', '')
                    if relationship == '夫妻':
                        marital_status_name = data.get(collection_name, dict()).get('pat_visit', dict()).get('marital_status_name', '')
                        if marital_status_name == '未婚':
                            reason = '联系与患者关系为夫妻，婚姻状态为未婚'
                            error_info = {'code': 'SY0034',
                                          'num': num,
                                          'relationship': relationship,
                                          'marital_status': marital_status_name,
                                          'reason': reason}
                            error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                            if 'score' in error_info:
                                patient_result['pat_info']['machine_score'] += error_info['score']
                            patient_result['pat_value'].append(error_info)
                            patient_result['pat_info'].setdefault('html', list())
                            if collection_name not in patient_result['pat_info']['html']:
                                patient_result['pat_info']['html'].append(collection_name)
                            self.all_result[data['_id']] = patient_result
                            num += 1

                admission_time = data.get(collection_name, dict()).get('pat_visit', dict()).get('admission_time', '')
                discharge_time = data.get(collection_name, dict()).get('pat_visit', dict()).get('discharge_time', '')

                # SY0037
                if self.filter_dept('SY0037', data):
                    if admission_time and discharge_time:
                        if admission_time > discharge_time:
                            reason = '入院日期大于等于出院日期'
                            error_info = {'code': 'SY0037',
                                          'num': num,
                                          'reason': reason}
                            error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                            if 'score' in error_info:
                                patient_result['pat_info']['machine_score'] += error_info['score']
                            patient_result['pat_value'].append(error_info)
                            patient_result['pat_info'].setdefault('html', list())
                            if collection_name not in patient_result['pat_info']['html']:
                                patient_result['pat_info']['html'].append(collection_name)
                            self.all_result[data['_id']] = patient_result
                            num += 1
                # SY0039
                if self.filter_dept('SY0039', data):
                    postcode = data.get(collection_name, dict()).get('pat_visit', dict()).get('postcode')
                    if postcode and len(postcode) != 6:
                        reason = '邮编位数非6位有效邮编'
                        error_info = {'code': 'SY0039',
                                      'num': num,
                                      'postcode': postcode,
                                      'reason': reason}
                        error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        patient_result['pat_info'].setdefault('html', list())
                        if collection_name not in patient_result['pat_info']['html']:
                            patient_result['pat_info']['html'].append(collection_name)
                        self.all_result[data['_id']] = patient_result
                        num += 1
                # SY0043
                if self.filter_dept('SY0043', data):
                    if data.get(collection_name, dict()).get('pat_visit', dict()).get('again_in_plan') == '是':
                        if not data.get(collection_name, dict()).get('pat_visit', dict()).get('again_in_purpose'):
                            reason = '有再住院计划无再住院目的'
                            error_info = {'code': 'SY0043',
                                          'num': num,
                                          'reason': reason}
                            error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                            if 'score' in error_info:
                                patient_result['pat_info']['machine_score'] += error_info['score']
                            patient_result['pat_value'].append(error_info)
                            patient_result['pat_info'].setdefault('html', list())
                            if collection_name not in patient_result['pat_info']['html']:
                                patient_result['pat_info']['html'].append(collection_name)
                            self.all_result[data['_id']] = patient_result
                            num += 1
                # SY0042
                if self.filter_dept('SY0042', data):
                    flag = False
                    discharge_class_name = data.get(collection_name, dict()).get('pat_visit', dict()).get('discharge_class_name', '')
                    if discharge_class_name != '医嘱离院':
                        if data.get('yizhu', list()):
                            yizhu_data = data['yizhu'][0]
                            for one_record in yizhu_data['yizhu']:
                                if one_record.get('order_item_name', '') == '出院':
                                    flag = True
                                    break
                        # 住院医嘱--医嘱项名称==出院 and 病案首页--就诊信息--出院方式 不等于医嘱离院
                    if not flag and discharge_class_name != '死亡':
                        if data.get('siwangjilu', list()):
                            flag = True
                    if flag:
                        reason = '医嘱离院、死亡患者与首页离院方式不相符'
                        error_info = {'code': 'SY0042',
                                      'num': num,
                                      'reason': reason}
                        error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        patient_result['pat_info'].setdefault('html', list())
                        if collection_name not in patient_result['pat_info']['html']:
                            patient_result['pat_info']['html'].append(collection_name)
                        self.all_result[data['_id']] = patient_result
                        num += 1
                # SWJL0000
                if self.filter_dept('SWJL0000', data):
                    discharge_class_name = data.get(collection_name, dict()).get('pat_visit', dict()).get('discharge_class_name', '')
                    if discharge_class_name == '死亡':
                        if data.get('siwangjilu', list()):
                            siwang_res = True
                        else:
                            siwang_res = False
                        if not siwang_res:
                            reason = '离院方式为死亡，死亡记录未书写'
                            error_info = {'code': 'SWJL0000',
                                          'num': num,
                                          'reason': reason}
                            error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                            if 'score' in error_info:
                                patient_result['pat_info']['machine_score'] += error_info['score']
                            patient_result['pat_value'].append(error_info)
                            patient_result['pat_info'].setdefault('html', list())
                            if collection_name not in patient_result['pat_info']['html']:
                                patient_result['pat_info']['html'].append(collection_name)
                            self.all_result[data['_id']] = patient_result
                            num += 1

                flag = True
                icu_days = data.get(collection_name, dict()).get('pat_visit', dict()).get('icu_days', '')
                v = re.findall('[\d]+\.?[\d]*', icu_days)
                if not v:
                    flag = False
                else:
                    icu_days = float(v[0])

                ccu_days = data.get(collection_name, dict()).get('pat_visit', dict()).get('ccu_days', '')
                v = re.findall('[\d]+\.?[\d]*', ccu_days)
                if not v:
                    flag = False
                else:
                    ccu_days = float(v[0])

                spec_level_nurs_days = data.get(collection_name, dict()).get('pat_visit', dict()).get('spec_level_nurs_days', '')
                v = re.findall('[\d]+\.?[\d]*', spec_level_nurs_days)
                if not v:
                    spec_level_nurs_days = 0
                else:
                    spec_level_nurs_days = float(v[0])
                icu_in_date = data.get(collection_name, dict()).get('pat_visit', dict()).get('icu_first_in_time', '')
                icu_out_date = data.get(collection_name, dict()).get('pat_visit', dict()).get('icu_first_out_time', '')

                if self.filter_dept('SY0059', data) and flag:
                    if icu_days + ccu_days != spec_level_nurs_days:
                        reason = '重症监护住院天数与特级护理天数不相符'
                        error_info = {'code': 'SY0059',
                                      'num': num,
                                      'icu_days': icu_days,
                                      'ccu_days': ccu_days,
                                      'spec_level_nurs_days': spec_level_nurs_days,
                                      'reason': reason}
                        error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        patient_result['pat_info'].setdefault('html', list())
                        if collection_name not in patient_result['pat_info']['html']:
                            patient_result['pat_info']['html'].append(collection_name)
                        self.all_result[data['_id']] = patient_result
                        num += 1

                if icu_in_date:
                    if self.filter_dept('SY0060', data) and admission_time:
                        if icu_in_date < admission_time:
                            reason = '入ICU时间小于入院时间'
                            error_info = {'code': 'SY0060',
                                          'num': num,
                                          'icu_in_date': icu_in_date,
                                          'admission_time': admission_time,
                                          'reason': reason}
                            error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                            if 'score' in error_info:
                                patient_result['pat_info']['machine_score'] += error_info['score']
                            patient_result['pat_value'].append(error_info)
                            patient_result['pat_info'].setdefault('html', list())
                            if collection_name not in patient_result['pat_info']['html']:
                                patient_result['pat_info']['html'].append(collection_name)
                            self.all_result[data['_id']] = patient_result
                            num += 1
                    if self.filter_dept('SY0061', data) and discharge_time:
                        if icu_in_date > discharge_time:
                            reason = '入ICU时间大于出院时间'
                            error_info = {'code': 'SY0061',
                                          'num': num,
                                          'icu_in_date': icu_in_date,
                                          'discharge_time': discharge_time,
                                          'reason': reason}
                            error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                            if 'score' in error_info:
                                patient_result['pat_info']['machine_score'] += error_info['score']
                            patient_result['pat_value'].append(error_info)
                            patient_result['pat_info'].setdefault('html', list())
                            if collection_name not in patient_result['pat_info']['html']:
                                patient_result['pat_info']['html'].append(collection_name)
                            self.all_result[data['_id']] = patient_result
                            num += 1
                if icu_out_date:
                    if self.filter_dept('SY0062', data) and icu_in_date:
                        if icu_out_date < icu_in_date:
                            reason = '出ICU时间小于入ICU时间'
                            error_info = {'code': 'SY0062',
                                          'num': num,
                                          'icu_out_date': icu_out_date,
                                          'icu_in_date': icu_in_date,
                                          'reason': reason}
                            error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                            if 'score' in error_info:
                                patient_result['pat_info']['machine_score'] += error_info['score']
                            patient_result['pat_value'].append(error_info)
                            patient_result['pat_info'].setdefault('html', list())
                            if collection_name not in patient_result['pat_info']['html']:
                                patient_result['pat_info']['html'].append(collection_name)
                            self.all_result[data['_id']] = patient_result
                            num += 1
                    if self.filter_dept('SY0063', data) and discharge_time:
                        if icu_out_date > discharge_time:
                            reason = '出ICU时间大于出院时间'
                            error_info = {'code': 'SY0063',
                                          'num': num,
                                          'icu_out_date': icu_out_date,
                                          'discharge_time': discharge_time,
                                          'reason': reason}
                            error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                            if 'score' in error_info:
                                patient_result['pat_info']['machine_score'] += error_info['score']
                            patient_result['pat_value'].append(error_info)
                            patient_result['pat_info'].setdefault('html', list())
                            if collection_name not in patient_result['pat_info']['html']:
                                patient_result['pat_info']['html'].append(collection_name)
                            self.all_result[data['_id']] = patient_result
                            num += 1
                if icu_in_date and icu_out_date and flag and self.filter_dept('SY0064', data):
                    delta_time = (datetime.strptime(icu_out_date, '%Y-%m-%d %H:%M:%S') - datetime.strptime(icu_in_date, '%Y-%m-%d %H:%M:%S')).days
                    if icu_days + ccu_days - delta_time > 1:
                        reason = '重症监护天数与重症监护进出明细不相符'
                        error_info = {'code': 'SY0064',
                                      'num': num,
                                      'icu_days': icu_days,
                                      'ccu_days': ccu_days,
                                      'icu_out_date': icu_out_date,
                                      'icu_in_date': icu_in_date,
                                      'reason': reason}
                        error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                        if 'score' in error_info:
                            patient_result['pat_info']['machine_score'] += error_info['score']
                        patient_result['pat_value'].append(error_info)
                        patient_result['pat_info'].setdefault('html', list())
                        if collection_name not in patient_result['pat_info']['html']:
                            patient_result['pat_info']['html'].append(collection_name)
                        self.all_result[data['_id']] = patient_result
                        num += 1
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result

    def check_gender_chanke(self, collection_name, **json_file):
        """
        collection = binganshouye
        性别 == '男' 检出，专科标识为产科
        SY0002
        """
        if json_file and self.filter_dept('SY0002', json_file):
            mongo_result = [json_file]
        else:
            return self.all_result
        for data in mongo_result:
            try:
                _, patient_result, num = self.get_patient_info(data, collection_name)
                sex_name = data.get(collection_name, dict()).get('pat_info', dict()).get('sex_name', '')
                person_name = data.get(collection_name, dict()).get('pat_info', dict()).get('person_name', '')
                if self.conf_dict['check_past_guominshi']['儿科'].findall(person_name):
                    continue
                if not sex_name:
                    continue
                if sex_name == '男':
                    reason = '病案首页病人信息性别有误'
                    error_info = {'code': 'SY0002',
                                  'num': num,
                                  'reason': reason}
                    error_info = self.supplementErrorInfo(error_info=error_info, collection_name=collection_name)
                    if 'score' in error_info:
                        patient_result['pat_info']['machine_score'] += error_info['score']
                    patient_result['pat_value'].append(error_info)
                    patient_result['pat_info'].setdefault('html', list())
                    if collection_name not in patient_result['pat_info']['html']:
                        patient_result['pat_info']['html'].append(collection_name)
                    self.all_result[data['_id']] = patient_result
            except:
                self.logger_error.error(data['_id'])
                self.logger_error.error(traceback.format_exc())
        return self.all_result


if __name__ == '__main__':
    app = CheckMultiRecords(debug=True)
