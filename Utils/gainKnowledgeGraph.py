#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
@version: V1.0
@author:
@mail:
@file: gainKnowledgeGraph.py
@time: 2019-04-23 09:45
@description: 知识库查询
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


class GainKnowledgeGraph(object):

    IS_INIT = False

    def __init__(self):
        if not GainKnowledgeGraph.IS_INIT:
            self.parameters = Properties()
            self.logger = LogUtils().getLogger('es_search')
            self.log_info = """hospital_code: [{0}], version: [{1}], serverip: [{2}], request_add: [{3}], request_data: [{4}],
            response_text: [{5}], response_code: [{6}], error_type: [{7}], error_content: [{8}], abnormal_info: [\n{9}], take_times: [{10:.2f}]s"""
            knowledge_host = self.parameters.properties.get('knowledge_host')
            knowledge_port = self.parameters.properties.get('knowledge_port')
            self.hospital_code = self.parameters.properties.get('hospital_code')
            self.ver = self.parameters.properties.get('version')
            self.standard_add = 'http://{}:{}/med/cdss/standardFromAliasList.json'.format(knowledge_host, knowledge_port)
            self.relationship_add = 'http://{}:{}/med/cdss/isFatherOrSon.json'.format(knowledge_host, knowledge_port)
            self.medicine_add = 'http://{}:{}/med/edit/searchKnowledge.json'.format(knowledge_host, knowledge_port)
            GainKnowledgeGraph.IS_INIT = True

    def __new__(cls, *args, **kwargs):
        """
        单例模式
        """
        if not hasattr(cls, 'instance'):
            cls.instance = super(GainKnowledgeGraph, cls).__new__(cls)
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
            res['error_source'] = 'knowledge_graph'
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

    def getStandardName(self, *args):
        """
        获取标准名称
        """
        start_time = time.time()
        word_list = list(args)
        data = {'word': json.dumps(word_list)}
        result = self._requestMethod(url=self.standard_add, data=data, start_time=start_time, input_info=word_list)
        return result

    def getRelationship(self, word1, word2, word_type=''):
        """
        两个词是否具有上下有关系
        :param word1: 词1
        :param word2: 词2
        :param word_type: 词类型
        :return: "result" 为true 或者 false
        """
        start_time = time.time()
        result = dict()
        if not word_type:
            type_list = ['disease', 'medicine', 'lab', 'lab_sub', 'exam', 'operation', 'symptom_sign']
        else:
            type_list = [word_type]
        for i in type_list:
            data = {'onto1': word1, 'onto2': word2, 'type': i}
            result = self._requestMethod(url=self.relationship_add, data=data, start_time=start_time, input_info=data)
            if result.get('res_flag'):
                if result.get('result') is True:
                    return result
        result['res_flag'] = False
        return result

    def getMedicineCategory(self, medicine_name):
        """
        获取药品的分类
        :param medicine_name:
        :return:
        """
        start_time = time.time()
        data = {'wiki': {'$or': {'medicine_obj.name': medicine_name,
                                 'medicine_obj.alias': medicine_name}},
                'result': {'wiki': ['medicine_obj.category',
                                    'medicine_obj.name']}}
        data = json.dumps(data)
        result = self._requestMethod(url=self.medicine_add, data=data, start_time=start_time, input_info=medicine_name)
        if result.get('res_flag'):
            if result.get('msg') == 'success':
                result_list = list(result.get('result', dict()).get('hit', dict()).values())
                res_list = list()
                for i in result_list:
                    category_list = i.get('medicine_obj.category', list())
                    res_list.extend(category_list)
                res = dict()
                res['res_flag'] = True
                res['response_time'] = result.get('response_time', '')
                res['result'] = res_list
                return res
        result['res_flag'] = False
        return result

    def getTargetCategory(self, input_category, target_category, start_time=''):
        """
        输入类别是否是目标类别的子类
        :param input_category:
        :param target_category:
        :param start_time:
        :return:
        """
        if not start_time:
            start_time = time.time()
        for category in input_category:
            res = dict()
            res['res_flag'] = False
            data = {'wiki': {'medicine_category_obj.name': category},
                    'result': {'wiki': ['medicine_category_obj.attribution',
                                        'medicine_category_obj.name']}}
            data = json.dumps(data)
            result = self._requestMethod(url=self.medicine_add, data=data, start_time=start_time, input_info=category)
            if result.get('res_flag'):
                res_list = list()
                if result.get('msg') == 'success':
                    result_list = list(result.get('result', dict()).get('hit', dict()).values())
                    for i in result_list:
                        category_list = i.get('medicine_category_obj.attribution', list())
                        res_list.extend(category_list)
                        if set(category_list) & set(target_category):
                            res['res_flag'] = True
                            res['response_time'] = result.get('response_time', '')
                            return res
                if 'root' in res_list or not res_list:
                    return res
                return self.getTargetCategory(res_list, target_category, start_time)
        return {'res_flag': False}

    def getSameContent(self, key_content, value_content):
        """
        找出是否有同义词或具有上下级关系的词，但未找出所有相有关系的词
        :param key_content: 单个词 或者 由词组成的可迭代对象
        :param value_content: 单个词 或者 由词组成的可迭代对象
        """
        if isinstance(key_content, str):
            key_standard = self.getStandardName(key_content)
        else:
            key_content = set(key_content)
            key_standard = self.getStandardName(*key_content)
        if not key_standard.get('res_flag'):
            return {}

        if isinstance(value_content, str):
            value_standard = self.getStandardName(value_content)
        else:
            value_content = set(value_content)
            value_standard = self.getStandardName(*value_content)
        if not value_standard.get('res_flag'):
            return {}

        key_dict = dict([(k, v) for k, v in key_standard.items() if isinstance(v, str)])
        value_dict = dict([(k, v) for k, v in value_standard.items() if isinstance(v, str)])
        if not (key_dict and value_dict):
            return {}
        key_set = set(key_dict.values())
        value_set = set(value_dict.values())
        same_word = key_set & value_set
        synonym_dict = dict()
        result = dict()
        for i in same_word:
            synonym_dict[i] = i
        for key_k, key_v in key_dict.items():
            if key_k in result:
                continue
            for value_k, value_v in value_dict.items():
                if synonym_dict.get(key_v) == value_v:
                    result[key_k] = value_k
                    break
                relation_res = self.getRelationship(key_v, value_v)
                if relation_res.get('res_flag'):
                    result[key_k] = value_k
                    break
        return result

    def medicineIsTargetCategory(self, medicine, target_category):
        """
        药品是否属于目标类别
        """
        # 获取药物标准名
        if isinstance(medicine, str):
            medicine_standard = self.getStandardName(medicine)
        else:
            medicine = set(medicine)
            medicine_standard = self.getStandardName(*medicine)
        if not medicine_standard.get('res_flag'):
            return {}

        medicine_dict = dict([(k, v) for k, v in medicine_standard.items() if isinstance(v, str)])
        if not medicine_dict:
            return {}

        medicine_set = set(medicine_dict.values())
        input_category = set()
        for i in medicine_set:
            # 获取标准名药物的类别
            category_result = self.getMedicineCategory(i)
            if category_result.get('res_flag') is True:
                input_category.update(category_result.get('result', list()))
        return self.getTargetCategory(input_category, target_category)


