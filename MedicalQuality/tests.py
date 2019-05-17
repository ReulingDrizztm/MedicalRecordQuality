from django.test import TestCase
from .statisticPatientsInfos import StatisticPatientInfos
import json


app = StatisticPatientInfos()


class ViewTest(TestCase):

    def __init__(self, methodName):
        super(ViewTest, self).__init__(methodName)  # 继承父类的构造方法
        self.localhost = 'http://localhost/med/MedicalQuality/'

    def record_to_regular(self, data=''):
        location = self.localhost + self.record_to_regular.__name__ + '.json'
        data = {'record': '首次病程'}
        if data and isinstance(data, dict):
            response = self.client.post(location, data=data)
        else:
            response = self.client.post(location)
        r = app.record_to_regular('首次病程')
        print(r)
        result = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.failUnlessEqual(r, result)