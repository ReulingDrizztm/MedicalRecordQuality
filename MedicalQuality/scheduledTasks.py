#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
@version: V1.0
@author:
@mail:
@file: scheduledTasks.py
@time: 2019-02-22 11:51
@description: 跑定时任务
"""
import os
import sys
cur_path = os.path.abspath(os.path.dirname(__file__))
root_path = os.path.split(cur_path)[0]
sys.path.append(root_path)  # 项目路径添加到系统路径
import traceback
from datetime import datetime, timedelta
from MedicalQuality.mainProgram import CheckMultiRecords
from Utils.MongoUtils import PushDataFromMDBUtils
from Utils.LogUtils import LogUtils
from Utils.loadingConfigure import Properties
# from MedicalQuality.statisticPatientsInfos import StatisticPatientInfos


def runZhongmo():
    """
    每天更新终末库数据，运行春光入库的数据
    """
    app = CheckMultiRecords(debug=True)
    logger = LogUtils().getLogger('scheduledTasks')
    parameter = Properties()
    try:
        day_delta = int(parameter.properties.get('extract_interval', '1')) + 1  # 质控比抽取间隔要多一天
        today = datetime.now()
        yesterday = today - timedelta(day_delta)
        app.time_limits = {"binganshouye.pat_visit.discharge_time": {"$gte": yesterday.strftime('%Y-%m-%d')}}
        app.PushData.mongodb_collection_name += '_zhongmo'  # 将数据存入终末库
        app.process(True)
        app.process_supplement(collection_name=parameter.properties.get('collection_name', 'MedicalRecordQuality'))  # 将终末三个月的数据分开存储
        return True
    except:
        logger.error(traceback.format_exc())
        return False


def runHuanjie():
    """
    在院：定时（4小时）运行mrq表数据并请求春光接口（检查/检验等数据）
    出院：运行“春光库及mrq表（含出院时间）”
    :return:
    """
    pass


def removeTableMrq():
    """
    每天从mrq表中删除春光入库了的数据, 包括mrq分词好的数据和html原文数据
    """
    logger = LogUtils().getLogger('scheduledTasks')
    try:
        app_mongo = PushDataFromMDBUtils()
        db = app_mongo.connectDataBase(app_mongo.mongodb_database_name)
        tables = db.list_collection_names()
        for mrq_collection in tables:
            if not mrq_collection.startswith('mrq_'):
                continue
            collection_name = mrq_collection.replace('mrq_', '')
            conn_mrq = db.get_collection(mrq_collection)
            conn = db.get_collection(collection_name)
            conn_result = conn.find({}, {})
            for data in conn_result:
                conn_mrq.delete_one({'_id': data['_id']})
        return True
    except:
        logger.error(traceback.format_exc())
        return False


if __name__ == '__main__':
    pass
