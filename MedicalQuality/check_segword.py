#!/usr/bin/env python3
# -*- coding:utf-8 -*

import os
import sys
cur_path = os.path.abspath(os.path.dirname(__file__))
root_path = os.path.split(cur_path)[0]
sys.path.append(root_path)  # 项目路径添加到系统路径
import traceback
from MedicalQuality.mainProgram import CheckMultiRecords
from Utils.LogUtils import LogUtils

logger = LogUtils().getLogger("record_info")
logger_info = LogUtils().getLogger("run_info")
logger_error = LogUtils().getLogger("root")


class CheckSegmentWord(CheckMultiRecords):

    def check_chief_content(self, time_limits):
        try:
            mongo_result = self.gain_info.collection_bingan.aggregate([
                    {"$match": time_limits},
                    {"$lookup": {"from": 'ruyuanjilu',
                                 "localField": "_id",
                                 "foreignField": "_id",
                                 "as": 'ruyuanjilu'}},
                    {"$match": {'ruyuanjilu.ruyuanjilu.chief_complaint': {'$exists': True}}},
                    {"$project": {'patient_id': 1,
                                  'visit_id': 1,
                                  'binganshouye': 1,
                                  'ruyuanjilu.ruyuanjilu.chief_complaint': 1,
                                  'ruyuanjilu.ruyuanjilu.chief_complaint.src': 1,
                                  'ruyuanjilu.ruyuanjilu.creator_name': 1,
                                  'ruyuanjilu.ruyuanjilu.last_modify_date_time': 1,
                                  'ruyuanjilu.batchno': 1}}], allowDiskUse=True).batch_size(50)

            for data in mongo_result:
                logger_info.info('{0} processing: {1}'.format(self.check_chief_content.__name__, data['_id']))
                collection_data, patient_result, num = self.get_patient_info(data)
                chief_time, flag = self.gain_info._gain_chief_time(collection_data['ruyuanjilu'].get('chief_complaint', dict()))
                chief_src = self.gain_info._gain_src(cursor=collection_data,
                                                     collection_name='ruyuanjilu',
                                                     chapter_name='chief_complaint')
                batchno = collection_data.get('batchno', '')
                creator_name = self.gain_info._gain_file_creator(cursor=collection_data,
                                                                 collection_name='ruyuanjilu')
                file_time = self.gain_info._gain_file_time(cursor=collection_data,
                                                           collection_name='ruyuanjilu')
                if chief_time:
                    logger_info.info('Done: {0}'.format(data['_id']))
                    continue
                else:
                    reason = '未提取出主诉内容信息'
                if self.debug:
                    logger.info('\n主诉缺失时间：\n\tid: {0}\n\tchapter: {1}\n\treason: {2}\n\tbatchno: {3}\n'.
                                format(data['_id'],
                                       collection_data['ruyuanjilu']['chief_complaint'],
                                       reason,
                                       batchno))
                error_info = {'code': 'RYJLZS0001',
                              'num': num,
                              'chief_src': chief_src,
                              'reason': reason}
                error_info = self.supplement_error_info(error_info, creator_name, file_time, 'ruyuanjilu')
                if 'score' in error_info:
                    patient_result['pat_info']['machine_score'] += error_info['score']
                patient_result['pat_value'].append(error_info)
                patient_result['pat_info'].setdefault('html', list())
                if 'ruyuanjilu' not in patient_result['pat_info']['html']:
                    patient_result['pat_info']['html'].append('ruyuanjilu')
                self.all_result[data['_id']] = patient_result
                logger_info.info('Done: {0}'.format(data['_id']))
        except:
            logger_error.error(traceback.format_exc())
        return self.all_result

    def check_past_deny_length(self, time_limits):
        try:
            mongo_result = self.gain_info.collection_bingan.aggregate([
                {"$match": time_limits},
                {"$lookup": {"from": 'ruyuanjilu',
                             "localField": "_id",
                             "foreignField": "_id",
                             "as": 'ruyuanjilu'}},
                {"$match": {'ruyuanjilu.ruyuanjilu.history_of_past_illness.deny': {'$exists': True},
                            '$or': [{'ruyuanjilu.ruyuanjilu.history_of_past_illness.disease.disease_name': {'$exists': True}},
                                    {'ruyuanjilu.ruyuanjilu.history_of_past_illness.operation.operation_name': {'$exists': True}}]}},
                {"$project": {'patient_id': 1,
                              'visit_id': 1,
                              'binganshouye': 1,
                              'ruyuanjilu.ruyuanjilu.history_of_past_illness.deny': 1,
                              'ruyuanjilu.ruyuanjilu.history_of_past_illness.src': 1,
                              'ruyuanjilu.ruyuanjilu.creator_name': 1,
                              'ruyuanjilu.batchno': 1,
                              'ruyuanjilu.ruyuanjilu.last_modify_date_time': 1}}], allowDiskUse=True).batch_size(50)
            for data in mongo_result:
                logger_info.info('{0} processing: {1}'.format(self.check_past_deny_length.__name__, data['_id']))
                collection_data, patient_result, num = self.get_patient_info(data)
                creator_name = self.gain_info._gain_file_creator(cursor=collection_data,
                                                                 collection_name='ruyuanjilu')
                file_time = self.gain_info._gain_file_time(cursor=collection_data, collection_name='ruyuanjilu')  # 获取文书时间
                past_src = self.gain_info._gain_src(cursor=collection_data,
                                                    collection_name='ruyuanjilu',
                                                    chapter_name='history_of_past_illness')
                past_chapter = collection_data.get('ruyuanjilu', dict()).get('history_of_past_illness', dict())
                batchno = collection_data.get('batchno', '')
                deny = past_chapter.get('deny', '').split(' ')
                target_deny = set()
                for d in deny:
                    if len(d) > 5:
                        target_deny.add(d)
                if not target_deny:
                    logger_info.info('Done: {0}'.format(data['_id']))
                    continue
                reason = '既往史否认项过长'
                if self.debug:
                    logger.info('\n既往史否认项过长：\n\tid: {0}\n\tdeny: {1}\n\tbatchno: {2}\n'.
                                format(data['_id'],
                                       '/'.join(target_deny),
                                       batchno))
                error_info = {'code': 'RYJLJWS0006',
                              'num': num,
                              'past_src': past_src,
                              'deny': '/'.join(target_deny),
                              'reason': reason}
                error_info = self.supplement_error_info(error_info, creator_name, file_time, 'ruyuanjilu')
                if 'score' in error_info:
                    patient_result['pat_info']['machine_score'] += error_info['score']
                patient_result['pat_value'].append(error_info)
                patient_result['pat_info'].setdefault('html', list())
                if 'ruyuanjilu' not in patient_result['pat_info']['html']:
                    patient_result['pat_info']['html'].append('ruyuanjilu')
                self.all_result[data['_id']] = patient_result
                logger_info.info('Done: {0}'.format(data['_id']))
        except:
            logger_error.error(traceback.format_exc())
        return self.all_result

    def check_present_ciqian(self, time_limits):
        try:
            mongo_result = self.gain_info.collection_bingan.aggregate([
                {"$match": time_limits},
                {"$lookup": {"from": 'ruyuanjilu',
                             "localField": "_id",
                             "foreignField": "_id",
                             "as": 'ruyuanjilu'}},
                {"$match": {'ruyuanjilu.ruyuanjilu.history_of_present_illness.time.time_value': '此前'}},
                {"$project": {'patient_id': 1,
                              'visit_id': 1,
                              'binganshouye': 1,
                              'ruyuanjilu.ruyuanjilu.history_of_present_illness.src': 1,
                              'ruyuanjilu.ruyuanjilu.history_of_present_illness.time.time_value': 1,
                              'ruyuanjilu.ruyuanjilu.creator_name': 1,
                              'ruyuanjilu.batchno': 1,
                              'ruyuanjilu.ruyuanjilu.last_modify_date_time': 1}}], allowDiskUse=True).batch_size(50)
            for data in mongo_result:
                logger_info.info('{0} processing: {1}'.format(self.check_present_ciqian.__name__, data['_id']))
                collection_data, patient_result, num = self.get_patient_info(data)
                creator_name = self.gain_info._gain_file_creator(cursor=collection_data,
                                                                 collection_name='ruyuanjilu')
                file_time = self.gain_info._gain_file_time(cursor=collection_data, collection_name='ruyuanjilu')  # 获取文书时间
                present_src = self.gain_info._gain_src(cursor=collection_data,
                                                       collection_name='ruyuanjilu',
                                                       chapter_name='history_of_present_illness')
                past_chapter = collection_data.get('ruyuanjilu', dict()).get('history_of_present_illness', dict())
                batchno = collection_data.get('batchno', '')
                time_model = past_chapter.get('time', list())
                if not time_model:
                    logger_info.info('Done: {0}'.format(data['_id']))
                    continue
                if time_model[0].get('time_value', '') != '此前':
                    logger_info.info('Done: {0}'.format(data['_id']))
                    continue
                if '此前' in present_src:
                    logger_info.info('Done: {0}'.format(data['_id']))
                    continue
                reason = '现病史首个时间节点为此前'
                if self.debug:
                    logger.info('\n现病史首个时间节点为此前:\n\tid: {0}\n\tbatchno: {1}\n'.
                                format(data['_id'],
                                       batchno))
                error_info = {'code': 'RYJLXBS0005',
                              'num': num,
                              'present_src': present_src,
                              'reason': reason}
                error_info = self.supplement_error_info(error_info, creator_name, file_time, 'ruyuanjilu')
                if 'score' in error_info:
                    patient_result['pat_info']['machine_score'] += error_info['score']
                patient_result['pat_value'].append(error_info)
                patient_result['pat_info'].setdefault('html', list())
                if 'ruyuanjilu' not in patient_result['pat_info']['html']:
                    patient_result['pat_info']['html'].append('ruyuanjilu')
                self.all_result[data['_id']] = patient_result
                logger_info.info('Done: {0}'.format(data['_id']))
        except:
            logger_error.error(traceback.format_exc())
        return self.all_result

    def seg_process(self):
        self.all_result = dict()
        time_limits = self.pre_process()
        if not time_limits:
            return False
        result = dict()
        for time_range in time_limits:  # 规则分为半年半年的数据运行
            time_para = {'binganshouye.pat_visit.discharge_time': {'$gte': time_range[0], '$lt': time_range[1]}}  # 运行规则的出院时间段
            # self.all_result = self.check_past_deny_length(time_limits=time_para)
            self.all_result = self.check_present_ciqian(time_limits=time_para)
        result.update(self.all_result)
        self.gain_info.write_to_file(result, './{0}.json'.format('present_ciqian'))
        # self.gain_info.write_to_file(result, './{0}.json'.format('past_deny'))
        return result


if __name__ == '__main__':
    app = CheckSegmentWord(debug=True)
    # app.seg_process()
