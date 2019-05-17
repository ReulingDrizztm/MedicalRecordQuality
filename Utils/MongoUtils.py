#!/usr/bin/env python3
# -*- coding:utf-8 -*

"""
@version: v1.0
@author:
@contact:
@software: PyCharm
@file: MongoUtils.py
@time: 26/06/18 下午 07:22
@description: 
"""
import os
import sys
cur_path = os.path.abspath(os.path.dirname(__file__))
root_path = os.path.split(cur_path)[0]
sys.path.append(root_path)  # 项目路径添加到系统路径
from pymongo import MongoClient
import traceback
from Utils.loadingConfigure import Properties
from pymongo.errors import DuplicateKeyError
from Utils.LogUtils import LogUtils


class MongoUtils(object):
    def __init__(self, debug=False):
        self.debug = debug

        # region 从properties文件中获取资源配置信息
        self.parameters = Properties()
        self.logger = LogUtils().getLogger("MongoUtils")
        self.mongodb_host = self.parameters.properties.get('mongo_host')
        self.mongodb_port = eval(self.parameters.properties.get('mongo_port'))
        self.mongodb_database_name = self.parameters.properties.get('mongodb')
        self.mongodb_collection_name = self.parameters.properties.get('collection_name')
        self.mongodb_collection_name_doctor = '{}_doctor'.format(self.mongodb_collection_name)
        self.mongodb_collection_name_huanjie = '{}_huanjie'.format(self.mongodb_collection_name)
        self.mongodb_collection_name_zhongmo = '{}_zhongmo'.format(self.mongodb_collection_name)
        self.username_wr = self.parameters.properties.get('username_write_read')
        self.password_wr = self.parameters.properties.get('password_write_read')
        # endregion

        # 数据库的连接操作
        self.client = MongoClient(host=self.mongodb_host, port=self.mongodb_port, connect=False)

        # 文书库
        if self.parameters.properties.get('record_host'):
            record_host = self.parameters.properties.get('record_host')
            record_port = eval(self.parameters.properties.get('record_port'))
            record_database = self.parameters.properties.get('record_mongodb')
            record_client = MongoClient(host=record_host, port=record_port, connect=False)
            self.record_db = record_client.get_database(name=record_database)
            if self.parameters.properties.get('record_auth') in ['true', 'True']:
                username = self.parameters.properties.get('record_username')
                password = self.parameters.properties.get('record_password')
                self.record_db.authenticate(username, password)
        else:
            self.record_db = self.connectDataBase()
        self.authed = False

    def _isAuth(self):
        if self.parameters.properties.get('mongo_auth') == 'false':
            return False
        if self.parameters.properties.get('mongo_auth') == 'False':
            return False
        return True

    def identifyAuth(self):
        """
        验证配置是否能通过数据库权限验证
        :return:
        """
        if self._isAuth():
            client = MongoClient(host=self.mongodb_host, port=self.mongodb_port, connect=False)
            db = client.get_database(name=self.mongodb_database_name)
            try:
                return db.authenticate(self.username_wr, self.password_wr)
            except:
                return False
        return True

    def connectDataBase(self, database_name=None):
        """
        功能:连接到指定的数据库
        """
        try:
            if database_name is None:
                db = self.client.get_database(name=self.mongodb_database_name)
            else:
                db = self.client.get_database(name=database_name)
            if self._isAuth():
                if self.authed:
                    db.logout()
                db.authenticate(self.username_wr, self.password_wr)
                self.authed = True
            return db
        except:
            self.logger.error(traceback.format_exc())

    def connectCollection(self, database_name, collection_name):
        """
        功能:获取数据库中指定的表
        """
        try:
            db = self.client.get_database(name=database_name)
            if self._isAuth():
                if self.authed:
                    db.logout()
                db.authenticate(self.username_wr, self.password_wr)
                self.authed = True
            collection = db.get_collection(name=collection_name)
            return collection
        except:
            self.logger.error(traceback.format_exc())


class PullDataFromMDBUtils(MongoUtils):

    def connection(self, collection_name=None):
        """
        功能:数据库连接
        """
        db = self.connectDataBase(database_name=self.mongodb_database_name)

        if not collection_name:
            collection = db.get_collection(name=self.mongodb_collection_name)
        else:
            collection = db.get_collection(name=collection_name)
        return collection


class PushDataFromMDBUtils(MongoUtils):

    def pushData(self, collection_name, data):
        """
        功能：将data数据推送到配置文件指定的database和collection中
        """
        collection = self.connectCollection(self.mongodb_database_name, collection_name=collection_name)
        key_list = list(data.keys())
        for key in key_list:
            if key == '':
                data.pop('')
        try:
            data_id = data['_id']
            result_status = collection.update({'_id': data_id}, {"$set": data}, upsert=True)

            if result_status and isinstance(result_status, dict) and 'updatedExisting' in result_status:
                self.logger.info('update id {0} in {1} succeed'.format(data_id, collection_name))
                return True
            else:
                self.logger.warning('update id {0} in {2} failed\n\t{1}'.format(data_id, result_status, collection_name))
                return False
        except DuplicateKeyError:
            data_id = data['_id']
            collection.update({'_id': data_id}, {"$set": data})
            self.logger.info('update id {0} in {1} succeed'.format(data_id, collection_name))
            return True
        except:
            self.logger.error("ERROR:[{0}]".format(traceback.format_exc()))
            return False


if __name__ == '__main__':
    app = PushDataFromMDBUtils()
    x = app.identifyAuth()
