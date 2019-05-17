#!/usr/bin/env python3
# -*- coding:utf-8 -*

"""
@version: V1.0
@author:
@mail:
@file: gainSynonym.py
@time: 2019-01-28 15:30
@description: 调用知识库同义词接口
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
from Utils.loadingConfigure import Properties
from Utils.LogUtils import LogUtils


class GainSynonym(object):

    is_init = False

    def __init__(self):
        if not GainSynonym.is_init:
            self.parameters = Properties()
            self.logger = LogUtils().getLogger('synonym')
            self.log_info = """hospital_code: [{0}], version: [{1}], serverip: [{2}], request_add: [{3}], request_data: [{4}],
            response_text: [{5}], response_code: [{6}], error_type: [{7}], error_content: [{8}], abnormal_info: [\n{9}], take_times: [{10:.2f}]s"""
            self.hospital_code = self.parameters.properties.get('hospital_code')
            self.ver = self.parameters.properties.get('version')
            self.synonym_host = self.parameters.properties.get('synonym_host')
            self.synonym_port = self.parameters.properties.get('synonym_port')
            GainSynonym.is_init = True

    def __new__(cls, *args, **kwargs):
        """
        单例模式
        """
        if not hasattr(cls, 'instance'):
            cls.instance = super(GainSynonym, cls).__new__(cls)
        return cls.instance

    def get_same_word(self, word):
        """
        获取同义词
        """
        start_time = time.time()
        res = dict()
        if not (self.synonym_host and self.synonym_port):
            res = {'res_flag': False, 'error_source': 'synonym', 'error_info': 'No synonym_host or synonym_port...'}
            return res
        data = {'word': word}
        add = 'http://{}:{}/med/cdss/sameWord.json'.format(self.synonym_host, self.synonym_port)
        r = requests.post(add, data=data)
        if r.status_code == 200:
            result = json.loads(r.text)
            time_cost = r.elapsed.total_seconds()
            res['res_flag'] = True
        else:
            r = requests.post(add, data=data)
            try:
                result = json.loads(r.text)
                time_cost = r.elapsed.total_seconds()
                res['res_flag'] = True
            except:
                HOST_NAME = socket.gethostname()
                HOST_IP = socket.gethostbyname(HOST_NAME)
                exc_type, exc_value, exc_traceback_obj = sys.exc_info()
                abnormal_info = ''.join(traceback.format_tb(exc_traceback_obj))
                info = self.log_info.format(self.hospital_code, self.ver, HOST_IP, add, data, r.text, r.status_code,
                                            exc_type.__name__, exc_value, abnormal_info, time.time()-start_time)
                self.logger.error(info)
                res['res_flag'] = False
                res['error_source'] = 'synonym'
                res['response_status'] = r.status_code
                res['response_text'] = r.text
                res['error_type'] = exc_type.__name__
                res['error_info'] = '.'.join(exc_value.args)
                res['abnormal_info'] = ''.join(traceback.format_tb(exc_traceback_obj))
                return res
        if res.get('res_flag'):
            res['response_time'] = time_cost
            res['result'] = list(set(result))
        return res

    def get_child_disease(self, word):
        """
        获取子疾病
        """
        result = list()
        if not (self.synonym_host and self.synonym_port):
            self.logger.error('No synonym_host or synonym_port...')
            return result
        data = {'word': word}
        add = 'http://{}:{}/med/cdss/getAllChildDisease.json'.format(self.synonym_host, self.synonym_port)
        r = requests.post(add, data=data)
        if r.status_code == 200:
            result = json.loads(r.text)
        else:
            r = requests.post(add, data=data)
            try:
                result = json.loads(r.text)
            except:
                info = '\nvalue: {}\nstatus_code: {}'.format(data, r.status_code)
                self.logger.error(info)
        return result.get(word, list())


if __name__ == '__main__':
    app = GainSynonym()
    r = app.get_child_disease('Patau综合征')
