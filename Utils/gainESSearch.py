#!/usr/bin/env python3
# -*- coding:utf-8 -*

"""
@version: V1.0
@author:
@mail:
@file: gainESSearch.py
@time: 2019-02-20 14:32
@description: 
"""
import os
import sys
cur_path = os.path.abspath(os.path.dirname(__file__))
root_path = os.path.split(cur_path)[0]
sys.path.append(root_path)  # 项目路径添加到系统路径
import json
import time
import socket
import requests
import traceback
from datetime import datetime
from Utils.loadingConfigure import Properties
from Utils.LogUtils import LogUtils


class GainESSearch(object):

    IS_INIT = False

    def __init__(self):
        if not GainESSearch.IS_INIT:
            self.parameters = Properties()
            self.logger = LogUtils().getLogger('es_search')
            self.log_info = """hospital_code: [{0}], version: [{1}], serverip: [{2}], request_add: [{3}], request_data: [{4}],
            response_text: [{5}], response_code: [{6}], error_type: [{7}], error_content: [{8}], abnormal_info: [\n{9}], take_times: [{10:.2f}]s"""
            es_host = self.parameters.properties.get('es_host')
            es_port = self.parameters.properties.get('es_port')
            self.hospital_code = self.parameters.properties.get('hospital_code')
            self.ver = self.parameters.properties.get('version')
            if es_port == '0':
                es_add = "{}/search/bysy".format(es_host)
            else:
                es_add = "{}:{}".format(es_host, es_port)
            self.id_add = 'http://{}/med/advanced/allVariableJilian.json'.format(es_add)
            self.record_add = 'http://{}/med/quality/getWenshuData.json'.format(es_add)
            self.record_list_add = 'http://{}/med/advanced/query/patients.json'.format(es_add)
            GainESSearch.IS_INIT = True

    def __new__(cls, *args, **kwargs):
        """
        单例模式
        """
        if not hasattr(cls, 'instance'):
            cls.instance = super(GainESSearch, cls).__new__(cls)
        return cls.instance

    def _requestMethod(self, url, data, start_time, input_info):
        res = {'res_flag': False}
        r = requests.post(url, data=data, timeout=5)
        if r.status_code != 200:
            r = requests.post(url, data=data, timeout=5)
        try:
            result = r.json()
            time_cost = r.elapsed.total_seconds()
        except:
            HOST_NAME = socket.gethostname()
            HOST_IP = socket.gethostbyname(HOST_NAME)
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            abnormal_info = ''.join(traceback.format_tb(exc_traceback_obj))
            info = self.log_info.format(self.hospital_code, self.ver, HOST_IP, url, data, r.text, r.status_code,
                                        exc_type.__name__, exc_value, abnormal_info, time.time()-start_time)
            self.logger.error(info)
            res['error_source'] = 'es'
            res['input_data'] = input_info
            res['request_add'] = url
            res['response_status'] = r.status_code
            res['response_text'] = r.text
            res['error_type'] = exc_type.__name__
            res['error_info'] = '.'.join(exc_value.args)
            res['abnormal_info'] = ''.join(traceback.format_tb(exc_traceback_obj))
            return res
        res['res_flag'] = True
        res['response_time'] = time_cost
        res.update(result)
        return res

    def getId(self, expression):
        start_time = time.time()
        res = dict()
        res['result'] = set()
        res['res_flag'] = False
        data = {
            'expressions': expression,
            "page": "0",
            "size": "10",
            "result": [[{"exp": "等于", "field": "住院病案首页_就诊信息_就诊次数", "flag": "1", "unit": "", "values": []}]]
        }
        r = requests.post(self.id_add, data=json.dumps(data))
        if r.status_code == 200:
            result = json.loads(r.text)
            time_cost = r.elapsed.total_seconds()
        else:
            r = requests.post(self.id_add, data=json.dumps(data))
            try:
                result = json.loads(r.text)
                time_cost = r.elapsed.total_seconds()
            except:
                HOST_NAME = socket.gethostname()
                HOST_IP = socket.gethostbyname(HOST_NAME)
                exc_type, exc_value, exc_traceback_obj = sys.exc_info()
                abnormal_info = ''.join(traceback.format_tb(exc_traceback_obj))
                info = self.log_info.format(self.hospital_code, self.ver, HOST_IP, self.id_add, data, r.text, r.status_code,
                                            exc_type.__name__, exc_value, abnormal_info, time.time()-start_time)
                self.logger.error(info)
                res['error_source'] = 'es'
                res['expression'] = expression
                res['response_status'] = r.status_code
                res['response_text'] = r.text
                res['error_type'] = exc_type.__name__
                res['error_info'] = '.'.join(exc_value.args)
                res['abnormal_info'] = ''.join(traceback.format_tb(exc_traceback_obj))
                return res
        if 'result' in result:
            res['res_flag'] = True
            res['response_time'] = time_cost
            if isinstance(result.get('result'), list):
                for one_batch in result['result']:
                    keys = set(one_batch.keys())
                    res['result'].update(keys)
            if 'Count' in result:
                count = int(result['Count'])
                if count != len(res['result']):
                    res['count'] = len(res['result'])
                    self.logger.warning('\nCount: {}\nlength: {}'.format(count, len(res), ))
                else:
                    res['count'] = count
        else:
            res['error_info'] = 'No "result" in result...'

        if not res['res_flag']:
            res.update(result)
            res['error_source'] = 'es'
            res['expression'] = expression
            HOST_NAME = socket.gethostname()
            HOST_IP = socket.gethostbyname(HOST_NAME)
            info = self.log_info.format(self.hospital_code, self.ver, HOST_IP, self.record_add, data, r.text, r.status_code,
                                        'res_flag is False', res, 'getId', time.time()-start_time)
            self.logger.warning(info)
        return res

    def getRecord(self, record_id, record_name, is_src=False):
        start_time = time.time()
        res = dict()
        res['res_flag'] = False
        data = {
            'esId': record_id,
            'wenshuName': record_name,
            'isSrc': is_src
        }
        r = requests.post(self.record_add, data=data)
        if r.status_code == 200:
            result = json.loads(r.text)
            time_cost = r.elapsed.total_seconds()
        else:
            r = requests.post(self.record_add, data=data)
            try:
                result = json.loads(r.text)
                time_cost = r.elapsed.total_seconds()
            except:
                HOST_NAME = socket.gethostname()
                HOST_IP = socket.gethostbyname(HOST_NAME)
                exc_type, exc_value, exc_traceback_obj = sys.exc_info()
                abnormal_info = ''.join(traceback.format_tb(exc_traceback_obj))
                info = self.log_info.format(self.hospital_code, self.ver, HOST_IP, self.record_add, data, r.text, r.status_code,
                                            exc_type.__name__, exc_value, abnormal_info, time.time()-start_time)
                self.logger.error(info)
                res['error_source'] = 'es'
                res['record_id'] = record_id
                res['record_name'] = record_name
                res['response_status'] = r.status_code
                res['response_text'] = r.text
                res['error_type'] = exc_type.__name__
                res['error_info'] = '.'.join(exc_value.args)
                res['abnormal_info'] = ''.join(traceback.format_tb(exc_traceback_obj))
                return res
        if result.get(record_id):
            res = json.loads(result.get(record_id))
            res['res_flag'] = True
            res['response_time'] = time_cost
        if not res['res_flag']:
            res.update(result)
            res['error_source'] = 'es'
            res['record_id'] = record_id
            res['record_name'] = record_name
            HOST_NAME = socket.gethostname()
            HOST_IP = socket.gethostbyname(HOST_NAME)
            info = self.log_info.format(self.hospital_code, self.ver, HOST_IP, self.record_add, data, r.text, r.status_code,
                                        'res_flag is False', res, 'getRecord', time.time()-start_time)
            self.logger.warning(info)
        return res

    def getRecordQuickly(self, patient_id, visit_id, record_name, record_type='2', is_src=False):
        """
        快速获取文书，type: 1表示门诊，2表示住院
        """
        record_id = '{}##{}#{}#{}'.format(self.hospital_code, record_type, patient_id, visit_id)
        return self.getRecord(record_id, record_name, is_src)

    def getEsIdByDate(self, start_date='', end_date=''):
        """
        按患者出院起止时间, 获取患者es查询ID
        """
        result = dict()
        result['result'] = list()
        expression = list()
        if start_date and not end_date:
            # 有起始日期，没有结束日期
            expression = [[{"field": "住院病案首页_就诊信息_出院时间", "exp": ">=", "flag": "or", "unit": "", "values": [start_date]}]]
        if end_date and not start_date:
            expression = [[{"field": "住院病案首页_就诊信息_出院时间", "exp": "<", "flag": "or", "unit": "", "values": [end_date]}]]
        if start_date and end_date:
            expression = [[{"field": "住院病案首页_就诊信息_出院时间", "exp": ">=", "flag": "or", "unit": "", "values": [start_date]}],
                          [{"field": "住院病案首页_就诊信息_出院时间", "exp": "<", "flag": "or", "unit": "", "values": [end_date]}]]
        if not expression:
            return {'res_flag': False, 'info': 'No "start_date" or "end_date" in input para...'}
        es_result = self.getId(expression)
        if not es_result.get('res_flag'):
            return es_result
        result['res_flag'] = True
        result['result'] = list(es_result['result'])
        result['count'] = len(result['result'])
        return result

    def getPatientRecordList(self, patient_id, visit_id, record_type='2'):
        start_time = time.time()
        record_id = '{}##{}#{}#{}'.format(self.hospital_code, record_type, patient_id, visit_id)
        data = {
            'expressions': [[{"field": "fieldId", "exp": "=", "flag": "or", "unit": "", "values": [record_id]}]],
            "page": "0",
            "size": "10",
            "resultField": ["文档列表_文档名"]
        }
        para = json.dumps(data)
        result = self._requestMethod(url=self.record_list_add, data=para, start_time=start_time, input_info=para)
        if not result.get('total'):
            result['res_flag'] = False
            return result
        if isinstance(result.get('hits'), list) and len(result.get('hits')) > 0:
            tmp = result['hits'][0]
            if isinstance(tmp, list) and len(tmp) > 0:
                res_tmp = tmp[0]
                if isinstance(res_tmp, dict) and isinstance(res_tmp.get('文档列表_文档名'), str):
                    res_list = res_tmp.get('文档列表_文档名').split(',')
                    result['result'] = res_list
                    result.pop('hits')
                    return result
        result['res_flag'] = False
        return result


if __name__ == '__main__':
    app = GainESSearch()
    expression = [[{"field": "住院病案首页_就诊信息_患者标识", "exp": "=", "flag": "or", "unit": "", "values": ["000052934000"]}],
                  [{"field": "住院病案首页_就诊信息_就诊次数", "exp": "=", "flag": "or", "unit": "", "values": ["4"]}]]
    # expression = [[{"field": "住院病案首页_就诊信息_出院时间", "exp": ">", "flag": "or", "unit": "", "values": ["2016-01-01"]}]]
    t1 = datetime.now()
    # result = app.getId(expression)
    result = app.getPatientRecordList('000052934000', '4')
    # for i in result:
    #     app.getRecord(i, 'binganshouye')
    # result = app.getRecord('BJDXDSYY##2#000665705900#1', 'yizhu')
    t = (datetime.now()-t1).total_seconds()
    print(json.dumps(result, ensure_ascii=False, indent=4))
    print('函数运行消耗 {0} 秒'.format(t))