if __name__ == '__main__':
    app = GainKnowledgeGraph()
    t1 = time.time()

    print('是否是父子关系, input: {}'.format("'冠状动脉粥样硬化性心脏病', '不稳定性心绞痛'"))
    r = app.getRelationship('冠状动脉粥样硬化性心脏病', '不稳定性心绞痛')
    print(json.dumps(r, ensure_ascii=False, indent=4))

    print('获取标准名, input: {}'.format('冠心病'))
    r = app.getStandardName('冠心病')
    print(json.dumps(r, ensure_ascii=False, indent=4))

    print('获取药物类别, input: {}'.format('精蛋白锌胰岛素注射液'))
    r = app.getMedicineCategory('精蛋白锌胰岛素注射液')
    print(json.dumps(r, ensure_ascii=False, indent=4))

    print('是否是子类别, input: {}'.format("['胰岛素类'], ['激素及影响内分泌药']"))
    r = app.getTargetCategory(['胰岛素类'], ['激素及影响内分泌药'])
    print(json.dumps(r, ensure_ascii=False, indent=4))

    print('药品是否属于目标类别, input: {}'.format("['精蛋白重组人胰岛素注射液'], ['抗高血压药', '胰岛素及影响血糖药']"))
    r = app.medicineIsTargetCategory(['精蛋白重组人胰岛素注射液'], ['抗高血压药', '胰岛素及影响血糖药'])
    print(json.dumps(r, ensure_ascii=False, indent=4))

    print('是否是同义词, input: {}'.format("['肩部背痛'], ['肩背部疼痛']"))
    r = app.getSameContent(['心界'], ['心界不大'])
    print(json.dumps(r, ensure_ascii=False, indent=4))

    print('函数运行消耗 {0} 秒'.format(time.time() - t1))
