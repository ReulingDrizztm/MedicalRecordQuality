from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^statisticDept\.json', views.statisticDept, name='statisticDept'),
    url(r'^findPatientByStatus\.json', views.findPatientByStatus, name='findPatientByStatus'),
    url(r'^findPatientHtml\.json', views.findPatientHtml, name='findPatientHtml'),
    url(r'^getPatientHtmlList\.json', views.getPatientHtmlList, name='getPatientHtmlList'),
    url(r'^saveModifyContent\.json', views.saveModifyContent, name='saveModifyContent'),
    url(r'^saveTestContent\.json', views.saveTestContent, name='saveTestContent'),
    url(r'^deptClassificationByMonth\.json', views.deptClassificationByMonth, name='deptClassificationByMonth'),
    url(r'^oneYearRightAndError\.json', views.oneYearRightAndError, name='oneYearRightAndError'),
    url(r'^oneYearRightAndError2\.json', views.oneYearRightAndError2, name='oneYearRightAndError2'),
    url(r'^regularManage\.json', views.regularManage, name='regularManage'),
    url(r'^graphPageHeader\.json', views.graphPageHeader, name='graphPageHeader'),
    url(r'^fileDownload', views.fileDownload, name='fileDownload'),
    url(r'^problemNameAndCode\.json', views.problemNameAndCode, name='problemNameAndCode'),
    url(r'^oneYearRightAndError3\.json', views.oneYearRightAndError3, name='oneYearRightAndError3'),
    url(r'^deptRightAndError\.json', views.deptRightAndError, name='deptRightAndError'),
    url(r'^showDataResult\.json', views.showDataResult, name='showDataResult'),
    url(r'^record_to_regular\.json', views.record_to_regular, name='record_to_regular'),
    url(r'^regular_to_detail\.json', views.regular_to_detail, name='regular_to_detail'),
    url(r'^detail_to_score\.json', views.detail_to_score, name='detail_to_score'),
    url(r'^record_list\.json', views.record_list, name='record_list'),
    url(r'^version\.json', views.version, name='version'),
    url(r'^testClient\.json', views.testClient, name='testClient'),
    url(r'^zhongmoDept\.json', views.zhongmoDept, name='zhongmoDept'),
    url(r'^deptProblemPercentage\.json', views.deptProblemPercentage, name='deptProblemPercentage'),
    url(r'^deptProblemClassify\.json', views.deptProblemClassify, name='deptProblemClassify'),
    url(r'^doctorProblemNum\.json', views.doctorProblemNum, name='doctorProblemNum'),
    url(r'^zhongmoRecordName\.json', views.zhongmoRecordName, name='zhongmoRecordName'),
    url(r'^zhongmoRegularName\.json', views.zhongmoRegularName, name='zhongmoRegularName'),
    url(r'^documentProblemClassify\.json', views.documentProblemClassify, name='documentProblemClassify'),
    url(r'^zhongmoFileDownloadMingxi\.json', views.zhongmoFileDownloadMingxi, name='zhongmoFileDownloadMingxi'),
    url(r'^zhongmoFileDownloadHuizong\.json', views.zhongmoFileDownloadHuizong, name='zhongmoFileDownloadHuizong'),
]