# -*-coding=utf-8-*-
import datetime
import httplib
import json
import random
import time

import qiye_wechat
from logger import Logger

logger = Logger('qianka_spider').logger

cookie = 'DIS4=a0a82cab557c4419b3faccba37a229a9; ln=1; lu=54371634; qk:referer=5568105ad8498; qk:guid:appstore=28ccb90e-920d-40ef-98ca-e55ac68d4d7d'
header = {"Host": "qianka.com",
          "Cookie": cookie,
          "Connection": "keep-alive"}


class Task:
    def __init__(self):
        pass


def get_timestamp():
    return int(time.time() * 1000)


def current_timestr():
    return time.strftime('%Y-%m-%d %H:%m:%S', time.localtime())


def get_task_list():
    """0正常返回，1，异常返回，2有进行中任务"""
    try:
        conn = httplib.HTTPConnection('qianka.com')
        url = 'https://qianka.com/s4/lite.subtask.list?t=%d' % get_timestamp()
        conn.request(method='GET', url=url, headers=header)
        response = conn.getresponse()
        resp_str = response.read()
        json_str = json.loads(resp_str)
        err_code = json_str['err_code']
        if err_code != 0:
            return 1, json_str['err_msg']
        payload = json_str['payload']
        tasks = payload['tasks']
        available_tasks = []

        for task in tasks:
            task_id = int(task['id'])
            status = int(task['status'])
            if status == 2:  # 进行中任务
                return 2, [task]
            reward = float(task['reward'])
            if reward >= 5:  # 大于5元的基本都是注册任务，过滤掉
                continue
            zs_reward = float(task['zs_reward'])
            quality = int(task['qty'])
            appstore_cost = float(task['appstore_cost'])
            profit = reward + zs_reward - appstore_cost
            if quality > 0:
                task_obj = Task()
                task_obj.id = task_id
                task_obj.quality = quality
                task_obj.profit = profit
                available_tasks.append(task_obj)
        task_list = []
        if len(available_tasks) > 0:
            task_list = sorted(available_tasks, key=lambda task: (task.profit, task.quality), reverse=True)
        return 0, task_list
    except Exception, e:
        logger.info(u'查询任务异常：')
        logger.exception(e)
        return 1, u'查询任务异常'


def grab(task=None):
    try:
        if task is None:
            logger.info(u'任务为空，抢任务失败')
            return
        logger.info(u'开始抢task_id=%d的任务...' % task.id)
        conn = httplib.HTTPConnection('qianka.com')
        url = 'https://qianka.com/s4/lite.subtask.start?t=%d&task_id=%d&quality=%d' % (
            get_timestamp(), task.id, task.quality)
        conn.request(method='GET', url=url, headers=header)
        response = conn.getresponse()
        resp_str = response.read()
        logger.info(resp_str)
        json_str = json.loads(resp_str)
        err_code = json_str['err_code']
        if err_code != 0:
            logger.info(u'抢task_id=%d的任务失败: %s' % (task.id, json_str['err_msg']))
            return
        payload = json_str['payload']
        logger.info(u'抢task_id=%d的任务结果: %s' % (task.id, payload['message']))
    except Exception, e:
        logger.info(u'抢task_id=%d的任务出现异常: ' + unicode(repr(e)))


def notify_dingding(msg=''):
    notify_data = {
        "token": "",
        "title": u"任务提醒",
        "server": "yangtao",
        "context": msg,
        "type": "markdown",
        "category": "1"
    }
    try:
        json_data = json.dumps(notify_data).encode()
        notify_header = {"Host": "qa01.letzgo.com.cn", "Content-Type": "application/json"}
        conn = httplib.HTTPSConnection('qa01.letzgo.com.cn')
        conn.request(method='POST', url='https://qa01.letzgo.com.cn/ding_service/api/ding/forward',
                     body=json_data, headers=notify_header)
        response = conn.getresponse()
        res = response.read()
        logger.info(res)
        return int(json.loads(res)["code"]) == 200
    except Exception, e:
        logger.info('notify ding ding failure: ' + unicode(repr(e)))
        return


if __name__ == '__main__':
    rounds = 1
    last_error_notify_time = 0
    while True:
        logger.info(u'第%d次轮询开始...' % rounds)
        search_status, result = get_task_list()
        if search_status == 1:  # 出现错误
            logger.info(result)
            current_millis = get_timestamp()
            if u'绑定钥匙' in result and current_millis - last_error_notify_time > 2 * 60 * 1000:  # 两分钟之后再提醒，避免一直重复提醒
                qiye_wechat.send(result)
                last_error_notify_time = current_millis
            randint = random.randint(10, 15)
            logger.info(u'暂停%d秒...' % randint)
            time.sleep(randint)
            continue
        if search_status == 2:  # 有进行中任务，暂停5分钟
            msg = u'您有进行中的任务，请及时处理！'
            logger.info(msg)
            qiye_wechat.send(msg=msg)
            logger.info(u'暂停5分钟...')
            time.sleep(5 * 60)
            continue
        for task in result:  # 有任务则抢
            if result.index(task) > 2:  # 只抢前三个，防止访问频率过高
                break
            grab(task)
            time.sleep(0.5)
        logger.info(u'第%d次轮询结束' % rounds)
        minute = datetime.datetime.now().minute
        if (28 <= minute <= 33) or (0 <= minute <= 3) or (58 <= minute <= 59):  # 整点附近加快刷新频率
            randint = random.randint(3, 4)
            logger.info(u'暂停%d秒...' % randint)
            time.sleep(randint)
        else:
            randint = random.randint(5, 20)
            logger.info(u'暂停%d秒...' % randint)
            time.sleep(randint)
        rounds = rounds + 1
