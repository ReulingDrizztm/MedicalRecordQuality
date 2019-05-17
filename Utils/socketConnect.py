#!/usr/bin/env python3
# -*- coding:utf-8 -*-


# socket 接口请求, 只能查 yizhu, jianchabaogao, jianyanbaogao，
# 检查，检验要加入入院时间，不要就诊次，医嘱只需要就诊次

import os
import sys
cur_path = os.path.abspath(os.path.dirname(__file__))
root_path = os.path.split(cur_path)[0]
sys.path.append(root_path)  # 项目路径添加到系统路径
import json
import socket
import traceback
from Utils.loadingConfigure import Properties
from Utils.LogUtils import LogUtils


class SocketConnect(object):
    # 是否初始化
    IS_INIT = False

    def __init__(self):
        if not SocketConnect.IS_INIT:
            self.parameters = Properties()
            self.logger = LogUtils().getLogger('socket_conn')
            self.host = self.parameters.properties.get('socket_host', '0.0.0.0')
            self.port = self.parameters.properties.get('socket_port', 0)
            if self.port:
                self.port = int(self.port)
            SocketConnect.IS_INIT = True

    def __new__(cls, *args, **kwargs):
        """
        单例模式
        """
        if not hasattr(cls, 'instance'):
            cls.instance = super(SocketConnect, cls).__new__(cls)
        return cls.instance

    def gainEmr(self, patient_id, visit_id, record_name, start_time='', end_time=''):
        res = dict()
        data = ''.encode()
        try:
            requests_add = (self.host, self.port)
            requests_info = '{}#{}#{}#{}#{}\n'.format(patient_id, visit_id, start_time, end_time, record_name)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(requests_add)
            s.settimeout(5)  # 超时
            s.sendall(requests_info.encode())
            while True:
                x = s.recv(1024, socket.MSG_WAITALL)
                data += x
                if not len(x):
                    break
            s.close()
            res = json.loads(data)
            if not res.get(record_name):
                res['res_flag'] = False
                res['error_info'] = 'no result in socket request.'
                res['error_source'] = 'socket'
                res['patient_id'] = patient_id
                res['visit_id'] = visit_id
                res['record_name'] = record_name
                info = '\npatient_id: {}\nvisit_id: {}\nstart_time: {}\nend_time: {}\nrecord_name: {}\nhost: {}\nport: {}\ndata: {}'.format(
                    patient_id, visit_id, start_time, end_time, record_name, self.host, self.port, data)
                self.logger.info(info)
                return res
            res['res_flag'] = True
        except:
            info = '\npatient_id: {}\nvisit_id: {}\nstart_time: {}\nend_time: {}\nrecord_name: {}\nhost: {}\nport: {}\ndata: {}'.format(
                patient_id, visit_id, start_time, end_time, record_name, self.host, self.port, data)
            self.logger.info(info)
            self.logger.error(traceback.format_exc())
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            res['res_flag'] = False
            res['patient_id'] = patient_id
            res['visit_id'] = visit_id
            res['record_name'] = record_name
            res['error_source'] = 'socket'
            res['error_type'] = exc_type.__name__
            res['error_info'] = '.'.join(exc_value.args)
            res['abnormal_info'] = ''.join(traceback.format_tb(exc_traceback_obj))
        return res

    def process(self, patient_id, visit_id, record_name, start_time='', end_time=''):
        socket_res = self.gainEmr(patient_id, visit_id, record_name, start_time, end_time)
        if not socket_res.get('res_flag'):
            return socket_res
        res = {'res_flag': True}
        if record_name in ['shouyeshoushu', 'shouyezhenduan', 'yizhu', 'jianchabaogao', 'jianyanbaogao']:
            res[record_name] = list()
            for value in socket_res.get(record_name, list()):
                tmp = dict()
                try:
                    assert isinstance(value, dict)
                except AssertionError:
                    info = '\npatient_id: {}\nvisit_id: {}\nstart_time: {}\nend_time: {}\nrecord_name: {}\nhost: {}\nport: {}\nvalue: {}'.format(
                            patient_id, visit_id, start_time, end_time, record_name, self.host, self.port, value)
                    self.logger.error(info)
                    continue
                for k, v in value.items():
                    if v:
                        key = k.lower()
                        if k == 'OPER_NO':
                            key = 'operation_num'
                        elif k == 'DRUG_AMOUNT_UNIT':
                            key = 'drug_amount_value_unit'
                        tmp[key] = v
                res[record_name].append(tmp)
        elif record_name == 'binganshouye':
            res[record_name] = dict()
            res[record_name]['pat_info'] = dict()
            res[record_name]['pat_visit'] = dict()
            if not socket_res.get(record_name, list()):
                return res
            value = socket_res.get(record_name, list())[0]
            for k, v in value.items():
                if not v:
                    continue
                key = k.lower()
                if k == 'PATIENT_IDVISIT':
                    key = 'patient_id'
                elif k == 'NAME':
                    key = 'person_name'
                elif k == 'SEX':
                    key = 'sex_name'
                if k in ['PATIENT_ID', 'PATIENT_IDVISIT', 'NAME', 'SEX', 'DATE_OF_BIRTH', 'NATION_NAME',
                         'NATIONALITY_NAME', 'ID_CARD_TYPE', 'ID_CARD_NO', 'BIRTH_ADDRESS', 'BLOOD_TYPE_NAME',
                         'RH_BLOOD_NAME', 'IDENTITY_NAME', 'FAMILY_ADDR_PROVINCE_NAME', 'BABY_AGE', 'BABY_BIRTH_WEIGHT',
                         'BABY_ADMIN_WEIGHT']:
                    res[record_name]['pat_info'][key] = v
                else:
                    res[record_name]['pat_visit'][key] = v
        if not res.get(record_name):
            res['res_flag'] = False
            res['record_name'] = record_name
            res['patient_id'] = patient_id
            res['visit_id'] = visit_id
            res['error_source'] = 'socket'
            res['error_info'] = 'no process result'
        return res


if __name__ == '__main__':
    app = SocketConnect()
    r = app.process('000724189200', '6', 'yizhu')  # siwangjilu ruyuanjilu shoushujilu shouyeshoushu binganshouye shouyezhenduan
    print(json.dumps(r, ensure_ascii=False, indent=2))
    # res = app.gainHiss('0009583961', '1', 'jianchabaogao')  # yizhu jianchabaogao
    # print(json.dumps(res, ensure_ascii=False, indent=2))
    # import requests
    # add = 'http://192.168.8.20:8801/document/examreport'
    # for i in r.get('jianchabaogao', list()):
    #     i['examine_class_name'] = i.get('exam_class_name', '')
    #     i['examine_item_name'] = i.get('exam_item_name', '')
    #     i['examine_diag'] = i.get('exam_diag', '')
    #     i['examine_feature'] = i.get('exam_feature', '')
    #     res = requests.post(add, data=json.dumps(i))
    #     print(json.dumps(json.loads(res.text), ensure_ascii=False, indent=2))
