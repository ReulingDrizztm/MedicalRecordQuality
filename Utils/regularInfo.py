#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import os
import sys
cur_path = os.path.abspath(os.path.dirname(__file__))
root_path = os.path.split(cur_path)[0]
sys.path.append(root_path)  # 项目路径添加到系统路径
from Utils.loadingConfigure import Properties


class RegularInfo(object):
    # 是否初始化

    def __init__(self, regular_code, step):
        regular_model = Properties().regular_model[step].copy()
        self.code = ''
        self.regular_name = ''
        self.regular_details = ''
        self.record_name = ''
        self.score = 0
        self.dept = ''
        self.setup = ''
        self.switch = ''
        self.degree = ''
        self.step = step
        if regular_code in regular_model:
            v = regular_model[regular_code]
            self.code = regular_code
            if len(v) > 0:
                self.regular_name = v[0]
            if len(v) > 1:
                self.regular_details = v[1]
            if len(v) > 2:
                record_name = v[2].split('--')[0]
                self.record_name = record_name
            if len(v) > 3:
                self.score = v[3]
            if len(v) > 4:
                self.dept = v[4]
            if len(v) > 5:
                self.setup = v[5]
            if len(v) > 6:
                self.switch = v[6]
            if len(v) > 7:
                self.degree = v[7]


if __name__ == '__main__':
    app = RegularInfo('SY0001', '终末')
