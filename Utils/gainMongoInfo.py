#!/usr/bin/env python3
# -*- coding:utf-8 -*

"""
@version: 
@author:
@contact:
@software: PyCharm Community Edition
@file: gainMongoInfo.py
@time: 18-7-16 上午11:20
@description: 
"""
import os
import sys
cur_path = os.path.abspath(os.path.dirname(__file__))
root_path = os.path.split(cur_path)[0]
sys.path.append(root_path)  # 项目路径添加到系统路径
import re
import json
from Utils.MongoUtils import PullDataFromMDBUtils
from Utils.loadingConfigure import Properties
from Utils.loadRelationship import Tree
from Utils.loadSynonym import Synonym
from Utils.gainSynonym import GainSynonym
from Utils.LogUtils import LogUtils
from datetime import datetime


class GainMongoInfo(object):
    """
    抽取数据库信息，提供各种功能
    """
    # 是否初始化
    is_init = False

    def __init__(self):
        if not GainMongoInfo.is_init:
            self.logger = LogUtils().getLogger("root")
            self.mongo_app = PullDataFromMDBUtils()
            self.database_name = self.mongo_app.mongodb_database_name
            self.collection_name = self.mongo_app.mongodb_collection_name  # 要处理的 collection
            self.parameters = Properties()
            self.hospital_code = self.parameters.properties.get('hospital_code')
            self.conf_dict = self.parameters.conf_dict.copy()
            # self.configure_path = os.path.join(cur_path, 'configure/check_configure.xml')  # 配置文件地址
            self.jiangya_path = os.path.join(root_path, 'configure/dict/jiangyajiangxuetang.csv')  # 降压降血糖药
            self.collection_bingan = self.mongo_app.record_db.get_collection(name='binganshouye')
            self.wordtree = Tree()  # 上下级关系词表
            self.wordsynonym = Synonym().dict_info  # 同义词表
            self.synonym_app = GainSynonym()
            GainMongoInfo.is_init = True

    def __new__(cls, *args, **kwargs):
        """
        单例模式
        """
        if not hasattr(cls, 'instance'):
            cls.instance = super(GainMongoInfo, cls).__new__(cls)
        return cls.instance

    def _load_time(self, time_str):
        """
        根据时间的字符串，将时间转换为数值型
        返回 tuple, 若没有单位则返回长度为1的 tuple
        """
        re_filter = self.conf_dict['load_time']
        for i in re_filter:
            if i[0].findall(time_str):
                return i[1]
        ymd_pat = re.compile('\d{4}[/\-年.]\d{0,2}[/\-月.]?\d{0,2}日?')  # 先看是不是具体日期
        ymd_pat_2 = re.compile('\d{2}[/\-年.]\d{1,2}[/\-月.]\d{0,2}日?')  # 有日期为 13-01-19
        ymd_pat_3 = re.compile('\d{1,2}(?:月)\d{1,2}日?')  # 2月28日
        if ymd_pat.findall(time_str):
            return ymd_pat.findall(time_str)[0], '具体日期'
        elif ymd_pat_2.findall(time_str):
            return '20' + (ymd_pat_2.findall(time_str)[0]), '具体日期'
        elif ymd_pat_3.findall(time_str):
            return ymd_pat_3.findall(time_str)[0], '具体日期'
        ymd_pat_time = re.compile('\d{1,2}:\d{1,2}(?::\d{1,2})?')  # 再看是不是具体时间
        if ymd_pat_time.findall(time_str):
            return ymd_pat_time.findall(time_str)[0],

        time_str = re.compile('\d*\d-').sub('', time_str)  # 4-5 只取5
        if not self._find_time_unit(time_str):  # 没有时间单位，只有数字
            if re.search('\d+\.\d*', time_str):  # 小数
                return float(re.search('\d+\.\d*', time_str).group()),
            elif re.search('\d+', time_str):  # 整数
                return int(re.search('\d+', time_str).group()),
            elif re.search('[一二两三四五六七八九十百千万亿零]+', time_str):
                return self._numStr_2_int(time_str),

        time_str = time_str.replace('个', '')

        time_num = None
        num = None
        sign = []
        for char in time_str:
            if re.compile('[一二两三四五六七八九十百千万亿零|\d]').findall(char):
                sign.append(True)
            else:
                sign.append(False)
        if True in sign:
            str_num = ''
            tmp = []  # 数字
            sub_str = []  # 其它字符
            for i, s in enumerate(sign):
                if s:
                    str_num += time_str[i]
                    sub_str.append('')
                if not s and str_num:
                    tmp.append(str_num)
                    str_num = ''
                    sub_str.append(time_str[i])
                elif not s:
                    sub_str.append(time_str[i])
            for i in range(1, len(sub_str)):
                if sub_str[i] == '':
                    if sub_str[i - 1] in ['', '#']:
                        sub_str[i] = '#'
            sub_str = [i for i in sub_str if i != '#']
            count = 0
            for i in range(len(sub_str)):
                if sub_str[i] == '':
                    if re.compile('\d').findall(tmp[count]):
                        sub_str[i] = tmp[count]
                    else:
                        sub_str[i] = str(self._numStr_2_int(tmp[count]))
                    count += 1
            right_type = ''.join(sub_str)
        else:
            right_type = time_str
        if re.compile('\\d+年\\d+半?月').findall(right_type):
            find = re.compile('\\d+\\.\\d|\\d+').findall(right_type)
            num = int(find[0]) * 12 + int(find[1])
            if num or num == 0:
                time_num = num
            if '半' in time_str:
                if isinstance(time_num, int):
                    time_num += 0.5
                else:
                    time_num = 0.5
            return time_num, '月'

        num_list = re.compile('\\d+\\.\\d|\\d+').findall(right_type)
        if num_list:
            try:
                num = int(num_list[0])
            except ValueError:
                num = float(num_list[0])
        if num or num == 0:
            time_num = num
        if '半' in time_str:
            if isinstance(time_num, int):
                time_num += 0.5
            else:
                time_num = 0.5
        unit = self._find_time_unit(right_type)
        if time_num or time_num == 0:
            return time_num, unit
        return time_str,  # 处理不成功返回原值

    @staticmethod
    def _find_time_unit(strings):
        """
        找到时间中的时间单位信息
        :param strings:
        :return:
        """
        time_units = {'周期', '年', '月', '周', '天', '日', '小时', '分钟', '秒', 'min'}
        time_unit = ''
        for timeunit in time_units:
            if timeunit in strings:
                time_unit = timeunit
                break
        return time_unit

    @staticmethod
    def _numStr_2_int(string):
        """
        将汉字数字转换成阿拉伯数字
        :param string: str or unicode，汉字数字
        :return: int
        """
        tmp_list = list(string)
        for i in tmp_list:
            if i not in ['一', '二', '两', '三', '四', '五', '六', '七',
                         '八', '九', '十', '百', '千', '万', '亿', '零']:
                return None
        trans_dict = {'一': 1, '二': 2, '两': 2, '三': 3,
                      '四': 4, '五': 5, '六': 6, '七': 7,
                      '八': 8, '九': 9, '十': 10, '百': 100,
                      '千': 1000, '万': 10000, '亿': 100000000}
        for i in range(len(tmp_list)):
            if tmp_list[i] in trans_dict:
                tmp_list[i] = trans_dict[tmp_list[i]]
        tmp_list = [i for i in tmp_list if isinstance(i, int)]
        formula = '0'
        for i in tmp_list:
            if i < 10:
                formula += '+' + str(i)
            elif i == 10 and tmp_list[0] == 10:
                formula += '+1*' + str(i)
            else:
                formula += '*' + str(i)
        return eval(formula)

    def _calc_time(self, input_date, file_time):
        res = set()
        file_date = datetime.strptime(file_time[:10], '%Y-%m-%d')
        try:
            if re.search('\d{4}年$', input_date):
                x = datetime.strptime(input_date, '%Y年')
            elif re.search('\d{4}年\d{1,2}月$', input_date):
                x = datetime.strptime(input_date, '%Y年%m月')
            elif re.search('\d{4}年\d{1,2}月\d{1,2}日$', input_date):
                x = datetime.strptime(input_date, '%Y年%m月%d日')
            elif re.search('\d{4}\.\d{1,2}$', input_date):
                x = datetime.strptime(input_date, '%Y.%m')
            elif re.search('\d{4}\.\d{1,2}\.\d{1,2}$', input_date):
                x = datetime.strptime(input_date, '%Y.%m.%d')
            elif re.search('\d{4}-\d{1,2}-\d{1,2}$', input_date):
                x = datetime.strptime(input_date, '%Y-%m-%d')
            elif re.search('\d{4}/\d{1,2}/\d{1,2}$', input_date):
                x = datetime.strptime(input_date, '%Y/%m/%d')
            else:
                res.add((input_date, '具体日期'))
                return res
            days = (file_date - x).days
            res.add((days, '天'))
            res.add((days, '日'))
            if days // 30:
                res.add((days // 30, '月'))
            if days // 365:
                res.add((days // 365, '年'))
                res.add(((days // 365)*12, '月'))
        except:
            self.logger.error(input_date)
            res.add((input_date, '具体日期'))
            return res
        return res

    @staticmethod
    def _gain_file_time(cursor, collection_name):
        """
        获取文书修改时间
        :param cursor: mongo 游标
        :return: str
        """
        file_time = ''
        if collection_name in cursor and 'last_modify_date_time' in cursor[collection_name]:
            file_time = cursor[collection_name]['last_modify_date_time']
        if not file_time.strip():
            file_time = '无文书时间'
        return file_time

    @staticmethod
    def _gain_file_creator(cursor, collection_name):
        if collection_name in cursor and 'creator_name' in cursor[collection_name]:
            creator_name = cursor[collection_name]['creator_name']
        else:
            creator_name = ''
        return creator_name

    @staticmethod
    def _gain_src(cursor, collection_name, chapter_name):
        """
        获取章节 src
        :param chapter_name:
        :return:
        """
        if collection_name in cursor:
            if chapter_name in cursor[collection_name]:
                if 'src' in cursor[collection_name][chapter_name]:
                    return cursor[collection_name][chapter_name]['src']
        return '章节无src'

    def _gain_symptom_time(self, symptom_model):
        """
        在症状模型中，获取一个主症状、其所有伴随症状和部位+主症状的时间，并将伴随症状的时间加到该主症状中
        :return:  {症状: 时间集合}
        """
        symptom_time = dict()
        # flag = False  # 是否有  <发生时间/持续时间> 标记
        # 如果 <主症状> 存在，获取 <主症状>
        if 'symptom_name' in symptom_model:
            main_symptom = symptom_model['symptom_name']
            symptom_time[main_symptom] = set()
            # 获取 <主症状> 下的 <发生时间/持续时间>
            if 'duration_of_symptom' in symptom_model:
                # flag = True
                # 如果时间为 str
                if isinstance(symptom_model['duration_of_symptom'], str):
                    duration_of_symptom = self._load_time(symptom_model['duration_of_symptom'])
                else:
                    duration_of_symptom = symptom_model['duration_of_symptom'],
                if len(duration_of_symptom) == 1:
                    duration_of_symptom = duration_of_symptom[0]
                    if 'duration_of_symptom_unit' in symptom_model:
                        symptom_time[main_symptom].add((duration_of_symptom,
                                                        symptom_model['duration_of_symptom_unit']))
                        if symptom_model['duration_of_symptom_unit'] == '年':
                            symptom_time[main_symptom].add((int(duration_of_symptom*12), '月'))
                        elif symptom_model['duration_of_symptom_unit'] == '月' and duration_of_symptom == 0.5:
                            symptom_time[main_symptom].add((2, '周'))
                        elif symptom_model['duration_of_symptom_unit'] == '日':
                            symptom_time[main_symptom].add((duration_of_symptom, '天'))
                    else:
                        symptom_time[main_symptom].add((duration_of_symptom,))
                else:
                    symptom_time[main_symptom].add(duration_of_symptom)
                    if duration_of_symptom[1] == '年':
                        symptom_time[main_symptom].add((int(duration_of_symptom[0]*12), '月'))
                    elif duration_of_symptom[1] == '月' and duration_of_symptom[0] == 0.5:
                        symptom_time[main_symptom].add((2, '周'))
                    elif duration_of_symptom[1] == '日':
                        symptom_time[main_symptom].add((duration_of_symptom[0], '天'))

            if 'duration_of_aggravation' in symptom_model:  # 加重时间
                # flag = True
                # 如果时间为 str
                # symptom_time.setdefault('加重症状', set())
                # symptom_time['加重症状'].add(main_symptom)
                if isinstance(symptom_model['duration_of_aggravation'], str):
                    duration_of_aggravation = self._load_time(symptom_model['duration_of_aggravation'])
                else:
                    duration_of_aggravation = symptom_model['duration_of_aggravation'],
                if len(duration_of_aggravation) == 1:
                    duration_of_aggravation = duration_of_aggravation[0]
                    if 'duration_of_aggravation_unit' in symptom_model:
                        symptom_time[main_symptom].add((duration_of_aggravation,
                                                        symptom_model['duration_of_aggravation_unit']))
                        if symptom_model['duration_of_aggravation_unit'] == '年':
                            symptom_time[main_symptom].add((int(duration_of_aggravation*12), '月'))
                        elif symptom_model['duration_of_aggravation_unit'] == '月' and duration_of_aggravation == 0.5:
                            symptom_time[main_symptom].add((2, '周'))
                        elif symptom_model['duration_of_aggravation_unit'] == '日':
                            symptom_time[main_symptom].add((duration_of_aggravation, '天'))
                    else:
                        symptom_time[main_symptom].add((duration_of_aggravation,))
                else:
                    symptom_time[main_symptom].add(duration_of_aggravation)
                    if duration_of_aggravation[1] == '年':
                        symptom_time[main_symptom].add((int(duration_of_aggravation[0]*12), '月'))
                    elif duration_of_aggravation[1] == '月' and duration_of_aggravation[0] == 0.5:
                        symptom_time[main_symptom].add((2, '周'))
                    elif duration_of_aggravation[1] == '日':
                        symptom_time[main_symptom].add((duration_of_aggravation[0], '天'))

            if 'duration_of_recurrence' in symptom_model:  # 加重时间
                # flag = True
                # 如果时间为 str
                if isinstance(symptom_model['duration_of_recurrence'], str):
                    duration_of_recurrence = self._load_time(symptom_model['duration_of_recurrence'])
                else:
                    duration_of_recurrence = symptom_model['duration_of_recurrence'],
                if len(duration_of_recurrence) == 1:
                    duration_of_recurrence = duration_of_recurrence[0]
                    if 'duration_of_recurrence_unit' in symptom_model:
                        symptom_time[main_symptom].add((duration_of_recurrence,
                                                        symptom_model['duration_of_recurrence_unit']))
                        if symptom_model['duration_of_recurrence_unit'] == '年':
                            symptom_time[main_symptom].add((int(duration_of_recurrence*12), '月'))
                        elif symptom_model['duration_of_recurrence_unit'] == '月' and duration_of_recurrence == 0.5:
                            symptom_time[main_symptom].add((2, '周'))
                        elif symptom_model['duration_of_recurrence_unit'] == '日':
                            symptom_time[main_symptom].add((duration_of_recurrence, '天'))
                    else:
                        symptom_time[main_symptom].add((duration_of_recurrence,))
                else:
                    symptom_time[main_symptom].add(duration_of_recurrence)
                    if duration_of_recurrence[1] == '年':
                        symptom_time[main_symptom].add((int(duration_of_recurrence[0]*12), '月'))
                    elif duration_of_recurrence[1] == '月' and duration_of_recurrence[0] == 0.5:
                        symptom_time[main_symptom].add((2, '周'))
                    elif duration_of_recurrence[1] == '日':
                        symptom_time[main_symptom].add((duration_of_recurrence[0], '天'))

            if 'occurrence_time_of_symptom'in symptom_model:
                symptom_time[main_symptom].add((symptom_model['occurrence_time_of_symptom'],))
                # flag = True
        # 若 <主症状> 不存在，作 False 标记
        else:
            main_symptom = False
        # 如果有 <伴随症状>
        if 'accompany_symptoms' in symptom_model:
            for acc_symptoms_model in symptom_model['accompany_symptoms']:

                # 如果 <伴随症状> 存在，获取 <伴随症状>
                if 'symptom_name' in acc_symptoms_model:
                    acc_symptoms = acc_symptoms_model['symptom_name']
                    symptom_time[acc_symptoms] = set()

                    # 获取 <伴随症状> 下的 <持续时间>，同时给主症状
                    #  <伴随症状> 下只有 <持续时间>
                    if 'duration_of_symptom' in acc_symptoms_model:
                        # flag = True

                        # 如果时间为 str
                        if isinstance(acc_symptoms_model['duration_of_symptom'], str):
                            acc_duration_of_symptom = re.compile('\d*\d-').sub('', acc_symptoms_model['duration_of_symptom'])
                            try:
                                acc_duration_of_symptom = int(acc_duration_of_symptom)
                            except ValueError:
                                acc_duration_of_symptom = float(acc_duration_of_symptom)
                        else:
                            acc_duration_of_symptom = acc_symptoms_model['duration_of_symptom']

                        if 'duration_of_symptom_unit' in acc_symptoms_model:
                            symptom_time[acc_symptoms].add((acc_duration_of_symptom,
                                                            acc_symptoms_model['duration_of_symptom_unit']))
                            if acc_symptoms_model['duration_of_symptom_unit'] == '年':
                                symptom_time[acc_symptoms].add((int(acc_duration_of_symptom*12), '月'))
                            elif acc_symptoms_model['duration_of_symptom_unit'] == '月' and acc_duration_of_symptom == 0.5:
                                symptom_time[main_symptom].add((2, '周'))
                            elif acc_symptoms_model['duration_of_symptom_unit'] == '日':
                                symptom_time[acc_symptoms].add((acc_duration_of_symptom, '天'))
                        else:
                            symptom_time[acc_symptoms].add((acc_duration_of_symptom,))
                    # 将 <伴随症状> 下的 <发生时间/持续时间> 加到主症状
                    if main_symptom:
                        symptom_time[main_symptom].update(symptom_time[acc_symptoms])
                # 如果 <伴随症状> 不存在，下一循环
                else:
                    continue
        # 如果 <主症状> 中有 <部位>
        if main_symptom and 'part' in symptom_model:
            part_name = ''
            for part in symptom_model['part']:
                part_name += part['part_name']
                if '左' in part_name or '右' in part_name:
                    symptom_time[main_symptom].add((part_name, '部位'))
            part_symptom = part_name + main_symptom
            symptom_time[part_symptom] = symptom_time[main_symptom]
        return symptom_time

    def _check_chief_symptom(self, symptom_model):
        """
        检查一个病历文书的症状模型时间
        :return: chief_time -- {'症状/伴随症状': {(时间, 单位)}}
        """
        chief_time = dict()
        # flag = False
        for i_s in symptom_model:
            chief_symptom = self._gain_symptom_time(i_s)
            # if one_flag:
            #     flag = True
            # chief_time 保存该次病历文书的所有症状时间
            for k, v in chief_symptom.items():
                if k not in chief_time:
                    chief_time[k] = v
                else:
                    chief_time[k].update(v)
        return chief_time

    @staticmethod
    def _gain_sign_time(sign_model):
        """
        检查一个病历文书的体征
        """
        sign_time = dict()
        # flag = False
        if 'sign_name' not in sign_model:
            return sign_time
        else:
            sign_name = sign_model['sign_name']
            if 'time' in sign_model:
                # flag = True
                t = sign_model['time']
                if 'time_unit' in sign_model:
                    t_unit = sign_model['time_unit']
                    sign_time[sign_name] = {(t, t_unit)}
                    if t_unit == '年':
                        sign_time[sign_name].add((int(t*12), '月'))
                    elif t_unit == '月' and t == 0.5:
                        sign_time[sign_name].add((2, '周'))
                    elif t_unit == '日':
                        sign_time[sign_name].add((t, '天'))
                else:
                    sign_time[sign_name] = {(t,)}
        return sign_time

    def _gain_disease_time(self, disease_model):
        """
        检查一个病历文书的主诉体征
        """
        disease_time = dict()

        for dis in disease_model:
            # 疾病模型
            if 'disease_name' in dis:
                disease_time.setdefault(dis['disease_name'], set())
                if 'disease_time' in dis:
                    disease_time[dis['disease_name']].add((dis['disease_time'],))
                if 'duration_of_illness' in dis:
                    if isinstance(dis['duration_of_illness'], str):
                        duration_of_illness = re.compile('\d*\d-').sub('', dis['duration_of_illness'])
                        try:
                            duration_of_illness = int(duration_of_illness)
                        except ValueError:
                            duration_of_illness = float(duration_of_illness)
                    else:
                        duration_of_illness = dis['duration_of_illness']
                    if 'duration_of_illness_unit' in dis:
                        disease_time[dis['disease_name']].add((duration_of_illness, dis['duration_of_illness_unit']))
                        if dis['duration_of_illness_unit'] == '年':
                            disease_time[dis['disease_name']].add((int(duration_of_illness*12), '月'))
                        elif dis['duration_of_illness_unit'] == '月' and duration_of_illness == 0.5:
                            disease_time[dis['disease_name']].add((2, '周'))
                        elif dis['duration_of_illness_unit'] == '日':
                            disease_time[dis['disease_name']].add((duration_of_illness, '天'))
                    else:
                        disease_time[dis['disease_name']].add((duration_of_illness,))

            # 症状模型
            if 'symptom' in dis:
                for symptom_model in dis['symptom']:
                    dis_symptom = self._gain_symptom_time(symptom_model)

                    for k, v in dis_symptom.items():
                        if k not in disease_time:
                            disease_time[k] = v
                        else:
                            disease_time[k].update(v)
                        if 'disease_name' in dis:
                            disease_time[k].update(disease_time[dis['disease_name']])

            if 'accompany_symptoms' in dis:
                for acc_sym in dis['accompany_symptoms']:
                    if 'symptom_name' in acc_sym:
                        acc_symptom_name = acc_sym['symptom_name']
                        disease_time.setdefault(acc_symptom_name, set())
                        if 'duration_of_symptom' in acc_sym:
                            if isinstance(acc_sym['duration_of_symptom'], str):
                                acc_duration_of_symptom = re.compile('\d*\d-').sub('', acc_sym['duration_of_symptom'])
                                try:
                                    acc_duration_of_symptom = int(acc_duration_of_symptom)
                                except ValueError:
                                    acc_duration_of_symptom = float(acc_duration_of_symptom)
                            else:
                                acc_duration_of_symptom = acc_sym['duration_of_symptom']

                            if 'duration_of_symptom_unit' in acc_sym:
                                disease_time[acc_symptom_name].add((acc_duration_of_symptom,
                                                                    acc_sym['duration_of_symptom_unit']))
                                if acc_sym['duration_of_symptom_unit'] == '年':
                                    disease_time[acc_symptom_name].add((int(acc_duration_of_symptom*12), '月'))
                                elif acc_sym['duration_of_symptom_unit'] == '月' and acc_duration_of_symptom == 0.5:
                                    disease_time[acc_symptom_name].add((2, '周'))
                                elif acc_sym['duration_of_symptom_unit'] == '日':
                                    disease_time[acc_symptom_name].add((acc_duration_of_symptom, '天'))
                            else:
                                disease_time[acc_symptom_name].add((acc_duration_of_symptom,))

            # 体征模型
            if 'sign' in dis:
                if 'sign_name' in dis['sign']:
                    sign_name = dis['sign']['sign_name']
                    disease_time.setdefault(sign_name, set())
                    if 'time' in dis['sign']:
                        if isinstance(dis['sign']['time'], str):
                            t = re.compile('\d*\d-').sub('', dis['sign']['time'])
                            try:
                                t = int(t)
                            except ValueError:
                                t = float(t)
                        else:
                            t = dis['sign']['time']
                        if 'time_unit' in dis['sign']:
                            t_unit = dis['sign']['time_unit']
                            disease_time[sign_name].add((t, t_unit))
                            if t_unit == '年':
                                disease_time[sign_name].add((int(t*12), '月'))
                            elif t_unit == '月' and t == 0.5:
                                disease_time[sign_name].add((2, '周'))
                            elif t_unit == '日':
                                disease_time[sign_name].add((t, '天'))
                        else:
                            disease_time[sign_name].add((t,))
                    if 'disease_name' in dis:
                        disease_time[sign_name].update(disease_time[dis['disease_name']])
            # 检验模型
            if 'lab' in dis:
                for l in dis['lab']:
                    if 'lab_item_name' in l:
                        disease_time.setdefault(l['lab_item_name'], set())
                        if 'report_time' in l:
                            disease_time[l['lab_item_name']].add((l['report_time'],))
                        if 'disease_name' in dis:
                            disease_time[l['lab_item_name']].update(disease_time[dis['disease_name']])

            # 检查模型
            if 'exam' in dis:
                for e in dis['exam']:
                    if 'exam_item_name' in e:
                        disease_time.setdefault(e['exam_item_name'], set())
                        if 'report_time' in e:
                            disease_time[e['exam_item_name']].add((e['report_time'],))  # 模型中的时间name
                        if 'exam_time' in e:
                            disease_time[e['exam_item_name']].add((e['exam_time'],))
                        if 'disease_name' in dis:
                            disease_time[e['exam_item_name']].update(disease_time[dis['disease_name']])

            # 药品模型
            if 'medicine' in dis:
                for m in dis['medicine']:
                    if 'medicine_name' in m:
                        disease_time.setdefault(m['medicine_name'], set())
                        if 'duration' in m:
                            if isinstance(m['duration'], str):
                                duration_medicine = re.compile('\d*\d-').sub('', m['duration'])
                                try:
                                    duration_medicine = int(duration_medicine)
                                except ValueError:
                                    duration_medicine = float(duration_medicine)
                            else:
                                duration_medicine = m['duration']
                            if 'duration_unit' in m:
                                disease_time[m['medicine_name']].add((duration_medicine, m['duration_unit']))
                                if m['duration_unit'] == '年':
                                    disease_time[m['medicine_name']].add((int(duration_medicine*12), '月'))
                                elif m['duration_unit'] == '月' and duration_medicine == 0.5:
                                    disease_time[m['medicine_name']].add((2, '周'))
                                elif m['duration_unit'] == '日':
                                    disease_time[m['medicine_name']].add((duration_medicine, '天'))
                            else:
                                disease_time[m['medicine_name']].add((duration_medicine,))
                        if 'start_date_time' in m:
                            if 'stop_date_time' in m:
                                disease_time[m['medicine_name']].add((m['start_date_time'], m['stop_date_time']))
                            else:
                                disease_time[m['medicine_name']].add((m['start_date_time'],))
                        if 'disease_name' in dis:
                            disease_time[m['medicine_name']].update(disease_time[dis['disease_name']])

            # 手术模型
            if 'operation' in dis:
                for o in dis['operation']:
                    if 'operation_name' in o:
                        disease_time.setdefault(o['operation_name'], set())
                        if 'postoperative_time' in o:
                            if isinstance(o['postoperative_time'], str):
                                postoperative_time = re.compile('\d*\d-').sub('', o['postoperative_time'])
                                try:
                                    postoperative_time = int(postoperative_time)
                                except ValueError:
                                    postoperative_time = float(postoperative_time)
                            else:
                                postoperative_time = o['postoperative_time']
                            if 'postoperative_time_unit' in o:
                                disease_time[o['operation_name']].add((postoperative_time, o['postoperative_time_unit']))
                                if o['postoperative_time_unit'] == '年':
                                    disease_time[o['operation_name']].add((int(postoperative_time*12), '月'))
                                elif o['postoperative_time_unit'] == '月' and postoperative_time == 0.5:
                                    disease_time[o['operation_name']].add((2, '周'))
                                elif o['postoperative_time_unit'] == '日':
                                    disease_time[o['operation_name']].add((postoperative_time, '天'))
                            else:
                                disease_time[o['operation_name']].add((postoperative_time,))
                        if 'disease_name' in dis:
                            disease_time[o['operation_name']].update(disease_time[dis['disease_name']])

        # flag = False
        # for k, v in disease_time.items():
        #     if v:
        #         flag = True
        #         break

        return disease_time

    def _gain_lab_time(self, lab_model):
        """
        检验模型时间
        """
        lab_time = dict()
        # flag = False
        for l in lab_model:
            if 'lab_item_name' in l:
                lab_time.setdefault(l['lab_item_name'], set())
                if 'report_time' in l:
                    # flag = True
                    report_time = self._load_time(l['report_time'])
                    lab_time[l['lab_item_name']].add(report_time)
            if 'lab_sub_item_name' in l:
                lab_time.setdefault(l['lab_sub_item_name'], set())
                if 'report_time' in l:
                    # flag = True
                    report_time = self._load_time(l['report_time'])
                    lab_time[l['lab_sub_item_name']].add(report_time)
        return lab_time

    @staticmethod
    def _gain_lab_info(lab_model, get_item):
        """
        检验模型配置信息
        """
        res = list()
        for l in lab_model:
            temp = dict()
            flag = False
            for k in get_item:
                if k in l:
                    temp[k] = l[k]
                    flag = True
            if flag:
                res.append(temp)
        return res

    def _gain_exam_time(self, exam_model):
        """
        检查模型
        """
        exam_time = dict()

        # flag = False
        if isinstance(exam_model, list):
            for e in exam_model:  # e为检查模型
                key = list()
                if 'exam_item_name' in e:
                    key.append(e['exam_item_name'])
                if 'exam_class_name' in e:
                    key.append(e['exam_class_name'])
                if 'exam_diag_quantization' in e:
                    for a in e['exam_diag_quantization']:  # a为检查量化细化模型
                        if 'quantization_text' in a:
                            key.append(a['quantization_text'])
                        if 'quantization_sub' in a:
                            for b in a['quantization_sub']:  # b为检查量化细化模型1
                                if 'quantization_text' in b:
                                    key.append(b['quantization_text'])
                                if 'quantization_sub' in b:
                                    for c in b['quantization_sub']:  # c为检查量化细化模型2
                                        if 'quantization_text' in c:
                                            key.append(c['quantization_text'])
                if not key:
                    continue
                for item_name in key:
                    exam_time.setdefault(item_name, set())
                    if 'report_time' in e:
                        # flag = True
                        report_time = self._load_time(e['report_time'])
                        exam_time[item_name].add(report_time)
                    if 'exam_time' in e:
                        # flag = True
                        report_time = self._load_time(e['exam_time'])
                        exam_time[item_name].add(report_time)
                    if 'exam_diag_date' in e:
                        if 'exam_diag_date_unit' in e:
                            exam_time[item_name].add((e['exam_diag_date'], e['exam_diag_date_unit']))
                        else:
                            exam_time[item_name].add((e['exam_diag_date'],))

        if isinstance(exam_model, dict):
            key = list()
            if 'exam_diag' in exam_model:
                key.append(exam_model['exam_diag'])
            if not key:
                return exam_time
            for item_name in key:
                exam_time.setdefault(item_name, set())
                if 'report_time' in exam_model:
                    # flag = True
                    report_time = self._load_time(exam_model['report_time'])
                    exam_time[item_name].add(report_time)
                if 'exam_time' in exam_model:
                    # flag = True
                    report_time = self._load_time(exam_model['exam_time'])
                    exam_time[item_name].add(report_time)
                if 'exam_diag_date' in exam_model:
                    if 'exam_diag_date_unit' in exam_model:
                        exam_time[item_name].add((exam_model['exam_diag_date'], exam_model['exam_diag_date_unit']))
                    else:
                        exam_time[item_name].add((exam_model['exam_diag_date'],))
        return exam_time

    @staticmethod
    def _gain_operation_time(operation_model):
        """
        手术模型
        """
        operation_time = dict()

        # flag = False
        for o in operation_model:
            if 'operation_name' in o:
                operation_time.setdefault(o['operation_name'], set())
                if 'postoperative_time' in o:
                    # flag = True
                    if isinstance(o['postoperative_time'], str):
                        postoperative_time = re.compile('\d*\d-').sub('', o['postoperative_time'])
                        try:
                            postoperative_time = int(postoperative_time)
                        except ValueError:
                            postoperative_time = float(postoperative_time)
                    else:
                        postoperative_time = o['postoperative_time']

                    if 'postoperative_time_unit' in o:
                        operation_time[o['operation_name']].add((postoperative_time, o['postoperative_time_unit']))
                        if o['postoperative_time_unit'] == '年':
                            operation_time[o['operation_name']].add((int(postoperative_time*12), '月'))
                        elif o['postoperative_time_unit'] == '月' and postoperative_time == 0.5:
                            operation_time[o['operation_name']].add((2, '周'))
                        elif o['postoperative_time_unit'] == '日':
                            operation_time[o['operation_name']].add((postoperative_time, '天'))

                    else:
                        operation_time[o['operation_name']].add((postoperative_time,))

        return operation_time

    def _gain_medicine_time(self, medicine_model):
        """
        药品模型
        """
        medicine_time = dict()

        # flag = False
        for m in medicine_model:
            if 'medicine_name' in m:
                medicine_time.setdefault(m['medicine_name'], set())
                if 'duration' in m:
                    # flag = True
                    if isinstance(m['duration'], str):
                        duration_medicine = self._load_time(m['duration'])
                    else:
                        duration_medicine = m['duration'],
                    if len(duration_medicine) == 1:
                        duration_medicine = duration_medicine[0]
                        if 'duration_unit' in m:
                            medicine_time[m['medicine_name']].add((duration_medicine, m['duration_unit']))
                            if m['duration_unit'] == '年':
                                medicine_time[m['medicine_name']].add((int(duration_medicine*12), '月'))
                            elif m['duration_unit'] == '月' and duration_medicine == 0.5:
                                medicine_time[m['medicine_name']].add((2, '周'))
                            elif m['duration_unit'] == '日':
                                medicine_time[m['medicine_name']].add((duration_medicine, '天'))
                        else:
                            medicine_time[m['medicine_name']].add((duration_medicine,))
                    else:
                        medicine_time[m['medicine_name']].add(duration_medicine)
                        if duration_medicine[1] == '年':
                            medicine_time[m['medicine_name']].add((int(duration_medicine[0]*12), '月'))
                        elif duration_medicine[1] == '月' and duration_medicine[0] == 0.5:
                            medicine_time[m['medicine_name']].add((2, '周'))
                        elif duration_medicine[1] == '日':
                            medicine_time[m['medicine_name']].add((duration_medicine[0], '天'))
                if 'start_date_time' in m:
                    # flag = True
                    if 'stop_date_time' in m:
                        medicine_time[m['medicine_name']].add((m['start_date_time'], m['stop_date_time']))
                    else:
                        medicine_time[m['medicine_name']].add((m['start_date_time'],))

        return medicine_time

    @staticmethod
    def _gain_treatment_time(treatment_model):
        """
        治疗模型
        """
        treatment_time = dict()
        # flag = False
        for t in treatment_model:
            if 'treatment_name' in t:
                treatment_time.setdefault(t['treatment_name'], set())
                if 'time' in t:
                    # flag = True
                    if isinstance(t['time'], str):
                        t_time = re.compile('\d*\d-').sub('', t['time'])
                        try:
                            t_time = int(t_time)
                        except ValueError:
                            t_time = float(t_time)
                    else:
                        t_time = t['time']
                    if 'time_unit' in t:
                        treatment_time[t['treatment_name']].add((t_time, t['time_unit']))
                        if t['time_unit'] == '年':
                            treatment_time[t['treatment_name']].add((int(t_time*12), '月'))
                        elif t['time_unit'] == '月' and t_time == 0.5:
                            treatment_time[t['treatment_name']].add((2, '周'))
                        elif t['time_unit'] == '日':
                            treatment_time[t['treatment_name']].add((t_time, '天'))
                    else:
                        treatment_time[t['treatment_name']].add((t_time,))
        return treatment_time

    def _gain_present_time_value(self, present_model):
        res = set()
        if 'time' in present_model:
            time_value_pre = ''
            for t in present_model['time']:
                time_value = ''
                if 'time_value' in t:
                    if t['time_value'] in self.conf_dict['time_value']:
                        time_value = time_value_pre
                    else:
                        time_value = self._load_time(t['time_value'])
                time_value_pre = time_value
                if time_value and len(time_value) > 1:
                    res.add(time_value)
                    if time_value[1] == '年':
                        res.add((int(time_value[0]*12), '月'))
                    elif time_value[1] == '月' and time_value[0] == 0.5:
                        res.add((2, '周'))
                    elif time_value[1] == '日':
                        res.add((time_value[0], '天'))
        return res

    def _gain_present_time(self, present_model):
        """
        获取现病史所有时间节点模型中的主症状、所有伴随症状、部位+主症状
        获取对应的时间，并将伴随症状的时间加到主症状中
        """
        if 'time' in present_model:
            all_symptom = dict()
            time_value_pre = ''
            for t in present_model['time']:
                time_value = ''
                if 'time_value' in t:
                    if t['time_value'] in self.conf_dict['time_value']:
                        time_value = time_value_pre
                    else:
                        time_value = self._load_time(t['time_value'])
                time_value_pre = time_value
                if 'symptom' in t:
                    symptom_list = t['symptom']
                    for symptom_model in symptom_list:
                        one_symptom = self._gain_symptom_time(symptom_model)
                        for k, v in one_symptom.items():
                            if k not in all_symptom:
                                all_symptom[k] = v
                            else:
                                all_symptom[k].update(v)
                            if k == '加重症状':
                                continue
                            if time_value:
                                all_symptom[k].add(time_value)
                                if len(time_value) == 2:
                                    if time_value[1] == '年':
                                        all_symptom[k].add((int(time_value[0]*12), '月'))
                                    elif time_value[1] == '月' and time_value[0] == 0.5:
                                        all_symptom[k].add((2, '周'))
                                    elif time_value[1] == '日':
                                        all_symptom[k].add((time_value[0], '天'))

                if 'sign' in t:
                    sign_time = self._gain_sign_time(t['sign'])
                    if sign_time:
                        for k, v in sign_time.items():
                            if k in all_symptom:
                                all_symptom[k].update(v)
                            else:
                                all_symptom[k] = v
                            if time_value:
                                all_symptom[k].add(time_value)
                                if len(time_value) == 2:
                                    if time_value[1] == '年':
                                        all_symptom[k].add((int(time_value[0]*12), '月'))
                                    elif time_value[1] == '月' and time_value[0] == 0.5:
                                        all_symptom[k].add((2, '周'))
                                    elif time_value[1] == '日':
                                        all_symptom[k].add((time_value[0], '天'))

                if 'diagnose' in t:

                    if 'diagnosis_name' in t['diagnose']:
                        diagnosis_name = t['diagnose']['diagnosis_name']
                    else:
                        diagnosis_name = ''

                    if 'diagnosis_time' in t['diagnose']:
                        diagnosis_time = t['diagnose']['diagnosis_name']
                    else:
                        diagnosis_time = ''

                    if diagnosis_name:
                        diagnosis = dict()
                        diagnosis_name_split = re.compile('\s|,|，').split(diagnosis_name)
                        for content in diagnosis_name_split:
                            content = content.strip()
                            diagnosis.setdefault(content, set())
                            if diagnosis_time:
                                diagnosis[content].add((diagnosis_time,))
                            for k, v in diagnosis.items():
                                if k in all_symptom:
                                    all_symptom[k].update(v)
                                else:
                                    all_symptom[k] = v
                                if time_value:
                                    all_symptom[k].add(time_value)
                                    if len(time_value) == 2:
                                        if time_value[1] == '年':
                                            all_symptom[k].add((int(time_value[0]*12), '月'))
                                        elif time_value[1] == '月' and time_value[0] == 0.5:
                                            all_symptom[k].add((2, '周'))
                                        elif time_value[1] == '日':
                                            all_symptom[k].add((time_value[0], '天'))

                if 'lab' in t:
                    lab_time = self._gain_lab_time(t['lab'])
                    if lab_time:
                        for k, v in lab_time.items():
                            if k in all_symptom:
                                all_symptom[k].update(v)
                            else:
                                all_symptom[k] = v
                            if time_value:
                                all_symptom[k].add(time_value)
                                if len(time_value) == 2:
                                    if time_value[1] == '年':
                                        all_symptom[k].add((int(time_value[0]*12), '月'))
                                    elif time_value[1] == '月' and time_value[0] == 0.5:
                                        all_symptom[k].add((2, '周'))
                                    elif time_value[1] == '日':
                                        all_symptom[k].add((time_value[0], '天'))

                if 'exam' in t:
                    exam_time = self._gain_exam_time(t['exam'])
                    if exam_time:
                        for k, v in exam_time.items():
                            if k in all_symptom:
                                all_symptom[k].update(v)
                            else:
                                all_symptom[k] = v
                            if time_value:
                                all_symptom[k].add(time_value)
                                if len(time_value) == 2:
                                    if time_value[1] == '年':
                                        all_symptom[k].add((int(time_value[0]*12), '月'))
                                    elif time_value[1] == '月' and time_value[0] == 0.5:
                                        all_symptom[k].add((2, '周'))
                                    elif time_value[1] == '日':
                                        all_symptom[k].add((time_value[0], '天'))

                if 'therapeutic_measures' in t:
                    treatment_time = self._gain_treatment_time(t['therapeutic_measures'])
                    if treatment_time:
                        for k, v in treatment_time.items():
                            if k in all_symptom:
                                all_symptom[k].update(v)
                            else:
                                all_symptom[k] = v
                            if time_value:
                                all_symptom[k].add(time_value)
                                if len(time_value) == 2:
                                    if time_value[1] == '年':
                                        all_symptom[k].add((int(time_value[0]*12), '月'))
                                    elif time_value[1] == '月' and time_value[0] == 0.5:
                                        all_symptom[k].add((2, '周'))
                                    elif time_value[1] == '日':
                                        all_symptom[k].add((time_value[0], '天'))

                if 'operation' in t:
                    operation_time = self._gain_operation_time(t['operation'])
                    if operation_time:
                        for k, v in operation_time.items():
                            if k in all_symptom:
                                all_symptom[k].update(v)
                            else:
                                all_symptom[k] = v
                            if time_value:
                                all_symptom[k].add(time_value)
                                if len(time_value) == 2:
                                    if time_value[1] == '年':
                                        all_symptom[k].add((int(time_value[0]*12), '月'))
                                    elif time_value[1] == '月' and time_value[0] == 0.5:
                                        all_symptom[k].add((2, '周'))
                                    elif time_value[1] == '日':
                                        all_symptom[k].add((time_value[0], '天'))

                if 'medicine' in t:
                    medicine_time = self._gain_medicine_time(t['medicine'])
                    if medicine_time:
                        for k, v in medicine_time.items():
                            if k in all_symptom:
                                all_symptom[k].update(v)
                            else:
                                all_symptom[k] = v
                            if time_value:
                                all_symptom[k].add(time_value)
                                if len(time_value) == 2:
                                    if time_value[1] == '年':
                                        all_symptom[k].add((int(time_value[0]*12), '月'))
                                    elif time_value[1] == '月' and time_value[0] == 0.5:
                                        all_symptom[k].add((2, '周'))
                                    elif time_value[1] == '日':
                                        all_symptom[k].add((time_value[0], '天'))
        else:
            return None, False
        flag = False
        for k, v in all_symptom.items():
            if v:
                flag = True
                break
        return all_symptom, flag

    def _gain_chief_time(self, chief_model):
        """
        获取病历文书的主诉的时间信息
        """
        chief_time = dict()
        if 'symptom' in chief_model:
            symptom_time = self._check_chief_symptom(chief_model['symptom'])
            # chief_time - - {'症状/伴随症状': {(时间, 单位)}}
            # error_info - - {'无主症状': set(id), '主诉时间缺失': set(id)}
            chief_time = symptom_time.copy()

        if 'sign' in chief_model:
            sign_time, sign_flag = self._gain_sign_time(chief_model['sign'])
            if sign_time:
                for k, v in sign_time.items():
                    if k in chief_time:
                        chief_time[k].update(v)
                    else:
                        chief_time[k] = v

        if 'disease' in chief_model:
            disease_time = self._gain_disease_time(chief_model['disease'])
            if disease_time:
                for k, v in disease_time.items():
                    if k in chief_time:
                        chief_time[k].update(v)
                    else:
                        chief_time[k] = v

        if 'lab' in chief_model:
            lab_time = self._gain_lab_time(chief_model['lab'])
            if lab_time:
                for k, v in lab_time.items():
                    if k in chief_time:
                        chief_time[k].update(v)
                    else:
                        chief_time[k] = v

        if 'exam' in chief_model:
            exam_time = self._gain_exam_time(chief_model['exam'])
            if exam_time:
                for k, v in exam_time.items():
                    if k in chief_time:
                        chief_time[k].update(v)
                    else:
                        chief_time[k] = v

        if 'treatment' in chief_model:
            treatment_time = self._gain_treatment_time(chief_model['treatment'])
            if treatment_time:
                for k, v in treatment_time.items():
                    if k in chief_time:
                        chief_time[k].update(v)
                    else:
                        chief_time[k] = v

        if 'operation' in chief_model:
            operation_time = self._gain_operation_time(chief_model['operation'])
            if operation_time:
                for k, v in operation_time.items():
                    if k in chief_time:
                        chief_time[k].update(v)
                    else:
                        chief_time[k] = v

        if 'medicine' in chief_model:
            medicine_time = self._gain_medicine_time(chief_model['medicine'])
            if medicine_time:
                for k, v in medicine_time.items():
                    if k in chief_time:
                        chief_time[k].update(v)
                    else:
                        chief_time[k] = v

        flag = False
        for k, v in chief_time.items():
            if v:
                flag = True
                break

        return chief_time, flag

    def _gain_same_content(self, key_content, value_content):
        """
        在 _gain_chief_time 和 _gain_present_time 的结果中获取内容相同的key
        """
        same_flag = dict()
        for k in key_content:
            if not k:
                continue
            for v in value_content:
                if not v:
                    continue
                if k in v or v in k:
                    same_flag[k] = v
                    break
        for k in key_content:  # 遍历key_content内容
            if not k:
                continue
            if k in value_content:  # 如果在value_content中
                same_flag[k] = k

            else:  # 如果不在value_content中

                if k in self.wordsynonym:  # 如果遍历 key_content 的内容在同义词表中
                    k_s = self.wordsynonym[k]
                    for k_s_i in k_s:  # 遍历key_content的同义词看是否在value_content中
                        for v in value_content:
                            if not v:
                                continue
                            if k_s_i in v or v in k_s_i:
                                if self.conf_dict['filter_word'].get(k, '') == v or self.conf_dict['filter_word'].get(v, '') == k:
                                    continue
                                same_flag[k] = v

                else:  # 如果遍历key_content的内容不在同义词表中，查上下级词表
                    self.wordtree.find_word(tree=self.wordtree.root, word=k)  # 找到 key_content 在不在上下级表
                    if self.wordtree.word_node:  # key_content 在上下级表
                        k_r = self.wordtree.word_node  # 取 key_content 该词的节点
                        while k_r.word != '*':  # 找父节点
                            for v in value_content:
                                if not v:
                                    continue
                                if k_r.word in v:
                                    same_flag[k] = v
                                if k_r.same:
                                    for k_r_s in k_r.same:
                                        if k_r_s in v:
                                            same_flag[k] = v
                                            break
                            k_r = k_r.parent
        return same_flag

    def _gain_same_content2(self, key_content, value_content):
        key_dict = dict()
        value_dict = dict()
        res = dict()
        for word in key_content:
            key_dict[word] = set(self.synonym_app.get_same_word(word))
            key_dict[word].update(self.synonym_app.get_child_disease(word))
        for word in value_content:
            value_dict[word] = set(self.synonym_app.get_same_word(word))
            value_dict[word].update(self.synonym_app.get_child_disease(word))
        for k, v in key_dict.items():
            for kk, vv in value_dict.items():
                if v.intersection(vv):
                    res[k] = kk
                elif k in kk:
                    res[k] = kk
        return res

    @staticmethod
    def _gain_disease_name(disease_model):
        """
        获取既往史的疾病名称
        """
        res = set()
        for d in disease_model:
            if 'disease_name' in d:
                res.add(d['disease_name'])
        return res

    @staticmethod
    def _gain_diagnosis_name(diagnosis_model):
        res = set()
        for d in diagnosis_model:
            if 'diagnosis_name' in d:
                res.add(d['diagnosis_name'])
        return res

    @staticmethod
    def _check_repeat_content(content_list):
        """
        检测重复内容，返回序列号
        """
        for i in range(len(content_list)):
            content_list[i] = re.sub("[，。,、]+", "", content_list[i])
        content_set = list(set(content_list))
        content_set.sort(key=content_list.index)  # content_set 按 content_list 的顺序
        final_repeat = []
        for i in content_set:
            if content_list.count(i) == 1 or i == '章节无src':
                continue
            else:
                repeat = []
                n = content_list.count(i)
                start_pos = 0
            for j in range(n):
                new_list = content_list[start_pos:]
                next_pos = new_list.index(i) + 1
                repeat.append(start_pos+next_pos-1)
                start_pos += next_pos
            final_repeat.append(repeat)
        return final_repeat

    @staticmethod
    def write_to_file(data, path):
        """
        将数据写入 json 文件
        """
        with open(path, 'w', encoding='utf8') as f:
            f.write(json.dumps(data, ensure_ascii=False, indent=4))

    @staticmethod
    def _gain_patient_info(cursor):
        """
        通过_id从病案首页获取接口数据
        输入pat_info数据
        """
        res = dict()
        res['machine_score'] = 0  # 机器扣分
        res['artificial_score'] = 0  # 机器扣分
        data = cursor.get('binganshouye', dict())
        if 'pat_info' in data:
            if 'person_name' in data['pat_info']:
                res['person_name'] = data['pat_info']['person_name']  # 患者姓名
        check_list = ['inp_no',
                      'patient_id',
                      'visit_id',
                      'discharge_time',
                      'admission_time',
                      'dept_admission_to_name',
                      'dept_discharge_from_name',
                      'district_discharge_from_name',
                      'district_admission_to_name',
                      'attending_doctor_name',
                      'inp_doctor_name',
                      'senior_doctor_name']
        if 'pat_visit' in data:
            for i in check_list:
                if i in data['pat_visit']:
                    res[i] = data['pat_visit'][i]
        return res

    def _gain_bingan_info(self, cursor):
        """
        根据 id 获取到的病人病案首页信息
        """
        patient_result = dict()
        patient_result['pat_info'] = self._gain_patient_info(cursor)  # 获取病案首页数据
        patient_result['pat_value'] = list()
        return patient_result

    def _gain_jiangya_medicine(self):
        res = set()
        with open(self.jiangya_path, 'r', encoding='utf8') as f:
            for line in f.readlines():
                line = line.strip()
                res.add(line)
        return res

    def compose_wslb(self, collection_name, patient_id=''):
        """
        获取collection_name表中的的病人的多个就诊次
        """
        mongo_collection = self.collection_name + '_repeat'
        collection = self.mongo_app.connectCollection(database_name=self.database_name,
                                                      collection_name=mongo_collection)
        result = dict()
        search_field = dict()
        if collection_name:
            search_field = {'info.'+collection_name: {'$exists': True}}
        if patient_id:
            search_field['_id'] = self.hospital_code + '#' + patient_id
        mongo_result = collection.find(search_field, {'info': 1}).batch_size(10000)
        for mongo_data in mongo_result:
            if mongo_data.get('_id'):
                result[mongo_data['_id']] = mongo_data.get('info', dict()).get(collection_name, list())
        return result

    def gain_statistics_info(self, time_left, time_right):
        collection = self.mongo_app.connectCollection(database_name=self.database_name,
                                                      collection_name=self.collection_name)
        pipeline = [{'$match': {'pat_info.discharge_time': {'$gt': time_left, '$lt': time_right}, 'pat_value.code': {'$exists': True}}},
                    {'$group': {'_id': '$pat_info.dept_discharge_from_name', 'error': {'$sum': 1}}}]
        pipeline_dept = [{'$match': {'pat_info.discharge_time': {'$gt': time_left, '$lt': time_right}, 'pat_value.code': {'$exists': True}}},
                         {"$unwind": '$pat_value'},
                         {'$group': {'_id': {'dept': '$pat_info.dept_discharge_from_name', 'name': '$pat_value.name'}, 'error': {'$sum': 1}}}]
        pipeline_bingan = [{'$match': {'binganshouye.pat_visit.discharge_time': {'$gt': time_left, '$lt': time_right}}},
                           {'$group': {'_id': '$binganshouye.pat_visit.dept_discharge_from_name', 'total': {'$sum': 1}}}]
        error_query_result = collection.aggregate(pipeline, allowDiskUse=True).batch_size(50)
        dept_query_result = collection.aggregate(pipeline_dept, allowDiskUse=True).batch_size(50)
        total_query_result = self.collection_bingan.aggregate(pipeline_bingan, allowDiskUse=True).batch_size(50)
        result = dict()
        result['_id'] = time_left
        result['info'] = list()
        temp = dict()
        temp2 = dict()
        for i in total_query_result:
            temp[i['_id']] = {'total': i['total']}
            temp[i['_id']]['error'] = 0
            temp[i['_id']]['error_ratio'] = 0
            temp[i['_id']]['right'] = i['total']

        for i in error_query_result:
            if i['_id'] not in temp:
                self.logger.warn(i['_id'])
                continue
            temp[i['_id']]['error'] = i['error']
            temp[i['_id']]['right'] = temp[i['_id']]['total'] - temp[i['_id']]['error']
            temp[i['_id']]['error_ratio'] = temp[i['_id']]['error'] / temp[i['_id']]['total'] if temp[i['_id']]['total'] else 0

        for i in dept_query_result:
            dept = i['_id'].get('dept')
            name = i['_id'].get('name')
            if not (dept and name):
                continue
            temp2.setdefault(dept, dict())
            temp2[dept][name] = i['error']

        for k, v in temp.items():
            x = {'dept': k}
            x.update(v)
            result['info'].append(x)
        result['dept_name'] = temp2
        if result['dept_name'] or result['info']:
            return result
        else:
            return {}

    def transFieldData(self, value):
        """
        递归寻找需要提取的字段
        """
        result = []
        if not value:
            return result
        if isinstance(value, dict):
            for value_key, value_value in value.items():
                if isinstance(value_value, str) or isinstance(value_value, int) or isinstance(value_value, float):
                    result.append(value_value)
                else:
                    tmp = self.transFieldData(value_value)
                    result.extend(tmp)
        elif isinstance(value, list):
            for i in value:
                tmp = self.transFieldData(i)
                result.extend(tmp)
        return result

    def getField(self, query_field, field=None):
        """
        获取传入字段的所有值
        query_field: 查询条件
        """
        result_list = []
        if not field:
            return result_list
        field_list = field.split(".")
        collection_name = field_list[0]
        conn = self.mongo_app.connectCollection(database_name=self.database_name, collection_name=collection_name)
        query_result = conn.distinct(field, query_field)
        # query_result = conn.find(query_field, {field: 1, "_id": 0})
        for mongo_data in query_result:
            # res_tmp = self.transFieldData(mongo_data)
            # result_list.extend(res_tmp)
            result_list.append(mongo_data)
        # result_list = set(result_list)
        return result_list


class SetEncoder(json.JSONEncoder):
    # json.dumps(r, ensure_ascii=False, indent=4, cls=SetEncoder)
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


if __name__ == '__main__':
    app = GainMongoInfo()
    # r = app.gain_statistics_info('2017-04', '2017-05')
    t1 = datetime.now()
    r = app._load_time('今晨')
    print((datetime.now()-t1).total_seconds())
    # print(json.dumps(r, ensure_ascii=False, indent=2))
