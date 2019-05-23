#!/usr/bin/env python
# encoding=utf-8

import os
import sys

cur_path = os.path.abspath(os.path.dirname(__file__))
root_path = os.path.split(cur_path)[0]
sys.path.append(root_path)  # 项目路径添加到系统路径
import time
import re
import xlwt
from datetime import datetime
from collections import OrderedDict
from Utils.MongoUtils import PullDataFromMDBUtils, PushDataFromMDBUtils
from Utils.loadingConfigure import Properties
from Utils.segmentWord import RunSegmentWord
from Utils.LogUtils import LogUtils
from Utils.gainESSearch import GainESSearch
from MedicalQuality.mainProgram import CheckMultiRecords


class StatisticPatientInfos(object):
    """
    统计患者的基本信息方法
    """

    def __init__(self, debug=False):
        self.debug = debug
        self.mongo_pull_utils = PullDataFromMDBUtils()
        self.mongo_push_utils = PushDataFromMDBUtils()
        self.parameters = Properties()
        self.run_regular = CheckMultiRecords(debug=True)
        self.logger_back = LogUtils().getLogger('backend')
        self.app_es = GainESSearch()
        self.database_name = self.mongo_pull_utils.mongodb_database_name
        self.record_database = self.parameters.properties.get('record_mongodb', '')
        self.collection_name = self.mongo_pull_utils.mongodb_collection_name  # 质控结果数据库

        # 加载规则模型
        self.regular_model = self.parameters.regular_model['终末']
        self.dept_list = self.parameters.dept.copy()
        self.conf_dict = self.parameters.conf_dict.copy()

    @staticmethod
    def this_month():
        # 获取当月的开始时间（x年x月格式），当前时间（x年x月x日 x时x分x秒格式）
        start = datetime.now().strftime('%Y-%m')
        end = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return start, end

    @staticmethod
    def last_month():
        # 获取上月月份和当月月份
        start_time = datetime.now()
        month = start_time.month - 1 if start_time.month > 1 else 12
        last_year = start_time.year - 1 if month == 12 else start_time.year
        start = datetime(last_year, month, 1).strftime('%Y-%m')
        end = datetime.now().strftime('%Y-%m')
        return start, end

    @staticmethod
    def last_two_month():
        # 获取上上月月份和上月月份
        start_time = datetime.now()
        last_two_month = 10 + start_time.month if start_time.month < 3 else start_time.month - 2
        last_two_year = start_time.year if last_two_month < 11 else start_time.year - 1
        month = start_time.month - 1 if start_time.month > 1 else 12
        last_year = start_time.year - 1 if month == 12 else start_time.year
        end = datetime(last_year, month, 1).strftime('%Y-%m')
        start = datetime(last_two_year, last_two_month, 1).strftime('%Y-%m')
        return start, end

    @staticmethod
    def last_tri_month():
        # 获取上上上月月份和上上月月份
        start_time = datetime.now()
        last_two_month = 10 + start_time.month if start_time.month < 3 else start_time.month - 2
        last_two_year = start_time.year if last_two_month < 11 else start_time.year - 1
        last_three_month = 9 + start_time.month if start_time.month < 4 else start_time.month - 3
        last_three_year = start_time.year if last_three_month < 10 else start_time.year - 1
        start = datetime(last_three_year, last_three_month, 1).strftime('%Y-%m')
        end = datetime(last_two_year, last_two_month, 1).strftime('%Y-%m')
        return start, end

    @staticmethod
    def transformMongoResult(query_result):
        """
        将mongo查询结果进行格式转化，转化为dict    ----> result 为 list 类型？？？
        """
        result = []
        for data_index, data_value in enumerate(query_result):
            data_value['problem_num'] = len(data_value.get('content', list())) + len(
                data_value.get('pat_value', list()))  # 统计问题条数
            result.append(data_value)
            for pat_value in data_value.get('pat_value', list()):
                if '--' in pat_value.get('path', ''):
                    pat_value['html_chinese'] = pat_value.get('path', '').split('--')[0]
                else:
                    pat_value['html_chinese'] = pat_value.get('path', '')
        return result

    def statisticDept(self, dept_name='all', start_date='', end_date='', last_month=''):
        """
        根据科室统计所有患者数量，默认是所有的科室
        """
        collection_name = self.collection_name + '_statistics_days'
        collection = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                             collection_name=collection_name)
        start = ''
        end = ''
        if last_month == '0':  # 本月
            start, end = self.this_month()
        elif last_month == '1':  # 上月
            start, end = self.last_month()
        elif last_month == '2':  # 上上月
            start, end = self.last_two_month()
        elif last_month == '3':
            start, end = self.last_tri_month()
        if start_date and end_date:
            if start and start_date < start:
                start_date = start
            if end and end_date > end:
                end_date = end
            time_field = {'$match': {'_id': {'$gte': start_date, '$lt': end_date}}}  # 不包括end_date的日期
        else:
            if start and end:
                start_date = start
                end_date = end
                time_field = {'$match': {'_id': {'$gte': start_date, '$lt': end_date}}}
            else:
                time_field = {'$match': {}}
        if (not dept_name) or dept_name == 'all':
            dept_field = {'$match': {}}
        else:
            dept_field = {'$match': {'info.dept': dept_name}}
        pipeline = [time_field,
                    {'$unwind': '$info'},
                    dept_field,
                    {'$group': {'_id': '$info.dept', 'value': {"$sum": '$info.error'}}},
                    {'$sort': {'value': -1}}]
        query_result = collection.aggregate(pipeline, allowDiskUse=True).batch_size(50)
        result = list()
        for data in query_result:
            if not re.sub('[A-Za-z0-9]*', '', data['_id']):
                continue
            result.append({'name': data['_id'], 'value': data['value']})
        total = sum([value['value'] for value in result])
        result.insert(0, {'name': '全部', 'value': total})
        return result

    def findPatientByStatusJiwang(self, status_bool='all', dept_name='all', show_num=10, page_num=0, patient_id='',
                                  regular_details='', code='', record='', start_date='', end_date='', category='',
                                  isResult=False):
        # category 的值为：shuxue， shoushu, siwang 中的一个。
        """
        既往数据查询
        """
        result = dict()
        query_field = dict()
        result['page_num'] = page_num
        result['show_num'] = show_num

        # 获取3个月前的月份值
        start_time = datetime.now()
        start_month = 9 + start_time.month if start_time.month < 4 else start_time.month - 3

        month_tab = '{}月'.format(start_month)
        result['month'] = [month_tab]
        # 获取全部分类的患者信息
        if isResult != 'all':
            if isResult:
                # 是问题病历
                query_field['pat_value.code'] = {'$exists': True}
            else:
                # 不是问题病历
                query_field['pat_value.code'] = {'$exists': False}
        if status_bool == 'all':
            status_bool = {'$in': [True, False]}
        elif status_bool == 'zero':
            status_bool = True
            query_field['pat_value'] = {'$size': 0}
        query_field['status'] = status_bool
        if dept_name and 'all' != dept_name:
            query_field['pat_info.dept_discharge_from_name'] = dept_name
        if patient_id:
            query_field['pat_info.patient_id'] = patient_id
        if regular_details:
            query_field['pat_value.name'] = regular_details
        if code:
            query_field['pat_value.regular_details'] = code
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
        start, end = self.last_tri_month()
        query_field['pat_info.discharge_time'] = dict()
        if start_date:
            query_field['pat_info.discharge_time']['$gt'] = start_date
        else:
            query_field['pat_info.discharge_time']['$gt'] = start
        if end_date:
            query_field['pat_info.discharge_time']['$lt'] = end_date
        else:
            query_field['pat_info.discharge_time']['$lt'] = end
        if record:
            query_field['pat_value.path'] = {'$regex': record}
        if category and category != 'all':
            query_field['pat_category.{}'.format(category)] = True
        conn = self.mongo_pull_utils.connection()
        query_result = conn.find(query_field).sort([('pat_info.discharge_time', 1)]).skip(page_num * show_num).limit(
            show_num)
        query_count = conn.find(query_field).count()
        result['num'] = query_count
        result['info'] = self.transformMongoResult(query_result)
        return result

    def findPatientByStatus(self, status_bool='all', dept_name='all', show_num=10, page_num=0, patient_id='',
                            regular_details='', code='', record='', start_date='', end_date='', category='',
                            isResult=False, last_month='0'):
        """
        既往/终末质控数据查询
        last_month: '0':本月, '1': 上月, '2': 上上月, '3': 既往
        """
        result = dict()
        query_field = dict()
        if last_month == '3':
            return self.findPatientByStatusJiwang(status_bool, dept_name, show_num, page_num, patient_id,
                                                  regular_details, code, record, start_date, end_date, category,
                                                  isResult)
        # 获取全部分类的患者信息
        if isResult != 'all':
            if isResult:
                # 是问题病历
                query_field['pat_value.code'] = {'$exists': True}
            else:
                # 不是问题病历
                query_field['pat_value.code'] = {'$exists': False}
        if status_bool == 'all':
            status_bool = {'$in': [True, False]}
        elif status_bool == 'zero':
            status_bool = True
            query_field['pat_value'] = {'$size': 0}
        query_field['status'] = status_bool
        if dept_name and 'all' != dept_name:
            query_field['pat_info.dept_discharge_from_name'] = dept_name
        if patient_id:
            query_field['pat_info.patient_id'] = patient_id
        if regular_details:
            query_field['pat_value.name'] = regular_details
        if code:
            query_field['pat_value.regular_details'] = code
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
            query_field['pat_value.path'] = {'$regex': record}

        start_time = datetime.now()
        last_two_month = 10 + start_time.month if start_time.month < 3 else start_time.month - 2
        last_two_year = start_time.year if last_two_month < 11 else start_time.year - 1
        last_month_date = start_time.month - 1 if start_time.month > 1 else 12
        last_year = start_time.year - 1 if last_month_date == 12 else start_time.year
        last_two_date = datetime(last_two_year, last_two_month, 1).strftime('%m月')
        last_date = datetime(last_year, last_month_date, 1).strftime('%m月')
        this_date = start_time.strftime('%m月')
        result['month'] = [last_two_date, last_date, this_date]
        result['page_num'] = page_num
        result['show_num'] = show_num

        if last_month == '0':
            collection_name = self.mongo_pull_utils.mongodb_collection_name + '_this_month'
            conn = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                           collection_name=collection_name)
        elif last_month == '1':
            collection_name = self.mongo_pull_utils.mongodb_collection_name + '_last_month'
            conn = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                           collection_name=collection_name)
        elif last_month == '2':
            collection_name = self.mongo_pull_utils.mongodb_collection_name + '_last_two_month'
            conn = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                           collection_name=collection_name)
        else:
            return result
        if category and category != 'all':
            query_field['pat_category.{}'.format(category)] = True
        query_result = conn.find(query_field).sort([('pat_info.discharge_time', 1), ('_id', 1)]).skip(
            page_num * show_num).limit(show_num)
        query_count = conn.find(query_field).count()
        result['num'] = query_count
        result['info'] = self.transformMongoResult(query_result)
        return result

    def getPatientHtmlList(self, data_id):
        """获取电子病历文档列表
        shouyezhenduan：首页诊断
        shouyeshoushu：首页手术
        hulitizhengyangli：
        """
        id_tmp = data_id.split('#')[:3]
        patient_id, visit_id = id_tmp[0], id_tmp[1]
        result = OrderedDict()  # 对字典中的元素进行排序

        # 根据 patient_id, visit_id 去 ES 接口中查询数据
        es_result = self.app_es.getPatientRecordList(patient_id, visit_id)
        if not es_result.get('res_flag'):
            result.update(es_result)
        else:
            html_list = es_result.get('result', list())
            for one_html in self.conf_dict['html_english_chinese']:
                if one_html in ['shouyezhenduan', 'shouyeshoushu', 'hulitizhengyangli']:
                    continue
                if one_html in html_list:
                    result[one_html] = self.conf_dict['html_english_chinese'][one_html]
        return result

    def findPatientHtml(self, data_id, record_name='', mongo=False):
        """终末质控详情页面 -- 分项详细栏"""
        id_tmp = data_id.split('#')[:3]
        search_id = '#'.join([id_tmp[2]] + id_tmp[0:2])
        query_field = {'_id': search_id}
        patient_id, visit_id = id_tmp[0], id_tmp[1]
        result = dict()
        result['time_cost'] = dict()
        result['time_cost']['mongo'] = 0
        result['time_cost']['es'] = 0
        result['error_info'] = list()
        result['regular_name'] = list(set(
            [regular_name['regular_classify'] for regular_name in self.regular_model.values() if
             regular_name.get('regular_classify')]))
        result['html'] = OrderedDict()
        if not (record_name and record_name in self.conf_dict['html_english_chinese']):
            return result
        # html 原文采用 es/mongo 混合查询
        if record_name in ['shouyezhenduan', 'shouyeshoushu', 'hulitizhengyangli']:
            return result
        if record_name == 'binganshouye':  # 单独处理病案首页
            if mongo:
                start_time = time.time()

                # 创建数据库查询链接
                conn = self.mongo_pull_utils.record_db.get_collection(name=record_name)
                conn_shouyeshoushu = self.mongo_pull_utils.record_db.get_collection(name='shouyeshoushu')
                conn_shouyezhenduan = self.mongo_pull_utils.record_db.get_collection(name='shouyezhenduan')
                # 查询数据
                query_result = conn.find_one(query_field) or dict()
                result_shouyeshoushu = conn_shouyeshoushu.find_one(query_field) or dict()
                result_shouyezhenduan = conn_shouyezhenduan.find_one(query_field) or dict()
                result['time_cost']['mongo'] += time.time() - start_time
            else:  # mongo == False
                start_time = time.time()
                conn = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                               collection_name='binganshouye')
                query_result = conn.find_one(query_field, {}) or dict()
                result['time_cost']['mongo'] += time.time() - start_time
                if query_result:
                    # 从 MongoDB 质控库中获取到了数据走此流程
                    start_time = time.time()
                    conn_shouyeshoushu = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                                                 collection_name='shouyeshoushu')
                    conn_shouyezhenduan = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                                                  collection_name='shouyezhenduan')
                    query_result = conn.find_one(query_field) or dict()
                    result_shouyeshoushu = conn_shouyeshoushu.find_one(query_field) or dict()
                    result_shouyezhenduan = conn_shouyezhenduan.find_one(query_field) or dict()
                    result['time_cost']['mongo'] += time.time() - start_time
                    # 先做逻辑运算，然后再做赋值运算
                else:
                    # 没有从 MongoDB 中获取到数据，则直接到 ES 中去获取数据
                    start_time = time.time()
                    query_result = self.app_es.getRecordQuickly(patient_id, visit_id, record_name)
                    if not query_result.get('res_flag'):
                        result['error_info'].append(query_result)
                        return result
                    result_shouyeshoushu = self.app_es.getRecordQuickly(patient_id, visit_id, 'shouyeshoushu')
                    if not result_shouyeshoushu.get('res_flag'):
                        result['error_info'].append(result_shouyeshoushu)
                    result_shouyezhenduan = self.app_es.getRecordQuickly(patient_id, visit_id, 'shouyezhenduan')
                    if not result_shouyezhenduan.get('res_flag'):
                        result['error_info'].append(result_shouyezhenduan)
                    result['time_cost']['es'] += time.time() - start_time
            binganshouye = query_result.get(record_name, dict())
            shouyeshoushu = result_shouyeshoushu.get('shouyeshoushu', list())
            shouyezhenduan = result_shouyezhenduan.get('shouyezhenduan', list())
            binganshouye['shouyeshoushu'] = shouyeshoushu
            binganshouye['shouyezhenduan'] = list()
            for one_record in shouyezhenduan:
                if one_record.get('diagnosis_type_name') != '病理诊断':
                    binganshouye['shouyezhenduan'].append(one_record)
            result['html'][self.conf_dict['html_english_chinese'][record_name]] = [binganshouye]
        else:  # record_name != 'binganshouye'
            if mongo:
                start_time = time.time()
                """
                yizhu: 医嘱
                jianchabaogao: 检查报告
                jianyanbaogao: 检验报告
                """
                if record_name in ['yizhu', 'jianchabaogao', 'jianyanbaogao']:
                    collection = self.mongo_pull_utils.record_db.get_collection(name=record_name)
                    query_result = collection.find_one(query_field) or dict()
                else:
                    collection_src_name = record_name + '_src'
                    collection = self.mongo_pull_utils.record_db.get_collection(name=collection_src_name)
                    show_field = {record_name + '.MR_CONTENT_HTML': 1, record_name + '.LAST_MODIFY_DATE_TIME': 1}
                    query_result = collection.find_one(query_field, show_field) or dict()
                result['time_cost']['mongo'] += time.time() - start_time
            else:
                start_time = time.time()
                if record_name in ['yizhu', 'jianchabaogao', 'jianyanbaogao', 'hulitizhengyangli']:
                    conn = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                                   collection_name=record_name)
                    query_result = conn.find_one(query_field, {}) or dict()
                else:
                    conn = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                                   collection_name=record_name + '_src')
                    query_result = conn.find_one(query_field, {}) or dict()
                result['time_cost']['mongo'] += time.time() - start_time
                # 质控库中没有原文则在es中查找
                if query_result:
                    start_time = time.time()
                    query_result = conn.find_one(query_field) or dict()
                    result['time_cost']['mongo'] += time.time() - start_time
                else:
                    start_time = time.time()
                    if record_name in ['yizhu', 'jianchabaogao', 'jianyanbaogao']:
                        query_result = self.app_es.getRecordQuickly(patient_id, visit_id, record_name, is_src=False)
                    else:
                        query_result = self.app_es.getRecordQuickly(patient_id, visit_id, record_name, is_src=True)
                    if not query_result.get('res_flag'):
                        result['error_info'].append(query_result)
                        return result
                    result['time_cost']['es'] += time.time() - start_time
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
            """
            dict.setdefault(key, default=None)
            key -- 查找的键值。
            default -- 键不存在时，设置的默认键值。
            如果字典中包含有给定键，则返回该键对应的值，否则返回为该键设置的值。
            """
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
        # 对字典按照键进行排序

        for k, v in result.items():
            # 字典嵌套字典，对嵌套中的字典进行排序
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

    def saveModifyContent(self, data_id, content, delete_list, doctor_name='', last_month='0'):
        """
        保存修改内容
        last_month: 0：终末，本月；1：终末，上月；2：终末，上上月，3：既往
        """
        collection = self.mongo_push_utils.connectCollection(database_name=self.database_name,
                                                             collection_name=self.collection_name + '_zhongmo')
        collection_name = ''  # 不存在时，collection连接既往库，存在时，连接终末库
        if last_month == '0':
            collection_name = self.collection_name + '_this_month'
        elif last_month == '1':
            collection_name = self.collection_name + '_last_month'
        elif last_month == '2':
            collection_name = self.collection_name + '_last_two_month'
        elif last_month == '3':
            collection = self.mongo_push_utils.connectCollection(database_name=self.database_name,
                                                                 collection_name=self.collection_name)
        data = collection.find_one({'_id': data_id})
        if not data:
            return False
        if delete_list:
            pat_value = list()
            del_value = data.get('del_value', list())
            # html_list = list()
            num = 1
            for n, one_pat_value in enumerate(data['pat_value']):
                if n in delete_list or str(n) in delete_list:
                    one_pat_value['del_reason'] = delete_list.get(n, '') or delete_list.get(str(n), '')
                    del_value.append(one_pat_value)
                    continue
                one_pat_value['num'] = num
                pat_value.append(one_pat_value)
                num += 1
                # if one_pat_value['html'] not in html_list:
                #     html_list.append(one_pat_value['html'])
            data['pat_value'] = pat_value
            # data['pat_info']['html'] = html_list
            collection.update({'_id': data_id}, {'$set': {'pat_value': pat_value}}, upsert=True)
            collection.update({'_id': data_id}, {'$set': {'del_value': del_value}}, upsert=True)
            if collection_name:
                conn = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                               collection_name=collection_name)
                conn.update({'_id': data_id}, {'$set': {'pat_value': pat_value}}, upsert=True)
                conn.update({'_id': data_id}, {'$set': {'del_value': del_value}}, upsert=True)
            # collection.update({'_id': data_id}, {'$set': {'pat_info.html': html_list}}, upsert=True)
        machine_score = sum([value['score'] for value in data.get('pat_value', list()) if 'score' in value])
        artificial_score = sum([float(value['score']) for value in content if 'score' in value])
        collection.update({'_id': data_id}, {'$set': {'content': content}}, upsert=True)
        collection.update({'_id': data_id}, {'$set': {'control_date': datetime.strftime(datetime.now(), '%Y-%m-%d')}},
                          upsert=True)
        collection.update({'_id': data_id}, {'$set': {'status': True}}, upsert=True)
        collection.update({'_id': data_id}, {'$set': {'pat_info.machine_score': machine_score}}, upsert=True)
        collection.update({'_id': data_id}, {'$set': {'pat_info.artificial_score': artificial_score}}, upsert=True)
        collection.update({'_id': data_id}, {'$set': {'record_quality_doctor': doctor_name}}, upsert=True)
        if collection_name:
            conn = self.mongo_push_utils.connectCollection(database_name=self.database_name,
                                                           collection_name=collection_name)
            conn.update({'_id': data_id}, {'$set': {'content': content}}, upsert=True)
            conn.update({'_id': data_id}, {'$set': {'control_date': datetime.strftime(datetime.now(), '%Y-%m-%d')}},
                        upsert=True)
            conn.update({'_id': data_id}, {'$set': {'status': True}}, upsert=True)
            conn.update({'_id': data_id}, {'$set': {'pat_info.machine_score': machine_score}}, upsert=True)
            conn.update({'_id': data_id}, {'$set': {'pat_info.artificial_score': artificial_score}}, upsert=True)
            conn.update({'_id': data_id}, {'$set': {'record_quality_doctor': doctor_name}}, upsert=True)
        return True

    def showDataResult(self, data_id, is_zhongmo=False):
        """
        is_zhongmo: True：终末，False：既往
        """
        if is_zhongmo:
            conn = self.mongo_pull_utils.connection(self.collection_name + '_zhongmo')  # 只读权限
        else:
            conn = self.mongo_pull_utils.connection(self.collection_name)
        show_field = {'pat_info.inp_no': 1,
                      'pat_info.patient_id': 1,
                      'pat_info.machine_score': 1,
                      'pat_info.artificial_score': 1,
                      'pat_info.dept_discharge_from_name': 1,
                      'pat_value': 1,
                      'content': 1,
                      'record_quality_doctor': 1}
        data = conn.find_one({'_id': data_id}, show_field) or dict()
        result = dict()
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

    def saveTestContent(self, data_id, regular_code, test_content):
        """
        保存修改内容
        """
        collection = self.mongo_pull_utils.connection(collection_name=self.collection_name + 'zhongmo')
        data = collection.find_one({'_id': data_id, 'pat_value.code': regular_code}, {'_id': 1})
        if not data:
            return False
        collection.update({'_id': data_id, 'pat_value.code': regular_code},
                          {'$set': {'pat_value.$.test_content': test_content}}, upsert=True)
        collection.update({'_id': data_id, 'pat_value.code': regular_code},
                          {'$set': {'pat_value.$.test_status': True}}, upsert=True)
        return True

    def deptClassificationByMonth(self, start_month='', end_month=''):
        """
        按月给出科室分类数
        """
        collection = self.mongo_pull_utils.connection(collection_name=self.collection_name + 'zhongmo')
        collection_bingan = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                                    collection_name='binganshouye')
        query_field = dict()
        if not start_month:
            month = datetime.now().month - 1 or 12
            if month == 12:
                year = datetime.now().year - 1
            else:
                year = datetime.now().year
            time_left = datetime.strftime(datetime(year, month, 1), '%Y-%m')
            time_right = datetime.strftime(datetime.now(), '%Y-%m')
        else:
            time_left = start_month
            time_right = end_month
        if time_left:
            query_field = {'$match': {'pat_info.discharge_time': {'$gt': time_left, '$lte': time_right}}}
        result = dict()
        temp = dict()
        query_result = collection.aggregate([query_field,
                                             {"$group": {"_id": "$pat_info.dept_discharge_from_name",
                                                         "count": {"$sum": 1}}}])
        query_result_bingan = collection_bingan.aggregate(
            [{'$match': {'binganshouye.pat_visit.discharge_time': {'$gt': time_left, '$lt': time_right}}},
             {"$group": {"_id": "$binganshouye.pat_visit.dept_discharge_from_name", "count": {"$sum": 1}}}])

        for value in query_result_bingan:
            temp.setdefault(value['_id'], {'error': 0})
            temp[value['_id']].update({'total': value['count']})

        for value in query_result:
            temp[value['_id']].update({'error': value['count']})

        result['info'] = list()
        for k, v in temp.items():
            result['info'].append({'dept': k,
                                   'total': v['total'],
                                   'error': v['error'],
                                   'right': v['total'] - v['error']})
        result['info'].sort(key=lambda x: x['error'], reverse=True)
        result['num'] = len(result['info'])
        return result

    def oneYearRightAndError(self):
        """
        按年份查询病历问题量
        既往质控页面
        """
        collection_name = self.collection_name + '_statistics'
        collection = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                             collection_name=collection_name)
        result = dict()
        query_result = collection.find().sort('_id', 1).batch_size(50)
        temp = dict()
        for data in query_result:
            date = data['_id']
            year = date[:4]
            result.setdefault(year, dict())
            temp.setdefault(year, dict())
            result[year].setdefault('info', list())
            error = sum([value['error'] for value in data['info']])
            right = sum([value['right'] for value in data['info']])
            total = sum([value['total'] for value in data['info']])
            result[year]['info'].append({'date': date,
                                         'error': error,
                                         'right': right,
                                         'total': total,
                                         'error_ratio': error / total if total else 0})
            for dept in data['info']:
                if not dept['dept']:
                    continue
                if not re.sub('[A-Za-z0-9]*', '', dept['dept']):
                    continue
                temp[year].setdefault(dept['dept'], dict())
                temp[year][dept['dept']].setdefault('error', 0)
                temp[year][dept['dept']].setdefault('total', 0)
                temp[year][dept['dept']]['error'] += dept['error']
                temp[year][dept['dept']]['total'] += dept['total']
        for k in result:
            result[k]['error_ratio_median'] = sum(
                sorted([value['error_ratio'] for value in result[k]['info']])[5:7]) / 2
            result[k]['info'].sort(key=lambda x: x['date'])
            result[k]['error_ratio_average'] = sum([value['error_ratio'] for value in result[k]['info']]) / 12
        temp_ratio = dict()
        for k, v in temp.items():
            temp_ratio[k] = dict()
            for kk, vv in v.items():
                value = 0 if vv['total'] == 0 else vv['error'] / vv['total']
                temp_ratio[k][kk] = value
        for k, v in temp_ratio.items():
            """病历问题量排名"""
            sorted_list = sorted(v.items(), key=lambda x: x[1], reverse=True)
            first_five = dict(sorted_list[:5])
            last_five = dict(sorted_list[-5:])
            result[k]['dept_ratio_first_5'] = first_five
            result[k]['dept_ratio_last_5'] = last_five
        return result

    def oneYearRightAndError2(self, left_line='', right_line=''):
        # 病历问题科室分布图
        collection_name = self.collection_name + '_statistics'
        collection = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                             collection_name=collection_name)
        result = dict()
        query_result = collection.find({}, {'info': 1}).sort('_id', 1).batch_size(500)
        for data in query_result:
            date = data['_id']
            year = date[:4]
            result.setdefault(year, list())
            info = [value for value in data['info'] if value['dept'] and re.sub('[A-Za-z0-9]*', '', value['dept'])]
            result[year].append({'date': date,
                                 'info': info})
        for k, v in result.items():
            for vv in v:
                vv['info'].sort(key=lambda x: x['error_ratio'], reverse=True)
                vv['left_line'] = 0
                vv['right_line'] = 0
                l = len(vv['info'])
                if l < 3:
                    continue
                vv['left_line'] = vv['info'][l // 3 - 1]['error_ratio']
                vv['right_line'] = vv['info'][2 * l // 3 - 1]['error_ratio']
                if left_line and right_line:
                    vv['left_line'] = float(left_line)
                    vv['right_line'] = float(right_line)
                if vv['left_line'] == 0:
                    vv['left_line'] = 1
                if vv['right_line'] == 1:
                    vv['right_line'] = 0
                vv['left_dept'] = [value for value in vv['info'] if value['error_ratio'] >= vv['left_line']]
                vv['mid_dept'] = [value for value in vv['info'] if
                                  vv['left_line'] > value['error_ratio'] > vv['right_line']]
                vv['right_dept'] = [value for value in vv['info'] if vv['right_line'] >= value['error_ratio']]
        return result

    def oneYearRightAndError3(self):
        # 科室问题分类
        collection_name = self.collection_name + '_statistics'
        collection = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                             collection_name=collection_name)
        result = dict()
        res = dict()
        query_result = collection.find({}, {'dept_name': 1}).sort('_id', 1).batch_size(50)
        for data in query_result:
            date = data['_id']
            year = date[:4]
            result.setdefault(year, list())
            temp = dict()
            for regular_model in self.regular_model.values():
                if regular_model.get('status') == '启用':
                    temp.setdefault(regular_model.get('regular_classify'), 0)
            for v in data['dept_name'].values():  # v = {问题名称: num}
                for kk, vv in v.items():
                    temp.setdefault(kk, 0)
                    temp[kk] += vv
            result[year].append({'date': date,
                                 'info': temp,
                                 'dept': list(temp.keys())})
        for k, v in result.items():
            v.sort(key=lambda x: x['date'])
            res[k] = dict()
            res[k]['problem_num'] = list()
            dept_set = set()
            temp = dict()
            total_list = list()
            for vv in v:
                dept_set.update(vv['dept'])
                if vv['info']:
                    total_list.append(sum(vv['info'].values()))
                else:
                    total_list.append(0)
            for dept_name in dept_set:
                temp.setdefault(dept_name, list())
                for kk, vv in enumerate(v):
                    if dept_name in vv['info']:
                        temp[dept_name].append(vv['info'][dept_name])
                    else:
                        temp[dept_name].append(0)
            t = dict()
            for name, data in temp.items():
                data_ratio = list(map(lambda x: x[0] / x[1] if x[0] else 0, zip(data, total_list)))
                t.update({name: {'data': data, 'data_ratio': data_ratio}})
            x = sorted(t.items(), key=lambda x: sum(x[1]['data']), reverse=True)
            for i in x:
                res[k]['problem_num'].append({i[0]: i[1]})
            res[k]['total'] = total_list
        return res

    def deptRightAndError(self, dept_name='', start_date='', end_date='', collection_suffix='_statistics',
                          last_month=''):
        collection_name = self.collection_name + collection_suffix
        collection = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                             collection_name=collection_name)
        result = dict()
        temp = dict()
        query_field = dict()
        start = ''
        end = ''
        if last_month == '0':  # 本月
            start, end = self.this_month()
        elif last_month == '1':  # 上月
            start, end = self.last_month()
        elif last_month == '2':  # 上上月
            start, end = self.last_two_month()
        if start_date and end_date:
            if start and start_date < start:
                start_date = start
            if end and end_date > end:
                end_date = end
            query_field["_id"] = {'$gte': start_date, '$lt': end_date}  # 不包括end_date的日期
        else:
            if start and end:
                start_date = start
                end_date = end
                query_field["_id"] = {'$gte': start_date, '$lt': end_date}
        if dept_name:
            show_keys = 'dept_name.' + dept_name
            show_field = {show_keys: 1}
            query_field[show_keys] = {'$exists': True}
        else:
            show_field = {'dept_name': 1}
        query_result = collection.find(query_field, show_field).batch_size(50)
        for data in query_result:
            for k_dept_name, v_problem_info in data['dept_name'].items():
                temp.setdefault(k_dept_name, dict())
                for problem_name, problem_num in v_problem_info.items():
                    temp[k_dept_name].setdefault(problem_name, 0)
                    temp[k_dept_name][problem_name] += problem_num
        for k, v in temp.items():
            if not re.sub('[A-Za-z0-9]*', '', k):
                continue
            result.setdefault(k, dict())
            info = sorted(v.items(), key=lambda x: x[1], reverse=True)
            result[k]['problem_name'] = list()
            result[k]['num'] = list()
            for i in info:
                result[k]['problem_name'].append(i[0])
                result[k]['num'].append(i[1])
            result[k]['problem_sum'] = sum(result[k]['num'])
        result_sort = dict(sorted(result.items(), key=lambda x: x[1]['problem_sum'], reverse=True))
        return result_sort

    def regularManage(self, sheet_name='', regular_name='', status='', dept='', record='', modified_code='',
                      modified_dept='', modified_score='', modified_status=''):
        """
        规则管理页面
        :param sheet_name: 医生端/环节/终末
        :param regular_name: 规则名称筛选
        :param status: 启用状态
        :param dept: 科室筛选，通用只匹配通用
        :param record: 文书筛选
        :param modified_code: 修改的规则码
        :param modified_dept: 修改后的科室
        :param modified_score: 修改后的质控分数
        :param modified_status: 修改后的启用状态
        """
        if regular_name == '全部':
            regular_name = ''
        if status == '全部':
            status = ''
        if record == '全部':
            record = ''
        if not dept:
            dept = '通用'
        if not sheet_name:
            sheet_name = '医生端'
        name_switch = {
            '医生端': 'regular_model_yishengduan',
            '环节': 'regular_model_huanjie',
            '终末': 'regular_model_zhongmo'
        }
        if modified_code and name_switch.get(sheet_name):
            conn = self.mongo_push_utils.connectCollection(database_name=self.database_name,
                                                           collection_name=name_switch.get(sheet_name))
            mongo_result = conn.find_one({'_id': modified_code}) or dict()
            if mongo_result:
                if modified_dept and mongo_result.get('dept'):
                    mongo_result['dept'] = modified_dept
                    mongo_result['modify_date'] = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
                    self.logger_back.info(
                        '[dept] of [{0}] has been modified to [{1}]'.format(modified_code, modified_dept))
                if modified_score and mongo_result.get('score'):
                    if isinstance(modified_code, str):
                        try:
                            score = float(modified_score)
                            mongo_result['score'] = score
                            mongo_result['modify_date'] = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
                            self.logger_back.info(
                                '[score] of [{0}] has been modified to [{1}]'.format(modified_code, modified_score))
                        except:
                            self.logger_back.info(
                                '[score] of [{0}] failed to modified to [{1}]'.format(modified_code, modified_score))
                    else:
                        mongo_result['score'] = modified_score
                        mongo_result['modify_date'] = datetime.strftime(datetime.now(), '%Y-%m-%d')
                if modified_status and mongo_result.get('status'):
                    mongo_result['status'] = modified_status
                    mongo_result['modify_date'] = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
                    self.logger_back.info(
                        '[status] of [{0}] has been modified to [{1}]'.format(modified_code, modified_status))
            self.mongo_push_utils.pushData(name_switch.get(sheet_name), mongo_result)
        result = self.showRegular(sheet_name, regular_name, status, dept, record)
        return result

    def showRegular(self, sheet_name='', regular_name='', status='', dept='', record=''):
        result = dict()
        result['info'] = list()
        dept_list = self.dept_list
        if record == '全部':
            record = ''
        if regular_name == '全部':
            regular_name = ''
        record_list = ['全部']
        # regular_name_list = ['全部']
        for regular_code, regular_info in self.parameters.regular_model.get(sheet_name, dict()).items():
            # if regular_info.get('regular_classify', '') and regular_info.get('regular_classify', '') not in regular_name_list:
            #     regular_name_list.append(regular_info.get('regular_classify'))
            if regular_info.get('record_name', '') and regular_info.get('record_name', '') not in record_list:
                record_list.append(regular_info.get('record_name'))
            if regular_name and regular_info.get('regular_classify', '') != regular_name:
                continue
            regular_dept = list()
            if dept:
                value = regular_info.get('dept', dict())
                if ('$in' in value and (dept not in value['$in'])) or ('$nin' in value and (dept in value['$nin'])) or (
                        dept == '通用' and value != {'$nin': []}):
                    continue
                if '$in' in value:
                    regular_dept = value['$in']
                if '$nin' in value:
                    if value['$nin']:
                        regular_dept = list(set(dept_list).difference(set(value['$nin'])))
                    else:
                        if dept != '通用':
                            continue
                        regular_dept = ['通用']
            if status and regular_info.get('status', '') != status:
                continue
            if record and regular_info.get('record_name', '') != record:
                continue
            one_regular = dict()
            one_regular['regular_code'] = regular_code
            one_regular['regular_dept'] = regular_dept
            one_regular['regular_name'] = regular_info.get('regular_classify', '')
            one_regular['regular_details'] = regular_info.get('regular_details', '')
            one_regular['regular_path'] = regular_info.get('record_name', '')
            one_regular['regular_point'] = regular_info.get('score', '')
            one_regular['regular_status'] = regular_info.get('status', '')
            one_regular['classification_flag'] = regular_info.get('classification_flag', '')
            result['info'].append(one_regular)
        dept_list.insert(0, '医务处')  # 添加医务处科室
        dept_list.insert(0, '通用')
        result['dept_list'] = dept_list
        result['record_list'] = record_list
        # result['regular_name_list'] = regular_name_list
        result['status_list'] = ['全部', '启用', '未启用']
        return result

    def graphPageHeader(self):
        """
        图表页页眉
        """
        collection_name = self.collection_name + '_statistics'
        collection = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                             collection_name=collection_name)
        time_range = self.conf_dict['time_limits']['binganshouye.pat_visit.discharge_time'].copy()
        query_result = collection.find({'_id': time_range}, {'info': 1})
        sample_num = 0
        for data in query_result:
            sample_num += sum([value['total'] for value in data['info']])
        regular_num = len([value for value in self.regular_model.values() if value.get('status') == '启用'])
        monitor_date = datetime.strftime(datetime.now(), '%Y-%m-%d')
        result = dict()
        result['sample_num'] = sample_num
        result['regular_num'] = regular_num
        result['monitor_date'] = monitor_date
        return result

    def fileDownload(self, status_bool='all', dept_name='all', patient_id='', regular_details='', code='', record='',
                     start_date='', end_date='', category='', isResult=False, last_month='0'):
        """
        last_month: 0：终末，本月；1：终末，上月；2：终末，上上月，3：既往
        """
        if not os.path.exists('./excel'):
            os.mkdir('./excel')
        else:
            for i in os.listdir('./excel'):
                os.remove('./excel/' + i)
        file_name = './excel/' + datetime.now().strftime("%Y%m%d%H%M%S") + '.xls'

        result_list = self.findPatientByStatus(status_bool, dept_name, 0, 0, patient_id, regular_details, code, record,
                                               start_date, end_date, category, isResult, last_month)
        data = result_list.get('info', list())
        workbook = xlwt.Workbook(encoding='utf-8')
        style = xlwt.XFStyle()  # 创建一个样式对象，初始化样式
        al = xlwt.Alignment()
        al.horz = xlwt.Alignment.HORZ_LEFT  # 设置水平左端对齐
        al.vert = xlwt.Alignment.VERT_CENTER  # 设置垂直居中
        style.alignment = al
        sheet_name = 'sheet1'
        worksheet = workbook.add_sheet(sheet_name, cell_overwrite_ok=True)
        worksheet.write(0, 0, '序号')
        worksheet.write(0, 1, '患者ID')
        worksheet.write(0, 2, '就诊次')
        worksheet.write(0, 3, '出院日期')
        worksheet.write(0, 4, '出院科室')
        worksheet.write(0, 5, '住院医生')
        worksheet.write(0, 6, '主治医生')
        worksheet.write(0, 7, '副主任/主任')
        worksheet.write(0, 8, '总得分')
        worksheet.write(0, 9, '扣分')
        worksheet.write(0, 10, '问题分类')
        worksheet.write(0, 11, '问题详情')
        line = 1
        for patient_num, value in enumerate(data, 1):
            start_line = line
            value_list = value['pat_value'].copy()
            for content in value.get('content', list()):
                value_list.append({'score': float(content.get('score', '0')), 'name': '人工: ' + content.get('reg', ''),
                                   'reason': '人工: ' + content.get('selectedText', '')})
            for pat_value in value_list:
                if worksheet.name != 'sheet' + str(line // 65535 + 1):
                    worksheet.merge(start_line, line - 1, 0, 0)
                    worksheet.merge(start_line, line - 1, 1, 1)
                    worksheet.merge(start_line, line - 1, 2, 2)
                    worksheet.merge(start_line, line - 1, 3, 3)
                    worksheet.merge(start_line, line - 1, 4, 4)
                    worksheet.merge(start_line, line - 1, 5, 5)
                    worksheet.merge(start_line, line - 1, 6, 6)
                    worksheet.merge(start_line, line - 1, 7, 7)
                    worksheet.merge(start_line, line - 1, 8, 8)
                    start_line = 1
                    sheet_name = 'sheet' + str(line // 65535 + 1)
                    worksheet = workbook.add_sheet(sheet_name, cell_overwrite_ok=True)
                    worksheet.write(0, 0, '序号')
                    worksheet.write(0, 1, '患者ID')
                    worksheet.write(0, 2, '就诊次')
                    worksheet.write(0, 3, '出院日期')
                    worksheet.write(0, 4, '出院科室')
                    worksheet.write(0, 5, '住院医生')
                    worksheet.write(0, 6, '主治医生')
                    worksheet.write(0, 7, '副主任/主任')
                    worksheet.write(0, 8, '总得分')
                    worksheet.write(0, 9, '扣分')
                    worksheet.write(0, 10, '问题分类')
                    worksheet.write(0, 11, '问题详情')
                    line += 1
                # line = line % 65535
                worksheet.write(line % 65535, 0, patient_num, style)
                worksheet.write(line % 65535, 1, value['pat_info'].get('patient_id', ''), style)
                worksheet.write(line % 65535, 2, value['pat_info'].get('visit_id', ''), style)
                worksheet.write(line % 65535, 3, value['pat_info'].get('discharge_time', '')[:10], style)
                worksheet.write(line % 65535, 4, value['pat_info'].get('dept_discharge_from_name', ''), style)
                worksheet.write(line % 65535, 5, value['pat_info'].get('inp_doctor_name', ''), style)
                worksheet.write(line % 65535, 6, value['pat_info'].get('attending_doctor_name', ''), style)
                worksheet.write(line % 65535, 7, value['pat_info'].get('senior_doctor_name', ''), style)
                worksheet.write(line % 65535, 8, 100 - float(value['pat_info'].get('machine_score', 0)) - float(
                    value['pat_info'].get('artificial_score', 0)), style)
                worksheet.write(line % 65535, 9, pat_value['score'], style)
                worksheet.write(line % 65535, 10, pat_value['name'], style)
                worksheet.write(line % 65535, 11, pat_value['reason'], style)
                line += 1
            worksheet.merge(start_line, line % 65535 - 1, 0, 0)
            worksheet.merge(start_line, line % 65535 - 1, 1, 1)
            worksheet.merge(start_line, line % 65535 - 1, 2, 2)
            worksheet.merge(start_line, line % 65535 - 1, 3, 3)
            worksheet.merge(start_line, line % 65535 - 1, 4, 4)
            worksheet.merge(start_line, line % 65535 - 1, 5, 5)
            worksheet.merge(start_line, line % 65535 - 1, 6, 6)
            worksheet.merge(start_line, line % 65535 - 1, 7, 7)
            worksheet.merge(start_line, line % 65535 - 1, 8, 8)
            if line % 1000 == 0:
                worksheet.flush_row_data()  # 减少内存占用
        workbook.save(file_name)
        return file_name

    def problemNameAndCode(self, regular_name='', record='', sheet_name='终末'):
        # 既往/终末质控页面 -- 筛选页面 -- 规则文书/问题分类
        result = dict()
        regular_excel = self.showRegular(sheet_name=sheet_name, record=record, regular_name=regular_name)
        code_list = set()
        for info in regular_excel['info']:
            if info.get('regular_status', '') != '启用':
                continue
            #     if record and record != '全部' and self.record_to_regular(record):
            #         if info['regular_name'] not in self.record_to_regular(record):
            #             continue
            if info['regular_details'].strip():
                result.setdefault(info['regular_name'], list())  # result = {规则名称：对应多种明细}
                result[info['regular_name']].append(info['regular_details'])
                code_list.add(info['regular_details'].strip())
        code_list = list(code_list)  # 启用的明细
        code_list.sort()
        code_list.insert(0, '全部')
        regular_list = list(result.keys())  # 规则名称
        regular_list.insert(0, '全部')
        record_list = ['全部']
        for k, v in self.parameters.regular_model.get(sheet_name, dict()).items():
            if v.get('record_name') and v.get('record_name') not in record_list:
                record_list.append(v.get('record_name'))
        # record_list = list(set(self.conf_dict['english_to_chinese'].values()))
        # record_list.insert(0, '全部')

        if regular_name and regular_name != '全部':
            return result[regular_name]
        elif regular_name == '全部':
            return code_list
        else:
            return {'regular_list': regular_list,
                    'code_list': code_list}

    def record_list(self, step='终末'):
        """
        启用了规则的文书
        """
        record_list = list()
        regular_model = self.parameters.regular_model[step]
        for regular_code, value in regular_model.items():  # 从 regular_model.xlsx 中读取文书名称及规则名称
            # 获取文书名称
            if value.get('status') != '启用':
                continue
            if not value.get('record_name'):
                continue
            name = value.get('record_name')
            if name in record_list:
                continue
            record_list.append(name)
        record_list.insert(0, '全部')
        return record_list

    def record_to_regular(self, record=''):
        """
        文书名称所包含的规则名称
        """
        if not record:
            return dict()
        result = dict()
        for regular_code, value in self.regular_model.items():  # 从 regular_model.xlsx 中读取文书名称及规则名称
            # 获取文书名称
            if not value.get('record_name'):
                continue
            record_name = value.get('record_name')
            # 文书名称作为 key 值
            result.setdefault(record_name, list())
            if not value.get('regular_classify'):
                continue
            regular_classify = value.get('regular_classify')
            result.setdefault(regular_classify, list())
            if regular_classify not in result[record_name]:
                result[record_name].append(regular_classify)
            if not value.get('regular_details'):
                continue
            regular_details = value.get('regular_details')
            if regular_details not in result[regular_classify]:
                result[regular_classify].append(regular_details)
            result[regular_details] = value.get('score', 0)
        return result.get(record, dict())

    def record_regular_detail_score(self, result_data=""):
        """
        文书名称所包含的规则名称
        :param result_data: 从视图函数传递过来的参数，是 record、regular、detail 之一
        :return: 规则名称查询结果
        """
        if not result_data:
            return dict()
        result = dict()
        for regular_code, value in self.regular_model.items():  # 从 regular_model.xlsx 中读取文书名称及规则名称
            # 获取文书名称
            if not value.get('record_name'):
                continue
            record_name = value.get('record_name')
            # 文书名称作为 key 值
            result.setdefault(record_name, list())
            if not value.get('regular_classify'):
                continue
            regular_classify = value.get('regular_classify')
            result.setdefault(regular_classify, list())
            if regular_classify not in result[record_name]:
                result[record_name].append(regular_classify)
            if not value.get('regular_details'):
                continue
            regular_details = value.get('regular_details')
            if regular_details not in result[regular_classify]:
                result[regular_classify].append(regular_details)
            result[regular_details] = value.get('score', 0)
        return result.get(result_data, dict())

    def regular_to_detail(self, regular=''):
        if regular:
            return self.record_to_regular(regular)
        else:
            return {}

    def detail_to_score(self, detail=''):
        if detail:
            return self.record_to_regular(detail)
        else:
            return {}

    def version(self):
        """
        获取当前系统的版本号
        :return:
        """
        result = dict()
        app_seg = RunSegmentWord()
        seg_ver = app_seg.version()
        if seg_ver.get('res_flag'):
            result['seg_ver'] = seg_ver.get('project_version')
        else:
            result['seg_ver'] = seg_ver
        result['mrq_ver'] = self.parameters.properties.get('version')
        return result

    def testClient(self, search_id, record_name):
        if '#' in search_id:
            _, patient_id, visit_id = search_id.split('#')
            binganshouye_result = self.app_es.getRecordQuickly(patient_id, visit_id, 'binganshouye')
            if not (binganshouye_result.get('res_flag') and binganshouye_result.get('binganshouye')):
                return binganshouye_result
            record = self.app_es.getRecordQuickly(patient_id, visit_id, record_name, is_src=True)
            if not (record.get('res_flag') and record.get(record_name)):
                return record
            result = dict()
            result['patient_id'] = patient_id
            result['visit_id'] = visit_id
            result['pageSource'] = '0'
            result['binganshouye'] = dict()
            result['binganshouye']['patient_id'] = patient_id
            result['binganshouye']['visit_id'] = visit_id
            binganshouye = binganshouye_result.get('binganshouye')
            result['binganshouye']['inp_no'] = binganshouye['pat_visit']['inp_no']
            result['binganshouye']['admission_time'] = binganshouye['pat_visit']['admission_time']
            result['binganshouye']['discharge_time'] = binganshouye['pat_visit']['discharge_time']
            result['binganshouye']['pat_info_sex_name'] = binganshouye['pat_info']['sex_name']
            result['binganshouye']['pat_info_age_value'] = binganshouye['pat_visit']['age_value']
            result['binganshouye']['pat_info_age_value_unit'] = binganshouye['pat_visit']['age_value_unit']
            result['binganshouye']['pat_info_marital_status_name'] = binganshouye['pat_visit']['marital_status_name']
            result['binganshouye']['pat_info_occupation_name'] = binganshouye['pat_visit']['occupation_name']
            result['binganshouye']['pat_info_pregnancy_status'] = binganshouye['pat_visit'].get('pregnancy_status')
            result['binganshouye']['pat_visit_dept_admission_to_name'] = binganshouye['pat_visit'][
                'dept_admission_to_name']
            result['binganshouye']['pat_visit_dept_admission_to_code'] = binganshouye['pat_visit'][
                'dept_admission_to_code']
            result['binganshouye']['district_admission_to_name'] = binganshouye['pat_visit'].get(
                'district_admission_to_name')
            result['binganshouye']['district_admission_to_code'] = binganshouye['pat_visit'].get(
                'district_admission_to_code')
            result['binganshouye']['drug_allergy_name'] = binganshouye['pat_visit'].get('drug_allergy_name')
            result['binganshouye']['senior_doctor_name'] = binganshouye['pat_visit']['senior_doctor_name']
            result['binganshouye']['attending_doctor_name'] = binganshouye['pat_visit']['attending_doctor_name']
            result['binganshouye']['inp_doctor_name'] = binganshouye['pat_visit']['inp_doctor_name']
            result['binganshouye']['rh_blood_name'] = binganshouye['pat_info']['rh_blood_name']
            result['binganshouye']['blood_type_name'] = binganshouye['pat_info']['blood_type_name']
            record_result = record.get(record_name, list())[0]
            result.setdefault('wenshuxinxi', dict())
            for k, v in record_result.items():
                if k == 'MR_CONTENT_HTML':
                    k = 'mr_content'
                result['wenshuxinxi'][k.lower()] = v
            result['res_flag'] = True
            return result
        else:
            return {'res_flag': False, 'info': 'id有误'}

    def zhongmoDept(self):
        """
        返回终末问题病历的科室
        :return:
        """
        conn = self.mongo_pull_utils.connection(self.collection_name + '_zhongmo')
        mongo_result = conn.find({}, {'pat_info.dept_discharge_from_name': 1})
        result = set()
        for data in mongo_result:
            if data.get('pat_info', dict()).get('dept_discharge_from_name'):
                result.add(data.get('pat_info', dict()).get('dept_discharge_from_name'))
        return list(result)

    def deptProblemPercentage(self):
        """
        问题病历数/病历总数
        问题病历数从_this_month, _last_month, _last_two_month取
        病历总数每日定时从binganshouye获取
        total_zhongmo_this_month: 本月病历总数
        total_zhongmo_last_month: 上月病历总数
        total_zhongmo_last_two_month: 上上月病历总数
        """
        # 本月各科室问题病历数
        conn = self.mongo_pull_utils.connection(self.collection_name + '_this_month')
        this_month_total = dict()
        this_month_num = dict()
        mongo_result = conn.find({}, {'pat_info.dept_discharge_from_name': 1, 'pat_value.code': 1})
        for data in mongo_result:
            if data.get('pat_info', dict()).get('dept_discharge_from_name'):
                dept = data['pat_info']['dept_discharge_from_name']
                this_month_total.setdefault(dept, 0)
                this_month_total[dept] += 1
                if data.get('pat_value', list()):
                    this_month_num.setdefault(dept, 0)
                    this_month_num[dept] += 1
        print(this_month_total)
        print(this_month_num)
        # 上月各科室问题病历数
        conn = self.mongo_pull_utils.connection(self.collection_name + '_last_month')
        last_month_total = dict()
        last_month_num = dict()
        mongo_result = conn.find({}, {'pat_info.dept_discharge_from_name': 1, 'pat_value.code': 1})
        for data in mongo_result:
            if data.get('pat_info', dict()).get('dept_discharge_from_name'):
                dept = data['pat_info']['dept_discharge_from_name']
                last_month_total.setdefault(dept, 0)
                last_month_total[dept] += 1
                if data.get('pat_value', list()):
                    last_month_num.setdefault(dept, 0)
                    last_month_num[dept] += 1
        # 上上月各科室问题病历数
        conn = self.mongo_pull_utils.connection(self.collection_name + '_last_two_month')
        last_two_month_total = dict()
        last_two_month_num = dict()
        mongo_result = conn.find({}, {'pat_info.dept_discharge_from_name': 1, 'pat_value.code': 1})
        for data in mongo_result:
            if data.get('pat_info', dict()).get('dept_discharge_from_name'):
                dept = data['pat_info']['dept_discharge_from_name']
                last_two_month_total.setdefault(dept, 0)
                last_two_month_total[dept] += 1
                if data.get('pat_value', list()):
                    last_two_month_num.setdefault(dept, 0)
                    last_two_month_num[dept] += 1
        # # 本月病历总数
        # conn = self.mongo_pull_utils.connection('total_zhongmo_this_month')
        # this_month_total = dict()
        # mongo_result = conn.find()
        # for data in mongo_result:
        #     if data.get('dept'):
        #         dept = data['dept']
        #         this_month_total.setdefault(dept, 0)
        #         this_month_total[dept] += 1
        # # 上月病历总数
        # conn = self.mongo_pull_utils.connection('total_zhongmo_last_month')
        # last_month_total = dict()
        # mongo_result = conn.find()
        # for data in mongo_result:
        #     if data.get('dept'):
        #         dept = data['dept']
        #         last_month_total.setdefault(dept, 0)
        #         last_month_total[dept] += 1
        # # 上上月病历总数
        # conn = self.mongo_pull_utils.connection('total_zhongmo_last_two_month')
        # last_two_month_total = dict()
        # mongo_result = conn.find()
        # for data in mongo_result:
        #     if data.get('dept'):
        #         dept = data['dept']
        #         last_two_month_total.setdefault(dept, 0)
        #         last_two_month_total[dept] += 1
        result = dict()
        tmp = sorted(this_month_num.items(), key=lambda x: x[1], reverse=True)
        dept_list = [value[0] for value in tmp]
        result['graph_data'] = list()
        this_month_percentage = dict()
        last_month_percentage = dict()
        for dept in dept_list:
            result['graph_data'].append({
                'dept': dept,
                'by': this_month_num.get(dept, 0) / this_month_total.get(dept, float('inf')),
                'sy': last_month_num.get(dept, 0) / last_month_total.get(dept, float('inf')),
                'ssy': last_two_month_num.get(dept, 0) / last_two_month_total.get(dept, float('inf')),
                'by_num': this_month_num.get(dept, 0),
                'sy_num': last_month_num.get(dept, 0),
                'ssy_num': last_two_month_num.get(dept, 0),
            })
            this_month_percentage[dept] = this_month_num.get(dept, 0) / this_month_total.get(dept, float('inf'))
            last_month_percentage[dept] = last_month_num.get(dept, 0) / last_month_total.get(dept, float('inf'))
        tmp = dict()
        for dept, percentage in this_month_percentage.items():
            tmp[dept] = percentage - last_month_percentage[dept]
        tmp_list = sorted(tmp.items(), key=lambda x: x[1], reverse=True)
        result['decrease'] = [value[0] for value in tmp_list if value[1] > 0][:5]
        result['increase'] = [value[0] for value in tmp_list if value[1] < 0][::-1][:5]
        return result

    def deptProblemClassify(self, dept):
        # 科室问题分类栏
        result = dict()
        month_list = ['this_month', 'last_month', 'last_two_month']
        temp = dict()
        for month_name in month_list:
            total = 0
            this_month = dict()
            temp[month_name] = list()
            conn = self.mongo_pull_utils.connection(self.collection_name + '_' + month_name)
            pipeline = [{'$match': {'pat_value.code': {'$exists': True}, 'pat_info.dept_discharge_from_name': dept}},
                        {'$unwind': '$pat_value'},
                        {'$group': {'_id': '$pat_value.name', 'value': {'$sum': 1}}}]
            mongo_result = conn.aggregate(pipeline, allowDiskUse=True)
            for data in mongo_result:
                name = data.get('_id')
                this_month[name] = data.get('value', 0)
                total += data.get('value', 0)
            tmp = sorted(this_month.items(), key=lambda x: x[1], reverse=True)
            for data in tmp:
                temp[month_name].append(
                    {'name': data[0], 'num': data[1], 'percentage': data[1] / (total or float('inf'))})
        result['name'] = list()
        result['this_month'] = list()
        for value in temp['this_month']:
            if value.get('name'):
                result['name'].append(value.get('name'))
                result['this_month'].append({'num': value.get('num', 0), 'percentage': value.get('percentage', 0)})
        for month_name in month_list[1:]:
            result.setdefault(month_name, [{'num': 0, 'percentage': 0}] * len(result['name']))
            for value in temp[month_name]:
                if value.get('name'):
                    if value.get('name') in result['name']:
                        index = result['name'].index(value.get('name'))
                        result[month_name][index] = {'num': value.get('num', 0),
                                                     'percentage': value.get('percentage', 0)}
                    else:
                        result['name'].append(value.get('name'))
                        result[month_name].append(
                            {'num': value.get('num', 0), 'percentage': value.get('percentage', 0)})
                        result['this_month'].append({'num': 0, 'percentage': 0})
                        if month_name == 'last_two_month':
                            result['last_month'].append({'num': 0, 'percentage': 0})
        return result

    def doctorProblemNum(self, dept):
        # 医生问题分类栏
        result = dict()
        result['senior_doctor_name'] = dict()
        result['attending_doctor_name'] = dict()
        result['inp_doctor_name'] = dict()
        month_list = ['this_month', 'last_month', 'last_two_month']
        for month_name in month_list:
            conn = self.mongo_pull_utils.connection(self.collection_name + '_' + month_name)
            if dept:
                mongo_result = conn.find({'pat_value.code': {'$exists': True},
                                          'pat_info.dept_discharge_from_name': dept},
                                         {'pat_info.attending_doctor_name': 1,
                                          'pat_info.inp_doctor_name': 1,
                                          'pat_info.senior_doctor_name': 1})
            else:
                mongo_result = conn.find({'pat_value.code': {'$exists': True}},
                                         {'pat_info.attending_doctor_name': 1,
                                          'pat_info.inp_doctor_name': 1,
                                          'pat_info.senior_doctor_name': 1})
            for data in mongo_result:
                if not data.get('pat_info', dict()).get('attending_doctor_name'):  # 主治医师
                    continue
                if not data.get('pat_info', dict()).get('inp_doctor_name'):  # 住院医师
                    continue
                if not data.get('pat_info', dict()).get('senior_doctor_name'):  # 主任医师
                    continue
                result['senior_doctor_name'].setdefault(data['pat_info']['senior_doctor_name'], dict())
                result['attending_doctor_name'].setdefault(data['pat_info']['attending_doctor_name'], dict())
                result['inp_doctor_name'].setdefault(data['pat_info']['inp_doctor_name'], dict())
                result['senior_doctor_name'][data['pat_info']['senior_doctor_name']].setdefault('this_month', 0)
                result['senior_doctor_name'][data['pat_info']['senior_doctor_name']].setdefault('last_month', 0)
                result['senior_doctor_name'][data['pat_info']['senior_doctor_name']].setdefault('last_two_month', 0)
                result['senior_doctor_name'][data['pat_info']['senior_doctor_name']].setdefault('children', list())
                result['attending_doctor_name'][data['pat_info']['attending_doctor_name']].setdefault('this_month', 0)
                result['attending_doctor_name'][data['pat_info']['attending_doctor_name']].setdefault('last_month', 0)
                result['attending_doctor_name'][data['pat_info']['attending_doctor_name']].setdefault('last_two_month',
                                                                                                      0)
                result['attending_doctor_name'][data['pat_info']['attending_doctor_name']].setdefault('children',
                                                                                                      list())
                result['inp_doctor_name'][data['pat_info']['inp_doctor_name']].setdefault('this_month', 0)
                result['inp_doctor_name'][data['pat_info']['inp_doctor_name']].setdefault('last_month', 0)
                result['inp_doctor_name'][data['pat_info']['inp_doctor_name']].setdefault('last_two_month', 0)
                result['senior_doctor_name'][data['pat_info']['senior_doctor_name']][month_name] += 1
                result['attending_doctor_name'][data['pat_info']['attending_doctor_name']][month_name] += 1
                result['inp_doctor_name'][data['pat_info']['inp_doctor_name']][month_name] += 1

                result['inp_doctor_name'][data['pat_info']['inp_doctor_name']].setdefault('back_to_previous', list())
                if data.get('pat_info', dict()).get('senior_doctor_name') not in \
                        result['inp_doctor_name'][data['pat_info']['inp_doctor_name']]['back_to_previous']:
                    result['inp_doctor_name'][data['pat_info']['inp_doctor_name']]['back_to_previous'].append(
                        data.get('pat_info', dict()).get('senior_doctor_name'))
                result['attending_doctor_name'][data['pat_info']['attending_doctor_name']].setdefault(
                    'back_to_previous', ['senior_doctor_name'])
                result['senior_doctor_name'][data['pat_info']['senior_doctor_name']].setdefault('back_to_previous', [])

                result['attending_doctor_name'][data['pat_info']['attending_doctor_name']].setdefault('parent',
                                                                                                      data.get(
                                                                                                          'pat_info',
                                                                                                          dict()).get(
                                                                                                          'senior_doctor_name'))
                result['inp_doctor_name'][data['pat_info']['inp_doctor_name']].setdefault('parent', data.get('pat_info',
                                                                                                             dict()).get(
                    'attending_doctor_name'))

                if data.get('pat_info', dict()).get('attending_doctor_name') not in \
                        result['senior_doctor_name'][data['pat_info']['senior_doctor_name']]['children']:
                    result['senior_doctor_name'][data['pat_info']['senior_doctor_name']]['children'].append(
                        data.get('pat_info', dict()).get('attending_doctor_name'))

                if data.get('pat_info', dict()).get('inp_doctor_name') not in \
                        result['attending_doctor_name'][data['pat_info']['attending_doctor_name']]['children']:
                    result['attending_doctor_name'][data['pat_info']['attending_doctor_name']]['children'].append(
                        data.get('pat_info', dict()).get('inp_doctor_name'))
        tmp = list()
        for inp_doctor_name, value in result['inp_doctor_name'].items():
            tmp.append((inp_doctor_name, value.get('this_month', 0) - value.get('last_month', 0)))  # 问题量本月减去上月
        tmp.sort(key=lambda x: x[1])
        result['increase'] = [value[0] for value in tmp if value[1] > 0][:5]
        result['decrease'] = [value[0] for value in tmp if value[1] < 0][::-1][:5]
        return result

    def zhongmoRecordName(self):
        conn = self.mongo_pull_utils.connection(self.collection_name + '_zhongmo')
        mongo_result = conn.find({'pat_value.code': {'$exists': True}}, {'pat_value.path': 1})
        result = set()
        for data in mongo_result:
            if data.get('pat_value', list()):
                for one_record in data['pat_value']:
                    regular_path = one_record.get('path')
                    if regular_path:
                        record_name = regular_path.split('--')[0]
                        result.add(record_name)
        result = list(result)
        result.insert(0, '全部')
        return result

    def zhongmoRegularName(self):
        conn = self.mongo_pull_utils.connection(self.collection_name + '_zhongmo')
        mongo_result = conn.find({'pat_value.code': {'$exists': True}}, {'pat_value.name': 1})
        result = set()
        for data in mongo_result:
            if data.get('pat_value', list()):
                for one_record in data['pat_value']:
                    name = one_record.get('name')
                    if name:
                        result.add(name)
        result = list(result)
        result.insert(0, '全部')
        return result

    def documentProblemClassify(self, record_name):
        # 病历问题分类统计 -- 终末监控页面
        result = dict()
        month_list = ['this_month', 'last_month', 'last_two_month']
        if record_name != '全部':
            match_field = {'$match': {'pat_value.code': {'$exists': True},
                                      'pat_value.path': {'$regex': record_name}}}
        else:
            match_field = {'$match': {'pat_value.code': {'$exists': True}}}
        for month_name in month_list:
            this_month = dict()
            result[month_name] = list()
            conn = self.mongo_pull_utils.connection(self.collection_name + '_' + month_name)
            pipeline = [{'$unwind': '$pat_value'},
                        match_field,
                        {'$group': {'_id': '$pat_value.name', 'value': {'$sum': 1}}}]
            mongo_result = conn.aggregate(pipeline, allowDiskUse=True)
            if month_name == 'this_month':
                for data in mongo_result:
                    name = data.get('_id')
                    this_month[name] = data.get('value', 0)
                result['name'] = list()
                result[month_name] = [0] * 5
                tmp = sorted(this_month.items(), key=lambda x: x[1], reverse=True)
                for n, data in enumerate(tmp[:5]):
                    result['name'].append(data[0])
                    result[month_name][n] = data[1]
            else:
                result[month_name] = [0] * 5
                for data in mongo_result:
                    name = data.get('_id')
                    if name not in result['name']:
                        continue
                    index = result['name'].index(name)
                    result[month_name][index] = data.get('value', 0)
        return result

    def zhongmoFileDownloadMingxi(self, start_date, end_date, dept, regular_name):
        # 从数据库中提取数据
        this_month = self.this_month()
        last_month = self.last_month()
        last_two_month = self.last_two_month()
        month_list = {'last_two_month': last_two_month, 'last_month': last_month, 'this_month': this_month}
        query_field = {'pat_value.code': {'$exists': True}}
        if dept and dept != '全部':
            query_field['pat_info.dept_discharge_from_name'] = dept
        if regular_name and regular_name != '全部':
            query_field['pat_value.name'] = regular_name
        input_info = list()
        for month_name, month_date in month_list.items():
            if start_date and (start_date > month_date[0]):
                continue
            if end_date and (end_date < month_date[0]):
                continue
            conn = self.mongo_pull_utils.connection(self.collection_name + '_' + month_name)
            mongo_result = conn.find(query_field)
            for data in mongo_result:
                tmp = dict()
                tmp['patient_id'] = data.get('pat_info', dict()).get('patient_id', '')
                tmp['visit_id'] = data.get('pat_info', dict()).get('visit_id', '')
                tmp['inp_no'] = data.get('pat_info', dict()).get('inp_no', '')
                tmp['discharge_time'] = data.get('pat_info', dict()).get('discharge_time', '')
                tmp['dept_discharge_from_name'] = data.get('pat_info', dict()).get('dept_discharge_from_name', '')
                tmp['senior_doctor_name'] = data.get('pat_info', dict()).get('senior_doctor_name', '')  # 主任
                tmp['attending_doctor_name'] = data.get('pat_info', dict()).get('attending_doctor_name', '')  # 主治
                tmp['inp_doctor_name'] = data.get('pat_info', dict()).get('inp_doctor_name', '')  # 住院
                tmp['zhongmo_doctor_name'] = data.get('zhongmo_doctor_name', '')
                tmp['machine_score'] = data.get('pat_info', dict()).get('machine_score', '')
                tmp['artificial_score'] = data.get('pat_info', dict()).get('artificial_score', '')
                for one_record in data.get('pat_value', list()):
                    if regular_name and regular_name != '全部' and one_record.get('name') != regular_name:
                        continue
                    tmp.setdefault('pat_value', list())
                    tmp['pat_value'].append(
                        {'details': one_record.get('regular_details', ''), 'name': one_record.get('name', '')})
                input_info.append(tmp)

        # 将数据库中提取的数据写入excel
        if not os.path.exists('./excel'):
            os.mkdir('./excel')
        else:
            for i in os.listdir('./excel'):
                os.remove('./excel/' + i)
        start_year, start_month = start_date.split('-')
        end_year, end_month = end_date.split('-')
        title = '{}年{}月~{}年{}月'.format(start_year, start_month, end_year, end_month)
        workbook = xlwt.Workbook(encoding='utf-8')
        sheet_name = 'sheet1'
        worksheet = workbook.add_sheet(sheet_name, cell_overwrite_ok=True)
        # 写标题
        title_font = xlwt.Font()  # 标题字体
        title_font.bold = True
        title_font.name = 'Times New Roman'
        title_font.height = 20 * 14
        title_al = xlwt.Alignment()  # 标题位置
        title_al.horz = xlwt.Alignment.HORZ_CENTER
        title_al.vert = xlwt.Alignment.VERT_CENTER
        title_style = xlwt.XFStyle()
        title_style.font = title_font
        title_style.alignment = title_al
        worksheet.row(0).height = 20 * 20
        worksheet.write_merge(0, 0, 0, 11, title, title_style)
        # 写抬头
        caption_font = xlwt.Font()  # 标题字体
        caption_font.bold = False
        caption_font.name = 'SimSun'
        caption_font.height = 20 * 11
        caption_al = xlwt.Alignment()  # 标题位置
        caption_al.horz = xlwt.Alignment.HORZ_CENTER
        caption_al.vert = xlwt.Alignment.VERT_CENTER
        caption_style = xlwt.XFStyle()
        caption_style.font = caption_font
        caption_style.alignment = caption_al
        worksheet.row(1).height = 20 * 18
        worksheet.write(1, 0, '患者ID', caption_style)
        worksheet.write(1, 1, '住院次', caption_style)
        worksheet.write(1, 2, '住院号', caption_style)
        worksheet.write(1, 3, '出院时间', caption_style)
        worksheet.write(1, 4, '出院科室', caption_style)
        worksheet.write(1, 5, '住院医生', caption_style)
        worksheet.write(1, 6, '主治医生', caption_style)
        worksheet.write(1, 7, '副主任/主任', caption_style)
        worksheet.write(1, 8, '质控医师', caption_style)
        worksheet.write(1, 9, '总扣分', caption_style)
        worksheet.write(1, 10, '问题详情', caption_style)
        worksheet.write(1, 11, '规则分类', caption_style)
        content_al = xlwt.Alignment()
        content_style = xlwt.XFStyle()
        content_al.horz = xlwt.Alignment.HORZ_LEFT
        content_al.vert = xlwt.Alignment.VERT_CENTER
        content_style.alignment = content_al
        content_style.font = caption_font
        line = 2
        for one_record in input_info:
            if not one_record.get('pat_value', list()):
                continue
            start_line = line
            end_line = line
            for one_value in one_record.get('pat_value', list()):
                worksheet.row(line).height = 20 * 18
                worksheet.write(line, 10, one_value.get('details', ''), content_style)
                worksheet.write(line, 11, one_value.get('name', ''), content_style)
                end_line = line
                line += 1
            worksheet.write_merge(start_line, end_line, 0, 0, one_record.get('patient_id', ''), caption_style)
            worksheet.write_merge(start_line, end_line, 1, 1, one_record.get('visit_id', ''), caption_style)
            worksheet.write_merge(start_line, end_line, 2, 2, one_record.get('inp_no', ''), caption_style)
            worksheet.write_merge(start_line, end_line, 3, 3, one_record.get('discharge_time', ''), caption_style)
            worksheet.write_merge(start_line, end_line, 4, 4, one_record.get('dept_discharge_from_name', ''),
                                  caption_style)
            worksheet.write_merge(start_line, end_line, 5, 5, one_record.get('senior_doctor_name', ''), caption_style)
            worksheet.write_merge(start_line, end_line, 6, 6, one_record.get('attending_doctor_name', ''),
                                  caption_style)
            worksheet.write_merge(start_line, end_line, 7, 7, one_record.get('inp_doctor_name', ''), caption_style)
            worksheet.write_merge(start_line, end_line, 8, 8, one_record.get('zhongmo_doctor_name', ''), caption_style)
            worksheet.write_merge(start_line, end_line, 9, 9, one_record.get('machine_score', ''), caption_style)
        file_name = './excel/' + datetime.now().strftime("%Y%m%d%H%M%S") + '.xls'
        workbook.save(file_name)
        return file_name

    def zhongmoFileDownloadHuizong(self, start_date, end_date, dept, regular_name):
        # 从数据库中提取数据
        this_month = self.this_month()
        last_month = self.last_month()
        last_two_month = self.last_two_month()
        month_list = {'last_two_month': last_two_month, 'last_month': last_month, 'this_month': this_month}
        query_field = {'pat_value.code': {'$exists': True}}
        match_field = {'$match': {'pat_value.code': {'$exists': True}}}
        if dept and dept != '全部':
            query_field['pat_info.dept_discharge_from_name'] = dept
            match_field['$match']['dept'] = dept
        if regular_name and regular_name != '全部':
            query_field['pat_value.name'] = regular_name
        total = dict()
        # total = {'科室名': {'total': 出院人数, 'document': 问题病历总份数, 'pat_value': {'详情1': '数量1', '详情2': '数量2'}}}
        for month_name, month_date in month_list.items():
            if start_date > month_date[0]:
                continue
            if end_date < month_date[0]:
                continue
            conn_count = self.mongo_pull_utils.connection('total_zhongmo_' + month_name)
            count_result = conn_count.aggregate([match_field, {'$group': {'_id': '$dept', 'value': {'$sum': 1}}}])
            # 出院人数
            for data in count_result:
                total.setdefault(data['_id'], dict())
                total[data['_id']].setdefault('total', 0)
                total[data['_id']]['total'] += data['value']

            conn = self.mongo_pull_utils.connection(self.collection_name + '_' + month_name)

            # 问题病历总份数
            num_result = conn.aggregate([{'$match': query_field}, {
                '$group': {'_id': '$pat_info.dept_discharge_from_name', 'value': {'$sum': 1}}}])
            for data in num_result:
                total.setdefault(data['_id'], dict())
                total[data['_id']].setdefault('document', 0)
                total[data['_id']]['document'] += data['value']
            mongo_result = conn.find(query_field, {'pat_info.dept_discharge_from_name': 1,
                                                   'pat_value.name': 1,
                                                   'pat_value.regular_details': 1})
            for data in mongo_result:
                dept_name = data.get('pat_info', dict()).get('dept_discharge_from_name')
                if not dept_name:
                    continue
                total.setdefault(dept_name, dict())
                total[dept_name].setdefault('pat_value', dict())
                for one_value in data.get('pat_value', list()):
                    if regular_name and regular_name != '全部' and one_value.get('name') != regular_name:
                        continue
                    if one_value.get('regular_details'):
                        total[dept_name]['pat_value'].setdefault(one_value.get('regular_details', ''), 0)
                        total[dept_name]['pat_value'][one_value.get('regular_details')] += 1

        # 将数据写入excel
        if not os.path.exists('./excel'):
            os.mkdir('./excel')
        else:
            for i in os.listdir('./excel'):
                os.remove('./excel/' + i)
        start_year, start_month = start_date.split('-')
        end_year, end_month = end_date.split('-')
        title = '{}年{}月~{}年{}月'.format(start_year, start_month, end_year, end_month)
        workbook = xlwt.Workbook(encoding='utf-8')
        sheet_name = 'sheet1'
        worksheet = workbook.add_sheet(sheet_name, cell_overwrite_ok=True)
        # 写标题
        title_style = xlwt.XFStyle()  # 标题风格
        title_font = xlwt.Font()  # 标题字体
        title_al = xlwt.Alignment()  # 标题位置
        title_font.bold = True
        title_font.name = 'Times New Roman'
        title_font.height = 20 * 14
        title_al.horz = xlwt.Alignment.HORZ_CENTER
        title_al.vert = xlwt.Alignment.VERT_CENTER
        title_style.font = title_font
        title_style.alignment = title_al
        worksheet.row(0).height = 20 * 20
        worksheet.write_merge(0, 0, 0, 4, title, title_style)
        # 写抬头
        caption_style = xlwt.XFStyle()  # 抬头风格
        caption_font = xlwt.Font()
        caption_al = xlwt.Alignment()
        caption_font.bold = False
        caption_font.name = 'SimSun'
        caption_font.height = 20 * 11
        caption_al.horz = xlwt.Alignment.HORZ_CENTER
        caption_al.vert = xlwt.Alignment.VERT_CENTER
        caption_style.font = caption_font
        caption_style.alignment = caption_al
        worksheet.row(1).height = 20 * 18
        worksheet.write(1, 0, '科室', caption_style)
        worksheet.write(1, 1, '出院人数', caption_style)
        worksheet.write(1, 2, '问题病历总份数', caption_style)
        worksheet.write(1, 3, '问题详情', caption_style)
        worksheet.write(1, 4, '问题份数', caption_style)
        content_style = xlwt.XFStyle()  # 内容风格
        content_al = xlwt.Alignment()
        content_al.horz = xlwt.Alignment.HORZ_LEFT
        content_al.vert = xlwt.Alignment.VERT_CENTER
        content_style.alignment = content_al
        content_style.font = caption_font
        line = 2
        for dept_name, value in total.items():
            if not value.get('pat_value', dict()):
                continue
            start_line = line
            end_line = line
            for details, num in value.get('pat_value', dict()).items():
                worksheet.row(line).height = 20 * 18
                worksheet.write(line, 3, details, content_style)
                worksheet.write(line, 4, num, caption_style)
                end_line = line
                line += 1
            worksheet.write_merge(start_line, end_line, 0, 0, dept_name, caption_style)
            worksheet.write_merge(start_line, end_line, 1, 1, value.get('total', ''), caption_style)
            worksheet.write_merge(start_line, end_line, 2, 2, value.get('document', ''), caption_style)
        file_name = './excel/' + datetime.now().strftime("%Y%m%d%H%M%S") + '.xls'
        workbook.save(file_name)
        return file_name


    def find_detail_data(self, inp_doctor_name, attending_doctor_name, senior_doctor_name):
        """
        终末监控页面，获取问题患者详情
        :param inp_doctor_name: 住院医师
        :param attending_doctor_name: 主治医师
        :param senior_doctor_name: 主任医师
        :return: 详情列表
        """
        conn = self.mongo_pull_utils.connection(self.collection_name + "_zhongmo")
        res = conn.find({}).batch_size(20)
        data_list = []
        for data in res:
            data_dict = {}
            if data.get("pat_info").get("inp_doctor_name") == inp_doctor_name:
                data_dict["_id"] = "#".join(data["_id"].split("#")[0:2])  # 患者ID#就诊次
                data_dict["person_name"] = data["pat_info"]["person_name"]  # 患者姓名
                data_dict["discharge_time"] = data["pat_info"]["discharge_time"]  # 出院时间
                data_dict["inp_doctor_name"] = inp_doctor_name  # 三级医师姓名（住院医师）
                data_dict["inp_doctor_name"] += "({}, {})".format(attending_doctor_name, senior_doctor_name)
                score_total = data["pat_info"]["machine_score"] + data["pat_info"]["artificial_score"]  # 总扣分
                grade = self.score_grade(score_total)  # 病历等级
                data_dict["grade"] = grade
                detail_list = []
                for pat_value in data["pat_value"]:
                    machine_dict = {}
                    machine_dict["score"] = pat_value.get("score", 0)
                    machine_dict["name"] = pat_value.get("name", "")
                    machine_dict["reason"] = pat_value.get("reason", "")
                    detail_list.append(machine_dict)
                for content in data["content"]:
                    content_dict = {}
                    content_dict["score"] = content.get("score", 0)
                    content_dict["name"] = "人工：" + content.get("reg", "")
                    content_dict["reason"] = content.get("text", "")
                    detail_list.append(content_dict)
                for del_value in data["content"]:
                    del_dict = {}
                    del_dict["score"] = del_value.get("score", 0)
                    del_dict["name"] = del_value.get("name", "")
                    del_dict["reason"] = del_value.get("reason", "")
                    if del_dict in detail_list:
                        detail_list.remove(del_dict)
                data_dict["detail"] = detail_list
                data_list.append(data_dict)
        return data_list

    @staticmethod
    def score_grade(score):
        """
        计算当前病历扣分情况下属于哪一级病历
        甲级： 大于90分
        乙级： 大于等于74分，小于等于90分
        丙级： 小于74分
        :param score: 当前病历扣分值
        :return: 当前病历的评分等级，分别为甲级、乙级、丙级
        """
        if 100 - score > 90:
            return "甲级"
        elif 100 - score < 74:
            return "丙级"
        else:
            return "乙级"

    def find_patient_by_status(self, page=""):
        """
        页眉栏的信息展示，包括监控样本数、甲级病历率、乙级病历率、丙级病历率
        病历率： 是当前级别病历总数与总病历数的比值
        :param page: 前端传递过来的参数，“zhongmo”表示监控的是终末页面，"jiwang"表示监控的是既往页面
        :return: dict{监控病例总数：%d，甲级病历率：%.2f，乙级病历率：%.2f，丙级病历率：%.2f}
        """
        medical_record_rate = {}

        if (not page) or page == "zhongmo":
            cursor = self.mongo_pull_utils.connection(self.collection_name + "_zhongmo")
        elif page == "jiwang":
            cursor = self.mongo_pull_utils.connection(self.collection_name)
        res_patient = cursor.find({}).batch_size(50)
        count = cursor.find({}).count()
        first = 0
        second = 0
        third = 0

        for data in res_patient:
            pat_value = data.get("pat_value", "")
            one = sum([score for score in [pat.get("score") for pat in pat_value]])
            content = data.get("content", "")
            two = sum([float(score) for score in [content.get("score") for content in content]])
            del_value = data.get("del_value", "")
            three = sum([score for score in [del_value.get("score") for del_value in del_value]])
            total = one + two - three
            if 100 - total >= 90:
                first += 1
            elif 74 < 100 - total < 90:
                second += 1
            else:
                third += 1
        medical_record_rate["record_total"] = count  # 监控病历总数
        medical_record_rate["class_A"] = first  # 甲级病历数
        medical_record_rate["class_B"] = second  # 乙级病历数
        medical_record_rate["class_C"] = third  # 丙级病历数
        medical_record_rate["ratio_class_A"] = "%.2f" % (first / count * 100)  # 甲级病历率
        medical_record_rate["ratio_class_B"] = "%.2f" % (second / count * 100)  # 乙级病历率
        medical_record_rate["ratio_class_C"] = "%.2f" % (third / count * 100)  # 丙级病历率
        return medical_record_rate

    def graph_page_header(self, page=""):
        """
        获取既往监控和终末监控页面页眉处的信息
        :param page: 值为 jiwang 或者 zhongmo，分别表示 既往 或者 终末，表示数据是既往监控页面发起的请求还是终末监控发起的请求
        :return:
        """
        if (not page) or page == "zhongmo":
            collection_name = self.collection_name + "_zhongmo"
        else:
            collection_name = self.collection_name + '_statistics'
        collection = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                             collection_name=collection_name)
        time_range = self.conf_dict['time_limits']['binganshouye.pat_visit.discharge_time'].copy()
        query_result = collection.find({'_id': time_range}, {'info': 1})
        sample_num = 0
        for data in query_result:
            sample_num += sum([value['total'] for value in data['info']])
        regular_num = len([value for value in self.regular_model.values() if value.get('status') == '启用'])
        monitor_date = datetime.strftime(datetime.now(), '%Y-%m-%d')
        result = dict()
        # result['sample_num'] = sample_num  # 监控样本数
        result['regular_num'] = regular_num  # 规则数
        result['monitor_date'] = monitor_date  # 监控日期
        result_count = self.count_dept(page=page)
        result["department_count"] = result_count  # 监控的科室总数
        medical_record_rate = self.find_patient_by_status(page=page)
        result.update(medical_record_rate)
        return result

    def count_dept(self, page=""):
        """
        统计监控的科室数量，page的值：“jiwang”表示 既往， "zhongmo"表示 终末
        :param page: jiwang 或者 zhongmo，表示是从既往或者终末页面发起的请求
        :return: 监控的科室数量
        """
        if (not page) or page == "zhongmo":
            collection_name = self.collection_name + "_zhongmo"
        else:
            collection_name = self.collection_name
        collection = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                             collection_name=collection_name)
        result = collection.aggregate(
            [
                {"$group": {
                    "_id": "$pat_info.dept_discharge_from_name",
                    "count": {"$sum": 1}
                }},
                {"$sort": {"count": -1}}
            ],
        )
        result_list = list(result)
        return len(result_list)

    def one_year_right_and_error(self):
        """
        既往监控页面病历问题量（百分比）以及 较去年病历问题量（上升/下降前五名科室名称）
        病历问题量需要统计既往质控数据库中所有数据。
        1、每年数据按月统计病历问题量，上一年的数据按月统计病历问题量
        2、每月数据计算出当月的病历问题量百分比，与上一年病历问题量的同比
        3、上升/下降前五名科室名称统计的是每一年的数据
        :return: 每年的数据统计结果
        """
        collection_name = self.collection_name + '_statistics'
        collection = self.mongo_pull_utils.connectCollection(database_name=self.database_name,
                                                             collection_name=collection_name)
        result = dict()
        query_result = collection.find().sort('_id', 1).batch_size(50)
        temp = dict()
        year_set = set()
        for data in query_result:
            date = data['_id']
            year = date[:4]
            year_set.add(int(year))
            result.setdefault(year, dict())
            temp.setdefault(year, dict())
            result[year].setdefault('info', list())
            error = sum([value['error'] for value in data['info']])
            right = sum([value['right'] for value in data['info']])
            total = sum([value['total'] for value in data['info']])
            result[year]['info'].append({'date': date,  # 日期，如2019-05
                                         'error': error,  # 当月问题病历数量
                                         'right': right,  # 当月没有问题病历数量
                                         'total': total,  # 当年病历总量
                                         'error_ratio': error/total if total else 0})  # 当月问题病历比率
            
            # 按年统计各科室病历问题量和病历总量
            for dept in data['info']:
                if not dept['dept']:
                    continue
                if not re.sub('[A-Za-z0-9]*', '', dept['dept']):
                    continue
                temp[year].setdefault(dept['dept'], dict())
                temp[year][dept['dept']].setdefault('error', 0)
                temp[year][dept['dept']].setdefault('total', 0)
                temp[year][dept['dept']]['error'] += dept['error']
                temp[year][dept['dept']]['total'] += dept['total']
        year_list = sorted(list(year_set))  # 将所有时间放如列表中并且从小到大排序
        result_handle = {}
        for year in year_list:
            # 按年组装响应数据格式
            dict_info = {}
            if year == year_list[0]:  # 首年数据与其他数据不同，单独处理
                info_list = self.hand_first_year(year, result)
                tmp_list, nurses_list, nurses_dict_year = self.count_temp(year, temp)
            else:
                info_list = self.handle_info(year, result)
                tmp_list = self.count_temp_this_year(year, temp)
            dict_info["info"] = info_list  # 详细情况列表，即病历问题量图表数据
            dict_info["dept_ratio_first_5"] = (sorted(tmp_list, key=lambda x: x["value"], reverse=True))[:5]  # 上升前五名
            dict_info["dept_ratio_last_5"] = (sorted(tmp_list, key=lambda x: x["value"], reverse=True))[-1:-6:-1]  # 下降前五名
            result_handle[str(year)] = dict_info  # 将一年的数据放到一个单独的字典中，然后每年的数据放到一个大字典中
        # print(result_handle)
        return result_handle

    def handle_info(self, year, d_source):
        """
        处理除开起始年的 info 里面的数据，将处理结果放如一个列表中返回
        :param year: 所处理的数据所在的年份，如 2019
        :param d_source: 统计好的每年的病历问题数据详情
        :return: 一年的病历问题量数据详情列表，分为12个月，每个月的数据为字典格式
        """
        detail_info = []
        last_year = year - 1  # 获取上一年的年份，如今年的年份为 2019 年，上一年为 2018 年
        dict_info = d_source.get(str(year)).get("info")  # 从统计结果中获取当年的 info 字段数据，是列表 [] 类型
        last_year_dict_info = d_source.get(str(last_year)).get("info")  # 从统计结果中获取上一年的 info 字段数据，是列表 [] 类型
        month_list = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]  # 事先构造一个全年月份的数组
        for month_num in month_list:
            month_ty = str(year) + "-" + month_num  # 构造当年的月份格式
            month_ly = str(last_year) + "-" + month_num  # 构造上一年的月份格式
            info_this_year_month = self.hand_this_month(month_ty, dict_info, month_ly, last_year_dict_info)
            detail_info.append(info_this_year_month)  # 将当月的数据添加到列表中
        return detail_info

    def hand_this_month(self, this_year_month, dict_info, last_year_month, info_last_year):
        """
        处理非第一年的 info 字段数据的详细过程
        :param this_year_month: 当年当月的月份数据
        :param dict_info: 当年当月的 info 字段的数据详情
        :param last_year_month: 去年当月的月份数据
        :param info_last_year: 去年当月的 info 字段里的详细数据
        :return: 组装好格式的 info 字段数据
        """
        info_detail = dict()
        info_detail["data_TY"] = "年".join(this_year_month.split("-")) + "月"  # 月份
        info_detail["error_TY"] = 0  # 今年当月问题病历数量
        info_detail["total_TY"] = 0  # 今年病历问题总量
        info_detail["error_LY"] = 0  # 去年当月问题病历数量
        info_detail["total_LY"] = 0  # 去年病历问题总量
        info_detail["error_ratio"] = 0  # 占比
        info_detail["year_on_year"] = 0  # 同比
        for detail_list_this_year in dict_info:  # detail_list 是 dict {} 类型
            if detail_list_this_year.get("date") != this_year_month:
                continue
            info_detail["error_TY"] += detail_list_this_year.get("error")
            info_detail["total_TY"] += detail_list_this_year.get("total")
            info_detail["error_ratio"] += detail_list_this_year.get("error_ratio")
        for detail_list_last_year in info_last_year:
            if detail_list_last_year.get("date") != last_year_month:
                continue
            info_detail["error_LY"] += detail_list_last_year.get("error", 0)
            info_detail["total_LY"] += detail_list_last_year.get("total", 0)
        if info_detail["total_LY"] <= 0:
            info_detail["year_on_year"] += info_detail["error_ratio"]
        else:
            info_detail["year_on_year"] += info_detail["error_ratio"] - (
                        info_detail["error_LY"] / info_detail["total_LY"])
        return info_detail

    def hand_first_year(self, year, d_source):
        """
        处理起始年的 info 字段数据的详细过程，起始年返回的的数据和其他数据不一样，单独处理。
        因为是起始年，没有同比数据，故同比项直接给了默认值 0
        起始年没有上一年，所以上一年的数据给了默认值 0，上升排名和下降排名用的是当年的排名
        :param year: 起始年的年份，如 2012
        :param d_source: 统计好的每年的病历问题数据详情
        :return: 起始年的病历问题量数据详情列表，分为12个月，每个月的数据为字典格式
        """
        detail_info = []
        dict_info = d_source.get(str(year)).get("info")
        month_list = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
        for month in month_list:
            info_detail = dict()
            month_str = str(year) + "-" + month
            info_detail["data_TY"] = str(year) + "年" + month + "月"
            info_detail["error_TY"] = 0  # 今年当月问题病历数量
            info_detail["total_TY"] = 0  # 今年病历问题总量
            info_detail["error_LY"] = 0  # 去年当月问题病历数量
            info_detail["total_LY"] = 0  # 去年病历问题总量
            info_detail["error_ratio"] = 0  # 占比
            info_detail["year_on_year"] = 0  # 同比
            for detail_list_this_year in dict_info:  # detail_list 是 dict {} 类型
                if detail_list_this_year.get("date") != month_str:
                    continue
                info_detail["error_TY"] += detail_list_this_year.get("error", 0)
                info_detail["total_TY"] += detail_list_this_year.get("total", 0)
                info_detail["error_LY"] = 0
                info_detail["total_LY"] = 0
                info_detail["error_ratio"] += detail_list_this_year.get("error_ratio", 0)
            detail_info.append(info_detail)
        return detail_info

    def count_temp_this_year(self, year, tmp):
        """
        处理除开第一年以外的年份里，各科室病历问题量排名
        因为要做 较上一年的病历问题量统计，所以需要引入上一年的病历问题统计结果
        :param year: 当年的年份，如 2019
        :param tmp: 各科室病历问题量统计结果
        :return: 非起始年的各科室病历问题量排名
        """
        last_year = year - 1
        nurses_year_list = []
        
        tmp_this_year, nurses_list_this_year, nurses_dict_this_year = self.count_temp(year, tmp)
        tmp_last_year, nurses_list_last_year, nurses_dict_last_year = self.count_temp(last_year, tmp)
        for nurses in nurses_list_this_year:
            nurses_dict = dict()
            if nurses in nurses_list_last_year:  # 如果该科在上一年就已经存在，则上升情况用当年的比率减去上一年的比率
                nurses_dict["name"] = nurses
                nurses_dict["value"] = nurses_dict_this_year.get(nurses) - nurses_dict_last_year.get(nurses)
            else:  # 如果该科室没有在上一年出现，或者是新设立的科室，则直接为当年的比率
                nurses_dict["name"] = nurses
                nurses_dict["value"] = nurses_dict_this_year.get(nurses)
            nurses_year_list.append(nurses_dict)  # 将结果添加到列表中，方便做排序
        return nurses_year_list

    def count_temp(self, year, tmp):
        """
        处理一年的各科室病历问题量上升排名和下降排名
        :param year: 当年的年份，如 2018
        :param tmp: 各科室病历问题量统计结果
        :return: 各科室病历问题量统计结果列表（做排序用），科室列表， 统计结果（做比较用）
        """
        tmp_list = tmp.get(str(year))
        result_list = []
        nurses_list = []
        nurses_dict_year = {}
        for nurses, detail in tmp_list.items():
            nurses_list.append(nurses)
            nurses_dict = dict()
            nurses_dict["name"] = nurses
            nurses_dict["value"] = detail.get("error") / detail.get("total") if detail.get("total") != 0 else 0
            nurses_dict_year[nurses] = nurses_dict["value"]  # 直接对字典排序，得到的是元祖，不方便做下一步统计
            result_list.append(nurses_dict)  # 将字典放入列表中，根据字典的值对列表排序，排序结果还是列表嵌套字典，方便下一步操作
        return result_list, nurses_list, nurses_dict_year


if __name__ == '__main__':
    app = StatisticPatientInfos()
    t1 = datetime.now()
    r = app.deptProblemPercentage()
    import json

    t = (datetime.now() - t1).total_seconds()
    print(json.dumps(r, ensure_ascii=False, indent=4))
    print('函数运行消耗 {0} 秒'.format(t))
