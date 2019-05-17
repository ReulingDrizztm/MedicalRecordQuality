#!/usr/bin/env python3
# -*- coding:utf-8 -*

"""
@version: 
@author:
@contact:
@software: PyCharm Community Edition
@file: urls.py
@time: 18-10-29 上午10:41
@description: 
"""
from django.conf.urls import url

from . import clientInterfaceViews


urlpatterns = [
    url(r'^processJsonFile\.json', clientInterfaceViews.processJsonFile, name='processJsonFile'),
    url(r'^processJsonFileBingan\.json', clientInterfaceViews.processJsonFileBingan, name='processJsonFileBingan'),
    url(r'^pushTransmitFlag\.json', clientInterfaceViews.pushTransmitFlag, name='pushTransmitFlag'),
    url(r'^modifyHuanjieResult\.json', clientInterfaceViews.modifyHuanjieResult, name='modifyHuanjieResult'),
    url(r'^showHuanjieDataResult\.json', clientInterfaceViews.showHuanjieDataResult, name='showHuanjieDataResult'),
    url(r'^doctorControlStats\.json', clientInterfaceViews.doctorControlStats, name='doctorControlStats'),
    url(r'^chooseRecordName\.json', clientInterfaceViews.chooseRecordName, name='chooseRecordName'),
    url(r'^recordModifySort\.json', clientInterfaceViews.recordModifySort, name='recordModifySort'),
    url(r'^freqHeatMap\.json', clientInterfaceViews.freqHeatMap, name='freqHeatMap'),
    url(r'^regularModifySort\.json', clientInterfaceViews.regularModifySort, name='regularModifySort'),
    url(r'^getPatientInfo\.json', clientInterfaceViews.getPatientInfo, name='getPatientInfo'),
    url(r'^getHuanjiePatientHtmlList\.json', clientInterfaceViews.getHuanjiePatientHtmlList, name='getHuanjiePatientHtmlList'),
    url(r'^getHuanjiePatientHtml\.json', clientInterfaceViews.getHuanjiePatientHtml, name='getHuanjiePatientHtml'),
    url(r'^statisticDept\.json', clientInterfaceViews.statisticDept, name='statisticDept'),
    url(r'^getDoctorInfo\.json', clientInterfaceViews.getDoctorInfo, name='getDoctorInfo'),
    url(r'^getClickCount\.json', clientInterfaceViews.getClickCount, name='getClickCount'),
    url(r'^getClickCountIcon\.json', clientInterfaceViews.getClickCountIcon, name='getClickCountIcon'),
    url(r'^doctorWorkStat\.json', clientInterfaceViews.doctorWorkStat, name='doctorWorkStat'),
    url(r'^doctorModifySort\.json', clientInterfaceViews.doctorModifySort, name='doctorModifySort'),
    url(r'^allDistrict\.json', clientInterfaceViews.allDistrict, name='allDistrict'),
    url(r'^showJsonFile\.json', clientInterfaceViews.showJsonFile, name='showJsonFile'),
    url(r'^problemNameAndCode\.json', clientInterfaceViews.problemNameAndCode, name='problemNameAndCode'),
    url(r'^doctorRank\.json', clientInterfaceViews.doctorRank, name='doctorRank'),
    url(r'^runDemo\.json', clientInterfaceViews.runDemo, name='runDemo'),
    url(r'^demoData\.json', clientInterfaceViews.demoData, name='demoData'),
]
