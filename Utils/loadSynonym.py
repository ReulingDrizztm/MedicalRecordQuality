#!/usr/bin/env python3
# -*- coding:utf-8 -*

"""
@version: 
@author:
@contact:
@software: PyCharm Community Edition
@file: loadSynonym.py
@time: 18-7-3 下午6:10
@description: 
"""
import os


class Synonym(object):
    def __init__(self):
        self.dict_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'configure/dict')
        self.dict_info = self.loadconf()

    def loadconf(self):
        word_dict = dict()
        for i in os.listdir(self.dict_path):
            if i.endswith('synonym.csv'):
                file_path = os.path.join(self.dict_path, i)
                with open(file_path, 'r', encoding='utf8') as f:
                    for line in f.readlines():
                        line = line.strip()
                        line = line.split(',')
                        word_dict.setdefault(line[0], set())
                        word_dict.setdefault(line[1], set())
                        word_dict[line[0]].add(line[1])
                        word_dict[line[1]].add(line[0])
        return word_dict


if __name__ == '__main__':
    app = Synonym()
