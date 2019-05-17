#!/usr/bin/env python3
# -*- coding:utf-8 -*

"""
@version: 
@author:
@contact:
@software: PyCharm Community Edition
@file: segmentWord.py
@time: 18-9-26 下午4:41
@description: 分词请求
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


class RunSegmentWord(object):
    # 是否初始化
    is_init = False

    def __init__(self):
        if not RunSegmentWord.is_init:
            self.parameters = Properties()
            self.logger = LogUtils().getLogger('segment')
            self.log_info = """hospital_code: [{0}], version: [{1}], serverip: [{2}], request_add: [{3}], request_data: [{4}],
            response_text: [{5}], response_code: [{6}], error_type: [{7}], error_content: [{8}], abnormal_info: [\n{9}], take_times: [{10:.2f}]s"""
            self.hospital_code = self.parameters.properties.get('hospital_code')
            self.ver = self.parameters.properties.get('version')
            self.conf_dict = self.parameters.conf_dict.copy()
            self.segment_ip = self.parameters.properties.get('segment_host', '0.0.0.0')
            self.segment_port = self.parameters.properties.get('segment_port', '0')
            self.segment_address = 'http://{}:{}/extraction/main'.format(self.segment_ip, self.segment_port)
            self.ver_address = 'http://{}:{}/extraction/version'.format(self.segment_ip, self.segment_port)
            self.emr_record = self.parameters.getInfo('emr_transform.txt')
            RunSegmentWord.is_init = True

    def __new__(cls, *args, **kwargs):
        """
        单例模式
        """
        if not hasattr(cls, 'instance'):
            cls.instance = super(RunSegmentWord, cls).__new__(cls)
        return cls.instance

    # def processHtml2(self, **kwargs):
    # self.segment_address = 'http://{}:{}/med'.format(self.segment_ip, self.segment_port)
    #     start_time = time.time()
    #     mr_class_code = kwargs.get('mr_class_code')
    #     mr_content = kwargs.get('mr_content_html')
    #     if not (mr_class_code and mr_content):
    #         return {'res_flag': False, 'error_info': 'no mr_content_html or mr_class_code', 'error_source': 'segment'}
    #     topic = kwargs.get('topic')
    #     request_address = self.segment_address + '/document/segwordment'
    #     result = dict()
    #     para = {'key': mr_class_code,
    #             'data': mr_content}
    #     if topic:
    #         para['topic'] = topic
    #     info = json.dumps(para)
    #     r = requests.post(request_address, data=info)
    #     if r.status_code == 200:
    #         result = json.loads(r.text)
    #         time_cost = r.elapsed.total_seconds()
    #     else:
    #         r = requests.post(request_address, data=info)
    #         try:
    #             result = json.loads(r.text)
    #             time_cost = r.elapsed.total_seconds()
    #         except:
    #             HOST_NAME = socket.gethostname()
    #             HOST_IP = socket.gethostbyname(HOST_NAME)
    #             exc_type, exc_value, exc_traceback_obj = sys.exc_info()
    #             abnormal_info = ''.join(traceback.format_tb(exc_traceback_obj))
    #             info = self.log_info.format(self.hospital_code, self.ver, HOST_IP, request_address, para, r.text, r.status_code,
    #                                         exc_type.__name__, exc_value, abnormal_info, time.time()-start_time)
    #             self.logger.error(info)
    #             result['res_flag'] = False
    #             result['error_source'] = 'segment'
    #             result['response_status'] = r.status_code
    #             result['response_text'] = r.text
    #             result['error_type'] = exc_type.__name__
    #             result['error_info'] = '.'.join(exc_value.args)
    #             result['abnormal_info'] = ''.join(traceback.format_tb(exc_traceback_obj))
    #             return result
    #     if result.get('result_status', dict()).get('result_code', '') == 'success':
    #         result = result.get('result', dict())
    #         for k, v in result.items():
    #             v['file_time_value'] = kwargs.get('caption_date_time', '')
    #             v['last_modify_date_time'] = kwargs.get('last_modify_date_time', '')
    #             v['creator_name'] = kwargs.get('creator_name', '')
    #         result['res_flag'] = True
    #     else:
    #         info = '\nkey: {0}\nresult_status: {1}'.format(mr_class_code, result.get('result_status', dict()))
    #         self.logger.error(info)
    #         result['res_flag'] = False
    #         result['error_source'] = 'segment'
    #     result['response_time'] = time_cost
    #     return result

    def processHtml(self, **kwargs):
        start_time = time.time()
        mr_class_code = kwargs.get('mr_class_code')
        mr_content = kwargs.get('mr_content_html')
        if not (mr_class_code and mr_content):
            return {'res_flag': False, 'error_info': 'no mr_content_html or mr_class_code', 'error_source': 'segment'}
        if not self.emr_record.get(mr_class_code):
            return {'res_flag': False, 'error_info': 'mr_class_code not in emr_transform sheet', 'error_source': 'segment'}
        theme = self.emr_record.get(mr_class_code, list())[0]
        topic = kwargs.get('topic')
        result = dict()
        para = {'mr_class_code': mr_class_code,
                'data_content': [mr_content],
                'data_theme': theme,
                'data_type': '0',
                'data_format': '0',
                'dept_name': 'all'}
        if topic:
            para['data_topic'] = topic
        info = json.dumps(para)
        r = requests.post(self.segment_address, data=info)
        if r.status_code == 200:
            result = json.loads(r.text)
            time_cost = r.elapsed.total_seconds()
        else:
            r = requests.post(self.segment_address, data=info)
            try:
                result = json.loads(r.text)
                time_cost = r.elapsed.total_seconds()
            except:
                HOST_NAME = socket.gethostname()
                HOST_IP = socket.gethostbyname(HOST_NAME)
                exc_type, exc_value, exc_traceback_obj = sys.exc_info()
                abnormal_info = ''.join(traceback.format_tb(exc_traceback_obj))
                info = self.log_info.format(self.hospital_code, self.ver, HOST_IP, self.segment_address, para, r.text, r.status_code,
                                            exc_type.__name__, exc_value, abnormal_info, time.time()-start_time)
                self.logger.error(info)
                if not isinstance(result, dict):
                    tmp = result
                    result = dict()
                    result['error_code'] = tmp
                result['res_flag'] = False
                result['error_source'] = 'segment'
                result['response_status'] = r.status_code
                result['response_text'] = r.text
                result['error_type'] = exc_type.__name__
                result['error_info'] = '.'.join(exc_value.args)
                result['abnormal_info'] = ''.join(traceback.format_tb(exc_traceback_obj))
                return result
        seg_result = dict()
        if isinstance(result, dict):
            if 'data_res' in result:
                seg_result[theme] = result['data_res']
                seg_result[theme]['file_time_value'] = kwargs.get('caption_date_time', '')
                seg_result[theme]['last_modify_date_time'] = kwargs.get('last_modify_date_time', '')
                seg_result[theme]['creator_name'] = kwargs.get('creator_name', '')
            seg_result['res_flag'] = True
        else:
            info = '\nkey: {0}\nresult_status: {1}'.format(mr_class_code, seg_result)
            self.logger.error(info)
            seg_result['res_flag'] = False
            seg_result['error_source'] = 'segment'
            seg_result['error_code'] = result
        seg_result['response_time'] = time_cost
        return seg_result

    def version(self):
        start_time = time.time()
        r = requests.get(self.ver_address)
        result = dict()
        if r.status_code == 200:
            result = json.loads(r.text)
            time_cost = r.elapsed.total_seconds()
        else:
            HOST_NAME = socket.gethostname()
            HOST_IP = socket.gethostbyname(HOST_NAME)
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            abnormal_info = ''.join(traceback.format_tb(exc_traceback_obj))
            info = self.log_info.format(self.hospital_code, self.ver, HOST_IP, self.ver_address, None, r.text, r.status_code,
                                        exc_type.__name__, exc_value, abnormal_info, time.time()-start_time)
            self.logger.error(info)
            result['res_flag'] = False
            result['error_source'] = 'segment'
            result['response_status'] = r.status_code
            result['response_text'] = r.text
            result['error_type'] = exc_type.__name__
            result['error_info'] = '.'.join(exc_value.args)
            result['abnormal_info'] = ''.join(traceback.format_tb(exc_traceback_obj))
            return result
        result['res_flag'] = True
        result['response_time'] = time_cost
        return result

    def process(self, content_list):
        start_time = time.time()
        url = 'http://{}:{}/extraction/main'.format(self.segment_ip, self.segment_port)
        seg_result = dict()
        res = dict()
        time_cost = 0
        for data in content_list:
            para = {'data_content': [data.get('value', '')],
                    'data_theme': data.get('key', ''),
                    'data_type': '1',
                    'data_format': '1',
                    'dept_name': 'all',
                    'display': "False"}
            info = json.dumps(para)
            r = requests.post(url, data=info)
            if r.status_code == 200:
                seg_result = json.loads(r.text)
                time_cost += r.elapsed.total_seconds()
            else:
                r = requests.post(self.segment_address, data=info)
                try:
                    seg_result = json.loads(r.text)
                    time_cost += r.elapsed.total_seconds()
                except:
                    HOST_NAME = socket.gethostname()
                    HOST_IP = socket.gethostbyname(HOST_NAME)
                    exc_type, exc_value, exc_traceback_obj = sys.exc_info()
                    abnormal_info = ''.join(traceback.format_tb(exc_traceback_obj))
                    info = self.log_info.format(self.hospital_code, self.ver, HOST_IP, self.segment_address, para, r.text, r.status_code,
                                                exc_type.__name__, exc_value, abnormal_info, time.time()-start_time)
                    self.logger.error(info)
                    if not isinstance(seg_result, dict):
                        tmp = seg_result
                        seg_result = dict()
                        seg_result['error_code'] = tmp
                    seg_result['res_flag'] = False
                    seg_result['error_source'] = 'segment'
                    seg_result['response_status'] = r.status_code
                    seg_result['response_text'] = r.text
                    seg_result['error_type'] = exc_type.__name__
                    seg_result['error_info'] = '.'.join(exc_value.args)
                    seg_result['abnormal_info'] = ''.join(traceback.format_tb(exc_traceback_obj))
                    return seg_result
            if isinstance(seg_result, dict):
                if 'data_res' in seg_result:
                    theme = data.get('chapter_name', '')
                    res[theme] = seg_result['data_res'].get('value', dict())
            else:
                info = '\nkey: {0}\nresult_status: {1}'.format(data.get('key', ''), seg_result)
                self.logger.error(info)
                tmp = dict()
                tmp['res_flag'] = False
                tmp['error_source'] = 'segment'
                tmp['error_code'] = seg_result
                return tmp
        result = {'ruyuanjilu': res}
        result['response_time'] = time_cost
        result['res_flag'] = True
        return result


if __name__ == '__main__':
    app = RunSegmentWord()
    ruyuanjilu = [
        {'key': 'ryjl_zs', 'value': '右腰部不适伴发热1天', 'chapter_name': 'chief_complaint'},
        {'key': 'ryjl_tgjc', 'value': 'T 39.4℃P 100次分R 20次分Bp 12775mmHg    发育正常，营养良好，神志清楚，自主体位，应答切题，查体合作。全身皮肤黏膜色泽正常，未见皮疹，无皮下结节、瘢痕，未见皮下出血点及瘀斑,未见肝掌,未见蜘蛛痣。全身浅表淋巴结未扪及肿大。头颅大小正常无畸形，五官端正。眼睑正常，巩膜无黄染，双侧瞳孔等圆等大，左瞳孔3.0mm，右瞳孔3.0mm，对光反射正常。外耳道未见分泌物,乳突无压痛。鼻腔通气良好，双鼻窦区均无压痛。口唇红润，伸舌居中，口腔黏膜正常，牙龈无出血。咽正常无充血，扁桃体无肿大。颈部无抵抗，颈静脉正常，气管居中,甲状腺未触及肿大。胸廓正常，呼吸运动正常，呼吸节律正常，双肺叩诊呈清音，双肺呼吸音清，未闻及干湿啰音。心前区无隆起，心尖搏动范围正常，心前区未触及震颤和心包摩擦感，心脏相对浊音界正常，心率70次分，心律齐整，各瓣膜听诊区未闻及杂音。腹部平坦，腹式呼吸存在，腹壁静脉无曲张，无胃型、肠型、蠕动波。腹肌柔软，无压痛、反跳痛，未触及腹部包块，肝脏肋下未触及，脾脏肋下未触及，肾脏未触及，Murphy\\script0  征阴性，肝浊音界存在，移动性浊音阴性，肾区无叩击痛，肠鸣音正常。外生殖器未查、肛门直肠未查。脊柱正常，\\script0 四肢无畸形，关节无红肿、活动自如，双下肢无浮肿。四肢肌力Ⅴ级，肌张力正常，双侧肱二、三头肌腱反射正常，双侧膝、跟腱反射正常，Hoffmann 征阴性、Babinski 征阴性、Kernig 征阴性。\x7f双肾区无红肿、无疤痕、无异常隆起，肋脊点、肋腰点无压痛、无叩痛、无放射痛。肋下未触及肾脏，双侧输尿管行程无压痛，膀胱区无充盈，无压痛。尿道外口无异常分泌物。', 'chapter_name': 'physical_examination'},
        {'key': 'ryjl_xbs', 'value': '患者于1天前无明显诱因出现右腰部不适，并出现发热，最高达39.4℃。无束带感、恶心、呕吐、腹泻、便血、头昏、头痛、心悸、胸闷。遂至我院就诊，现为进一步诊断治疗，门诊以“右肾感染”收住入院。自发病以来精神状态一般，食欲一般，睡眠良好，大便正常，小便正常，体力情况如常，体重无明显变化。', 'chapter_name': 'history_of_present_illness'},
        {'key': 'ryjl_jws', 'value': '两月前行右URL、支架置入术。否认高血压史、冠心病史、糖尿病等慢性病史,否认肝炎、结核等传染病史，头孢曲松过敏，预防接种史不详。', 'chapter_name': 'history_of_past_illness'},
        {'key': 'ryjl_grs', 'value': '否认血吸虫疫水接触史，否认到过地方病高发及传染病流行地区否认嗜酒史、吸烟史。无常用药品及麻醉毒品嗜好。否认工业毒物、粉尘、放射性物质接触史。否认冶游史。否认疫区接触史。', 'chapter_name': 'social_history'},
        {'key': 'ryjl_yjhys', 'value': '家人身体健康。', 'chapter_name': 'menstrual_and_obstetrical_histories'},
        {'key': 'ryjl_jzs', 'value': '否认家族遗传病史。', 'chapter_name': 'history_of_family_member_diseases'},
    ]
    shangjiyishichafangjilu = [
        {
            "mr_code": "EMR10.00.03_43",
            "topic": "姜亮主任医师、李彦主治医师、胡攀攀住院总医师首次查房记录",
            "mr_content": "<html>\r\n<head>\r\n<title>北　京　大　学　第　三　医　院</title>\r\n<style type=\"text/css\">\r\n.table1 {\r\nBORDER-RIGHT: #000000 0px solid; BORDER-TOP: #000000 1px solid; BORDER-LEFT: #000000 1px solid; BORDER-BOTTOM: #000000 0px solid\r\n}\r\n.td1 {\r\n\tBORDER-RIGHT: #000000 1px solid; BORDER-TOP: #000000 0px solid; BORDER-LEFT: #000000 0px solid; BORDER-BOTTOM: #000000 1px solid\r\n}\r\n</style>\r\n</head>\r\n<body bgcolor=\"#005757\">\r\n<table width=\"794\" align=\"center\"  border=\"1\" cellspacing=\"0\" bordercolor=black  rules=none bgcolor=\"#FFFFFF\">\r\n<tr><td>\r\n<table width=\"669\" align=\"center\">\r\n<tr><td>\r\n<table  height=\"57\" align=\"center\">\r\n<tr><td>\r\n</td></tr>\r\n</table>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 18px;font-weight: bold;\">北　京　大　学　第　三　医　院</span></p>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 28px;font-weight: bold;\">&nbsp;病&nbsp;历&nbsp;记&nbsp;录&nbsp;</span><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n<table width=\"665\" height=\"21\">\r\n<tr style=\"display:none\">\r\n<td width=\"170\">&nbsp;</td>\r\n<td width=\"77\">&nbsp;</td>\r\n<td width=\"179\">&nbsp;</td>\r\n<td width=\"84\">&nbsp;</td>\r\n<td width=\"155\">&nbsp;</td>\r\n</tr>\r\n<tr>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">姓名:</span><span style=\"font-family: 宋体; font-size: 14px;\">刘欢</span></p>\r\n</td>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 14px;\">第&nbsp;</span>1\r\n<span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;页</span></p>\r\n</td>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p align=\"right\"><span style=\"font-family: 宋体; font-size: 14px;\">住院号:</span><span style=\"font-family: 宋体; font-size: 14px;\">5042725</span></p>\r\n</td>\r\n</tr>\r\n</table>\r\n<hr></hr>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;font-weight: bold;\">2018-12-04&nbsp;08:33</span><span style=\"font-family: 宋体; font-size: 14px;\">　　　　　</span><span style=\"font-family: 宋体; font-size: 14px;font-weight: bold;\">姜亮主任医师、李彦主治医师、胡攀攀住院总医师首次查房记录</span></p>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">患者病情</span><span style=\"font-family: 宋体; font-size: 14px;\">病人述2017年8月开始无明显诱因出现腰背部疼痛，VSA评分4分，自认为“受凉”所致，无下肢疼痛、麻木，活动无受限，自行采用外贴膏药治疗，约1个月后疼痛明显缓解。自此久坐后常有腰背部酸胀不适，站立活动或卧床休息症状可缓解，未在意。于2018年8月再次出现腰背部疼痛，VSA评分4分，站立行走、翻身等动作诱发疼痛加重，卧床休息疼痛可减轻，继续采用外贴膏药治疗，约1个月后腰背部疼痛减轻，但出现右小腿后侧及足底麻木感，无下肢疼痛，无乏力、盗汗，无夜间痛，继续观察，未给予重视，于10月初开始出现右下肢膝关节以远乏力感，行走时出现步态跛行，步态不稳，自觉右下肢乏力及麻木症状进行性加重，于2周前开始因右下肢乏力严重，自行行走困难，故前往当地医院就诊，查腰椎核磁、CT等相关检查，结果提示T11病理性骨折、骨巨细胞瘤？嗜酸性肉芽肿？。病人及家属为求进一步诊治前来我院，经门诊医师看病人后以“T11病理性骨折”收治入院。</span><span style=\"font-family: 宋体; font-size: 14px;\">，</span><span style=\"font-family: 宋体; font-size: 14px;\">查体</span><span style=\"font-family: 宋体; font-size: 14px;\">神志</span><span style=\"font-family: 宋体; font-size: 14px;\">清</span><span style=\"font-family: 宋体; font-size: 14px;\">，精神</span><span style=\"font-family: 宋体; font-size: 14px;\">可</span><span style=\"font-family: 宋体; font-size: 14px;\">，</span><span style=\"font-family: 宋体; font-size: 14px;\">脊柱生理曲度尚可，胸椎棘突后侧无明显压痛，右下肢自腹股沟以远针刺觉减退，左下肢针刺觉正常。左侧髂腰肌肌力IV级，右侧髂腰肌肌力IV-级；双侧股四头肌肌力V级，左侧胫前肌力V级，右侧胫前肌肌力III级；左侧小腿三头肌肌力V级，右侧小腿三头肌肌力IV级；左侧拇背伸肌肌力V级，右侧拇背伸肌肌力III级。双侧膝腱反射亢进，双侧跟腱反射活跃，双侧Babinski征阳性，双侧Chaddock征阳性，左侧踝阵挛阳性，右侧踝阵挛可疑阳性。</span></p>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">姜亮主任医师、李彦主治医师、胡攀攀住院总医师</span><span style=\"font-family: 宋体; font-size: 14px;\">查房，</span><span style=\"font-family: 宋体; font-size: 14px;\">病史</span><span style=\"font-family: 宋体; font-size: 14px;\">如前</span><span style=\"font-family: 宋体; font-size: 14px;\">，查体</span><span style=\"font-family: 宋体; font-size: 14px;\">同前</span><span style=\"font-family: 宋体; font-size: 14px;\">，</span><span style=\"font-family: 宋体; font-size: 14px;\">诊断为:1.T11病理性骨折&nbsp;Frankel&nbsp;D&nbsp;T11肿瘤&nbsp;椎管内肿瘤&nbsp;胸脊髓损伤&nbsp;2.双下肢不全瘫，</span><span style=\"font-family: 宋体; font-size: 14px;\">嘱患者绝对卧床，暂给予神经营养、脱水、对症治疗，完善相关辅助检查后制定进一步治疗计划</span><span style=\"font-family: 宋体; font-size: 14px;\">。</span></p>\r\n<p align=\"right\"><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span><img src=\"data:image/jpg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAA0AFMDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD3+iiigArz2w8R3Y+OGraJPPL9hOnxCCMsSglA3nA6AlS59wntWl4t+I+h+Fo5bfzjfasBti0+1BkkLnAUPj7mSR1554B6V5v4V8Ga14h8YeIIPFGs3lpeqlpeXSWEwD+a6yhAJNvyBEZl2rx82MkCgD2J/FGhR65Fojataf2nKSFtRKDJkDOCB0OOea1q5fwv8PvDvhHEmm2Ze6wR9quG8yQA9cHoue+AM9811FABWFN4lS08YQaBeWrwLd25lsrsuCk7qTvix2YDDe4J9OauveNrHSNSj0azt59V12UZj060xuA/vSMfljXpyx79DWXqmhXmt6cmo+NdRg0+zsZ0vVs7FsJDsJOZJmG5jgkHbsHJxng0AdutxC8zQpNG0q8sgYEj6ipK5fwolxeM+q/ZP7N011KWFgIwjeWSCZpBjh2wML2HXknHUUAFFFFAGL4g1fVNKFt/Znh651dpSwcQzxxCLA4yXI6n8sH2zjf2N4p8Sndr2oDRtPJB/s3SZSZXHHElxgH1yEC8HrXZ1zHjDXLuzjtdE0Yg67qpMVsSMi3QD552/wBlB0HckDnmgDif7MfUfF9vp3gvSbCHRvD8zGa4mBEBv8YywHzTNGpOOR8zcsMDNPR/D95qXxk8Sadq+v6nJKllbyyTWEpshNwMAhDnaA2AM59Sa9EV9G+HXhS1gkM/2aIiJTHC80s8rZJJCgksxySemTXmWoa54pj8a6j4r0fwpqtlZXVgltJcXtmGkjCEkyeTvXPGMZYDjJ9KAOk8XeH7HwhorX2iatrdrrEjhLC3j1CScXdwfuoYpCwcEnJ44GTXpcPmmCMzhRLtG8J03Y5x7ZrkfCGg6bLFbeK5dQu9Y1C7tw8d/fDaY42AOI4wAsSn0AzyeTW5H4k0ae5NvbahBcyqcOts3m+X6lyuQg92xQBbupLLTobnU7nyYEjiLz3DAAhFBPJ64HNeT69qWq+M1tdVuJpNH8JxTK9lb+QJbzVZQcoUhPBHGVDAj+Igjleuu/H0GoXUumeFNPfxDdr8kskTBbOHp/rJj8p4OcLuJwa5Hwv4Vu/HPiHXdT8Zai19HYXbadFaWjtDbgqAZVA4YoGYDqN235s8YANXwv4pm0qwm04z6h4n1qWdpRaW0i3H2NSAFjluOI1I2knkYJIAwBnfXSvFmu7m1jVY9GtGHFnpB3TYOD89w46jkfIo+tZXh++tNW8XRJpVzb6b4c0zzIbG0tWWIajNyJJAoxuiTkDAwWyc8V6HQBTsNMt9Oso7SAztHHnBmneVzkknLMSTye5oq5RQBi+IfE1l4cijlvHCoUeWQ/3IkGWb35KKB3Z1Fc34duLLTJrvxP4s1Cx0/WdUAxBd3KobO2HMcA3EYP8AE2MZYnjirPiL4b6f4r8XW2r61Obmxt7fyo9P2bRvyTuLg5x833RjJVecDFaVj4A8Iacwa18NaWrjo7Wyuw/FgTQBnt8S9Fu5DDoNvqOvzhtpXTrVmjU/7UrbUA991cH4sv8AxRr+qjS/FlwPB+gSFCgEP2qO5JP3JZ1OxeeoJA5Gc9a9Jvbrxfps0gstH0vVLTP7kJdtayKPQqysp9Mgj6CsnUo/HnifT59MfStF0Wzuo2guJLi5a8k2MMEoqqq5wf4jigDN8ReGV0u1tVOl6x4z1GdiIIbm48uzh2gcsi7Yo1weBtOcY96Sx+G2ra6sT+NdUQWK8x6BpIMFnGOwYjBf+h7kV6JpenxaTpNnpsDO0NpAkEbSHLFVUKMnucCrdAGPqE+n+EPCl5dW9rDb2WnWzyrBEoRflBOAB3J/U1ieFfDUy/C6HSbm5nt73ULV5bu4TAkWWfLOee4LEfhW54k8O2finR20q/eYWjyxySpEwXzAjBtp4PykgZxz71r0AeGaHYaFa+NYbHQNLm1L/hHSY1Maq091dhdpeWVsCOGMZUDIBYnaG216L4J8Sav4juNZe/tLGKztLkW9tNZytIsjAHzBuYDdtOBuAAJzjOM1T8RzefqDeDfDEcVnf6gDcaneW6BPskLHDSEjrK/Re/8AEcYzXX6Xplno2l22m6fAsFpbRiOKNewH8z3J7nmgC3RRRQAUUUUAFFFFABRRRQAVm+Ibuaw8N6neWz7J4LWSSNsA4YKSDg8daKKAM3wRo1rpfh6C5iMkt5qKLd3l1M26WeR1BJY+gzgAcAV0lFFABRRRQB//2Q==\" width=\"90\" height=\"52\"><span style=\"font-family: 宋体; font-size: 14px;\">/</span><span style=\"font-family: 宋体; font-size: 14px;\">孙宪平</span><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n<hr></hr>\r\n<table width=\"678\" height=\"21\">\r\n<tr style=\"display:none\">\r\n<td width=\"226\">&nbsp;</td>\r\n<td width=\"226\">&nbsp;</td>\r\n<td width=\"226\">&nbsp;</td>\r\n</tr>\r\n<tr>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 16px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n</tr>\r\n</table>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n<table  height=\"40\" align=\"center\">\r\n<tr><td>\r\n</td></tr>\r\n</table>\r\n</td></tr>\r\n</table>\r\n</td></tr>\r\n</table>\r\n</body>\r\n</html>\r\n"
        },
        {
            "mr_code": "EMR10.00.03_44",
            "topic": "姜亮主任医师、李彦主治医师、胡攀攀住院总医师常规查房记录",
            "mr_content": "<html>\r\n<head>\r\n<title>北　京　大　学　第　三　医　院</title>\r\n<style type=\"text/css\">\r\n.table1 {\r\nBORDER-RIGHT: #000000 0px solid; BORDER-TOP: #000000 1px solid; BORDER-LEFT: #000000 1px solid; BORDER-BOTTOM: #000000 0px solid\r\n}\r\n.td1 {\r\n\tBORDER-RIGHT: #000000 1px solid; BORDER-TOP: #000000 0px solid; BORDER-LEFT: #000000 0px solid; BORDER-BOTTOM: #000000 1px solid\r\n}\r\n</style>\r\n</head>\r\n<body bgcolor=\"#005757\">\r\n<table width=\"794\" align=\"center\"  border=\"1\" cellspacing=\"0\" bordercolor=black  rules=none bgcolor=\"#FFFFFF\">\r\n<tr><td>\r\n<table width=\"669\" align=\"center\">\r\n<tr><td>\r\n<table  height=\"57\" align=\"center\">\r\n<tr><td>\r\n</td></tr>\r\n</table>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 18px;font-weight: bold;\">北　京　大　学　第　三　医　院</span></p>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 28px;font-weight: bold;\">&nbsp;病&nbsp;历&nbsp;记&nbsp;录&nbsp;</span><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n<table width=\"665\" height=\"21\">\r\n<tr style=\"display:none\">\r\n<td width=\"170\">&nbsp;</td>\r\n<td width=\"77\">&nbsp;</td>\r\n<td width=\"179\">&nbsp;</td>\r\n<td width=\"84\">&nbsp;</td>\r\n<td width=\"155\">&nbsp;</td>\r\n</tr>\r\n<tr>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">姓名:</span><span style=\"font-family: 宋体; font-size: 14px;\">刘欢</span></p>\r\n</td>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 14px;\">第&nbsp;</span>1\r\n<span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;页</span></p>\r\n</td>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p align=\"right\"><span style=\"font-family: 宋体; font-size: 14px;\">住院号:</span><span style=\"font-family: 宋体; font-size: 14px;\">5042725</span></p>\r\n</td>\r\n</tr>\r\n</table>\r\n<hr></hr>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;font-weight: bold;\">2018-12-05&nbsp;08:15</span><span style=\"font-family: 宋体; font-size: 14px;\">　　　　　</span><span style=\"font-family: 宋体; font-size: 14px;font-weight: bold;\">姜亮主任医师、李彦主治医师、胡攀攀住院总医师常规查房记录</span></p>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">今日患者</span><span style=\"font-family: 宋体; font-size: 14px;\">一般状态尚可，</span><span style=\"font-family: 宋体; font-size: 14px;\">神志</span><span style=\"font-family: 宋体; font-size: 14px;\">清</span><span style=\"font-family: 宋体; font-size: 14px;\">，精神</span><span style=\"font-family: 宋体; font-size: 14px;\">可</span><span style=\"font-family: 宋体; font-size: 14px;\">，睡眠、饮食情况尚可，二便如常。</span><span style=\"font-family: 宋体; font-size: 14px;\">查体</span><span style=\"font-family: 宋体; font-size: 14px;\">查体神志清，精神可，脊柱生理曲度尚可，胸椎棘突后侧无明显压痛，右下肢自腹股沟以远针刺觉减退，左下肢针刺觉正常。左侧髂腰肌肌力IV级，右侧髂腰肌肌力IV-级；双侧股四头肌肌力V级，左侧胫前肌力V级，右侧胫前肌肌力III级；左侧小腿三头肌肌力V级，右侧小腿三头肌肌力IV级；左侧拇背伸肌肌力V级，右侧拇背伸肌肌力III级。双侧膝腱反射亢进，双侧跟腱反射活跃，双侧Babinski征阳性，双侧Chaddock征阳性，左侧踝阵挛阳性，右侧踝阵挛可疑阳性。</span></p>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">姜亮主任医师、李彦主治医师、胡攀攀住院总医师</span><span style=\"font-family: 宋体; font-size: 14px;\">查房指示：拟今日下午行CT引导下穿刺活检术。</span></p>\r\n<p align=\"right\"><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span><img src=\"data:image/jpg;base64,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\" width=\"90\" height=\"52\"><span style=\"font-family: 宋体; font-size: 14px;\">/</span><span style=\"font-family: 宋体; font-size: 14px;\">孙宪平</span><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n<hr></hr>\r\n<table width=\"678\" height=\"21\">\r\n<tr style=\"display:none\">\r\n<td width=\"226\">&nbsp;</td>\r\n<td width=\"226\">&nbsp;</td>\r\n<td width=\"226\">&nbsp;</td>\r\n</tr>\r\n<tr>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 16px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n</tr>\r\n</table>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n<table  height=\"40\" align=\"center\">\r\n<tr><td>\r\n</td></tr>\r\n</table>\r\n</td></tr>\r\n</table>\r\n</td></tr>\r\n</table>\r\n</body>\r\n</html>\r\n"
        },
        {
            "mr_code": "EMR10.00.03_44",
            "topic": "姜亮主任医师、李彦主治医师、胡攀攀住院总医师常规查房记录",
            "mr_content": "<html>\r\n<head>\r\n<title>北　京　大　学　第　三　医　院</title>\r\n<style type=\"text/css\">\r\n.table1 {\r\nBORDER-RIGHT: #000000 0px solid; BORDER-TOP: #000000 1px solid; BORDER-LEFT: #000000 1px solid; BORDER-BOTTOM: #000000 0px solid\r\n}\r\n.td1 {\r\n\tBORDER-RIGHT: #000000 1px solid; BORDER-TOP: #000000 0px solid; BORDER-LEFT: #000000 0px solid; BORDER-BOTTOM: #000000 1px solid\r\n}\r\n</style>\r\n</head>\r\n<body bgcolor=\"#005757\">\r\n<table width=\"794\" align=\"center\"  border=\"1\" cellspacing=\"0\" bordercolor=black  rules=none bgcolor=\"#FFFFFF\">\r\n<tr><td>\r\n<table width=\"669\" align=\"center\">\r\n<tr><td>\r\n<table  height=\"57\" align=\"center\">\r\n<tr><td>\r\n</td></tr>\r\n</table>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 18px;font-weight: bold;\">北　京　大　学　第　三　医　院</span></p>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 28px;font-weight: bold;\">&nbsp;病&nbsp;历&nbsp;记&nbsp;录&nbsp;</span><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n<table width=\"665\" height=\"21\">\r\n<tr style=\"display:none\">\r\n<td width=\"170\">&nbsp;</td>\r\n<td width=\"77\">&nbsp;</td>\r\n<td width=\"179\">&nbsp;</td>\r\n<td width=\"84\">&nbsp;</td>\r\n<td width=\"155\">&nbsp;</td>\r\n</tr>\r\n<tr>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">姓名:</span><span style=\"font-family: 宋体; font-size: 14px;\">刘欢</span></p>\r\n</td>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 14px;\">第&nbsp;</span>1\r\n<span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;页</span></p>\r\n</td>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p align=\"right\"><span style=\"font-family: 宋体; font-size: 14px;\">住院号:</span><span style=\"font-family: 宋体; font-size: 14px;\">5042725</span></p>\r\n</td>\r\n</tr>\r\n</table>\r\n<hr></hr>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;font-weight: bold;\">2018-12-07&nbsp;08:09</span><span style=\"font-family: 宋体; font-size: 14px;\">　　　　　</span><span style=\"font-family: 宋体; font-size: 14px;font-weight: bold;\">姜亮主任医师、李彦主治医师、胡攀攀住院总医师常规查房记录</span></p>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">今日患者一般状态良好，神志清，精神可，睡眠、饮食情况尚可，略有咳嗽，二便如常。查体：右下肢自腹股沟以远针刺觉减退，左下肢针刺觉正常。左侧髂腰肌肌力IV级，右侧髂腰肌肌力IV-级；双侧股四头肌肌力V级，左侧胫前肌力V级，右侧胫前肌肌力III+级；左侧小腿三头肌肌力V级，右侧小腿三头肌肌力IV级；左侧拇背伸肌肌力V级，右侧拇背伸肌肌力III+级。双侧膝腱反射亢进，双侧跟腱反射活跃，双侧Babinski征阳性，双侧Chaddock征阳性，左侧踝阵挛阳性，右侧踝阵挛可疑阳性。</span></p>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">2018-12-05CT引导下胸椎病变穿刺活检(增强),&nbsp;患者CT增强扫描后穿刺前观察病变情况有变化，经与患者家属及病房主管医生沟通后中止手术，观察患者CT增强后无不适，患者在家属及管床医生陪同下安返病房，调整诊疗方案计划。</span></p>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">姜亮主任医师、李彦主治医师、胡攀攀住院总医师查房指示：病人未能穿刺成功，继续对症治疗，拟择期手术。</span></p>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n<p align=\"right\"><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span><img src=\"data:image/jpg;base64,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\" width=\"90\" height=\"52\"><span style=\"font-family: 宋体; font-size: 14px;\">/</span><span style=\"font-family: 宋体; font-size: 14px;\">孙宪平</span><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n<hr></hr>\r\n<table width=\"678\" height=\"21\">\r\n<tr style=\"display:none\">\r\n<td width=\"226\">&nbsp;</td>\r\n<td width=\"226\">&nbsp;</td>\r\n<td width=\"226\">&nbsp;</td>\r\n</tr>\r\n<tr>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 16px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n</tr>\r\n</table>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n<table  height=\"40\" align=\"center\">\r\n<tr><td>\r\n</td></tr>\r\n</table>\r\n</td></tr>\r\n</table>\r\n</td></tr>\r\n</table>\r\n</body>\r\n</html>\r\n"
        },
        {
            "mr_code": "EMR10.00.03_44",
            "topic": "姜亮主任医师、李彦主治医师、胡攀攀住院总医师常规查房记录",
            "mr_content": "<html>\r\n<head>\r\n<title>北　京　大　学　第　三　医　院</title>\r\n<style type=\"text/css\">\r\n.table1 {\r\nBORDER-RIGHT: #000000 0px solid; BORDER-TOP: #000000 1px solid; BORDER-LEFT: #000000 1px solid; BORDER-BOTTOM: #000000 0px solid\r\n}\r\n.td1 {\r\n\tBORDER-RIGHT: #000000 1px solid; BORDER-TOP: #000000 0px solid; BORDER-LEFT: #000000 0px solid; BORDER-BOTTOM: #000000 1px solid\r\n}\r\n</style>\r\n</head>\r\n<body bgcolor=\"#005757\">\r\n<table width=\"794\" align=\"center\"  border=\"1\" cellspacing=\"0\" bordercolor=black  rules=none bgcolor=\"#FFFFFF\">\r\n<tr><td>\r\n<table width=\"669\" align=\"center\">\r\n<tr><td>\r\n<table  height=\"57\" align=\"center\">\r\n<tr><td>\r\n</td></tr>\r\n</table>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 18px;font-weight: bold;\">北　京　大　学　第　三　医　院</span></p>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 28px;font-weight: bold;\">&nbsp;病&nbsp;历&nbsp;记&nbsp;录&nbsp;</span><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n<table width=\"665\" height=\"21\">\r\n<tr style=\"display:none\">\r\n<td width=\"170\">&nbsp;</td>\r\n<td width=\"77\">&nbsp;</td>\r\n<td width=\"179\">&nbsp;</td>\r\n<td width=\"84\">&nbsp;</td>\r\n<td width=\"155\">&nbsp;</td>\r\n</tr>\r\n<tr>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">姓名:</span><span style=\"font-family: 宋体; font-size: 14px;\">刘欢</span></p>\r\n</td>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 14px;\">第&nbsp;</span>1\r\n<span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;页</span></p>\r\n</td>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p align=\"right\"><span style=\"font-family: 宋体; font-size: 14px;\">住院号:</span><span style=\"font-family: 宋体; font-size: 14px;\">5042725</span></p>\r\n</td>\r\n</tr>\r\n</table>\r\n<hr></hr>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;font-weight: bold;\">2018-12-09&nbsp;08:14</span><span style=\"font-family: 宋体; font-size: 14px;\">　　　　　</span><span style=\"font-family: 宋体; font-size: 14px;font-weight: bold;\">姜亮主任医师、李彦主治医师、胡攀攀住院总医师常规查房记录</span></p>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">今日患者一般状态良好，神清语利，神志清，精神可，睡眠、饮食情况尚可，二便如常。查体：右下肢自腹股沟以远针刺觉减退，左侧髂腰肌肌力IV级，右侧髂腰肌肌力IV-级；双侧股四头肌肌力V级，左侧胫前肌力V级，右侧胫前肌肌力III+级；左侧小腿三头肌肌力V级，右侧小腿三头肌肌力IV级；左侧拇背伸肌肌力V级，右侧拇背伸肌肌力III+级。</span></p>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">姜亮主任医师、李彦主治医师、胡攀攀住院总医师</span><span style=\"font-family: 宋体; font-size: 14px;\">查房指示：继续观察、对症治疗，拟择期手术。</span></p>\r\n<p align=\"right\"><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span><img src=\"data:image/jpg;base64,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\" width=\"90\" height=\"52\"><span style=\"font-family: 宋体; font-size: 14px;\">/</span><span style=\"font-family: 宋体; font-size: 14px;\">孙宪平</span><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n<hr></hr>\r\n<table width=\"678\" height=\"21\">\r\n<tr style=\"display:none\">\r\n<td width=\"226\">&nbsp;</td>\r\n<td width=\"226\">&nbsp;</td>\r\n<td width=\"226\">&nbsp;</td>\r\n</tr>\r\n<tr>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 16px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n</tr>\r\n</table>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n<table  height=\"40\" align=\"center\">\r\n<tr><td>\r\n</td></tr>\r\n</table>\r\n</td></tr>\r\n</table>\r\n</td></tr>\r\n</table>\r\n</body>\r\n</html>\r\n"
        },
        {
            "mr_code": "EMR10.00.03_44",
            "topic": "姜亮主任医师、李彦主治医师、胡攀攀住院总医师常规查房记录",
            "mr_content": "<html>\r\n<head>\r\n<title>北　京　大　学　第　三　医　院</title>\r\n<style type=\"text/css\">\r\n.table1 {\r\nBORDER-RIGHT: #000000 0px solid; BORDER-TOP: #000000 1px solid; BORDER-LEFT: #000000 1px solid; BORDER-BOTTOM: #000000 0px solid\r\n}\r\n.td1 {\r\n\tBORDER-RIGHT: #000000 1px solid; BORDER-TOP: #000000 0px solid; BORDER-LEFT: #000000 0px solid; BORDER-BOTTOM: #000000 1px solid\r\n}\r\n</style>\r\n</head>\r\n<body bgcolor=\"#005757\">\r\n<table width=\"794\" align=\"center\"  border=\"1\" cellspacing=\"0\" bordercolor=black  rules=none bgcolor=\"#FFFFFF\">\r\n<tr><td>\r\n<table width=\"669\" align=\"center\">\r\n<tr><td>\r\n<table  height=\"57\" align=\"center\">\r\n<tr><td>\r\n</td></tr>\r\n</table>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 18px;font-weight: bold;\">北　京　大　学　第　三　医　院</span></p>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 28px;font-weight: bold;\">&nbsp;病&nbsp;历&nbsp;记&nbsp;录&nbsp;</span><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n<table width=\"665\" height=\"21\">\r\n<tr style=\"display:none\">\r\n<td width=\"170\">&nbsp;</td>\r\n<td width=\"77\">&nbsp;</td>\r\n<td width=\"179\">&nbsp;</td>\r\n<td width=\"84\">&nbsp;</td>\r\n<td width=\"155\">&nbsp;</td>\r\n</tr>\r\n<tr>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">姓名:</span><span style=\"font-family: 宋体; font-size: 14px;\">刘欢</span></p>\r\n</td>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 14px;\">第&nbsp;</span>1\r\n<span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;页</span></p>\r\n</td>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p align=\"right\"><span style=\"font-family: 宋体; font-size: 14px;\">住院号:</span><span style=\"font-family: 宋体; font-size: 14px;\">5042725</span></p>\r\n</td>\r\n</tr>\r\n</table>\r\n<hr></hr>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;font-weight: bold;\">2018-12-11&nbsp;08:09</span><span style=\"font-family: 宋体; font-size: 14px;\">　　　　　</span><span style=\"font-family: 宋体; font-size: 14px;font-weight: bold;\">姜亮主任医师、李彦主治医师、胡攀攀住院总医师常规查房记录</span></p>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">今日患者一般状态尚可，神清语利，精神可，生命体征平稳，睡眠、饮食情况尚可，二便如常。查体：右下肢自腹股沟以远针刺觉减退，左侧髂腰肌肌力IV级，右侧髂腰肌肌力IV-级；双侧股四头肌肌力V级，左侧胫前肌力V级，右侧胫前肌肌力III+级；左侧小腿三头肌肌力V级，右侧小腿三头肌肌力IV级；左侧拇背伸肌肌力V级，右侧拇背伸肌肌力IV级。</span></p>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">姜亮主任医师、李彦主治医师、胡攀攀住院总医师</span><span style=\"font-family: 宋体; font-size: 14px;\">查房指示：今日行椎体肿瘤供应血管栓塞术，完善术前准备，拟明日手术。</span></p>\r\n<p align=\"right\"><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span><img src=\"data:image/jpg;base64,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\" width=\"90\" height=\"52\"><span style=\"font-family: 宋体; font-size: 14px;\">/</span><span style=\"font-family: 宋体; font-size: 14px;\">孙宪平</span><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n<hr></hr>\r\n<table width=\"678\" height=\"21\">\r\n<tr style=\"display:none\">\r\n<td width=\"226\">&nbsp;</td>\r\n<td width=\"226\">&nbsp;</td>\r\n<td width=\"226\">&nbsp;</td>\r\n</tr>\r\n<tr>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 16px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n</tr>\r\n</table>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n<table  height=\"40\" align=\"center\">\r\n<tr><td>\r\n</td></tr>\r\n</table>\r\n</td></tr>\r\n</table>\r\n</td></tr>\r\n</table>\r\n</body>\r\n</html>\r\n"
        }
    ]
    x = {
            "mr_class_code": "EMR10.00.03",
            "topic": "姜亮主任医师、李彦主治医师、胡攀攀住院总医师常规查房记录",
            "mr_content_html": "<html>\r\n<head>\r\n<title>北　京　大　学　第　三　医　院</title>\r\n<style type=\"text/css\">\r\n.table1 {\r\nBORDER-RIGHT: #000000 0px solid; BORDER-TOP: #000000 1px solid; BORDER-LEFT: #000000 1px solid; BORDER-BOTTOM: #000000 0px solid\r\n}\r\n.td1 {\r\n\tBORDER-RIGHT: #000000 1px solid; BORDER-TOP: #000000 0px solid; BORDER-LEFT: #000000 0px solid; BORDER-BOTTOM: #000000 1px solid\r\n}\r\n</style>\r\n</head>\r\n<body bgcolor=\"#005757\">\r\n<table width=\"794\" align=\"center\"  border=\"1\" cellspacing=\"0\" bordercolor=black  rules=none bgcolor=\"#FFFFFF\">\r\n<tr><td>\r\n<table width=\"669\" align=\"center\">\r\n<tr><td>\r\n<table  height=\"57\" align=\"center\">\r\n<tr><td>\r\n</td></tr>\r\n</table>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 18px;font-weight: bold;\">北　京　大　学　第　三　医　院</span></p>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 28px;font-weight: bold;\">&nbsp;病&nbsp;历&nbsp;记&nbsp;录&nbsp;</span><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n<table width=\"665\" height=\"21\">\r\n<tr style=\"display:none\">\r\n<td width=\"170\">&nbsp;</td>\r\n<td width=\"77\">&nbsp;</td>\r\n<td width=\"179\">&nbsp;</td>\r\n<td width=\"84\">&nbsp;</td>\r\n<td width=\"155\">&nbsp;</td>\r\n</tr>\r\n<tr>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">姓名:</span><span style=\"font-family: 宋体; font-size: 14px;\">刘欢</span></p>\r\n</td>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 14px;\">第&nbsp;</span>1\r\n<span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;页</span></p>\r\n</td>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p align=\"right\"><span style=\"font-family: 宋体; font-size: 14px;\">住院号:</span><span style=\"font-family: 宋体; font-size: 14px;\">5042725</span></p>\r\n</td>\r\n</tr>\r\n</table>\r\n<hr></hr>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;font-weight: bold;\">2018-12-11&nbsp;08:09</span><span style=\"font-family: 宋体; font-size: 14px;\">　　　　　</span><span style=\"font-family: 宋体; font-size: 14px;font-weight: bold;\">姜亮主任医师、李彦主治医师、胡攀攀住院总医师常规查房记录</span></p>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">今日患者一般状态尚可，神清语利，精神可，生命体征平稳，睡眠、饮食情况尚可，二便如常。查体：右下肢自腹股沟以远针刺觉减退，左侧髂腰肌肌力IV级，右侧髂腰肌肌力IV-级；双侧股四头肌肌力V级，左侧胫前肌力V级，右侧胫前肌肌力III+级；左侧小腿三头肌肌力V级，右侧小腿三头肌肌力IV级；左侧拇背伸肌肌力V级，右侧拇背伸肌肌力IV级。</span></p>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">姜亮主任医师、李彦主治医师、胡攀攀住院总医师</span><span style=\"font-family: 宋体; font-size: 14px;\">查房指示：今日行椎体肿瘤供应血管栓塞术，完善术前准备，拟明日手术。</span></p>\r\n<p align=\"right\"><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span><img src=\"data:image/jpg;base64,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\" width=\"90\" height=\"52\"><span style=\"font-family: 宋体; font-size: 14px;\">/</span><span style=\"font-family: 宋体; font-size: 14px;\">孙宪平</span><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n<hr></hr>\r\n<table width=\"678\" height=\"21\">\r\n<tr style=\"display:none\">\r\n<td width=\"226\">&nbsp;</td>\r\n<td width=\"226\">&nbsp;</td>\r\n<td width=\"226\">&nbsp;</td>\r\n</tr>\r\n<tr>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p align=\"center\"><span style=\"font-family: 宋体; font-size: 16px;\">&nbsp;</span></p>\r\n</td>\r\n<td>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n</td>\r\n</tr>\r\n</table>\r\n<p><span style=\"font-family: 宋体; font-size: 14px;\">&nbsp;</span></p>\r\n<table  height=\"40\" align=\"center\">\r\n<tr><td>\r\n</td></tr>\r\n</table>\r\n</td></tr>\r\n</table>\r\n</td></tr>\r\n</table>\r\n</body>\r\n</html>\r\n"
            # "mr_content": "1"
        }
    # r = app.processHtml(**x)
    r = app.process(ruyuanjilu)
    # r = app.segment('现病史', "患者40天前无明显诱因出现咳嗽，咳白痰，痰中带血丝，痰易咳出，晨起为重，无发热、盗汗、呼吸困难、胸痛等不适，未重视。半月前于体检时行胸部CT示：右侧肺门旁及右肺下叶占位，右肺中叶局部阻塞性不张，右肺下叶间质性改变，纵隔内多发淋巴结显示。后为明确病变性质，就诊于中国科学院肿瘤医院，行气管镜检查，检查过程中患者出现胸闷、心悸，查心电图示心房颤动，遂中止检查。2天前就诊于北京安贞医院，行心电图仍为房颤，查超声心动图示：左室运动不协调，左房增大，升主动脉增宽，三尖瓣及主动脉瓣轻度返流。予普罗帕酮治疗。现为再次明确肺内病变性质收入我院。患者自发病以来精神、睡眠、饮食可，二便如常，体重较前无明显改变。")
    print(json.dumps(r, ensure_ascii=False, indent=2))
