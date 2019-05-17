"""
WSGI config for MedicalRecordQuality project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/howto/deployment/wsgi/
"""

import os
import traceback
from django.core.wsgi import get_wsgi_application
from apscheduler.schedulers.background import BackgroundScheduler

from MedicalQuality.scheduledTasks import runZhongmo
from RecordClient.timedTask import HospitalServerInfo
from Utils.LogUtils import LogUtils

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "MedicalRecordQuality.settings")
scheduler = BackgroundScheduler()
scheduler._logger.disabled = True


## 定时任务
@scheduler.scheduled_job('cron', hour="3")  # 定时任务，每天晚上3点运行
def hospital_server_info():
    """
    定时请求电子病历服务器Webservice，获取在院/出院患者数据，医生患者数
    """
    logger = LogUtils().getLogger('scheduledTasks')
    try:
        app = HospitalServerInfo()
        print('start {0}'.format(app))
        app.get_inhospitalpatdata()
        app.get_inhospitalpatnum()
        app.get_dischargepatdata()
        app.get_dischargepatnum()
        print('end {0}'.format(app))
    except:
        logger.error(traceback.format_exc())


@scheduler.scheduled_job('cron', hour="3")
def runRegularScheduled():
    """
    每天定时跑终末质控
    """
    logger = LogUtils().getLogger('scheduledTasks')
    try:
        runZhongmo()
    except:
        logger.error(traceback.format_exc())
        return False


# try:
#     scheduler.start()
# except(KeyboardInterrupt, SystemExit):
#     scheduler.shutdown()
## 结束-定时任务


application = get_wsgi_application()
