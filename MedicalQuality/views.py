import json
import os
import sys
cur_path = os.path.abspath(os.path.dirname(__file__))
root_path = os.path.split(cur_path)[0]
sys.path.append(root_path)  # 项目路径添加到系统路径
from django.http import HttpResponse, StreamingHttpResponse
from MedicalQuality.statisticPatientsInfos import StatisticPatientInfos

from Utils.decoratorFunc import views_log


@views_log
def statisticDept(request):
    """
    统计质控病历的科室信息
    """
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)
            dept_name = data.get('dept_name', 'all')
            start_date = data.get('start_date', '')
            end_date = data.get('end_date', '')
            last_month = data.get('last_month', '')

            result = statistic_app.statisticDept(dept_name=dept_name, start_date=start_date, end_date=end_date, last_month=last_month)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':
            dept_name = request.POST.get('dept_name', 'all')
            start_date = request.POST.get('start_date', '')
            end_date = request.POST.get('end_date', '')
            last_month = request.POST.get('last_month', '')

            result = statistic_app.statisticDept(dept_name=dept_name, start_date=start_date, end_date=end_date, last_month=last_month)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def findPatientByStatus(request):
    """
    根据核验状态获取患者信息
    """
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            status_bool = data.get('status_bool', 'all')
            if status_bool == 'false':
                status_bool = False
            elif status_bool == 'true':
                status_bool = True
            elif status_bool == 'zero':
                status_bool = 'zero'
            elif isinstance(status_bool, bool):
                pass
            else:
                status_bool = 'all'
            dept_name = data.get('dept_name', 'all')
            show_num = data.get('show_num', 10)
            page_num = data.get('page_num', 0)
            patient_id = data.get('patient_id', '')
            regular_details = data.get('regular_details', '')
            if regular_details == '全部':
                regular_details = ''
            code = data.get('code', '')
            record = data.get('record', '')
            if code == '全部':
                code = ''
            start_date = data.get('start_date', '')
            end_date = data.get('end_date', '')
            category = data.get('category', '')
            isResult = data.get('isResult', 'all')
            last_month = data.get('last_month', '0')

            result = statistic_app.findPatientByStatus(status_bool=status_bool,
                                                       dept_name=dept_name,
                                                       show_num=show_num,
                                                       page_num=page_num,
                                                       patient_id=patient_id,
                                                       regular_details=regular_details,
                                                       code=code,
                                                       record=record,
                                                       start_date=start_date,
                                                       end_date=end_date,
                                                       category=category,
                                                       isResult=isResult,
                                                       last_month=last_month)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':
            status_bool = request.POST.get('status_bool', 'all')
            if status_bool == 'false':
                status_bool = False
            elif status_bool == 'true':
                status_bool = True
            elif status_bool == 'zero':
                status_bool = 'zero'
            elif isinstance(status_bool, bool):
                pass
            else:
                status_bool = 'all'
            dept_name = request.POST.get('dept_name', 'all')
            show_num = request.POST.get('show_num', 10)
            page_num = request.POST.get('page_num', 0)
            patient_id = request.POST.get('patient_id', '')
            regular_details = request.POST.get('regular_details', '')
            if regular_details == '全部':
                regular_details = ''
            code = request.POST.get('code', '')
            record = request.POST.get('record', '')
            if code == '全部':
                code = ''
            start_date = request.POST.get('start_date', '')
            end_date = request.POST.get('end_date', '')
            category = request.POST.get('category', '')
            isResult = request.POST.get('isResult', 'all')
            last_month = request.POST.get('last_month', '0')

            result = statistic_app.findPatientByStatus(status_bool=status_bool,
                                                       dept_name=dept_name,
                                                       show_num=show_num,
                                                       page_num=page_num,
                                                       patient_id=patient_id,
                                                       regular_details=regular_details,
                                                       code=code,
                                                       record=record,
                                                       start_date=start_date,
                                                       end_date=end_date,
                                                       category=category,
                                                       isResult=isResult,
                                                       last_month=last_month)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def findPatientHtml(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            data = json.loads(data)

            data_id = data.get('data_id', '')
            record_name = data.get('record_name', '')
            mongo = data.get('mongo', False)

            result = statistic_app.findPatientHtml(data_id=data_id, record_name=record_name, mongo=mongo)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':
            data_id = request.POST.get('data_id', '')
            record_name = request.POST.get('record_name', '')
            mongo = request.POST.get('mongo', False)

            result = statistic_app.findPatientHtml(data_id=data_id, record_name=record_name, mongo=mongo)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def getPatientHtmlList(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            data = json.loads(data)

            data_id = data.get('data_id', '')

            result = statistic_app.getPatientHtmlList(data_id=data_id)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':
            data_id = request.POST.get('data_id', '')

            result = statistic_app.getPatientHtmlList(data_id=data_id)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def saveModifyContent(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            data = json.loads(data)

            data_id = data.get('_id', '')
            content = data.get('content', list())
            delete_list = data.get('delete_list', list())
            doctor_name = data.get('doctor_name', '')
            last_month = data.get('last_month', '0')

            result = statistic_app.saveModifyContent(data_id=data_id, content=content, delete_list=delete_list, doctor_name=doctor_name, last_month=last_month)
            return HttpResponse(result)
        elif request.content_type == 'multipart/form-data':

            data_id = request.POST.get('_id', '')
            content = request.POST.get('content', list())
            delete_list = request.POST.get('delete_list', list())
            doctor_name = request.POST.get('doctor_name', '')
            last_month = request.POST.get('last_month', '0')

            result = statistic_app.saveModifyContent(data_id=data_id, content=content, delete_list=delete_list, doctor_name=doctor_name, last_month=last_month)
            return HttpResponse(result)
        else:
            return HttpResponse(False)


@views_log
def saveTestContent(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            data = json.loads(data)

            data_id = data.get('_id', '')
            regular_code = data.get('code', '')
            test_content = data.get('test_content', {'fenci': '', 'cibiao': '', 'guize': '', 'zhengque': ''})

            result = statistic_app.saveTestContent(data_id=data_id, regular_code=regular_code, test_content=test_content)
            return HttpResponse(result)
        elif request.content_type == 'multipart/form-data':

            data_id = request.POST.get('_id', '')
            regular_code = request.POST.get('code', '')
            test_content = request.POST.get('test_content', {'fenci': '', 'cibiao': '', 'guize': '', 'zhengque': ''})

            result = statistic_app.saveTestContent(data_id=data_id, regular_code=regular_code, test_content=test_content)
            return HttpResponse(result)
        else:
            return HttpResponse(False)


@views_log
def deptClassificationByMonth(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            start_month = data.get('start_month', '')
            end_month = data.get('end_month', '')

            result = statistic_app.deptClassificationByMonth(start_month=start_month, end_month=end_month)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            start_month = request.POST.get('start_month', '')
            end_month = request.POST.get('end_month', '')

            result = statistic_app.deptClassificationByMonth(start_month=start_month, end_month=end_month)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def oneYearRightAndError(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':

            result = statistic_app.oneYearRightAndError()
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            result = statistic_app.oneYearRightAndError()
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def oneYearRightAndError2(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            data = json.loads(data)

            left_line = data.get('left_line', '')
            right_line = data.get('right_line', '')

            result = statistic_app.oneYearRightAndError2(left_line=left_line, right_line=right_line)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            left_line = request.POST.get('left_line', '')
            right_line = request.POST.get('right_line', '')

            result = statistic_app.oneYearRightAndError2(left_line=left_line, right_line=right_line)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def oneYearRightAndError3(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':

            result = statistic_app.oneYearRightAndError3()
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            result = statistic_app.oneYearRightAndError3()
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def deptRightAndError(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            dept_name = data.get('dept_name', '')
            start_date = data.get('start_date', '')
            end_date = data.get('end_date', '')

            result = statistic_app.deptRightAndError(dept_name=dept_name, start_date=start_date, end_date=end_date)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            dept_name = request.POST.get('dept_name', '')
            start_date = request.POST.get('start_date', '')
            end_date = request.POST.get('end_date', '')

            result = statistic_app.deptRightAndError(dept_name=dept_name, start_date=start_date, end_date=end_date)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def regularManage(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            sheet_name = data.get('sheet_name', '')
            regular_name = data.get('regular_name', '')
            status = data.get('status', '')
            dept = data.get('dept', '')
            record = data.get('record', '')
            modified_dept = data.get('modified_dept', '')
            modified_code = data.get('modified_code', '')
            modified_score = data.get('modified_score', '')
            modified_status = data.get('modified_status', '')

            result = statistic_app.regularManage(sheet_name=sheet_name,
                                                 regular_name=regular_name,
                                                 status=status,
                                                 dept=dept,
                                                 record=record,
                                                 modified_dept=modified_dept,
                                                 modified_code=modified_code,
                                                 modified_score=modified_score,
                                                 modified_status=modified_status)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            sheet_name = request.POST.get('sheet_name', '')
            regular_name = request.POST.get('regular_name', '')
            status = request.POST.get('status', '')
            dept = request.POST.get('dept', '')
            record = request.POST.get('record', '')
            modified_dept = request.POST.get('modified_dept', '')
            modified_code = request.POST.get('modified_code', '')
            modified_score = request.POST.get('modified_score', '')
            modified_status = request.POST.get('modified_status', '')

            result = statistic_app.regularManage(sheet_name=sheet_name,
                                                 regular_name=regular_name,
                                                 status=status,
                                                 dept=dept,
                                                 record=record,
                                                 modified_dept=modified_dept,
                                                 modified_code=modified_code,
                                                 modified_score=modified_score,
                                                 modified_status=modified_status)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def graphPageHeader(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            result = statistic_app.graphPageHeader()
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':
            result = statistic_app.graphPageHeader()
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def fileDownload(request):
    def file_iterator(file_name, chunk_size=512):
            with open(file_name, 'rb') as f:
                while True:
                    c = f.read(chunk_size)
                    if c:
                        yield c
                    else:
                        break
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            status_bool = data.get('status_bool', 'all')
            if status_bool == 'false':
                status_bool = False
            elif status_bool == 'true':
                status_bool = True
            elif isinstance(status_bool, bool):
                pass
            else:
                status_bool = 'all'
            dept_name = data.get('dept_name', 'all')
            patient_id = data.get('patient_id', '')
            regular_details = data.get('regular_details', '')
            code = data.get('code', '')
            record = data.get('record', '')
            start_date = data.get('start_date', '')
            end_date = data.get('end_date', '')
            category = data.get('category', '')
            isResult = data.get('isResult', '')
            last_month = data.get('last_month', False)

            file_name = statistic_app.fileDownload(status_bool=status_bool,
                                                   dept_name=dept_name,
                                                   patient_id=patient_id,
                                                   regular_details=regular_details,
                                                   code=code,
                                                   record=record,
                                                   start_date=start_date,
                                                   end_date=end_date,
                                                   category=category,
                                                   isResult=isResult,
                                                   last_month=last_month)
            response = StreamingHttpResponse(file_iterator(file_name))
            response['Content-Type'] = 'application/octet-stream'
            response['Content-Disposition'] = 'attachment;filename="{0}"'.format(file_name)
            return response

        elif request.content_type == 'multipart/form-data':
            status_bool = request.POST.get('status_bool', 'all')
            if status_bool == 'false':
                status_bool = False
            elif status_bool == 'true':
                status_bool = True
            elif isinstance(status_bool, bool):
                pass
            else:
                status_bool = 'all'
            dept_name = request.POST.get('dept_name', 'all')
            patient_id = request.POST.get('patient_id', '')
            regular_details = request.POST.get('regular_details', '')
            code = request.POST.get('code', '')
            record = request.POST.get('record', '')
            start_date = request.POST.get('start_date', '')
            end_date = request.POST.get('end_date', '')
            category = request.POST.get('category', '')
            isResult = request.POST.get('isResult', '')
            last_month = request.POST.get('last_month', False)

            file_name = statistic_app.fileDownload(status_bool=status_bool,
                                                   dept_name=dept_name,
                                                   patient_id=patient_id,
                                                   regular_details=regular_details,
                                                   code=code,
                                                   record=record,
                                                   start_date=start_date,
                                                   end_date=end_date,
                                                   category=category,
                                                   isResult=isResult,
                                                   last_month=last_month)
            response = StreamingHttpResponse(file_iterator(file_name))
            response['Content-Type'] = 'application/octet-stream'
            response['Content-Disposition'] = 'attachment;filename="{0}"'.format(file_name)
            return response
        else:
            return False


@views_log
def problemNameAndCode(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            regular_name = data.get('regular_name', '')
            record = data.get('record', '')
            manage = data.get('manage', False)
            sheet_name = data.get('sheet_name', '')

            result = statistic_app.problemNameAndCode(regular_name=regular_name, record=record, manage=manage, sheet_name=sheet_name)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            regular_name = request.POST.get('regular_name', '')
            record = request.POST.get('record', '')
            manage = request.POST.get('manage', False)
            sheet_name = request.POST.get('sheet_name', '')

            result = statistic_app.problemNameAndCode(regular_name=regular_name, record=record, manage=manage, sheet_name=sheet_name)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def showDataResult(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            data_id = data.get('data_id', '')
            is_zhongmo = data.get('is_zhongmo', False)

            result = statistic_app.showDataResult(data_id=data_id, is_zhongmo=is_zhongmo)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            data_id = request.POST.get('data_id', '')
            is_zhongmo = request.POST.get('is_zhongmo', False)

            result = statistic_app.showDataResult(data_id=data_id, is_zhongmo=is_zhongmo)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def record_to_regular(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            record = data.get('record', '')

            result = statistic_app.record_to_regular(record=record)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            record = request.POST.get('record', '')

            result = statistic_app.record_to_regular(record=record)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def regular_to_detail(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            regular = data.get('regular', '')

            result = statistic_app.regular_to_detail(regular=regular)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            regular = request.POST.get('regular', '')

            result = statistic_app.regular_to_detail(regular=regular)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def detail_to_score(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            detail = data.get('detail', '')

            result = statistic_app.detail_to_score(detail=detail)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            detail = request.POST.get('detail', '')

            result = statistic_app.detail_to_score(detail=detail)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def record_list(request):
    statistic_app = StatisticPatientInfos()
    # logger.info(request.META.get('REMOTE_ADDR'))
    if request.method == 'POST':
        if request.content_type == 'text/plain':

            result = statistic_app.record_list()
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            result = statistic_app.record_list()
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def version(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':

            result = statistic_app.version()
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            result = statistic_app.version()
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def testClient(request):
    if request.method == 'POST':
        statistic_app = StatisticPatientInfos()
        search_id = ''
        record_name = ''
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            search_id = data.get('search_id', '')
            record_name = data.get('record_name', '')
        elif request.content_type == 'multipart/form-data':

            search_id = request.POST.get('search_id', '')
            record_name = request.POST.get('record_name', '')
        if not search_id:
            return HttpResponse(json.dumps({'res_flg': False, 'info': '请输入文档ID'}))
        if not record_name:
            return HttpResponse(json.dumps({'res_flg': False, 'info': '请输入文书名'}))
        user_obj = request.user
        yonghuxingxi = dict()
        if user_obj.is_anonymous:
            yonghuxingxi['user_id'] = ''
            yonghuxingxi['user_name'] = ''
            yonghuxingxi['user_dept'] = ''
            yonghuxingxi['role_id'] = ''
            yonghuxingxi['role_name'] = ''
        else:
            yonghuxingxi['user_id'] = user_obj.USER_ID
            yonghuxingxi['user_name'] = user_obj.USER_NAME
            yonghuxingxi['user_dept'] = request.session.get('dept')
            yonghuxingxi['role_name'] = request.session.get('role')
            yonghuxingxi['role_id'] = request.session.get('role_id')
        result = statistic_app.testClient(search_id=search_id, record_name=record_name)
        result['yonghuxinxi'] = yonghuxingxi
        return HttpResponse(json.dumps({'res_flg': True, 'result': result}))
    return HttpResponse(json.dumps({'res_flg': False, 'info': 'use POST method to request'}))


@views_log
def zhongmoDept(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':

            result = statistic_app.zhongmoDept()
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            result = statistic_app.zhongmoDept()
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def deptProblemPercentage(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':

            result = statistic_app.deptProblemPercentage()
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            result = statistic_app.deptProblemPercentage()
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def deptProblemClassify(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            dept = data.get('dept', '')

            result = statistic_app.deptProblemClassify(dept=dept)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            dept = request.POST.get('dept', '')

            result = statistic_app.deptProblemClassify(dept=dept)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def doctorProblemNum(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            dept = data.get('dept', '')

            result = statistic_app.doctorProblemNum(dept=dept)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            dept = request.POST.get('dept', '')

            result = statistic_app.doctorProblemNum(dept=dept)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def zhongmoRecordName(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':

            result = statistic_app.zhongmoRecordName()
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            result = statistic_app.zhongmoRecordName()
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def zhongmoRegularName(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':

            result = statistic_app.zhongmoRegularName()
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            result = statistic_app.zhongmoRegularName()
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def documentProblemClassify(request):
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            record_name = data.get('record_name', '')

            result = statistic_app.documentProblemClassify(record_name=record_name)
            return HttpResponse(json.dumps(result))
        elif request.content_type == 'multipart/form-data':

            record_name = request.POST.get('record_name', '')

            result = statistic_app.documentProblemClassify(record_name=record_name)
            return HttpResponse(json.dumps(result))
        else:
            return HttpResponse(json.dumps({}))


@views_log
def zhongmoFileDownloadMingxi(request):
    def file_iterator(file_name, chunk_size=512):
            with open(file_name, 'rb') as f:
                while True:
                    c = f.read(chunk_size)
                    if c:
                        yield c
                    else:
                        break
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            start_date = data.get('start_date', '')
            end_date = data.get('end_date', '')
            dept = data.get('dept', '')
            regular_name = data.get('regular_name', '')

            file_name = statistic_app.zhongmoFileDownloadMingxi(start_date=start_date,
                                                                end_date=end_date,
                                                                dept=dept,
                                                                regular_name=regular_name)
            response = StreamingHttpResponse(file_iterator(file_name))
            response['Content-Type'] = 'application/octet-stream'
            response['Content-Disposition'] = 'attachment;filename="{0}"'.format(file_name)
            return response

        elif request.content_type == 'multipart/form-data':
            start_date = request.POST.get('start_date', '')
            end_date = request.POST.get('end_date', '')
            dept = request.POST.get('dept', '')
            regular_name = request.POST.get('regular_name', '')

            file_name = statistic_app.zhongmoFileDownloadMingxi(start_date=start_date,
                                                                end_date=end_date,
                                                                dept=dept,
                                                                regular_name=regular_name)
            response = StreamingHttpResponse(file_iterator(file_name))
            response['Content-Type'] = 'application/octet-stream'
            response['Content-Disposition'] = 'attachment;filename="{0}"'.format(file_name)
            return response
        else:
            return False


@views_log
def zhongmoFileDownloadHuizong(request):
    def file_iterator(file_name, chunk_size=512):
            with open(file_name, 'rb') as f:
                while True:
                    c = f.read(chunk_size)
                    if c:
                        yield c
                    else:
                        break
    statistic_app = StatisticPatientInfos()
    if request.method == 'POST':
        if request.content_type == 'text/plain':
            data = request.body
            data = data.decode('utf-8')
            if not data:
                data = '{}'
            data = json.loads(data)

            start_date = data.get('start_date', '')
            end_date = data.get('end_date', '')
            dept = data.get('dept', '')
            regular_name = data.get('regular_name', '')

            file_name = statistic_app.zhongmoFileDownloadHuizong(start_date=start_date,
                                                                 end_date=end_date,
                                                                 dept=dept,
                                                                 regular_name=regular_name)
            response = StreamingHttpResponse(file_iterator(file_name))
            response['Content-Type'] = 'application/octet-stream'
            response['Content-Disposition'] = 'attachment;filename="{0}"'.format(file_name)
            return response

        elif request.content_type == 'multipart/form-data':
            start_date = request.POST.get('start_date', '')
            end_date = request.POST.get('end_date', '')
            dept = request.POST.get('dept', '')
            regular_name = request.POST.get('regular_name', '')

            file_name = statistic_app.zhongmoFileDownloadHuizong(start_date=start_date,
                                                                 end_date=end_date,
                                                                 dept=dept,
                                                                 regular_name=regular_name)
            response = StreamingHttpResponse(file_iterator(file_name))
            response['Content-Type'] = 'application/octet-stream'
            response['Content-Disposition'] = 'attachment;filename="{0}"'.format(file_name)
            return response
        else:
            return False


if __name__ == '__main__':
    pass
