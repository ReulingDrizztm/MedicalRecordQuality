# -*- coding:utf-8 -*
"""
@version: v1.0
@author: shangyafei
@contact: shangyafei@bjgoodwill.com
@software: PyCharm Community Edition
@File: loadingConfigure.py
@time: 16/05/17 下午 04:37
"""
import os
import sys
curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
import re
import threading
from pymongo import MongoClient
from XML2Dict.encoder import XML2Dict
# XML2Dict 是把 xml 格式的数据转化成 dict 格式的数据


class Properties(object):
    _INSTANCE_LOCK = threading.Lock()
    _IS_INIT = False

    def __new__(cls, *args, **kwargs):
        if not hasattr(Properties, '_instance'):
            with Properties._INSTANCE_LOCK:
                if not hasattr(Properties, '_instance'):
                    Properties._instance = object.__new__(cls)
        return Properties._instance

    def __init__(self):
        if not Properties._IS_INIT:

            # 读取 base.properties
            self.properties = self.getInfo('base.properties')

            # 读取 .xml
            self.conf_dict = self.__loadconf()

            self.regular_model = dict()
            self.dept = list()
            self.dept_dict = dict()
            self.ward_dept = dict()
            Properties._IS_INIT = True

    def __getattribute__(self, item):
        """
        访问类属性时，先访问该方法
        """
        if item == 'regular_model':
            return self.__getRegularModel()
        elif item == 'dept':
            return self.__deptList()
        elif item == 'dept_dict':
            return self.__codeDeptWard()
        elif item == 'ward_dept':
            return self.__wardDept()
        return super(Properties, self).__getattribute__(item)

    @staticmethod
    def __getDict(strName, dictName, value):

        if value.find(',') > 0:
            value_list = value.split(',')
            dictName[strName] = value_list
        else:
            dictName[strName] = value
            return

    def getInfo(self, fileName):
        """
        读取配置文件夹中的txt文件内容
        """
        try:
            result = dict()
            f = os.path.join(rootPath, 'configure/{}'.format(fileName))
            if not os.path.exists(f):
                f = os.path.join(os.path.dirname(__file__), 'configure/{}'.format(fileName))
            with open(f, 'r', encoding='utf8') as pro_file:
                for line in pro_file.readlines():
                    line = line.strip().replace('\n', '')
                    if line.find("#") != -1:
                        line = line[0:line.find('#')]
                    if line.find('=') > 0:
                        strs = line.split('=')
                        strs[1] = line[len(strs[0]) + 1:]
                        self.__getDict(strs[0].strip(), result, strs[1].strip())
            return result
        except Exception as e:
            raise e

    @staticmethod
    def __loadconf():
        """
        导入配置文件所有信息
        """
        conf = dict()
        configure_path = os.path.join(rootPath, 'configure')
        if os.path.isdir(configure_path):
            for p in os.listdir(configure_path):
                if not p.endswith('.xml'):
                    continue
                path = os.path.join(configure_path, p)
                with open(path, 'r') as f:
                    f_doc = f.read()
                info = XML2Dict().parse(f_doc)['configuration']['property']
                if isinstance(info, dict):
                    conf[info['name'].decode('utf8')] = eval(info['value'].decode('utf8'))
                else:
                    for v in info:
                        if v['value']:
                            conf[v['name'].decode('utf8')] = eval(v['value'].decode('utf8'))
                        else:
                            conf[v['name'].decode('utf8')] = None
        else:
            with open(configure_path, 'r') as f:
                f_doc = f.read()
            info = XML2Dict().parse(f_doc)['configuration']['property']
            if isinstance(info, dict):
                conf[info['name'].decode('utf8')] = eval(info['value'].decode('utf8'))
            else:
                for v in info:
                    if v['value']:
                        conf[v['name'].decode('utf8')] = eval(v['value'].decode('utf8'))
                    else:
                        conf[v['name'].decode('utf8')] = None
        return conf

    def __getRegularModel(self):
        """
        加载规则模型
        """
        client = MongoClient(host=self.properties.get('mongo_host'), port=eval(self.properties.get('mongo_port')), connect=False)
        db = client.get_database(name=self.properties.get('mongodb'))
        if self.properties.get('mongo_auth') != 'false':
            db.authenticate(self.properties.get('username_write_read'), self.properties.get('password_write_read'))
        regular_collection_list = {'regular_model_yishengduan': '医生端', 'regular_model_huanjie': '环节', 'regular_model_zhongmo': '终末'}
        result = {}
        for collection_name, key in regular_collection_list.items():
            conn = db.get_collection(collection_name)
            mongo_result = conn.find()
            result.setdefault(key, dict())
            for data in mongo_result:
                data['code'] = data['_id']
                data['dept'] = self.__loadRegularDept(data['dept'])
                result[key][data['_id']] = data
        return result

    @staticmethod
    def __loadRegularDept(regular_dept):
        """
        处理规则模型中的科室
        """
        result = dict()
        if regular_dept == '通用':
            result = {'$nin': []}
        else:
            dept_split = regular_dept.split('、')
            if regular_dept.startswith('除'):
                flag = True
            else:
                flag = False
            for dept in dept_split:
                if flag:
                    result.setdefault('$nin', list())
                    result['$nin'].append(dept.replace('除', ''))
                else:
                    result.setdefault('$in', list())
                    result['$in'].append(dept)
        return result

    # def getRegularModel(self, model_path):
    #     """
    #     加载规则模型
    #     """
    #     model_dict = {}
    #     if os.path.isdir(model_path):
    #         for k, v in self.name_switch.items():
    #             file = os.path.join(model_path, v)
    #             with open(file, 'r', encoding='utf8') as f:
    #                 for line in f.readlines():
    #                     line = line.strip()
    #                     line_split = line.split(',')
    #                     regular_code = line_split[0]
    #                     value = line_split[1:]
    #                     if re.findall('^[0-9]+\.?\d*$', value[3]):
    #                         value[3] = float(value[3])
    #                     else:
    #                         value[3] = 0
    #                     value_4 = dict()
    #                     if value[4] == '通用':
    #                         value_4 = {'$nin': []}
    #                     else:
    #                         dept_split = value[4].split('、')
    #                         if value[4].startswith('除'):
    #                             flag = True
    #                         else:
    #                             flag = False
    #                         for dept in dept_split:
    #                             if flag:
    #                                 value_4.setdefault('$nin', list())
    #                                 value_4['$nin'].append(dept.replace('除', ''))
    #                             else:
    #                                 value_4.setdefault('$in', list())
    #                                 value_4['$in'].append(dept)
    #                     value[4] = value_4
    #                     if re.findall('^\d{4}-\d{1,2}-\d{1,2}$', value[5]):
    #                         value[5] = datetime.strftime(datetime.strptime(value[5], '%Y-%m-%d'), '%Y-%m-%d')
    #                     model_dict.setdefault(k, dict())
    #                     model_dict[k][regular_code] = value
    #     return model_dict

    def __readDeptInfo(self):
        result = list()
        file = self.dept_path
        if not os.path.exists(file):
            return result
        with open(file, 'r', encoding='utf8') as f:
            for line in f.readlines():
                line = line.strip()
                line_split = line.split(',')
                result.append(line_split)
        return result

    def __getDept(self):
        dept_list = set()
        code_name = dict()
        ward_dept = dict()
        for one_record in self.dept_info:
            if len(one_record) >= 4:
                dept_list.add(one_record[3])
                code_name[one_record[0]] = one_record[2]
                code_name[one_record[1]] = one_record[3]
                ward_dept[one_record[2]] = one_record[3]
        dept_list = list(dept_list)
        return dept_list, code_name, ward_dept

    def __deptList(self):
        client = MongoClient(host=self.properties.get('mongo_host'), port=eval(self.properties.get('mongo_port')), connect=False)
        db = client.get_database(name=self.properties.get('mongodb'))
        if self.properties.get('mongo_auth') != 'false':
            db.authenticate(self.properties.get('username_write_read'), self.properties.get('password_write_read'))
        conn = db.get_collection('MedicalQuality_dept')
        result = conn.distinct('DEPT_NAME')
        return result

    def __codeDeptWard(self):
        client = MongoClient(host=self.properties.get('mongo_host'), port=eval(self.properties.get('mongo_port')), connect=False)
        db = client.get_database(name=self.properties.get('mongodb'))
        if self.properties.get('mongo_auth') != 'false':
            db.authenticate(self.properties.get('username_write_read'), self.properties.get('password_write_read'))
        conn_dept = db.get_collection('MedicalQuality_dept')
        conn_ward = db.get_collection('MedicalQuality_district')
        result = dict()
        dept_result = conn_dept.find({}, {'DEPT_CODE': 1, 'DEPT_NAME': 1})
        ward_result = conn_ward.find({}, {'WARD_CODE': 1, 'WARD_NAME': 1})
        for data in dept_result:
            if data.get('DEPT_CODE') and data.get('DEPT_NAME'):
                result[data['DEPT_CODE']] = data['DEPT_NAME']
        for data in ward_result:
            if data.get('WARD_CODE') and data.get('WARD_NAME'):
                result[data['WARD_CODE']] = data['WARD_NAME']
        return result

    def __wardDept(self):
        client = MongoClient(host=self.properties.get('mongo_host'), port=eval(self.properties.get('mongo_port')), connect=False)
        db = client.get_database(name=self.properties.get('mongodb'))
        if self.properties.get('mongo_auth') != 'false':
            db.authenticate(self.properties.get('username_write_read'), self.properties.get('password_write_read'))
        conn_dept = db.get_collection('MedicalQuality_dept')
        result = dict()
        mongo_result = conn_dept.aggregate([
            {'$lookup': {
                "from": "MedicalQuality_district",
                "localField": "DEPT_CODE",
                "foreignField": "dept_id",
                "as": "district"}},
            {'$unwind': '$district'},
            {'$project': {'DEPT_NAME': 1, 'WARD_NAME': '$district.WARD_NAME'}}
        ], allowDiskUse=True)
        for data in mongo_result:
            if data.get('WARD_NAME') and data.get('DEPT_NAME'):
                result[data['WARD_NAME']] = data['DEPT_NAME']
        return result


if __name__ == '__main__':
    app = Properties()
    x = app.regular_model['终末']
    # import json
    # print(json.dumps(app.conf_dict, ensure_ascii=False, indent=4))
