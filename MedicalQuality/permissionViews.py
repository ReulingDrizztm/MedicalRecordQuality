#!/usr/bin/env python3
# -*- coding:utf-8 -*

"""
@version: 
@author:
@contact:
@software: PyCharm Community Edition
@file: permissionViews.py
@time: 18-10-26 下午3:10
@description: 权限接口视图页
"""
import json
import os
import sys
import xlrd
cur_path = os.path.abspath(os.path.dirname(__file__))
root_path = os.path.split(cur_path)[0]
sys.path.append(root_path)  # 项目路径添加到系统路径
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from MedicalQuality.models import User, Role, RoleAnotherName, Permission, Dept, District
from MedicalQuality.permissionInit import initPermission
from Utils.decoratorFunc import views_log
from datetime import datetime


@views_log
def userRegister(request):
    """
    用户注册
    """
    if request.method == 'POST':
        username = ''
        password = ''
        USER_ID = ''
        USER_NAME = ''
        USER_DEPT = ''
        EDUCATION_TITLE = ''
        GROUP_CODE = ''
        USER_TYPE = ''
        IS_ROUNDS = ''
        LOCKED_TIME = ''
        ROLE_NAME = ''
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            username = data.get('USER_LOGIN_NAME', '')
            password = data.get('password', '')
            USER_ID = data.get('USER_LOGIN_NAME', '')
            USER_NAME = data.get('USER_NAME', '')
            USER_DEPT = data.get('USER_DEPT', '')
            EDUCATION_TITLE = data.get('EDUCATION_TITLE', '')
            GROUP_CODE = data.get('GROUP_CODE', '')
            USER_TYPE = data.get('USER_TYPE')
            IS_ROUNDS = data.get('IS_ROUNDS')
            LOCKED_TIME = data.get('LOCKED_TIME')
            ROLE_NAME = data.get('ROLE_NAME', '')

        elif request.content_type == 'multipart/form-data':
            username = request.POST.get('USER_LOGIN_NAME', '')
            password = request.POST.get('password', '')
            USER_ID = request.POST.get('USER_LOGIN_NAME', '')
            USER_NAME = request.POST.get('USER_NAME', '')
            USER_DEPT = request.POST.get('USER_DEPT', '')
            EDUCATION_TITLE = request.POST.get('EDUCATION_TITLE', '')
            GROUP_CODE = request.POST.get('GROUP_CODE', '')
            USER_TYPE = request.POST.get('USER_TYPE')
            IS_ROUNDS = request.POST.get('IS_ROUNDS')
            LOCKED_TIME = request.POST.get('LOCKED_TIME')
            ROLE_NAME = request.POST.get('ROLE_NAME', '')
        if not username:
            return HttpResponse(json.dumps({'res_flag': False, 'info': u'请输入用户名'}))
        if not password:
            return HttpResponse(json.dumps({'res_flag': False, 'info': u'请输入密码'}))
        if not ROLE_NAME:
            return HttpResponse(json.dumps({'res_flag': False, 'info': u'请分配给用户相应角色'}))
        if not USER_DEPT:
            return HttpResponse(json.dumps({'res_flag': False, 'info': u'请分配给用户相应科室'}))
        if User.objects.filter(username=username).exists():
            data = {'res_flag': False, 'info': u'用户已存在'}
            return HttpResponse(json.dumps(data))
        else:
            dept_obj = Dept.objects.filter(DEPT_NAME=USER_DEPT).first()
            user = User.objects.create_user(username=username,
                                            password=password,
                                            USER_ID=USER_ID,
                                            USER_NAME=USER_NAME,
                                            EDUCATION_TITLE=EDUCATION_TITLE,
                                            GROUP_CODE=GROUP_CODE,
                                            USER_TYPE=USER_TYPE,
                                            IS_ROUNDS=IS_ROUNDS,
                                            LOCKED_TIME=LOCKED_TIME)
            if user is not None:
                user.is_active = True
                role_obj = RoleAnotherName.objects.filter(ROLE_A_NAME=ROLE_NAME).first()
                user.role.add(role_obj)
                user.dept.add(dept_obj)
                user.save()
            return HttpResponse(json.dumps({'res': True}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def userLoginPre(request):
    """
    返回用户科室和角色列表
    """
    if request.method == 'POST':
        username = ''
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            username = data.get('USER_LOGIN_NAME', '')
        elif request.content_type == 'multipart/form-data':
            username = request.POST.get('USER_LOGIN_NAME', '')
        if username:
            user_obj = User.objects.filter(username=username).first()
            if not user_obj:
                return HttpResponse(json.dumps({'res_flag': False, 'info': '没有这个账户'}))

            dept = userDept(user_obj)
            role = userRole(user_obj)
            return HttpResponse(json.dumps({'res_flag': True, 'dept': dept, 'role': role}))
        else:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请输入用户名'}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def userLogin(request):
    """
    用户登陆
    """
    if request.method == 'POST':
        username = ''
        password = ''
        ROLE_NAME = ''
        USER_DEPT = ''
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            username = data.get('USER_LOGIN_NAME', '')
            password = data.get('password', '')
            ROLE_NAME = data.get('ROLE_NAME', '')
            USER_DEPT = data.get('USER_DEPT', '')
        elif request.content_type == 'multipart/form-data':
            username = request.POST.get('USER_LOGIN_NAME', '')
            password = request.POST.get('password', '')
            ROLE_NAME = request.POST.get('ROLE_NAME', '')
            USER_DEPT = request.POST.get('USER_DEPT', '')
        if not User.objects.filter(username=username).exists():
            return HttpResponse(json.dumps({'res_flag': False, 'info': '用户名错误'}))
        user = authenticate(username=username, password=password)
        if user:
            if user.is_active:
                if user.is_superuser:
                    login(request, user)
                    return HttpResponse(json.dumps({'res_flag': True}))
                if not ROLE_NAME:
                    return HttpResponse(json.dumps({'res_flag': False, 'info': '请选择角色'}))
                if not USER_DEPT:
                    return HttpResponse(json.dumps({'res_flag': False, 'info': '请选择科室'}))
                login(request, user)
                role_obj = user.role.filter(ROLE_A_NAME=ROLE_NAME).first()
                if not role_obj:
                    return HttpResponse(json.dumps({'res_flag': False, 'info': '该用户没有这个角色'}))
                dept_obj = user.dept.filter(DEPT_NAME=USER_DEPT).first()
                if not dept_obj:
                    return HttpResponse(json.dumps({'res_flag': False, 'info': '该用户没有这个科室'}))
                if not role_obj.role_mrq:
                    return HttpResponse(json.dumps({'res_flag': False, 'info': '该电子病历角色未绑定质控项目角色'}))
                initPermission(request, role_obj, dept_obj)  # 在这里为用户分配角色，初始化其权限
                permission_list = role_obj.role_mrq.permissions.values('title', 'parent').distinct()
                permission_info = dict()
                for i in permission_list:
                    if i.get('parent'):
                        permission_info.setdefault(i.get('parent'), list())
                        permission_info[i.get('parent')].append(i.get('title'))
                return HttpResponse(json.dumps({'res_flag': True, 'permission_info': permission_info}))
            else:
                return HttpResponse(json.dumps({'res_flag': False, 'info': '未启用的账户'}))
        else:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '密码错误'}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def userResetPassword(request):
    """
    重置密码
    """
    if request.method == 'POST':
        username = ''
        password = ''
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            username = data.get('USER_LOGIN_NAME', '')
            password = data.get('password', '')
        elif request.content_type == 'multipart/form-data':
            username = request.POST.get('USER_LOGIN_NAME', '')
            password = request.POST.get('password', '')
        if not username:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请求中没有用户名'}))
        if not password:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请输入新密码'}))
        user_obj = User.objects.filter(username=username).first()
        user_obj.set_password(password)
        user_obj.save()
        login(request, user_obj)
        return HttpResponse(json.dumps({'res_flag': True}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def userModifyPassword(request):
    """
    修改密码
    """
    if request.method == 'POST':
        username = ''
        password_ori = ''
        password = ''
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            username = data.get('USER_LOGIN_NAME', '')
            password = data.get('password', '')
            password_ori = data.get('password_ori', '')
        elif request.content_type == 'multipart/form-data':
            username = request.POST.get('USER_LOGIN_NAME', '')
            password = request.POST.get('password', '')
            password_ori = request.POST.get('password_ori', '')
        if not username:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请求中没有用户名'}))
        if not password:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请输入新密码'}))
        if not password_ori:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请输入原始密码'}))
        user_obj = User.objects.filter(username=username).first()
        if user_obj.check_password(password_ori):
            user_obj.set_password(password)
            user_obj.save()
            login(request, user_obj)
        else:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '密码错误'}))
        return HttpResponse(json.dumps({'res_flag': True}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def userSwitchDeptRole(request):
    """
    切换角色和科室
    """
    if request.method == 'POST':
        username = ''
        ROLE_NAME = ''
        USER_DEPT = ''
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            username = data.get('USER_LOGIN_NAME', '')
            ROLE_NAME = data.get('ROLE_NAME', '')
            USER_DEPT = data.get('USER_DEPT', '')
        elif request.content_type == 'multipart/form-data':
            username = request.POST.get('USER_LOGIN_NAME', '')
            ROLE_NAME = request.POST.get('ROLE_NAME', '')
            USER_DEPT = request.POST.get('USER_DEPT', '')
        if not ROLE_NAME:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请选择角色'}))
        if not USER_DEPT:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请选择科室'}))
        if username:
            user_obj = User.objects.filter(username=username).first()
            role_obj = user_obj.role.filter(ROLE_A_NAME=ROLE_NAME).first()
            if not role_obj:
                return HttpResponse(json.dumps({'res_flag': False, 'info': '该用户没有这个角色'}))
            dept_obj = user_obj.dept.filter(DEPT_NAME=USER_DEPT).first()
            if not dept_obj:
                return HttpResponse(json.dumps({'res_flag': False, 'info': '该用户没有这个科室'}))
            initPermission(request, role_obj, dept_obj)
            permission_list = role_obj.role_mrq.permissions.values('title', 'parent').distinct()
            permission_info = dict()
            for i in permission_list:
                if i.get('parent'):
                    permission_info.setdefault(i.get('parent'), list())
                    permission_info[i.get('parent')].append(i.get('title'))
            return HttpResponse(json.dumps({'res_flag': True, 'permission_info': permission_info}))
        return HttpResponse(json.dumps({'res_flag': False, 'info': '请求中没有用户名'}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def userEdit(request):
    """
    编辑用户
    """
    if request.method == 'POST':
        username = ''
        USER_ID = ''
        USER_NAME = ''
        EDUCATION_TITLE = ''
        GROUP_CODE = ''
        USER_TYPE = None
        IS_ROUNDS = None
        LOCKED_TIME = None
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            username = data.get('USER_LOGIN_NAME', '')
            USER_ID = data.get('USER_ID', '')
            USER_NAME = data.get('USER_NAME', '')
            EDUCATION_TITLE = data.get('EDUCATION_TITLE', '')
            GROUP_CODE = data.get('GROUP_CODE', '')
            USER_TYPE = None if not data.get('USER_TYPE') else int(data.get('USER_TYPE'))
            IS_ROUNDS = None if not data.get('IS_ROUNDS') else int(data.get('IS_ROUNDS'))
            LOCKED_TIME = None if not data.get('LOCKED_TIME') else int(data.get('LOCKED_TIME'))
        elif request.content_type == 'multipart/form-data':
            username = request.POST.get('USER_LOGIN_NAME', '')
            USER_ID = request.POST.get('USER_ID', '')
            USER_NAME = request.POST.get('USER_NAME', '')
            EDUCATION_TITLE = request.POST.get('EDUCATION_TITLE', '')
            GROUP_CODE = request.POST.get('GROUP_CODE', '')
            USER_TYPE = None if not request.POST.get('USER_TYPE') else int(request.POST.get('USER_TYPE'))
            IS_ROUNDS = None if not request.POST.get('IS_ROUNDS') else int(request.POST.get('IS_ROUNDS'))
            LOCKED_TIME = None if not request.POST.get('LOCKED_TIME') else int(request.POST.get('LOCKED_TIME'))
        if username:
            user_obj = User.objects.filter(username=username).first()
            if not user_obj:
                return HttpResponse(json.dumps({'res_flag': False, 'info': 'no {} in database'.format(username)}))
            field = list()
            if user_obj.USER_ID != USER_ID:
                user_obj.USER_ID = USER_ID
                field.append('USER_ID')
            if user_obj.USER_NAME != USER_NAME:
                user_obj.USER_NAME = USER_NAME
                field.append('USER_NAME')
            if user_obj.EDUCATION_TITLE != EDUCATION_TITLE:
                user_obj.EDUCATION_TITLE = EDUCATION_TITLE
                field.append('EDUCATION_TITLE')
            if user_obj.GROUP_CODE != GROUP_CODE:
                user_obj.GROUP_CODE = GROUP_CODE
                field.append('GROUP_CODE')
            if user_obj.USER_TYPE != USER_TYPE:
                user_obj.USER_TYPE = USER_TYPE
                field.append('USER_TYPE')
            if user_obj.IS_ROUNDS != IS_ROUNDS:
                user_obj.IS_ROUNDS = IS_ROUNDS
                field.append('IS_ROUNDS')
            if user_obj.LOCKED_TIME != LOCKED_TIME:
                user_obj.LOCKED_TIME = LOCKED_TIME
                field.append('LOCKED_TIME')
            if field:
                user_obj.save(update_fields=field)
                info = '{} has been updated.'.format(field)
                return HttpResponse(json.dumps({'res_flag': True, 'info': info}))
            else:
                return HttpResponse(json.dumps({'res_flag': True, 'info': 'no field has been updated.'}))
        else:
            return HttpResponse(json.dumps({'res_flag': False, 'info': 'no USER_LOGIN_NAME in the request'}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def userEditDept(request):
    """
    编辑用户科室
    """
    if request.method == 'POST':
        username = ''
        user_dept = list()
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            username = data.get('USER_LOGIN_NAME', '')
            user_dept = data.get('user_dept', list())
        elif request.content_type == 'multipart/form-data':
            username = request.POST.get('USER_LOGIN_NAME', '')
            user_dept = request.POST.get('user_dept', list())
        if username:
            user_obj = User.objects.filter(username=username).first()  # 用户对象
            dept_list = user_obj.dept.all()  # 该用户的所有科室对象
            result = list()
            if user_dept:
                for i in dept_list:
                    if i.DEPT_NAME not in user_dept:  # 现有科室名不在修改后科室列表中
                        dept_obj = Dept.objects.filter(DEPT_NAME=i.DEPT_NAME).first()
                        user_obj.dept.remove(dept_obj)
                    else:
                        result.append(i.DEPT_NAME)  # 现有科室名在修改后科室列表中
                for i in user_dept:
                    if i not in result:
                        dept_obj = Dept.objects.filter(DEPT_NAME=i).first()
                        user_obj.dept.add(dept_obj)
                        result.append(i)
                return HttpResponse(json.dumps({'res_flag': True, 'info': '，'.join(result)}))
            else:
                return HttpResponse(json.dumps({'res_flag': False, 'info': '请输入科室'}))
        else:
            return HttpResponse(json.dumps({'res_flag': False, 'info': 'no USER_LOGIN_NAME in the request'}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def userEditRole(request):
    """
    编辑用户角色
    """
    if request.method == 'POST':
        username = ''
        user_role = list()
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            username = data.get('USER_LOGIN_NAME', '')
            user_role = data.get('user_role', list())
        elif request.content_type == 'multipart/form-data':
            username = request.POST.get('USER_LOGIN_NAME', '')
            user_role = request.POST.get('user_role', list())
        if username:
            user_obj = User.objects.filter(username=username).first()  # 用户对象
            role_list = user_obj.role.all()  # 该用户的所有科室对象
            result = list()
            if user_role:
                for i in role_list:
                    if i.ROLE_A_NAME not in user_role:  # 现有科室名不在修改后科室列表中
                        role_obj = RoleAnotherName.objects.filter(ROLE_A_NAME=i.ROLE_A_NAME).first()
                        user_obj.role.remove(role_obj)
                    else:
                        result.append(i.ROLE_A_NAME)  # 现有科室名在修改后科室列表中
                for i in user_role:
                    if i not in result:
                        role_obj = RoleAnotherName.objects.filter(ROLE_A_NAME=i).first()
                        user_obj.role.add(role_obj)
                        result.append(i)
                return HttpResponse(json.dumps({'res_flag': True, 'info': '，'.join(result)}))
            else:
                return HttpResponse(json.dumps({'res_flag': False, 'info': '请输入角色'}))
        else:
            return HttpResponse(json.dumps({'res_flag': False, 'info': 'no USER_LOGIN_NAME in the request'}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def userLogout(request):
    """
    用户登出
    """
    if request.method == 'POST':
        logout(request)
        request.session.clear_expired()
        return HttpResponse(json.dumps({'res_flag': True}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def userDelete(request):
    """
    删除用户
    """
    if request.method == 'POST':
        username = ''
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            username = data.get('USER_LOGIN_NAME', '')
        elif request.content_type == 'multipart/form-data':
            username = request.POST.get('USER_LOGIN_NAME', '')
        if isinstance(username, str):
            user_obj = User.objects.filter(username=username).first()
            user_obj.delete()
        elif isinstance(username, list):
            for i in username:
                user_obj = User.objects.filter(username=i).first()
                user_obj.delete()
        return HttpResponse(json.dumps({'res_flag': True}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def userShow(request):
    """
    查看用户
    """
    if request.method == 'POST':
        username = ''
        dept = ''
        result = list()
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            username = data.get('USER_NAME', '')
            dept = data.get('dept', '')
        elif request.content_type == 'multipart/form-data':
            username = request.POST.get('USER_NAME', '')
            dept = request.POST.get('dept', '')
        if dept == '全部':
            dept = ''
        if username:
            if dept:
                dept_obj = Dept.objects.filter(DEPT_NAME=dept).first()
                user_list = dept_obj.user_set.filter(USER_NAME__contains=username)
            else:
                user_list = User.objects.filter(USER_NAME__contains=username)
        else:
            if dept:
                dept_obj = Dept.objects.filter(DEPT_NAME=dept).first()
                user_list = dept_obj.user_set.all()
            else:
                user_list = User.objects.all()
        if user_list:
            for i in user_list:
                if i.is_superuser:
                    continue
                user_dept = userDept(i)
                user_role = userRole(i)
                result.append({
                    'USER_ID': i.USER_ID,
                    'USER_NAME': i.USER_NAME,
                    'USER_LOGIN_NAME': i.username,
                    'EDUCATION_TITLE': i.EDUCATION_TITLE,
                    'ACCOUNT_STATUS': i.is_active,
                    'USER_TYPE': i.USER_TYPE,
                    'IS_ROUNDS': i.IS_ROUNDS,
                    'GROUP_CODE': i.GROUP_CODE,
                    'CREATE_DATE': i.date_joined.strftime("%y-%m-%d %H:%M:%S"),
                    'LOCKED_TIME': i.LOCKED_TIME,
                    'USER_DEPT': '，'.join(user_dept),
                    'USER_ROLE': '，'.join(user_role)
                })
        return HttpResponse(json.dumps({'result': result}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def userUpload(request):
    if request.method == 'POST':
        excel_file = request.FILES.get('file')
        wb = xlrd.open_workbook(file_contents=excel_file.read())
        sheet_obj = wb.sheet_by_index(0)
        nrow = sheet_obj.nrows
        ncol = sheet_obj.ncols
        caption_list = ['USER_ID', 'USER_NAME', 'EDUCATION_TITLE', 'USER_LOGIN_NAME', 'GROUP_CODE', 'USER_TYPE',
                        'IS_ROUNDS', 'LOCKED_TIME', 'ROLE_ID', 'ROLE_NAME', 'USER_DEPT', 'USER_PWD']
        caption_dict = dict()
        for col in range(ncol):
            if sheet_obj.cell_value(0, col) in caption_list:
                caption_dict[sheet_obj.cell_value(0, col)] = col
        if 'USER_LOGIN_NAME' not in caption_dict:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请输入USER_LOGIN_NAME'}))
        if 'USER_PWD' not in caption_dict:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请输入USER_PWD'}))
        if 'ROLE_NAME' not in caption_dict:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请输入ROLE_NAME'}))
        if 'USER_DEPT' not in caption_dict:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请输入USER_DEPT'}))
        for row in range(nrow):
            col = caption_dict['USER_LOGIN_NAME']
            if sheet_obj.cell_type(row, col) == 2:
                username = str(int(sheet_obj.cell_value(row, col))).strip()
            else:
                username = sheet_obj.cell_value(row, col).strip()
            if not username.strip():
                return HttpResponse(json.dumps({'res_flag': False, 'info': '第{}行USER_LOGIN_NAME为空'.format(row+1)}))
        result = dict()
        for row in range(1, nrow):
            username_col = caption_dict['USER_LOGIN_NAME']
            if sheet_obj.cell_type(row, username_col) == 2:
                username = str(int(sheet_obj.cell_value(row, username_col))).strip()
            else:
                username = sheet_obj.cell_value(row, username_col).strip()
            # if username in result:
            #     result[username]['info'] = '第{}行重复用户名'.format(row+1)
            #     continue
            result[username] = {'res_flag': False}
            # if User.objects.filter(username=username).exists():
            #     result[username]['info'] = '用户已经存在'
            #     continue

            password_col = caption_dict['USER_PWD']
            if sheet_obj.cell_type(row, password_col) == 2:
                password = str(int(sheet_obj.cell_value(row, password_col)))
            else:
                password = sheet_obj.cell_value(row, password_col)
            if not password:
                result[username]['info'] = '没有密码'
                continue

            role_col = caption_dict['ROLE_NAME']
            if sheet_obj.cell_type(row, role_col) == 2:
                role = str(int(sheet_obj.cell_value(row, role_col))).strip()
            else:
                role = sheet_obj.cell_value(row, role_col).strip()
            if not RoleAnotherName.objects.filter(ROLE_A_NAME=role).exists():
                result[username]['info'] = '没有角色[{}]'.format(role)
                continue
            else:
                role_obj = RoleAnotherName.objects.filter(ROLE_A_NAME=role).first()

            dept_cole = caption_dict['USER_DEPT']
            if sheet_obj.cell_type(row, dept_cole) == 2:
                dept = str(int(sheet_obj.cell_value(row, dept_cole))).strip()
            else:
                dept = sheet_obj.cell_value(row, dept_cole).strip()
            if not Dept.objects.filter(DEPT_CODE=dept).exists():
                result[username]['info'] = '没有科室[{}]'.format(dept)
                continue
            else:
                dept_obj = Dept.objects.filter(DEPT_CODE=dept).first()
            data = dict()
            for k, v in caption_dict.items():
                if k not in ['USER_ID', 'USER_NAME', 'EDUCATION_TITLE', 'GROUP_CODE', 'USER_TYPE', 'IS_ROUNDS', 'LOCKED_TIME']:
                    continue
                if k != 'LOCKED_TIME':
                    if sheet_obj.cell_type(row, v) == 2:
                        value = str(int(sheet_obj.cell_value(row, v))).strip()
                    else:
                        value = sheet_obj.cell_value(row, v).strip()
                else:
                    if sheet_obj.cell_type(row, v) == 3:
                        value = datetime(*xlrd.xldate_as_tuple(sheet_obj.cell_value(row, v), 0))
                    else:
                        value = None
                data[k] = value
            if User.objects.filter(username=username).exists():
                User.objects.filter(username=username).update(password=password, **data)
                result[username]['res_flag'] = True
            else:
                user_obj = User.objects.create_user(username=username, password=password, **data)
                if user_obj is not None:
                    user_obj.role.add(role_obj)
                    user_obj.dept.add(dept_obj)
                    user_obj.save()
                    result[username]['res_flag'] = True
        return HttpResponse(json.dumps(result))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def roleRegister(request):
    """
    添加角色
    """
    if request.method == 'POST':
        ROLE_ID = ''
        ROLE_NAME = ''
        PERMISSION_TYPE = ''
        ROLE_PERMISSION_ID = None
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            ROLE_ID = data.get('ROLE_ID', '')
            ROLE_NAME = data.get('ROLE_NAME', '')
            PERMISSION_TYPE = data.get('PERMISSION_TYPE', '')
            ROLE_PERMISSION_ID = data.get('ROLE_PERMISSION_ID')

        elif request.content_type == 'multipart/form-data':
            ROLE_ID = request.POST.get('ROLE_ID', '')
            ROLE_NAME = request.POST.get('ROLE_NAME', '')
            PERMISSION_TYPE = request.POST.get('PERMISSION_TYPE', '')
            ROLE_PERMISSION_ID = request.POST.get('ROLE_PERMISSION_ID')
        if not ROLE_NAME:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请输入角色'}))
        if not ROLE_ID:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请输入角色id'}))
        if Role.objects.filter(ROLE_NAME=ROLE_NAME).exists():
            data = {'res_flag': False, 'info': '角色已经存在'}
            return HttpResponse(json.dumps(data))
        else:
            ROLE_PERMISSION_ID = int(ROLE_PERMISSION_ID) if ROLE_PERMISSION_ID else None
            role_obj = Role.objects.create(ROLE_ID=ROLE_ID,
                                           ROLE_NAME=ROLE_NAME,
                                           PERMISSION_TYPE=PERMISSION_TYPE,
                                           ROLE_PERMISSION_ID=ROLE_PERMISSION_ID)
            if role_obj is not None:
                role_obj.save()
            return HttpResponse(json.dumps({'res': True}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def roleEditPermission(request):
    """
    角色编辑权限
    """
    if request.method == 'POST':
        ROLE_NAME = ''
        role_title = list()  # 角色权限列表
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            ROLE_NAME = data.get('ROLE_NAME', '')
            role_title = data.get('role_title', list())
        elif request.content_type == 'multipart/form-data':
            ROLE_NAME = request.POST.get('ROLE_NAME', '')
            role_title = request.POST.get('role_title', list())
        if ROLE_NAME:
            role_obj = Role.objects.filter(ROLE_NAME=ROLE_NAME).first()
            title_list = role_obj.permissions.all()
            result = list()
            if role_title:
                for i in title_list:
                    if i.title not in role_title:
                        permission_obj = Permission.objects.filter(title=i.title).first()
                        role_obj.permissions.remove(permission_obj)
                    else:
                        result.append(i.title)
                for i in role_title:
                    if i not in result:
                        permission_obj = Permission.objects.filter(title=i).first()
                        role_obj.permissions.add(permission_obj)
                        result.append(i)
                return HttpResponse(json.dumps({'res_flag': True, 'info': role_title}))
            else:
                return HttpResponse(json.dumps({'res_flag': False, 'info': '请分配权限'}))
        else:
            return HttpResponse(json.dumps({'res_flag': False, 'info': 'no ROLE_NAME in the request'}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def roleEdit(request):
    """
    编辑角色
    """
    if request.method == 'POST':
        ROLE_NAME = ''
        ROLE_ID = ''
        PERMISSION_TYPE = ''
        ROLE_PERMISSION_ID = None
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            ROLE_NAME = data.get('ROLE_NAME', '')
            ROLE_ID = data.get('ROLE_ID', '')
            PERMISSION_TYPE = data.get('PERMISSION_TYPE', '')
            ROLE_PERMISSION_ID = None if not data.get('ROLE_PERMISSION_ID') else int(data.get('ROLE_PERMISSION_ID'))
        elif request.content_type == 'multipart/form-data':
            ROLE_NAME = request.POST.get('ROLE_NAME', '')
            ROLE_ID = request.POST.get('ROLE_ID', '')
            PERMISSION_TYPE = request.POST.get('PERMISSION_TYPE', '')
            ROLE_PERMISSION_ID = None if not request.POST.get('ROLE_PERMISSION_ID') else int(request.POST.get('ROLE_PERMISSION_ID'))
        if ROLE_NAME:
            role_obj = Role.objects.filter(ROLE_NAME=ROLE_NAME).first()
            if not role_obj:
                return HttpResponse(json.dumps({'res_flag': False, 'info': 'no {} in database'.format(ROLE_NAME)}))
            field = list()
            if role_obj.ROLE_ID != ROLE_ID:
                role_obj.ROLE_ID = ROLE_ID
                field.append('ROLE_ID')
            if role_obj.PERMISSION_TYPE != PERMISSION_TYPE:
                role_obj.PERMISSION_TYPE = PERMISSION_TYPE
                field.append('PERMISSION_TYPE')
            if role_obj.ROLE_PERMISSION_ID != ROLE_PERMISSION_ID:
                role_obj.ROLE_PERMISSION_ID = ROLE_PERMISSION_ID
                field.append('ROLE_PERMISSION_ID')
            if field:
                role_obj.save(update_fields=field)
                info = '{} has been updated.'.format(field)
                return HttpResponse(json.dumps({'res_flag': True, 'info': info}))
            else:
                return HttpResponse(json.dumps({'res_flag': True, 'info': 'no field has been updated.'}))
        else:
            return HttpResponse(json.dumps({'res_flag': True, 'info': 'no ROLE_NAME in the request.'}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def roleShow(request):
    """
    查看角色
    """
    if request.method == 'POST':
        ROLE_NAME = ''
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            ROLE_NAME = data.get('ROLE_NAME', '')
        elif request.content_type == 'multipart/form-data':
            ROLE_NAME = request.POST.get('ROLE_NAME', '')
        if ROLE_NAME:
            role_list = Role.objects.filter(ROLE_NAME=ROLE_NAME)
        else:
            role_list = Role.objects.all()
        result = list()
        if role_list:
            for i in role_list:
                permission_obj_list = i.permissions.all()
                permission_list = list()
                for j in permission_obj_list:
                    permission_list.append(j.title)
                result.append({
                    'ROLE_ID': i.ROLE_ID,
                    'ROLE_NAME': i.ROLE_NAME,
                    'PERMISSION_TYPE': i.PERMISSION_TYPE,
                    'ROLE_PERMISSION_ID': i.ROLE_PERMISSION_ID,
                    'title': '，'.join(permission_list)
                })
        return HttpResponse(json.dumps({'result': result}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def roleDelete(request):
    """
    删除角色
    """
    if request.method == 'POST':
        ROLE_NAME = ''
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            ROLE_NAME = data.get('ROLE_NAME', '')
        elif request.content_type == 'multipart/form-data':
            ROLE_NAME = request.POST.get('ROLE_NAME', '')
        if isinstance(ROLE_NAME, str):
            role_obj = Role.objects.filter(ROLE_NAME=ROLE_NAME).first()
            if role_obj:
                role_obj.delete()
        elif isinstance(ROLE_NAME, list):
            for i in ROLE_NAME:
                role_obj = Role.objects.filter(ROLE_NAME=i).first()
                if role_obj:
                    role_obj.delete()
        return HttpResponse(json.dumps({'res_flag': True}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def permissionRegister(request):
    """
    添加权限
    """
    if request.method == 'POST':
        title = ''
        url = ''
        interface = ''
        parent = ''
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            title = data.get('title', '')
            url = data.get('url', '')
            interface = data.get('interface', '')
            parent = data.get('parent', '')

        elif request.content_type == 'multipart/form-data':
            title = request.POST.get('title', '')
            url = request.POST.get('url', '')
            interface = request.POST.get('interface', '')
            parent = request.POST.get('parent', '')

        if Permission.objects.filter(title=title).exists():
            data = {'res_flag': False, 'info': '权限名已经存在'}
            return HttpResponse(json.dumps(data))
        elif not (url or interface):
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请配置权限具体内容'}))
        else:
            permission_obj = Permission.objects.create(title=title,
                                                       url=url,
                                                       interface=interface,
                                                       parent=parent)
            if permission_obj is not None:
                permission_obj.save()
            return HttpResponse(json.dumps({'res': True}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def permissionEdit(request):
    """
    修改权限
    """
    if request.method == 'POST':
        title = ''
        url = ''
        interface = ''
        parent = ''
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            title = data.get('title', '')
            url = data.get('url', '')
            interface = data.get('interface', '')
            parent = data.get('parent', '')
        elif request.content_type == 'multipart/form-data':
            title = request.POST.get('title', '')
            url = request.POST.get('url', '')
            interface = request.POST.get('interface', '')
            parent = request.POST.get('parent', '')
        if title:
            permission_obj = Permission.objects.filter(title=title).first()
            if not permission_obj:
                return HttpResponse(json.dumps({'res_flag': False, 'info': 'no {} in database'.format(title)}))
            field = list()
            if permission_obj.url != url:
                permission_obj.url = url
                field.append('url')
            if permission_obj.interface != interface:
                permission_obj.interface = interface
                field.append('interface')
            if permission_obj.parent != parent:
                permission_obj.parent = parent
                field.append('parent')
            if field:
                permission_obj.save(update_fields=field)
                info = '{} has been updated.'.format(field)
                return HttpResponse(json.dumps({'res_flag': True, 'info': info}))
            else:
                return HttpResponse(json.dumps({'res_flag': True, 'info': 'no field has been updated.'}))
        else:
            return HttpResponse(json.dumps({'res_flag': True, 'info': '请输入权限名'}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def permissionShow(request):
    """
    查看权限详情
    """
    if request.method == 'POST':
        permission_list = Permission.objects.all()
        result = list()
        for i in permission_list:
            result.append({
                'title': i.title,
                'url': i.url,
                'interface': i.interface,
                'parent': i.parent
            })
        return HttpResponse(json.dumps({'result': result}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def permissionDelete(request):
    """
    删除权限
    """
    if request.method == 'POST':
        title = ''
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            title = data.get('title', '')
        elif request.content_type == 'multipart/form-data':
            title = request.POST.get('title', '')
        if isinstance(title, str):
            permission_obj = Permission.objects.filter(title=title).first()
            permission_obj.delete()
        elif isinstance(title, list):
            for i in title:
                permission_obj = Permission.objects.filter(title=i).first()
                permission_obj.delete()
        return HttpResponse(json.dumps({'res_flag': True}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def roleAnotherNameRegister(request):
    """
    添加电子病历角色名
    """
    if request.method == 'POST':
        ROLE_A_ID = ''
        ROLE_A_NAME = ''
        PERMISSION_A_TYPE = ''
        ROLE_A_PERMISSION_ID = ''
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            ROLE_A_ID = data.get('ROLE_A_ID', '')
            ROLE_A_NAME = data.get('ROLE_A_NAME', '')
            PERMISSION_A_TYPE = data.get('PERMISSION_A_TYPE', '')
            ROLE_A_PERMISSION_ID = data.get('ROLE_A_PERMISSION_ID', '')

        elif request.content_type == 'multipart/form-data':
            ROLE_A_ID = request.POST.get('ROLE_A_ID', '')
            ROLE_A_NAME = request.POST.get('ROLE_A_NAME', '')
            PERMISSION_A_TYPE = request.POST.get('PERMISSION_A_TYPE', '')
            ROLE_A_PERMISSION_ID = request.POST.get('ROLE_A_PERMISSION_ID', '')
        if not ROLE_A_NAME:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请输入角色名'}))
        if not ROLE_A_ID:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请输入id'}))
        if RoleAnotherName.objects.filter(ROLE_A_NAME=ROLE_A_NAME).exists():
            data = {'res_flag': False, 'info': '电子病历角色表中该角色已经存在'}
            return HttpResponse(json.dumps(data))
        else:
            ROLE_A_PERMISSION_ID = int(ROLE_A_PERMISSION_ID) if ROLE_A_PERMISSION_ID else None
            role_obj = RoleAnotherName.objects.create(ROLE_A_ID=ROLE_A_ID,
                                                      ROLE_A_NAME=ROLE_A_NAME,
                                                      PERMISSION_A_TYPE=PERMISSION_A_TYPE,
                                                      ROLE_A_PERMISSION_ID=ROLE_A_PERMISSION_ID)
            if role_obj is not None:
                role_obj.save()
            return HttpResponse(json.dumps({'res': True}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def roleAnotherNameEdit(request):
    """
    修改电子病历角色
    """
    if request.method == 'POST':
        ROLE_A_NAME = ''
        ROLE_A_ID = ''
        PERMISSION_A_TYPE = ''
        ROLE_A_PERMISSION_ID = None
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            ROLE_A_NAME = data.get('ROLE_A_NAME', '')
            ROLE_A_ID = data.get('ROLE_A_ID', '')
            PERMISSION_A_TYPE = data.get('PERMISSION_A_TYPE', '')
            ROLE_A_PERMISSION_ID = None if not data.get('ROLE_A_PERMISSION_ID') else int(data.get('ROLE_A_PERMISSION_ID'))
        elif request.content_type == 'multipart/form-data':
            ROLE_A_NAME = request.POST.get('ROLE_A_NAME', '')
            ROLE_A_ID = request.POST.get('ROLE_A_ID', '')
            PERMISSION_A_TYPE = request.POST.get('PERMISSION_A_TYPE', '')
            ROLE_A_PERMISSION_ID = None if not request.POST.get('ROLE_A_PERMISSION_ID') else int(request.POST.get('ROLE_A_PERMISSION_ID'))
        if ROLE_A_NAME:
            role_a_obj = RoleAnotherName.objects.filter(ROLE_A_NAME=ROLE_A_NAME).first()
            if not role_a_obj:
                return HttpResponse(json.dumps({'res_flag': False, 'info': 'no {} in database'.format(ROLE_A_NAME)}))
            field = list()
            if role_a_obj.ROLE_A_ID != ROLE_A_ID:
                role_a_obj.ROLE_A_ID = ROLE_A_ID
                field.append('ROLE_A_ID')
            if role_a_obj.PERMISSION_A_TYPE != PERMISSION_A_TYPE:
                role_a_obj.PERMISSION_A_TYPE = PERMISSION_A_TYPE
                field.append('PERMISSION_A_TYPE')
            if role_a_obj.ROLE_A_PERMISSION_ID != ROLE_A_PERMISSION_ID:
                role_a_obj.ROLE_A_PERMISSION_ID = ROLE_A_PERMISSION_ID
                field.append('ROLE_A_PERMISSION_ID')
            if field:
                role_a_obj.save(update_fields=field)
                info = '{} has been updated.'.format(field)
                return HttpResponse(json.dumps({'res_flag': True, 'info': info}))
            else:
                return HttpResponse(json.dumps({'res_flag': True, 'info': 'no field has been updated.'}))
        else:
            return HttpResponse(json.dumps({'res_flag': True, 'info': 'no ROLE_A_NAME in the request.'}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def roleAnotherNameShow(request):
    """
    查看电子病历角色表
    """
    if request.method == 'POST':
        ROLE_A_NAME = ''
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            ROLE_A_NAME = data.get('ROLE_A_NAME', '')
        elif request.content_type == 'multipart/form-data':
            ROLE_A_NAME = request.POST.get('ROLE_A_NAME', '')
        if ROLE_A_NAME:
            role_a_list = RoleAnotherName.objects.filter(ROLE_A_NAME=ROLE_A_NAME)
        else:
            role_a_list = RoleAnotherName.objects.all()
        result = list()
        if role_a_list:
            for i in role_a_list:
                data = {
                    'ROLE_A_ID': i.ROLE_A_ID,
                    'ROLE_A_NAME': i.ROLE_A_NAME,
                    'PERMISSION_A_TYPE': i.PERMISSION_A_TYPE,
                    'ROLE_A_PERMISSION_ID': i.ROLE_A_PERMISSION_ID,
                }
                if i.role_mrq:
                    data['MRQ_ROLE'] = i.role_mrq.ROLE_NAME
                result.append(data)
        return HttpResponse(json.dumps({'result': result}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def roleAnotherNameUpload(request):
    if request.method == 'POST':
        excel_file = request.FILES.get('file')
        wb = xlrd.open_workbook(filename=None, file_contents=excel_file.read())
        sheet_obj = wb.sheet_by_index(0)
        nrow = sheet_obj.nrows
        ncol = sheet_obj.ncols
        caption_list = ['ROLE_ID', 'ROLE_NAME', 'PERMISSION_TYPE', 'ROLE_PERMISSION_ID']
        caption_dict = dict()
        for col in range(ncol):
            if sheet_obj.cell_value(0, col) in caption_list:
                caption_dict[sheet_obj.cell_value(0, col)] = col
        if 'ROLE_ID' not in caption_dict:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请输入ROLE_ID'}))
        if 'ROLE_NAME' not in caption_dict:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请输入ROLE_NAME'}))
        for row in range(nrow):
            col = caption_dict['ROLE_ID']
            if sheet_obj.cell_type(row, col) == 2:
                ROLE_ID = str(int(sheet_obj.cell_value(row, col))).strip()
            else:
                ROLE_ID = sheet_obj.cell_value(row, col).strip()
            if not ROLE_ID:
                return HttpResponse(json.dumps({'res_flag': False, 'info': '第{}行ROLE_ID为空'.format(row+1)}))
        result = dict()
        for row in range(1, nrow):
            id_col = caption_dict['ROLE_ID']
            if sheet_obj.cell_type(row, id_col) == 2:
                role_id = str(int(sheet_obj.cell_value(row, id_col))).strip()
            else:
                role_id = sheet_obj.cell_value(row, id_col).strip()
            # if role_id in result:
            #     result[role_id]['info'] = '第{}行重复角色ID'.format(row+1)
            #     continue
            result[role_id] = {'res_flag': False}
            # if RoleAnotherName.objects.filter(ROLE_A_ID=role_id).exists():
            #     result[role_id]['info'] = '角色已经存在'
            #     continue

            name_col = caption_dict['ROLE_NAME']
            if sheet_obj.cell_type(row, name_col) == 2:
                role_name = str(int(sheet_obj.cell_value(row, name_col))).strip()
            else:
                role_name = sheet_obj.cell_value(row, name_col).strip()
            if not role_name:
                result[role_id]['info'] = '没有角色名'
                continue

            data = {'ROLE_A_ID': role_id, 'ROLE_A_NAME': role_name}

            type_col = caption_dict['PERMISSION_TYPE']
            if sheet_obj.cell_type(row, type_col) == 2:
                permission_type = str(int(sheet_obj.cell_value(row, type_col))).strip()
            else:
                permission_type = sheet_obj.cell_value(row, type_col).strip()
            if permission_type:
                data['PERMISSION_A_TYPE'] = permission_type
                
            permission_col = caption_dict['ROLE_PERMISSION_ID']
            if sheet_obj.cell_type(row, permission_col) == 2:
                role_permission = str(int(sheet_obj.cell_value(row, permission_col))).strip()
            else:
                role_permission = sheet_obj.cell_value(row, permission_col).strip()
            if permission_type:
                data['ROLE_A_PERMISSION_ID'] = role_permission
            if RoleAnotherName.objects.filter(ROLE_A_ID=role_id).exists():
                RoleAnotherName.objects.filter(ROLE_A_ID=role_id).update(**data)
                result[role_id]['res_flag'] = True
            else:
                role_obj = RoleAnotherName.objects.create(**data)
                if role_obj is not None:
                    role_obj.save()
                    result[role_id]['res_flag'] = True
        return HttpResponse(json.dumps(result))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def roleAnotherNameToMrqName(request):
    """
    电子病历角色绑定质控角色
    """
    if request.method == 'POST':
        ROLE_NAME = ''
        ROLE_A_NAME = list()
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            ROLE_NAME = data.get('ROLE_NAME', '')
            ROLE_A_NAME = data.get('ROLE_A_NAME', list())
        elif request.content_type == 'multipart/form-data':
            ROLE_NAME = request.POST.get('ROLE_NAME', '')
            ROLE_A_NAME = request.POST.get('ROLE_A_NAME', list())
        if not ROLE_A_NAME:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请求中没有电子病历角色'}))
        if not ROLE_NAME:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请求中没有质控角色'}))
        role_obj = Role.objects.filter(ROLE_NAME=ROLE_NAME).first()
        if not role_obj:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '没有质控角色，请先建立该角色'}))
        role_a_obj_list = role_obj.roleanothername_set.all()  # 该项目角色当前拥有的EMR角色
        for i in ROLE_A_NAME:
            role_a_obj = RoleAnotherName.objects.filter(ROLE_A_NAME=i).first()  # 需要添加的EMR角色
            if not role_a_obj:
                continue
            if role_a_obj not in role_a_obj_list:
                role_a_obj.role_mrq = role_obj
                role_a_obj.save()
        for i in role_a_obj_list:
            if i.ROLE_A_NAME not in ROLE_A_NAME:
                i.role_mrq = None
                i.save()
        return HttpResponse(json.dumps({'res_flag': True}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def roleToEmrRoleShow(request):
    """
    质控角色对应EMR角色
    """
    if request.method == 'POST':
        role_list = Role.objects.all()
        result = dict()
        for i in role_list:
            result[i.ROLE_NAME] = [value['ROLE_A_NAME'] for value in i.roleanothername_set.values('ROLE_A_NAME')]
        return HttpResponse(json.dumps(result))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def roleAnotherNameDelete(request):
    """
    删除电子病历角色
    """
    if request.method == 'POST':
        ROLE_A_NAME = ''
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            ROLE_A_NAME = data.get('ROLE_A_NAME', '')
        elif request.content_type == 'multipart/form-data':
            ROLE_A_NAME = request.POST.get('ROLE_A_NAME', '')
        if isinstance(ROLE_A_NAME, str):
            role_a_obj = RoleAnotherName.objects.filter(ROLE_A_NAME=ROLE_A_NAME).first()
            role_a_obj.delete()
        elif isinstance(ROLE_A_NAME, list):
            for i in ROLE_A_NAME:
                role_a_obj = RoleAnotherName.objects.filter(ROLE_A_NAME=i).first()
                role_a_obj.delete()
        return HttpResponse(json.dumps({'res_flag': True}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def deptRegister(request):
    """
    添加病区
    """
    if request.method == 'POST':
        WARD_CODE = ''
        DEPT_CODE = ''
        WARD_NAME = ''
        DEPT_NAME = ''
        DEPT_INPUT_CODE = ''
        WARD_INPUT_CODE = ''
        DEPT_EMR = None
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            WARD_CODE = data.get('WARD_CODE', '')
            DEPT_CODE = data.get('DEPT_CODE', '')
            WARD_NAME = data.get('WARD_NAME', '')
            DEPT_NAME = data.get('DEPT_NAME', '')
            DEPT_INPUT_CODE = data.get('DEPT_INPUT_CODE', '')
            WARD_INPUT_CODE = data.get('WARD_INPUT_CODE', '')
            DEPT_EMR = None if not data.get('DEPT_EMR') else data.get('DEPT_EMR')

        elif request.content_type == 'multipart/form-data':
            WARD_CODE = request.POST.get('WARD_CODE', '')
            DEPT_CODE = request.POST.get('DEPT_CODE', '')
            WARD_NAME = request.POST.get('WARD_NAME', '')
            DEPT_NAME = request.POST.get('DEPT_NAME', '')
            DEPT_INPUT_CODE = request.POST.get('DEPT_INPUT_CODE', '')
            WARD_INPUT_CODE = request.POST.get('WARD_INPUT_CODE', '')
            DEPT_EMR = None if not request.POST.get('DEPT_EMR') else request.POST.get('DEPT_EMR')
        if not (DEPT_NAME and DEPT_CODE):
            data = {'res_flag': False, 'info': '请输入科室名及其ID'}
            return HttpResponse(json.dumps(data))
        if not (WARD_NAME and WARD_CODE):
            data = {'res_flag': False, 'info': '请输入病区名及其ID'}
            return HttpResponse(json.dumps(data))
        if District.objects.filter(WARD_CODE=WARD_CODE).exists() or District.objects.filter(WARD_NAME=WARD_NAME).exists():
            data = {'res_flag': False, 'info': '病区已经存在'}
            return HttpResponse(json.dumps(data))
        if Dept.objects.filter(DEPT_CODE=DEPT_CODE).exists():
            dept_obj = Dept.objects.filter(DEPT_CODE=DEPT_CODE).first()
        else:
            dept_obj = Dept.objects.create(DEPT_CODE=DEPT_CODE,
                                           DEPT_NAME=DEPT_NAME,
                                           DEPT_INPUT_CODE=DEPT_INPUT_CODE,
                                           DEPT_EMR=DEPT_EMR)
        district_obj = District.objects.create(WARD_CODE=WARD_CODE,
                                               WARD_NAME=WARD_NAME,
                                               WARD_INPUT_CODE=WARD_INPUT_CODE)

        if dept_obj is not None and district_obj is not None:
            district_obj.dept = dept_obj
            dept_obj.save()
            district_obj.save()
        return HttpResponse(json.dumps({'res': True}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def deptShow(request):
    """
    查看病区
    """
    if request.method == 'POST':
        name = ''
        emr = ''
        result = list()
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            name = data.get('name', '')
            emr = data.get('emr', '')
        elif request.content_type == 'multipart/form-data':
            name = request.POST.get('name', '')
            emr = request.POST.get('emr', '')
        if name == '全部':
            name = ''
        if name:
            dept_obj = Dept.objects.filter(DEPT_NAME=name).first()
            if dept_obj:
                if emr == '启用':
                    dept_obj = Dept.objects.filter(DEPT_NAME=name, DEPT_EMR__gt=0).first()
                elif emr == '不启用':
                    dept_obj = Dept.objects.filter(DEPT_NAME=name, DEPT_EMR=0).first()
                if not dept_obj:
                    return HttpResponse(json.dumps({'res_flag': True, 'result': result}))
                district_list = dept_obj.district_set.order_by('WARD_CODE')
                for j in district_list:
                    result.append({
                        'WARD_CODE': j.WARD_CODE,
                        'DEPT_CODE': dept_obj.DEPT_CODE,
                        'WARD_NAME': j.WARD_NAME,
                        'DEPT_NAME': dept_obj.DEPT_NAME,
                        'DEPT_INPUT_CODE': dept_obj.DEPT_INPUT_CODE,
                        'WARD_INPUT_CODE': j.WARD_INPUT_CODE,
                        'DEPT_EMR': dept_obj.DEPT_EMR
                    })
            else:
                district_obj = District.objects.filter(WARD_NAME=name).first()
                dept_obj = district_obj.dept
                if emr == '启用' and (dept_obj.DEPT_EMR != 1 or dept_obj.DEPT_EMR != 2):
                    return HttpResponse(json.dumps({'res_flag': True, 'result': result}))
                elif emr == '不启用' and dept_obj.DEPT_EMR != 0:
                    return HttpResponse(json.dumps({'res_flag': True, 'result': result}))
                result = [{
                        'WARD_CODE': district_obj.WARD_CODE,
                        'DEPT_CODE': dept_obj.DEPT_CODE,
                        'WARD_NAME': district_obj.WARD_NAME,
                        'DEPT_NAME': dept_obj.DEPT_NAME,
                        'DEPT_INPUT_CODE': dept_obj.DEPT_INPUT_CODE,
                        'WARD_INPUT_CODE': district_obj.WARD_INPUT_CODE,
                        'DEPT_EMR': dept_obj.DEPT_EMR
                    }]
        else:
            if emr == '启用':
                dept_list = Dept.objects.filter(DEPT_EMR__gt=0).order_by('DEPT_CODE')
            elif emr == '不启用':
                dept_list = Dept.objects.filter(DEPT_EMR=0).order_by('DEPT_CODE')
            else:
                dept_list = Dept.objects.order_by('DEPT_CODE')
            if not dept_list:
                return HttpResponse(json.dumps({'res_flag': True, 'result': result}))
            for i in dept_list:
                district_list = i.district_set.order_by('WARD_CODE')
                for j in district_list:
                    result.append({
                        'WARD_CODE': j.WARD_CODE,
                        'DEPT_CODE': i.DEPT_CODE,
                        'WARD_NAME': j.WARD_NAME,
                        'DEPT_NAME': i.DEPT_NAME,
                        'DEPT_INPUT_CODE': i.DEPT_INPUT_CODE,
                        'WARD_INPUT_CODE': j.WARD_INPUT_CODE,
                        'DEPT_EMR': i.DEPT_EMR
                    })
        return HttpResponse(json.dumps({'res_flag': True, 'result': result}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def deptDelete(request):
    """
    删除病区
    """
    if request.method == 'POST':
        WARD_NAME = ''
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            WARD_NAME = data.get('WARD_NAME', '')
        elif request.content_type == 'multipart/form-data':
            WARD_NAME = request.POST.get('WARD_NAME', '')
        if WARD_NAME:
            district_obj = District.objects.filter(WARD_NAME=WARD_NAME).first()
            if district_obj:
                district_obj.delete()
                return HttpResponse(json.dumps({'res_flag': True}))
            else:
                return HttpResponse(json.dumps({'res_flag': False, 'info': 'no {} in database'.format(WARD_NAME)}))
        else:
            return HttpResponse(json.dumps({'res_flag': False, 'info': 'no WARD_NAME input'}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def deptWardList(request):
    if request.method == 'POST':
        dept_list = Dept.objects.values('DEPT_NAME').distinct()
        ward_list = District.objects.values('WARD_NAME').distinct()
        result = ['全部']
        for i in dept_list:
            if i.get('DEPT_NAME'):
                result.append(i['DEPT_NAME'])
        for i in ward_list:
            if i.get('WARD_NAME'):
                result.append(i['WARD_NAME'])
        return HttpResponse(json.dumps({'res_flag': True, 'result': result}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def deptList(request):
    if request.method == 'POST':
        dept_list = Dept.objects.values('DEPT_NAME').distinct()
        result = ['全部']
        for i in dept_list:
            if i.get('DEPT_NAME'):
                result.append(i['DEPT_NAME'])
        return HttpResponse(json.dumps({'res_flag': True, 'result': result}))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


@views_log
def deptUpload(request):
    if request.method == 'POST':
        excel_file = request.FILES.get('file')
        wb = xlrd.open_workbook(filename=None, file_contents=excel_file.read())
        sheet_obj = wb.sheet_by_index(0)
        nrow = sheet_obj.nrows
        ncol = sheet_obj.ncols
        caption_list = ['WARD_CODE', 'DEPT_CODE', 'WARD_NAME', 'DEPT_NAME',
                        'DEPT_INPUT_CODE', 'WARD_INPUT_CODE', 'DEPT_EMR']
        caption_dict = dict()
        for col in range(ncol):
            if sheet_obj.cell_value(0, col) in caption_list:
                caption_dict[sheet_obj.cell_value(0, col)] = col
        if 'WARD_CODE' not in caption_dict:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请输入WARD_CODE'}))
        if 'DEPT_CODE' not in caption_dict:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请输入DEPT_CODE'}))
        if 'WARD_NAME' not in caption_dict:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请输入WARD_NAME'}))
        if 'DEPT_NAME' not in caption_dict:
            return HttpResponse(json.dumps({'res_flag': False, 'info': '请输入DEPT_NAME'}))
        for row in range(nrow):
            col = caption_dict['WARD_CODE']
            if sheet_obj.cell_type(row, col) == 2:
                WARD_CODE = str(int(sheet_obj.cell_value(row, col))).strip()
            else:
                WARD_CODE = sheet_obj.cell_value(row, col).strip()
            if not WARD_CODE:
                return HttpResponse(json.dumps({'res_flag': False, 'info': '第{}行WARD_CODE为空'.format(row+1)}))

            col = caption_dict['DEPT_CODE']
            if sheet_obj.cell_type(row, col) == 2:
                DEPT_CODE = str(int(sheet_obj.cell_value(row, col))).strip()
            else:
                DEPT_CODE = sheet_obj.cell_value(row, col).strip()
            if not DEPT_CODE:
                return HttpResponse(json.dumps({'res_flag': False, 'info': '第{}行DEPT_CODE为空'.format(row+1)}))

        result = dict()
        for row in range(1, nrow):
            ward_code_col = caption_dict['WARD_CODE']
            if sheet_obj.cell_type(row, ward_code_col) == 2:
                WARD_CODE = str(int(sheet_obj.cell_value(row, ward_code_col))).strip()
            else:
                WARD_CODE = sheet_obj.cell_value(row, ward_code_col).strip()

            result[WARD_CODE] = {'res_flag': False}

            dept_code_col = caption_dict['DEPT_CODE']
            if sheet_obj.cell_type(row, dept_code_col) == 2:
                DEPT_CODE = str(int(sheet_obj.cell_value(row, dept_code_col))).strip()
            else:
                DEPT_CODE = sheet_obj.cell_value(row, dept_code_col).strip()

            district_data = dict()
            dept_data = dict()
            for k, v in caption_dict.items():
                if k in ['WARD_NAME', 'WARD_INPUT_CODE']:
                    if sheet_obj.cell_type(row, v) == 2:
                        value = str(int(sheet_obj.cell_value(row, v))).strip()
                    else:
                        value = sheet_obj.cell_value(row, v).strip()
                    district_data[k] = value
                elif k in ['DEPT_NAME', 'DEPT_INPUT_CODE', 'DEPT_EMR']:
                    if sheet_obj.cell_type(row, v) == 2:
                        value = str(int(sheet_obj.cell_value(row, v))).strip()
                    else:
                        value = sheet_obj.cell_value(row, v).strip()
                    dept_data[k] = value
            if District.objects.filter(WARD_CODE=WARD_CODE).exists():
                District.objects.filter(WARD_CODE=WARD_CODE).update(**district_data)
                ward_obj = District.objects.filter(WARD_CODE=WARD_CODE).first()
            else:
                ward_obj = District.objects.create(WARD_CODE=WARD_CODE, **district_data)
            if Dept.objects.filter(DEPT_CODE=DEPT_CODE).exists():
                Dept.objects.filter(DEPT_CODE=DEPT_CODE).update(**dept_data)
                dept_obj = Dept.objects.filter(DEPT_CODE=DEPT_CODE).first()
            else:
                dept_obj = Dept.objects.create(DEPT_CODE=DEPT_CODE, **dept_data)

            if dept_obj and ward_obj:
                ward_obj.dept = dept_obj
                dept_obj.save()
                ward_obj.save()
                result[WARD_CODE]['res_flag'] = True

        return HttpResponse(json.dumps(result))
    return HttpResponse(json.dumps({'res_flag': False, 'info': 'use POST method to request'}))


def userDept(user_obj):
    dept_list = user_obj.dept.all()
    result = list()
    for i in dept_list:
        result.append(i.DEPT_NAME)
    return result


def userRole(user_obj):
    role_list = user_obj.role.all()
    result = list()
    for i in role_list:
        result.append(i.ROLE_A_NAME)
    return result
