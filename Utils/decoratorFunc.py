#!/usr/bin/env python3
# -*- coding:utf-8 -*

# 装饰器函数

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
    """统计函数执行时间"""
    @wraps(func)
    # def wrapper(*args, **kwargs):
    # 此处没有使用到类，如果在函数内加上 self 参数的话，相当于函数必须要至少传一个参数
    # 但是调用的函数是不需要传递参数的，并且 self 是类里面的函数自带的一个参数，所以这里需要把 self 参数去掉
    def wrapper(self, *args, **kwargs):
        start_time = datetime.now()
        print('{0}, {1} start...'.format(start_time, func.__name__))
        try:
            # 这里需要把 self 参数去掉，理由同上
            # r = func(*args, **kwargs)
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
    视图函数装饰器，捕捉程序异常
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
