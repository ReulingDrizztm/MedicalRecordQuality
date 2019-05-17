#!/usr/bin/env python3
# -*- coding:utf-8 -*-

# 将规则导出列表.xlsx转化成csv

import os
import sys
curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
import xlrd
from datetime import datetime


def process():
    regular_xlsx = os.path.join(rootPath, 'configure/regular_model.xlsx')
    release_path = os.path.join(rootPath, 'configure/regular_model')
    if not os.path.exists(release_path):
        os.mkdir(release_path)
    workbook = xlrd.open_workbook(regular_xlsx)
    name_switch = {'医生端': 'yishengduan.csv', '环节': 'huanjie.csv', '终末': 'zhongmo.csv'}
    for sheet in workbook.sheets():
        sheet_line = list()
        file_name = name_switch.get(sheet.name)
        if not file_name:
            continue
        nrows = sheet.nrows
        ncols = sheet.ncols
        for row in range(1, nrows):
            if not sheet.cell_value(row, 1):
                continue
            line = list()
            for col in range(1, ncols):
                if sheet.cell(row, col).ctype == 2:
                    line.append(str(sheet.cell_value(row, col)))
                elif sheet.cell(row, col).ctype == 3:
                    date = datetime(*xlrd.xldate_as_tuple(sheet.cell_value(row, col), 0))
                    line.append(date.strftime('%Y-%m-%d'))
                else:
                    line.append(sheet.cell_value(row, col))
            line.append('\n')
            line_str = ','.join(line)
            sheet_line.append(line_str)
        with open(os.path.join(release_path, file_name), 'w', encoding='utf8') as f:
            s = ''.join(sheet_line)
            f.write(s)
            print('{} has been saved.'.format(os.path.join(release_path, file_name)))
    return True


if __name__ == '__main__':
    app = process()
