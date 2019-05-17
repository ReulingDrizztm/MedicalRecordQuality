#!/usr/bin/env python3
# -*- coding:utf-8 -*-

from django.conf import settings
from django.shortcuts import HttpResponse
import re
import json


class MiddlewareMixin(object):
    def __init__(self, get_response=None):
        self.get_response = get_response
        super(MiddlewareMixin, self).__init__()

    def __call__(self, request):
        response = None
        if hasattr(self, 'process_request'):
            response = self.process_request(request)
        if not response:
            response = self.get_response(request)
        if hasattr(self, 'process_response'):
            response = self.process_response(request, response)
        return response


class MedicalQualityMiddleware(MiddlewareMixin):
    """
    检查用户的url请求是否是其权限范围内
    先过登陆前白名单，再看是否过期，再看是否是超级用户，再过白名单，最后看权限
    """
    @staticmethod
    def process_request(request):
        request_url = request.META.get('HTTP_REFERER')  # 访问地址
        request_interface = request.path_info  # 访问接口
        request.session.set_expiry(1800)  # 30分钟超时

        # 登陆前白名单
        for interface in settings.SAFE_INTERFACE_BEFORE_LOGIN:
            if re.match(interface, request_interface):
                return None
        if request_url is not None:
            for url in settings.SAFE_URL_BEFORE_LOGIN:
                if url in request_url:
                    return None

        # 是否登陆，是否是超级用户
        if request.user.is_anonymous:
            return HttpResponse(json.dumps({'login_flag': False, 'info': '请重新登陆'}))
        if request.user.is_superuser:
            return None

        # 如果请求在登陆后白名单，放行
        if request_url is not None:
            for url in settings.SAFE_URL:
                if url in request_url:
                    return None
        for interface in settings.SAFE_INTERFACE:
            if re.match(interface, request_interface):
                return None

        # 查看权限
        permission_url = request.session.get(settings.SESSION_PERMISSION_URL_KEY)
        permission_interface = request.session.get(settings.SESSION_PERMISSION_INTERFACE_KEY)
        if not (permission_url or permission_interface):
            return HttpResponse(json.dumps({'login_flag': False, 'info': '该角色无权限'}))
        flag = False
        if request_url is not None:
            if permission_url:
                for url in permission_url:
                    url_pattern = settings.REGEX_URL.format(url=url)
                    if url_pattern.endswith('.html') and url_pattern in request_url:
                        flag = True
                        break
                    if not request_url.endswith('.html'):  # 首页直接访问
                        flag = True
                        break
        if permission_interface:
            flag = False
            for interface in permission_interface:
                interface_pattern = settings.REGEX_INTERFACE.format(interface=interface)
                if re.match(interface_pattern, request_interface):
                    flag = True
                    break
        if flag:
            return None
        else:
            # 如果是调试模式，显示可访问url
            if settings.DEBUG:
                info = '<br/>' + ('<br/>'.join(permission_url))
                return HttpResponse('无权限，请尝试访问以下地址：%s' % info)
            else:
                return HttpResponse(json.dumps({'login_flag': False, 'info': '无权限访问'}))
