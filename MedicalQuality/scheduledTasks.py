#!/usr/bin/env python3
# -*- coding:utf-8 -*-

# 跑定时任务

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
from MedicalQuality.statisticPatientsInfos import StatisticPatientInfos


def runZhongmo():
    """
    每天更新终末库数据
    """
    app = CheckMultiRecords(debug=True)
    logger = LogUtils().getLogger('scheduledTasks')
    parameter = Properties()
    try:
        day_delta = int(parameter.properties.get('extract_interval', '1')) + 1  # 质控比抽取间隔要多一天
        today = datetime.now()
        yesterday = today - timedelta(day_delta)
        if today.day == 1:
            collection_ori = app.PushData.mongodb_collection_name + '_last_two_month'
            rename_collection = app.PushData.mongodb_collection_name + '_last_two_month_bak'
            collection = app.PushData.connectCollection(database_name=app.PushData.mongodb_database_name,
                                                        collection_name=collection_ori)
            try:
                collection.rename(rename_collection, dropTarget=True)
            except:
                logger.warning('No collection {0}'.format(collection_ori))

            collection_ori = app.PushData.mongodb_collection_name + '_last_month'
            rename_collection = app.PushData.mongodb_collection_name + '_last_two_month'
            collection = app.PushData.connectCollection(database_name=app.PushData.mongodb_database_name,
                                                        collection_name=collection_ori)
            try:
                collection.rename(rename_collection, dropTarget=True)
            except:
                logger.warning('No collection {0}'.format(collection_ori))

            collection_ori = app.PushData.mongodb_collection_name + '_this_month'
            rename_collection = app.PushData.mongodb_collection_name + '_last_month'
            collection = app.PushData.connectCollection(database_name=app.PushData.mongodb_database_name,
                                                        collection_name=collection_ori)
            try:
                collection.rename(rename_collection, dropTarget=True)
            except:
                logger.warning('No collection {0}'.format(collection_ori))
        app.time_limits = {"binganshouye.pat_visit.discharge_time": {"$gte": yesterday.strftime('%Y-%m-%d')}}
        app.PushData.mongodb_collection_name += '_zhongmo'
        app.process(True)
        app.process_supplement(collection_name=parameter.properties.get('collection_name', 'MedicalRecordQuality'))  # 只存终末的三个月数据
        return True
    except:
        logger.error(traceback.format_exc())
        return False


def calcTotalDocument():
    """
    每天定时查询近三个月病案首页文档数,记录出院患者ID及其科室
    """
    logger = LogUtils().getLogger('scheduledTasks')
    app_mongo = PushDataFromMDBUtils()
    app = StatisticPatientInfos()
    conn = app_mongo.connectCollection(database_name=app_mongo.mongodb_database_name,
                                       collection_name='MedicalRecordQuality_zhongmo')
    try:
        this_month = app.this_month()
        last_month = app.last_month()
        last_two_month = app.last_two_month()
        today = datetime.now()
        if today.day == 1:
            collection_ori = 'total_zhongmo_last_two_month'
            rename_collection = 'total_zhongmo_last_two_month_bak'
            collection = app_mongo.connectCollection(database_name=app_mongo.mongodb_database_name,
                                                     collection_name=collection_ori)
            try:
                collection.rename(rename_collection, dropTarget=True)
            except:
                logger.warning('No collection {0}'.format(collection_ori))

            collection_ori = 'total_zhongmo_last_month'
            rename_collection = 'total_zhongmo_last_two_month'
            collection = app_mongo.connectCollection(database_name=app_mongo.mongodb_database_name,
                                                     collection_name=collection_ori)
            try:
                collection.rename(rename_collection, dropTarget=True)
            except:
                logger.warning('No collection {0}'.format(collection_ori))

            collection_ori = 'total_zhongmo_this_month'
            rename_collection = 'total_zhongmo_last_month'
            collection = app_mongo.connectCollection(database_name=app_mongo.mongodb_database_name,
                                                     collection_name=collection_ori)
            try:
                collection.rename(rename_collection, dropTarget=True)
            except:
                logger.warning('No collection {0}'.format(collection_ori))

        mongo_result = conn.find({'pat_info.discharge_time': {'$gt': this_month[0], '$lt': this_month[1]}}, {'pat_info.dept_discharge_from_name': 1})
        for data in mongo_result:
            push_data = {'_id': data['_id']}
            if not data.get('pat_info', dict()).get('dept_discharge_from_name'):
                continue
            push_data['dept'] = data['pat_info']['dept_discharge_from_name']
            app_mongo.pushData('total_zhongmo_this_month', push_data)

        mongo_result = conn.find({'pat_info.discharge_time': {'$gt': last_month[0], '$lt': last_month[1]}}, {'pat_info.dept_discharge_from_name': 1})
        for data in mongo_result:
            push_data = {'_id': data['_id']}
            if not data.get('pat_info', dict()).get('dept_discharge_from_name'):
                continue
            push_data['dept'] = data['pat_info']['dept_discharge_from_name']
            app_mongo.pushData('total_zhongmo_last_month', push_data)

        mongo_result = conn.find({'pat_info.discharge_time': {'$gt': last_two_month[0], '$lt': last_two_month[1]}}, {'pat_info.dept_discharge_from_name': 1})
        for data in mongo_result:
            push_data = {'_id': data['_id']}
            if not data.get('pat_info', dict()).get('dept_discharge_from_name'):
                continue
            push_data['dept'] = data['pat_info']['dept_discharge_from_name']
            app_mongo.pushData('total_zhongmo_last_two_month', push_data)
        return True
    except:
        logger.error(traceback.format_exc())
        return False


def removeTableMrq():
    """
    每天从mrq表中删除春光入库了的数据
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
