#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
@version: V1.0
@author:
@mail:
@file: initialization.py
@time: 2019-04-04 17:16
@description: 
"""
import os
import sys
cur_path = os.path.abspath(os.path.dirname(__file__))
root_path = os.path.split(cur_path)[0]
sys.path.append(root_path)  # 项目路径添加到系统路径
import xlrd
from datetime import datetime
import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'MedicalRecordQuality.settings'
django.setup()
from MedicalQuality.models import User, Dept, District
from Utils.MongoUtils import PushDataFromMDBUtils
from Utils.segmentWord import RunSegmentWord
import traceback


def step0():
    """
    验证数据库权限
    """
    try:
        print('Project initializing...')
        print('Step 0. Checking database authority')
        app_mongo = PushDataFromMDBUtils()
        if app_mongo.identifyAuth():
            print('\tVerification passed.')
            return True
        else:
            print('\tVerification failed.')
            return False
    except:
        print(traceback.format_exc())
        return False


def step1():
    """
    初始化项目超级管理员
    """
    try:
        print('Step 1. Checking Superuser')
        user_obj = User.objects.filter(is_superuser=True).first()
        if not user_obj:
            superuser_obj = User.objects.create_superuser(username='mrq', USER_ID='mrq', password='jhmk8uhbmrq', email='yuanli@bjgoodwill.com')
            if superuser_obj:
                superuser_obj.save()
                print('\tno superuser, creating it...superuser has been created.')
        else:
            print('\tsuperuser exists.')
        return True
    except:
        print(traceback.format_exc())
        return False


def step2():
    """
    初始化规则管理
    """
    try:
        print('Step 2. Checking Regular Model')
        app_mongo = PushDataFromMDBUtils()
        regular_xlsx = os.path.join(cur_path, 'configure/regular_model.xlsx')
        workbook = xlrd.open_workbook(regular_xlsx)
        name_switch = {
            '医生端': 'regular_model_yishengduan',
            '环节': 'regular_model_huanjie',
            '终末': 'regular_model_zhongmo'
        }
        caption_list = ['路径', '二级路径', '规则码', '规则分类', '规则明细',
                        '扣分', '专科标识', '类别标识', '状态', '创建时间', '修改时间']
        caption_col = dict()
        for sheet in workbook.sheets():
            if not caption_col:
                cols = sheet.ncols
                for col in range(cols):
                    if sheet.cell_value(0, col) in caption_list:
                        caption_col[sheet.cell_value(0, col)] = col
            collection_name = name_switch.get(sheet.name)
            if not collection_name:
                continue
            conn = app_mongo.connectCollection(database_name=app_mongo.mongodb_database_name,
                                               collection_name=collection_name)
            nrows = sheet.nrows
            for row in range(1, nrows):
                # 规则码为空则跳过
                if sheet.cell(row, caption_col['规则码']).ctype != 1:
                    continue
                else:
                    value = sheet.cell_value(row, caption_col['规则码'])
                    if not value.strip():
                        continue
                code = sheet.cell_value(row, caption_col['规则码'])
                mongo_result = conn.find_one({'_id': code}, {'modify_date': 1}) or dict()
                if not mongo_result:
                    mongo_result['_id'] = code
                if '修改时间' in caption_col:
                    # 该规则是否在数据库中，在的话验证修改时间，不在的话直接插入数据库
                    modify_date_db = mongo_result.get('modify_date', '').strip()
                    if sheet.cell(row, caption_col['修改时间']).ctype == 1:
                        modify_date_xls = sheet.cell_value(row, caption_col['修改时间'])
                    elif sheet.cell(row, caption_col['修改时间']).ctype == 3:
                        date = datetime(*xlrd.xldate_as_tuple(sheet.cell_value(row, caption_col['修改时间']), 0))
                        modify_date_xls = date.strftime('%Y-%m-%d')
                    else:
                        continue
                    # 如果excel中没有修改时间，或者该修改时间比数据库中要早，则不更新该条规则
                    if modify_date_db >= modify_date_xls:
                        continue
                    mongo_result['modify_date'] = modify_date_xls
                if '路径' in caption_col:
                    if '--' in sheet.cell_value(row, caption_col['路径']):
                        mongo_result['record_name'] = sheet.cell_value(row, caption_col['路径']).split('--')[0]
                        mongo_result['chapter'] = sheet.cell_value(row, caption_col['路径']).split('--')[1]
                    else:
                        mongo_result['record_name'] = sheet.cell_value(row, caption_col['路径'])
                        mongo_result['chapter'] = sheet.cell_value(row, caption_col['路径'])
                if '二级路径' in caption_col:
                    mongo_result['chapter'] = sheet.cell_value(row, caption_col['二级路径'])
                if '规则分类' in caption_col:
                    mongo_result['regular_classify'] = sheet.cell_value(row, caption_col['规则分类'])
                if '规则明细' in caption_col:
                    mongo_result['regular_details'] = sheet.cell_value(row, caption_col['规则明细'])
                if '专科标识' in caption_col:
                    mongo_result['dept'] = sheet.cell_value(row, caption_col['专科标识'])
                if '类别标识' in caption_col:
                    mongo_result['classification_flag'] = sheet.cell_value(row, caption_col['类别标识'])
                if '状态' in caption_col:
                    mongo_result['status'] = sheet.cell_value(row, caption_col['状态']) or '未启用'

                # 创建时间
                if '创建时间' in caption_col:
                    if sheet.cell(row, caption_col['创建时间']).ctype == 1:
                        create_date = sheet.cell_value(row, caption_col['创建时间'])
                    elif sheet.cell(row, caption_col['创建时间']).ctype == 3:
                        date = datetime(*xlrd.xldate_as_tuple(sheet.cell_value(row, caption_col['创建时间']), 0))
                        create_date = date.strftime('%Y-%m-%d')
                    else:
                        create_date = ''
                    mongo_result['create_date'] = create_date

                # 扣分
                if '扣分' in caption_col:
                    if sheet.cell(row, caption_col['扣分']).ctype == 1:
                        try:
                            score = float(sheet.cell_value(row, caption_col['扣分']))
                        except:
                            score = 0
                    elif sheet.cell(row, caption_col['扣分']).ctype == 2:
                        score = sheet.cell_value(row, caption_col['扣分'])
                    else:
                        score = 0
                    mongo_result['score'] = score
                app_mongo.pushData(collection_name, mongo_result)
            print('\t{} update to database'.format(sheet.name))
        return True
    except:
        print(traceback.format_exc())
        return False


def step3():
    """
    验证分词版本
    """
    try:
        print('Step 3. Checking Word Segment Service')
        app_seg = RunSegmentWord()
        ver = app_seg.version().get('project_version', '')
        if not ver:
            print('\tWarning: Word segment service is unreachable.')
            return False
        else:
            if ver != 'V3.0.0.190313':
                print('\tWarning: Version of word segment service is {}, mrq project set it V3.0.0.190313.'.format(ver))
            else:
                print('\tWord Segment Service Version is Corresponding.')
            return True
    except:
        print(traceback.format_exc())
        return False


def step4():
    """
    初始化科室数据
    """
    try:
        print('Step 3. Checking Dept Infomation')
        regular_xlsx = os.path.join(cur_path, 'configure/DEPT_INFO.xlsx')
        workbook = xlrd.open_workbook(regular_xlsx)
        caption_list = ['WARD_CODE', 'WARD_NAME', 'DEPT_CODE', 'DEPT_NAME']
        caption_sub_list = ['DEPT_INPUT_CODE', 'DEPT_EMR', 'WARD_INPUT_CODE']
        for sheet in workbook.sheets():
            caption_col = dict()
            cols = sheet.ncols
            for col in range(cols):
                if sheet.cell_value(0, col) in caption_list:
                    caption_col[sheet.cell_value(0, col)] = col
            if len(caption_col) < 4:
                continue
            for col in range(cols):
                if sheet.cell_value(0, col) in caption_sub_list:
                    caption_col[sheet.cell_value(0, col)] = col
            nrows = sheet.nrows
            for row in range(1, nrows):
                if sheet.cell(row, caption_col['WARD_CODE']).ctype == 2:
                    WARD_CODE = str(int(sheet.cell_value(row, caption_col['WARD_CODE'])))
                else:
                    WARD_CODE = sheet.cell_value(row, caption_col['WARD_CODE'])
                if sheet.cell(row, caption_col['DEPT_CODE']).ctype == 2:
                    DEPT_CODE = str(int(sheet.cell_value(row, caption_col['DEPT_CODE'])))
                else:
                    DEPT_CODE = sheet.cell_value(row, caption_col['DEPT_CODE'])
                WARD_NAME = sheet.cell_value(row, caption_col['WARD_NAME'])
                DEPT_NAME = sheet.cell_value(row, caption_col['DEPT_NAME'])
                if 'DEPT_INPUT_CODE' in caption_col:
                    DEPT_INPUT_CODE = sheet.cell_value(row, caption_col['DEPT_INPUT_CODE'])
                else:
                    DEPT_INPUT_CODE = None
                if 'WARD_INPUT_CODE' in caption_col:
                    WARD_INPUT_CODE = sheet.cell_value(row, caption_col['WARD_INPUT_CODE'])
                else:
                    WARD_INPUT_CODE = None
                if 'DEPT_EMR' in caption_col:
                    DEPT_EMR = sheet.cell_value(row, caption_col['DEPT_EMR'])
                else:
                    DEPT_EMR = None
                if Dept.objects.filter(DEPT_CODE=DEPT_CODE).exists():
                    dept_obj = Dept.objects.filter(DEPT_CODE=DEPT_CODE).first()
                else:
                    dept_obj = Dept.objects.create(DEPT_CODE=DEPT_CODE,
                                                   DEPT_NAME=DEPT_NAME,
                                                   DEPT_INPUT_CODE=DEPT_INPUT_CODE,
                                                   DEPT_EMR=DEPT_EMR)
                if District.objects.filter(WARD_CODE=WARD_CODE).exists():
                    district_obj = District.objects.filter(WARD_CODE=WARD_CODE).first()
                else:
                    district_obj = District.objects.create(WARD_CODE=WARD_CODE,
                                                           WARD_NAME=WARD_NAME,
                                                           WARD_INPUT_CODE=WARD_INPUT_CODE)

                if dept_obj is not None and district_obj is not None:
                    district_obj.dept = dept_obj
                    dept_obj.save()
                    district_obj.save()
        return True
    except:
        print(traceback.format_exc())
        return False


def projectInit():
    x = False
    x = step0()
    if not x:
        return x
    x = step1()
    if not x:
        return x
    x = step2()
    if not x:
        return x
    # x = step3()
    # if not x:
    #     return x
    x = step4()
    return x


if __name__ == '__main__':
    app = step2()
    if app:
        print('Initialization Done!')
