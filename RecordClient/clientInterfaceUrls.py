#!/usr/bin/env python3
# -*- coding:utf-8 -*

# 电子病历客户端数据接口路由

from django.conf.urls import url

from . import clientInterfaceViews


urlpatterns = [
    # 获取医生的姓名和 id 等信息
    url(r'^processJsonFile\.json', clientInterfaceViews.processJsonFile, name='processJsonFile'),
    # 获取病案首页文本
    url(r'^processJsonFileBingan\.json', clientInterfaceViews.processJsonFileBingan, name='processJsonFileBingan'),
    # 获取同比表格页数据
    url(r'^doctorControlStats\.json', clientInterfaceViews.doctorControlStats, name='doctorControlStats'),
    # 配置文件中运行的规则所选文书名称
    url(r'^chooseRecordName\.json', clientInterfaceViews.chooseRecordName, name='chooseRecordName'),
    # 文书问题修改频次排行
    url(r'^recordModifySort\.json', clientInterfaceViews.recordModifySort, name='recordModifySort'),
    # 热度图数据
    url(r'^freqHeatMap\.json', clientInterfaceViews.freqHeatMap, name='freqHeatMap'),
    # 规则修改排行
    url(r'^regularModifySort\.json', clientInterfaceViews.regularModifySort, name='regularModifySort'),
    # 环节质控 只展示最后一次有问题的
    url(r'^getPatientInfo\.json', clientInterfaceViews.getPatientInfo, name='getPatientInfo'),
    # 统计各个科室问题病历数
    url(r'^statisticDept\.json', clientInterfaceViews.statisticDept, name='statisticDept'),
    # 获取医生的详细信息
    url(r'^getDoctorInfo\.json', clientInterfaceViews.getDoctorInfo, name='getDoctorInfo'),

    # 点击内容计数
    url(r'^getClickCount\.json', clientInterfaceViews.getClickCount, name='getClickCount'),
    # 点击图标计数
    url(r'^getClickCountIcon\.json', clientInterfaceViews.getClickCountIcon, name='getClickCountIcon'),

    # 点击计数合并之后的路由
    url(r'GetClickCount\.json', clientInterfaceViews.get_click_count_icon, name='get_click_count'),

    # 获取医生工作列表
    url(r'^doctorWorkStat\.json', clientInterfaceViews.doctorWorkStat, name='doctorWorkStat'),
    # 查看病区下有哪些医生，对医生规则修改情况进行统计
    url(r'^doctorModifySort\.json', clientInterfaceViews.doctorModifySort, name='doctorModifySort'),
    # 始终返回所有科室，输入科室返回该科室病区
    url(r'^allDistrict\.json', clientInterfaceViews.allDistrict, name='allDistrict'),
    # 环节列表展示原始数据
    url(r'^showJsonFile\.json', clientInterfaceViews.showJsonFile, name='showJsonFile'),
    # 与既往质控和终末质控中的问题分类类似，获取规则文书列表和问题分类列表
    url(r'^problemNameAndCode\.json', clientInterfaceViews.problemNameAndCode, name='problemNameAndCode'),
    # 获取医生病历数、问题病历数、排名、易犯问题排名、较上月情况比较等数据
    url(r'^doctorRank\.json', clientInterfaceViews.doctorRank, name='doctorRank'),
    # 运行随机病历，获取执行结果
    url(r'^runDemo\.json', clientInterfaceViews.runDemo, name='runDemo'),
    # 生成随机病历文档
    url(r'^demoData\.json', clientInterfaceViews.demoData, name='demoData'),
]
