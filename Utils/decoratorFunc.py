#!/usr/bin/env python3
# -*- coding:utf-8 -*

"""
@version: 
@author:
@contact:
@software: PyCharm Community Edition
@file: runtime_class_method.py
@time: 18-10-29 上午11:20
@description: 装饰器函数
"""
import os
import sys
import json
import traceback
from functools import wraps
from datetime import datetime
cur_path = os.path.abspath(os.path.dirname(__file__))
root_path = os.path.split(cur_path)[0]
sys.path.append(root_path)  # 项目路径添加到系统路径

from django.http import HttpResponse
from Utils.LogUtils import LogUtils


def run_time(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = datetime.now()
        print('{0}, {1} start...'.format(start_time, func.__name__))
        try:
            r = func(self, *args, **kwargs)
        except:
            r = kwargs
            print(traceback.format_exc())
            return r
        end_time = datetime.now()
        print('{0}, {1} end...'.format(end_time, func.__name__))
        cost_time = (end_time - start_time).total_seconds()
        print('{0}s taken for {1}'.format(cost_time, func.__name__))
        return r
    return wrapper


def views_log(func):
    """
    视图函数装饰器
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = LogUtils().getLogger('backend')
        try:
            return func(*args, **kwargs)
        except:
            logger.error(traceback.format_exc())
            exc_type, exc_value, exc_traceback_obj = sys.exc_info()
            try:
                r = HttpResponse(json.dumps({'error_func': func.__name__,
                                             'error_info': '.'.join(exc_value.args),
                                             'error_type': exc_type.__name__,
                                             'abnormal_info': ''.join(traceback.format_tb(exc_traceback_obj)),
                                             'res_flag': False}))
            except:
                r = HttpResponse(json.dumps({'error_func': func.__name__,
                                             'abnormal_info': ''.join(traceback.format_tb(exc_traceback_obj)),
                                             'res_flag': False}))
            r.status_code = 500
            return r
    return wrapper
