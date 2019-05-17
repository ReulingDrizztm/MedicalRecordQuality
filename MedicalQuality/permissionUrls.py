#!/usr/bin/env python3
# -*- coding:utf-8 -*

# 权限接口地址页

from django.conf.urls import url

from . import permissionViews

urlpatterns = [
    url(r'^userRegister\.json', permissionViews.userRegister, name='userRegister'),
    url(r'^userLoginPre\.json', permissionViews.userLoginPre, name='userLoginPre'),
    url(r'^userLogin\.json', permissionViews.userLogin, name='userLogin'),
    url(r'^userResetPassword\.json', permissionViews.userResetPassword, name='userResetPassword'),
    url(r'^userModifyPassword\.json', permissionViews.userModifyPassword, name='userModifyPassword'),
    url(r'^userSwitchDeptRole\.json', permissionViews.userSwitchDeptRole, name='userSwitchDeptRole'),
    url(r'^userEdit\.json', permissionViews.userEdit, name='userEdit'),
    url(r'^userEditRole\.json', permissionViews.userEditRole, name='userEditRole'),
    url(r'^userEditDept\.json', permissionViews.userEditDept, name='userEditDept'),
    url(r'^userLogout\.json', permissionViews.userLogout, name='userLogout'),
    url(r'^userDelete\.json', permissionViews.userDelete, name='userDelete'),
    url(r'^userUpload\.json', permissionViews.userUpload, name='userUpload'),
    url(r'^userShow\.json', permissionViews.userShow, name='userShow'),
    url(r'^roleRegister\.json', permissionViews.roleRegister, name='roleRegister'),
    url(r'^roleEditPermission\.json', permissionViews.roleEditPermission, name='roleEditPermission'),
    url(r'^roleEdit\.json', permissionViews.roleEdit, name='roleEdit'),
    url(r'^roleShow\.json', permissionViews.roleShow, name='roleShow'),
    url(r'^roleDelete\.json', permissionViews.roleDelete, name='roleDelete'),
    url(r'^permissionRegister\.json', permissionViews.permissionRegister, name='permissionRegister'),
    url(r'^permissionShow\.json', permissionViews.permissionShow, name='permissionShow'),
    url(r'^permissionEdit\.json', permissionViews.permissionEdit, name='permissionEdit'),
    url(r'^permissionDelete\.json', permissionViews.permissionDelete, name='permissionDelete'),
    url(r'^roleAnotherNameRegister\.json', permissionViews.roleAnotherNameRegister, name='roleAnotherNameRegister'),
    url(r'^roleAnotherNameEdit\.json', permissionViews.roleAnotherNameEdit, name='roleAnotherNameEdit'),
    url(r'^roleAnotherNameShow\.json', permissionViews.roleAnotherNameShow, name='roleAnotherNameShow'),
    url(r'^roleToEmrRoleShow\.json', permissionViews.roleToEmrRoleShow, name='roleToEmrRoleShow'),
    url(r'^roleAnotherNameDelete\.json', permissionViews.roleAnotherNameDelete, name='roleAnotherNameDelete'),
    url(r'^roleAnotherNameUpload\.json', permissionViews.roleAnotherNameUpload, name='roleAnotherNameUpload'),
    url(r'^roleAnotherNameToMrqName\.json', permissionViews.roleAnotherNameToMrqName, name='roleAnotherNameToMrqName'),
    url(r'^deptRegister\.json', permissionViews.deptRegister, name='deptRegister'),
    url(r'^deptWardList\.json', permissionViews.deptWardList, name='deptWardList'),
    url(r'^deptList\.json', permissionViews.deptList, name='deptList'),
    url(r'^deptShow\.json', permissionViews.deptShow, name='deptShow'),
    url(r'^deptDelete\.json', permissionViews.deptDelete, name='deptDelete'),
    url(r'^deptUpload\.json', permissionViews.deptUpload, name='deptUpload'),
]
