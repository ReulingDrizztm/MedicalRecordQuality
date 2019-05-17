import json
import os
import sys
cur_path = os.path.abspath(os.path.dirname(__file__))
root_path = os.path.split(cur_path)[0]
sys.path.append(root_path)  # 项目路径添加到系统路径
from Utils.LogUtils import LogUtils
from django.http import HttpResponse
from Utils.decoratorFunc import views_log
if os.path.abspath(os.path.dirname(__file__)).endswith('Test'):
    from RecordClientTest.clientInterface import ClientInterface
else:
    from RecordClient.clientInterface import ClientInterface


@views_log
def processJsonFile(request):
    """
    获取医生的姓名和 id
    :param request:
    :return:
    """
    logger_seg = LogUtils().getLogger('segment')
    logger = LogUtils().getLogger('backend')
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            json_file = json.loads(data)

            if not json_file.get('wenshuxinxi', dict()).get('file_unique_id'):
                logger.error("[{}#{}] no [file_unique_id]".format(
                    json_file.get('binganshouye', dict()).get('patient_id', ''),
                    json_file.get('binganshouye', dict()).get('visit_id', '')))

            if os.path.abspath(os.path.dirname(__file__)).endswith('Test'):
                logger_seg.info(json_file)

            result = app.processJsonFile(json_file=json_file)  # 这里获取医生姓名和id
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            json_file = request.POST

            if not json_file.get('wenshuxinxi', dict()).get('file_unique_id'):
                logger.error("[{}#{}] no [file_unique_id]".format(
                    json_file.get('binganshouye', dict()).get('patient_id', ''),
                    json_file.get('binganshouye', dict()).get('visit_id', '')))

            if os.path.abspath(os.path.dirname(__file__)).endswith('Test'):
                logger_seg.info(json_file)

            result = app.processJsonFile(json_file=json_file)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def processJsonFileBingan(request):
    # 获取病案首页文本
    logger_seg = LogUtils().getLogger('segment')
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            json_file = json.loads(data)

            if os.path.abspath(os.path.dirname(__file__)).endswith('Test'):
                logger_seg.info(json_file)

            result = app.processJsonFileBingan(json_file=json_file)  # 这里获取医生姓名和id
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            json_file = request.POST

            if os.path.abspath(os.path.dirname(__file__)).endswith('Test'):
                logger_seg.info(json_file)

            result = app.processJsonFileBingan(json_file=json_file)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def doctorControlStats(request):
    # 获取同比表格页数据
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            ward_name = data.get('ward_name', '')
            record_name = data.get('record_name', '')
            regular_name = data.get('regular_name', '')
            in_hospital = data.get('in_hospital', True)
            step = data.get('step', '医生端')

            result = app.doctorControlStats(ward_name=ward_name, record_name=record_name, regular_name=regular_name, in_hospital=in_hospital, step=step)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            ward_name = request.POST.get('ward_name', '')
            record_name = request.POST.get('record_name', '')
            regular_name = request.POST.get('regular_name', '')
            in_hospital = request.POST.get('in_hospital', True)
            step = request.POST.get('step', '医生端')

            result = app.doctorControlStats(ward_name=ward_name, record_name=record_name, regular_name=regular_name, in_hospital=in_hospital, step=step)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def chooseRecordName(request):
    # 配置文件中运行的规则所选文书名称
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            record = data.get('record', '')
            step = data.get('step', '医生端')

            result = app.chooseRecordName(record=record, step=step)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            record = request.POST.get('record', '')
            step = request.POST.get('step', '医生端')

            result = app.chooseRecordName(record=record, step=step)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def recordModifySort(request):
    # 文书问题修改频次排行
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            ward_name = data.get('ward_name', '')
            in_hospital = data.get('in_hospital', True)

            result = app.recordModifySort(ward_name=ward_name, in_hospital=in_hospital)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            ward_name = request.POST.get('ward_name', '')
            in_hospital = request.POST.get('in_hospital', True)

            result = app.recordModifySort(ward_name=ward_name, in_hospital=in_hospital)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def freqHeatMap(request):
    # 热度图数据
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            record_name = data.get('record_name', '')
            ward_name = data.get('ward_name', '')
            in_hospital = data.get('in_hospital', True)

            result = app.freqHeatMap(record_name=record_name, ward_name=ward_name, in_hospital=in_hospital)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            record_name = request.POST.get('record_name', '')
            ward_name = request.POST.get('ward_name', '')
            in_hospital = request.POST.get('in_hospital', True)

            result = app.freqHeatMap(record_name=record_name, ward_name=ward_name, in_hospital=in_hospital)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def regularModifySort(request):
    # 规则修改排行
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            ward_name = data.get('ward_name', '')
            record_name = data.get('record_name', '')
            regular_name = data.get('regular_name', '')
            in_hospital = data.get('in_hospital', True)

            result = app.regularModifySort(ward_name=ward_name,
                                           record_name=record_name,
                                           regular_name=regular_name,
                                           in_hospital=in_hospital)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            ward_name = request.POST.get('ward_name', '')
            record_name = request.POST.get('record_name', '')
            regular_name = request.POST.get('regular_name', '')
            in_hospital = request.POST.get('in_hospital', True)

            result = app.regularModifySort(ward_name=ward_name,
                                           record_name=record_name,
                                           regular_name=regular_name,
                                           in_hospital=in_hospital)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def getPatientInfo(request):
    # 环节质控 只展示最后一次有问题的
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            ward_name = data.get('ward_name', '')
            show_num = data.get('show_num', 10)
            page_num = data.get('page_num', 0)
            patient_id = data.get('patient_id', '')
            name = data.get('name', '')
            details = data.get('details', '')
            in_hospital = data.get('in_hospital', True)

            result = app.getPatientInfo(ward_name=ward_name,
                                        show_num=show_num,
                                        page_num=page_num,
                                        patient_id=patient_id,
                                        name=name,
                                        details=details,
                                        in_hospital=in_hospital)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            ward_name = request.POST.get('ward_name', '')
            show_num = request.POST.get('show_num', 10)
            page_num = request.POST.get('page_num', 0)
            patient_id = request.POST.get('patient_id', '')
            name = request.POST.get('name', '')
            details = request.POST.get('details', '')
            in_hospital = request.POST.get('in_hospital', True)

            result = app.getPatientInfo(ward_name=ward_name,
                                        show_num=show_num,
                                        page_num=page_num,
                                        patient_id=patient_id,
                                        name=name,
                                        details=details,
                                        in_hospital=in_hospital)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def statisticDept(request):
    # 统计各个科室问题病历数
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            ward_name = data.get('ward_name', '')
            in_hospital = data.get('in_hospital', True)

            result = app.statisticDept(ward_name=ward_name,
                                       in_hospital=in_hospital)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            ward_name = request.POST.get('ward_name', '')
            in_hospital = request.POST.get('in_hospital', True)

            result = app.statisticDept(ward_name=ward_name,
                                       in_hospital=in_hospital)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def getDoctorInfo(request):
    # 获取医生的详细信息
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            doctor_json = data

            result = app.getDoctorInfo(doctor_json=doctor_json)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            doctor_json = request.POST

            result = app.getDoctorInfo(doctor_json=doctor_json)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def getClickCount(request):
    # 点击内容计数
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            doctor_id = data.get('doctor_id', '')
            doctor_name = data.get('doctor_name', '')
            patient_id = data.get('patient_id', '')
            visit_id = data.get('visit_id', '')

            result = app.getClickCount(patient_id=patient_id, visit_id=visit_id, doctor_name=doctor_name,
                                       doctor_id=doctor_id)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            doctor_id = request.POST.get('doctor_id', '')
            doctor_name = request.POST.get('doctor_name', '')
            patient_id = request.POST.get('patient_id', '')
            visit_id = request.POST.get('visit_id', '')

            result = app.getClickCount(patient_id=patient_id, visit_id=visit_id, doctor_name=doctor_name,
                                       doctor_id=doctor_id)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def getClickCountIcon(request):
    # 点击图标计数
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            doctor_id = data.get('doctor_id', '')
            doctor_name = data.get('doctor_name', '')
            patient_id = data.get('patient_id', '')
            visit_id = data.get('visit_id', '')

            result = app.getClickCount(patient_id=patient_id, visit_id=visit_id, doctor_name=doctor_name,
                                       doctor_id=doctor_id, loc=True)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            doctor_id = request.POST.get('doctor_id', '')
            doctor_name = request.POST.get('doctor_name', '')
            patient_id = request.POST.get('patient_id', '')
            visit_id = request.POST.get('visit_id', '')

            result = app.getClickCount(patient_id=patient_id, visit_id=visit_id, doctor_name=doctor_name,
                                       doctor_id=doctor_id, loc=True)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def get_click_count_icon(request, flag=True):
    # 点击计数
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            doctor_id = data.get('doctor_id', '')
            doctor_name = data.get('doctor_name', '')
            patient_id = data.get('patient_id', '')
            visit_id = data.get('visit_id', '')
            if flag:
                # 有传递 flag 参数，表示是在点击图标
                result = app.getClickCount(patient_id=patient_id, visit_id=visit_id, doctor_name=doctor_name,
                                           doctor_id=doctor_id, loc=True)
            else:
                # 没有 flag 参数或者 flag 的值为 False，表示点击的是内容
                result = app.getClickCount(patient_id=patient_id, visit_id=visit_id, doctor_name=doctor_name,
                                           doctor_id=doctor_id)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            doctor_id = request.POST.get('doctor_id', '')
            doctor_name = request.POST.get('doctor_name', '')
            patient_id = request.POST.get('patient_id', '')
            visit_id = request.POST.get('visit_id', '')
            if flag:
                # 有传递 flag 参数，表示是在点击图标
                result = app.getClickCount(patient_id=patient_id, visit_id=visit_id, doctor_name=doctor_name,
                                           doctor_id=doctor_id, loc=True)
            else:
                # 没有 flag 参数或者 flag 的值为 False，表示点击的是内容
                result = app.getClickCount(patient_id=patient_id, visit_id=visit_id, doctor_name=doctor_name,
                                           doctor_id=doctor_id)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def doctorWorkStat(request):
    # 获取医生工作列表
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            ward_name = data.get('ward_name', '')
            in_hospital = data.get('in_hospital', True)

            result = app.doctorWorkStat(ward_name=ward_name,
                                        in_hospital=in_hospital)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            ward_name = request.POST.get('ward_name', '')
            in_hospital = request.POST.get('in_hospital', True)

            result = app.doctorWorkStat(ward_name=ward_name,
                                        in_hospital=in_hospital)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def doctorModifySort(request):
    # 查看病区下有哪些医生，对医生规则修改情况进行统计
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            ward_name = data.get('ward_name', '')
            in_hospital = data.get('in_hospital', True)

            result = app.doctorModifySort(ward_name=ward_name,
                                          in_hospital=in_hospital)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            ward_name = request.POST.get('ward_name', '')
            in_hospital = request.POST.get('in_hospital', True)

            result = app.doctorModifySort(ward_name=ward_name,
                                          in_hospital=in_hospital)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def allDistrict(request):
    # 始终返回所有科室，输入科室返回该科室病区
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            ward_name = data.get('ward_name', '')

            result = app.allDistrict(ward_name=ward_name)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            ward_name = request.POST.get('ward_name', '')

            result = app.allDistrict(ward_name=ward_name)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def showJsonFile(request):
    # 环节列表展示原始数据
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            patient_id = data.get('patient_id', '')
            visit_id = data.get('visit_id', '')

            result = app.showJsonFile(patient_id=patient_id, visit_id=visit_id)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            patient_id = request.POST.get('patient_id', '')
            visit_id = request.POST.get('visit_id', '')

            result = app.showJsonFile(patient_id=patient_id, visit_id=visit_id)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def problemNameAndCode(request):
    # 与既往质控和终末质控中的问题分类类似，获取文书列表和问题分类列表
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            regular_name = data.get('regular_name', '')
            in_hospital = data.get('in_hospital', True)

            result = app.problemNameAndCode(regular_name=regular_name, in_hospital=in_hospital)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            regular_name = request.POST.get('regular_name', '')
            in_hospital = request.POST.get('in_hospital', True)

            result = app.problemNameAndCode(regular_name=regular_name, in_hospital=in_hospital)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def doctorRank(request):
    # 获取医生病历数、问题病历数、排名、易犯问题排名、较上月情况比较等数据
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            doctor_id = data.get('doctor_id', '')
            dept = data.get('dept', '')

            result = app.doctorRank(doctor_id=doctor_id, dept=dept)  # 这里获取医生id
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            doctor_id = request.POST.get('doctor_id', '')
            dept = request.POST.get('dept', '')

            result = app.doctorRank(doctor_id=doctor_id, dept=dept)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def demoData(request):
    """
    生成示例病历文档
    :param request:
    :return:
    """
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':

            result = app.demoData()
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            result = app.demoData()
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def runDemo(request):
    # 运行随机病历，获取执行结果
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            json_file = json.loads(data)

            result = app.runDemo(json_file=json_file)  # 这里获取医生姓名和id
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            json_file = request.POST

            result = app.runDemo(json_file=json_file)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))
