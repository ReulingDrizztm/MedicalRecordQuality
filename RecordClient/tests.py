from django.test import TestCase
from .clientInterface import ClientInterface
import json


app = ClientInterface()


class ViewTest(TestCase):

    def __init__(self, methodName):
        super(ViewTest, self).__init__(methodName)  # 继承父类的构造方法
        self.localhost = 'http://localhost/med/RecordClientTest/'

    def recordModifySort(self, data=''):
        location = self.localhost + self.recordModifySort.__name__ + '.json'
        if data and isinstance(data, dict):
            response = self.client.post(location, data=data)
        else:
            response = self.client.post(location)
        r = app.recordModifySort()
        result = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.failUnlessEqual(r, result)
