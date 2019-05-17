#!/usr/bin/env python3
# -*- coding:utf-8 -*

import re
import os


class Node(object):
    def __init__(self, word=None):
        self.word = word
        self.children = list()  # 子节点
        self.same = list()  # 同义词
        self.parent = None  # 父节点


class Tree(object):

    is_init = False

    def __init__(self):
        if not Tree.is_init:
            self.root = Node('*')
            self.dict_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'configure/dict/relationship.csv')
            self.loadconf()
            self.word_node = None
            Tree.is_init = True

    def __new__(cls, *args, **kwargs):
        """
        单例模式
        """
        if not hasattr(cls, 'instance'):
            cls.instance = super(Tree, cls).__new__(cls)
        return cls.instance

    def loadconf(self):
        with open(self.dict_path, 'r', encoding='utf8') as f:
            for line in f.readlines():
                line = line.strip()
                line_list = line.split(',')
                line_list.insert(0, '*')
                for index in range(1, len(line_list)):
                    parent, children = line_list[index-1], line_list[index]
                    self.add_word(parent, children)
        return

    def find_word(self, tree, word):
        if tree.word == word:
            return tree
        elif tree.children:
            for i in tree.children:
                if not self.find_word(i, word):
                    continue
                else:
                    return self.find_word(i, word)
        else:
            return False

    def add_word(self, parent, word):
        new_node = Node(word)
        if '(' in parent or '（' in parent:
            parent = re.sub('[\)|\）]*', '', parent)
            parent = re.split('[\(|\（]', parent)
            parent = parent[0]
        same_flag = ''
        if '(' in word or '（' in word:
            word = re.sub('[\)|\）]*', '', word)
            word = re.split('[\(|\（]', word)
            same_flag = word[1]
            word = word[0]
        if self.find_word(self.root, word):
            if same_flag:
                self.find_word(self.root, word).same.append(same_flag)
            return
        if '(' in new_node.word or '（' in new_node.word:
            new_node.word = re.sub('[\)|\）]*', '', new_node.word)
            word = re.split('[\(|\（]', new_node.word)
            new_node.word = word[0]
            new_node.same.append(word[1])
        parent_node = self.find_word(self.root, parent)
        new_node.parent = parent_node
        parent_node.children.append(new_node)


if __name__ == "__main__":
    t = Tree()
    x = t.find_word(t.root, "左下腹痛")
    t.add_word('*', '头痛（脑壳痛）')
