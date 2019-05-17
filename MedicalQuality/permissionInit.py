#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
@version: V1.0
@author:
@mail:
@file: permissionInit.py
@time: 2019-03-20 11:17
@description: 权限初始化
"""
from django.conf import settings


def initPermission(request, role_obj, dept_obj):
    """
    初始化用户权限, 写入session
    role_obj 电子病历用户模型
    role_obj.role_mrq 质控病历用户模型
    dept_obj 科室模型
    """
    permission_item_list = role_obj.role_mrq.permissions.values('url', 'title', 'interface', 'parent').distinct()
    permission_url_list = []  # 用户权限url列表，--> 用于中间件验证用户权限[{"title":xxx, "url":xxx},{},]
    permission_interface_list = []  # 用户权限接口列表，--> [{"title":xxx, "interface": xxx},{},]

    for item in permission_item_list:
        if item['url']:
            # temp = {"title": item['title'],
            #         "url": item["url"]}
            permission_url_list.append(item["url"])
        if item['interface']:
            # temp = {"title": item['title'],
                    # "interface": item["interface"]}
            permission_interface_list.append(item["interface"])

    # 注：session在存储时，会先对数据进行序列化，因此对于Queryset对象写入session， 加list()转为可序列化对象

    # 保存用户权限url列表
    request.session[settings.SESSION_PERMISSION_URL_KEY] = permission_url_list
    request.session[settings.SESSION_PERMISSION_INTERFACE_KEY] = permission_interface_list
    request.session['role'] = role_obj.ROLE_A_NAME
    request.session['role_id'] = role_obj.ROLE_A_ID
    request.session['dept'] = dept_obj.DEPT_NAME
