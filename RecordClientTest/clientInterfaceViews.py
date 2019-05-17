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
def pushTransmitFlag(request):
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            data = json.loads(data)

            patient_id = data.get('patient_id', '')
            visit_id = data.get('visit_id', '')
            collection_name = data.get('collection_name', '')

            result = app.pushTransmitFlag(patient_id=patient_id, visit_id=visit_id, collection_name=collection_name)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            patient_id = request.POST.get('patient_id', '')
            visit_id = request.POST.get('visit_id', '')
            collection_name = request.POST.get('collection_name', '')

            result = app.pushTransmitFlag(patient_id=patient_id, visit_id=visit_id, collection_name=collection_name)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(False)


@views_log
def modifyHuanjieResult(request):
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            data = json.loads(data)

            data_id = data.get('_id', '')
            content = data.get('content', list())
            delete_list = data.get('delete_list', dict())
            doctor_name = data.get('doctor_name', '')

            result = app.modifyHuanjieResult(data_id=data_id, content=content, delete_list=delete_list, doctor_name=doctor_name)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            data_id = request.POST.get('_id', '')
            content = request.POST.get('content', list())
            delete_list = request.POST.get('delete_list', dict())
            doctor_name = request.POST.get('doctor_name', '')

            result = app.modifyHuanjieResult(data_id=data_id, content=content, delete_list=delete_list, doctor_name=doctor_name)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(False)


@views_log
def showHuanjieDataResult(request):
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            data = json.loads(data)

            data_id = data.get('data_id', '')

            result = app.showHuanjieDataResult(data_id=data_id)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            data_id = request.POST.get('data_id', '')

            result = app.showHuanjieDataResult(data_id=data_id)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(False)

@views_log
def doctorControlStats(request):
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
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            status_bool = data.get('status_bool', 'all')
            dept_name = data.get('dept_name', 'all')
            show_num = data.get('show_num', 10)
            page_num = data.get('page_num', 0)
            patient_id = data.get('patient_id', '')
            name = data.get('name', '')
            details = data.get('details', '')
            record = data.get('record', '')
            category = data.get('category', '')
            isResult = data.get('isResult', False)
            in_hospital = data.get('in_hospital', True)

            result = app.getPatientInfo(status_bool=status_bool,
                                        dept_name=dept_name,
                                        show_num=show_num,
                                        page_num=page_num,
                                        patient_id=patient_id,
                                        name=name,
                                        details=details,
                                        record=record,
                                        category=category,
                                        isResult=isResult,
                                        in_hospital=in_hospital)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            status_bool = request.POST.get('status_bool', 'all')
            dept_name = request.POST.get('dept_name', 'all')
            show_num = request.POST.get('show_num', 10)
            page_num = request.POST.get('page_num', 0)
            patient_id = request.POST.get('patient_id', '')
            name = request.POST.get('name', '')
            details = request.POST.get('details', '')
            record = request.POST.get('record', '')
            category = request.POST.get('category', '')
            isResult = request.POST.get('isResult', False)
            in_hospital = request.POST.get('in_hospital', True)

            result = app.getPatientInfo(status_bool=status_bool,
                                        dept_name=dept_name,
                                        show_num=show_num,
                                        page_num=page_num,
                                        patient_id=patient_id,
                                        name=name,
                                        details=details,
                                        record=record,
                                        category=category,
                                        isResult=isResult,
                                        in_hospital=in_hospital)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def statisticDept(request):
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

            result = app.getClickCount(patient_id=patient_id, visit_id=visit_id, doctor_name=doctor_name, doctor_id=doctor_id)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            doctor_id = request.POST.get('doctor_id', '')
            doctor_name = request.POST.get('doctor_name', '')
            patient_id = request.POST.get('patient_id', '')
            visit_id = request.POST.get('visit_id', '')

            result = app.getClickCount(patient_id=patient_id, visit_id=visit_id, doctor_name=doctor_name, doctor_id=doctor_id)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def getClickCountIcon(request):
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

            result = app.getClickCount(patient_id=patient_id, visit_id=visit_id, doctor_name=doctor_name, doctor_id=doctor_id, loc=True)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            doctor_id = request.POST.get('doctor_id', '')
            doctor_name = request.POST.get('doctor_name', '')
            patient_id = request.POST.get('patient_id', '')
            visit_id = request.POST.get('visit_id', '')

            result = app.getClickCount(patient_id=patient_id, visit_id=visit_id, doctor_name=doctor_name, doctor_id=doctor_id, loc=True)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def getHuanjiePatientHtmlList(request):
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            data_id = data.get('data_id', '')

            result = app.getHuanjiePatientHtmlList(data_id=data_id)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            data_id = request.POST.get('data_id', '')

            result = app.getHuanjiePatientHtmlList(data_id=data_id)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def getHuanjiePatientHtml(request):
    app = ClientInterface()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            data_id = data.get('data_id', '')
            record_name = data.get('record_name', '')

            result = app.getHuanjiePatientHtml(data_id=data_id, record_name=record_name)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            data_id = request.POST.get('data_id', '')
            record_name = request.POST.get('record_name', '')

            result = app.getHuanjiePatientHtml(data_id=data_id, record_name=record_name)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def doctorWorkStat(request):
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
