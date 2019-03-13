# -*-coding=utf-8-*-
import httplib
import json
import logging
import random
import sqlite3
import time
from ConfigParser import ConfigParser
from datetime import datetime


class Logger(object):
    """日志模块"""

    def __init__(self, name=None, level=logging.INFO):
        self.logger = logging.getLogger(name)
        format_str = logging.Formatter('%(asctime)s - [%(pathname)s line:%(lineno)d] => %(levelname)s: %(message)s')
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(format_str)
        self.logger.addHandler(stream_handler)

        file_handler = logging.FileHandler(filename='info.log', mode='a', encoding='utf-8')
        file_handler.setFormatter(format_str)
        self.logger.addHandler(file_handler)

        self.logger.setLevel(level)


class Task(object):
    """任务列表中的任务信息"""

    def __init__(self):
        self.id = 0
        self.quality = 0
        self.reward = 0
        self.zs_reward = 0
        self.profit = 0
        self.status = 0
        self.icon = ''


class TaskDetail(object):
    """任务详细信息"""

    def __init__(self):
        self.task_id = 0
        self.app_name = ''
        self.app_keyword = ''
        self.scheme_url = ''
        self.callback_url = ''
        self.expire_at = 0
        self.task_status = ''
        self.tips = ''


class QiyeWechat(object):
    """企业微信消息发送"""

    def __init__(self):
        self.logger = Logger('QiyeWechat').logger
        self.corp_id = ConfigUtil.get('qiyewechat', 'corp_id')
        self.agent_id = ConfigUtil.get('qiyewechat', 'agent_id')
        self.secret = ConfigUtil.get('qiyewechat', 'secret')
        self.header = {
            "Host": "qyapi.weixin.qq.com",
            "Connection": "keep-alive",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
        }

    def __get_access_token(self):
        conn = sqlite3.connect('master.db')
        cursor = conn.cursor()
        sql = "SELECT * FROM t_access_token WHERE STATUS=1 ORDER BY ID DESC;"
        row = cursor.execute(sql).fetchone()
        cursor.close()
        conn.close()
        if self.__is_valid_token(row):
            return row[1]
        else:
            access_token, expire_in = self.__get_access_token_from_wechat()
            if access_token is None:
                raise Exception('get access token from wechat failure')
            self.__save_access_token(access_token, expire_in)
            return access_token

    def __is_valid_token(self, row=None):
        if row is None:
            return False
        expire_in = row[2]
        status = row[3]
        create_date = row[4]
        if status == 0:
            return False
        current_time = int(time.time() * 1000)
        duration = int((current_time - create_date) / 1000)
        if duration >= expire_in:
            return False
        return True

    def __get_access_token_from_wechat(self):
        try:
            url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=%s&corpsecret=%s' % (self.corp_id, self.secret)
            conn = httplib.HTTPSConnection("qyapi.weixin.qq.com", timeout=5)
            conn.request(method='GET', url=url, headers=self.header)
            response = conn.getresponse()
            resp_str = response.read()
            json_str = json.loads(resp_str)
            return json_str['access_token'], json_str['expires_in']
        except Exception, e:
            self.logger.exception(e)
            return None, None

    def __save_access_token(self, token='', expire_in=7200, status=1):
        current_time = int(time.time() * 1000)
        conn = sqlite3.connect('master.db')
        cursor = conn.cursor()
        update_sql = "UPDATE t_access_token set STATUS=0 WHERE STATUS=1;"
        cursor.execute(update_sql)
        insert_sql = "INSERT INTO t_access_token(ACCESS_TOKEN, EXPIRE_IN, STATUS,CREATE_DATE) VALUES ('%s',%d,%d,'%s');" % (
            token, expire_in, status, str(current_time))
        cursor.execute(insert_sql)
        conn.commit()
        cursor.close()
        conn.close()

    def send_msg(self, msg=''):
        try:
            access_token = self.__get_access_token()
            body = {
                "touser": "@all",
                "toparty": "",
                "totag": "",
                "msgtype": "text",
                "agentid": self.agent_id,
                "text": {
                    "content": msg
                },
                "safe": 0
            }
            json_body = json.dumps(body).encode('utf-8')
            url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=%s' % access_token
            conn = httplib.HTTPSConnection("qyapi.weixin.qq.com", timeout=5)
            conn.request(method='POST', url=url, body=json_body, headers=self.header)
            response = conn.getresponse()
            resp_str = response.read()
            json_str = json.loads(resp_str)
            self.logger.info(u'企业微信发文本消息结果：%s' % json_str['errmsg'])
        except Exception, e:
            self.logger.exception(e)

    def send_news(self, title=u'消息通知', description=u'消息',
                  pic_url='http://img.zcool.cn/community/01786557e4a6fa0000018c1bf080ca.png'):
        try:
            access_token = self.__get_access_token()
            body = {
                "touser": "@all",
                "toparty": "",
                "totag": "",
                "msgtype": "news",
                "agentid": self.agent_id,
                "news": {
                    "articles": [
                        {
                            "title": title,
                            "description": description,
                            "url": pic_url,
                            "picurl": pic_url,
                            "btntxt": u"查看更多"
                        }
                    ]
                }
            }
            json_body = json.dumps(body).encode('utf-8')
            url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=%s' % access_token
            conn = httplib.HTTPSConnection("qyapi.weixin.qq.com", timeout=5)
            conn.request(method='POST', url=url, body=json_body, headers=self.header)
            response = conn.getresponse()
            resp_str = response.read()
            json_str = json.loads(resp_str)
            self.logger.info(u'企业微信发图文消息结果：%s' % json_str['errmsg'])
        except Exception, e:
            self.logger.exception(e)


class Dingding(object):
    """钉钉消息发送"""

    def __init__(self):
        self.logger = Logger('Dingding').logger

    def send_msg(self, msg=''):
        try:
            notify_data = {
                "token": ConfigUtil.get('dingding', 'token'),
                "title": u"任务提醒",
                "server": "yangtao",
                "context": msg,
                "type": "markdown",
                "category": "1"
            }
            json_data = json.dumps(notify_data).encode()
            notify_header = {"Host": "qa01.letzgo.com.cn", "Content-Type": "application/json"}
            conn = httplib.HTTPSConnection('qa01.letzgo.com.cn', timeout=5)
            conn.request(method='POST', url='https://qa01.letzgo.com.cn/ding_service/api/ding/forward',
                         body=json_data, headers=notify_header)
            response = conn.getresponse()
            res = response.read()
            self.logger.info(res)
            return int(json.loads(res)["code"]) == 200
        except Exception, e:
            self.logger.exception(e)
            return False


class DateUtil(object):
    def __init__(self):
        pass

    @staticmethod
    def get_timestamp():
        return int(time.time() * 1000)

    @staticmethod
    def current_timestr():
        return time.strftime('%Y-%m-%d %H:%m:%S', time.localtime())


class ConfigUtil(object):
    __logger = Logger('ConfigUtil').logger

    def __init__(self):
        pass

    @staticmethod
    def get(section, key_name):
        try:
            conf = ConfigParser()
            conf.read('config.ini')
            return conf.get(section, key_name)
        except Exception, e:
            ConfigUtil.__logger.exception(e)
            return ''


class QianKa(object):
    def __init__(self):
        self.logger = Logger('QianKa').logger
        self.header = {"Host": "qianka.com", "Cookie": ConfigUtil.get('qianka', 'cookie'), "Connection": "keep-alive"}
        self.wechat = QiyeWechat()
        self.dingding = Dingding()

    def __get_task_list(self):
        """0正常返回，1异常返回，2有进行中任务，3访问频率过高"""
        try:
            conn = httplib.HTTPSConnection(host='qianka.com', timeout=30)
            url = 'https://qianka.com/s4/lite.subtask.list?t=%d' % DateUtil.get_timestamp()
            conn.request(method='GET', url=url, headers=self.header)
            response = conn.getresponse()
            resp_str = response.read()
            conn.close()
            json_str = json.loads(resp_str)
            err_code = json_str['err_code']
            err_msg = json_str['err_msg']
            if err_code != 0:
                return 1, err_msg
            if u'访问频率过高' in err_msg:
                return 3, err_msg
            payload = json_str['payload']
            tasks = payload['tasks']
            available_tasks = []
            for task in tasks:
                try:
                    task_id = int(task['id'])
                    status = int(task['status'])
                    reward = float(task['reward'])
                    zs_reward = float(task['zs_reward'])
                    quality = int(task['qty'])
                    appstore_cost = float(task['appstore_cost'])
                    icon = task['icon']
                    profit = reward - appstore_cost
                except Exception, e:
                    self.logger.exception(e)
                    continue
                if reward >= 5:
                    continue
                task = Task()
                task.id = task_id
                task.quality = quality
                task.reward = reward
                task.zs_reward = zs_reward
                task.profit = profit
                task.status = status
                task.icon = icon
                if status == 2:  # 进行中任务
                    return 2, task
                elif status == 1 and quality > 0:
                    available_tasks.append(task)
            task_list = []
            if len(available_tasks) > 0:
                task_list = sorted(available_tasks, key=lambda task: (task.profit, task.quality), reverse=True)
            return 0, task_list
        except Exception, e:
            self.logger.info(u'查询任务异常：')
            self.logger.exception(e)
            return 1, u'查询任务异常'

    def __get_task_detail(self, task=None):
        try:
            if task is None:
                self.logger.info(u'任务为空，任务详情查询失败')
                return None
            conn = httplib.HTTPSConnection(host='qianka.com', timeout=5)
            url = 'https://qianka.com/s4/lite.subtask.detail?t=%d&task_id=%d' % (DateUtil.get_timestamp(), task.id)
            conn.request(method='GET', url=url, headers=self.header)
            response = conn.getresponse()
            resp_str = response.read()
            json_str = json.loads(resp_str)
            err_code = json_str['err_code']
            if err_code != 0:
                self.logger.info(json_str['err_msg'])
                return None
            payload = json_str['payload']
            task_id = payload['task_id']
            app_name = payload['app_name']
            app_keyword = payload['app_keyword']
            scheme_url = payload['scheme_url']
            callback_url = payload['callback_url']
            expire_at = payload['expire_at']
            task_status = payload['task_status']
            tips = payload['tips']
            detail = TaskDetail()
            detail.task_id = task_id
            detail.app_name = app_name
            detail.app_keyword = app_keyword
            detail.scheme_url = scheme_url
            detail.callback_url = callback_url
            detail.expire_at = expire_at
            detail.task_status = task_status
            detail.tips = tips
            return detail
        except Exception, e:
            self.logger.exception(e)
            return None

    def __grab_task(self, task=None):
        try:
            if task is None:
                self.logger.info(u'任务为空，抢任务失败')
                return
            self.logger.info(u'开始抢task_id=%d的任务...' % task.id)
            conn = httplib.HTTPSConnection(host='qianka.com', timeout=30)
            url = 'https://qianka.com/s4/lite.subtask.start?t=%d&task_id=%d&quality=%d' % (
                DateUtil.get_timestamp(), task.id, task.quality)
            conn.request(method='GET', url=url, headers=self.header)
            response = conn.getresponse()
            resp_str = response.read()
            self.logger.info(resp_str)
            json_str = json.loads(resp_str)
            err_code = json_str['err_code']
            if err_code != 0:
                err_msg = json_str['err_msg']
                self.logger.info(u'抢task_id=%d的任务失败: %s' % (task.id, err_msg))
                if u'未安装证书' in err_msg:
                    return 'not_install_credentials'
                else:
                    return
            payload = json_str['payload']
            self.logger.info(u'抢task_id=%d的任务结果: %s' % (task.id, payload['message']))
        except Exception, e:
            self.logger.info(u'抢task_id=%d的任务出现异常: ' % task.id)
            self.logger.exception(e)

    def __is_shield_time(self):
        try:
            now = datetime.now()
            hour = now.hour
            minute = now.minute
            if minute < 10:
                minute_str = '0' + str(minute)
            else:
                minute_str = str(minute)
            now_time = int(str(hour) + minute_str)
            shield_time = ConfigUtil.get('qianka', 'shield.time')
            if shield_time is None:
                return False
            time_split = shield_time.split('-')
            start_time = int(time_split[0].replace(':', '').strip())
            end_time = int(time_split[1].replace(':', '').strip())
            if end_time > start_time:  # 同一天
                return start_time <= now_time <= end_time
            else:  # 跨天
                return now_time >= start_time or now_time <= end_time
        except Exception, e:
            self.logger.exception(e)
            return False

    def execute(self):
        rounds = 1
        rebind_notify = {}  # 重新绑定通知数据
        in_process_notify = {}  # 进行中任务通知数据
        credentials_notify = {}  # 重新安装证书通知数据
        while True:
            if self.__is_shield_time():
                time.sleep(60)
                continue
            self.logger.info(u'第%d次轮询开始...' % rounds)
            search_status, result = self.__get_task_list()
            if search_status == 3:  # 访问频率过高，暂停10秒
                self.logger.info(u'访问频率过高，暂停%d秒...' % 10)
                time.sleep(10)
                continue
            if search_status == 1:  # 出现错误
                self.logger.info(result)
                if u'绑定钥匙' in result:
                    # 只通知4次，依次间隔0,1,3,5分钟
                    if rebind_notify.get('notify_times'):  # 不是第一次发通知
                        current_millis = DateUtil.get_timestamp()
                        notify_times = rebind_notify.get('notify_times')
                        last_notify_time = rebind_notify.get('last_notify_time')
                        notify_duration = (notify_times * 2 - 1) * 60 * 1000
                        is_notify = notify_times <= 4 and current_millis - last_notify_time > notify_duration
                        if is_notify:
                            self.wechat.send_msg(result)
                            notify_times = notify_times + 1
                            rebind_notify['notify_times'] = notify_times
                            rebind_notify['last_notify_time'] = current_millis
                    else:  # 没有通知次数，则表明是第一次通知
                        self.wechat.send_msg(result)
                        rebind_notify['notify_times'] = 1
                        rebind_notify['last_notify_time'] = DateUtil.get_timestamp()
                self.logger.info(u'暂停%d秒...' % 5)
                time.sleep(5)
                continue
            rebind_notify.clear()
            if search_status == 2:  # 有进行中任务，暂停5分钟
                detail = self.__get_task_detail(result)
                if detail:
                    left_time = int((detail.expire_at * 1000 - DateUtil.get_timestamp()) / 1000 / 60)
                    title = u'任务【' + detail.app_name + u'】正在进行中，请速完成！'
                    description = u'奖励总计%g元，将于%d分钟后过期' % (result.profit, left_time)
                else:
                    title = u'您有进行中的任务，请速完成！'
                    description = u'奖励总计%g元' % result.profit
                self.logger.info(title + u'，' + description)
                if in_process_notify.get('task_id') == result.id:  # 该任务已经通知过了，则只暂停15秒
                    notify_times = in_process_notify.get('notify_times')
                    last_notify_time = in_process_notify.get('last_notify_time')
                    notify_duration = notify_times * 60 * 1000  # 通知间隔
                    current_millis = DateUtil.get_timestamp()
                    is_notify = notify_times <= 4 and current_millis - last_notify_time > notify_duration
                    if is_notify:
                        self.wechat.send_news(title=title, description=description, pic_url=result.icon)
                        notify_times = notify_times + 1
                        in_process_notify['notify_times'] = notify_times
                        in_process_notify['last_notify_time'] = current_millis
                    self.logger.info(u'您有进行中的任务，暂停%d秒...' % 15)
                    time.sleep(15)
                else:  # 第一次通知，第一次通知暂停5分钟
                    self.wechat.send_news(title=title, description=description, pic_url=result.icon)
                    self.logger.info(u'您有进行中的任务，暂停%d分钟...' % 4)
                    time.sleep(4 * 60)
                    in_process_notify['task_id'] = result.id
                    in_process_notify['notify_times'] = 1
                    in_process_notify['last_notify_time'] = DateUtil.get_timestamp()
                continue
            in_process_notify.clear()  # 没有进行中任务，清空进行中任务的通知字典
            for task in result:  # 有任务则抢
                if result.index(task) > 2:  # 只抢前三个，防止访问频率过高
                    break
                grab_res = self.__grab_task(task)
                if grab_res is not None and grab_res == 'not_install_credentials':
                    current_millis = DateUtil.get_timestamp()
                    if credentials_notify.get('notify_times'):
                        notify_times = credentials_notify.get('notify_times')
                        last_notify_time = credentials_notify.get('last_notify_time')
                        if notify_times < 3 and current_millis - last_notify_time > 3 * 60 * 1000:
                            self.wechat.send_msg(u'请重新安装证书')
                            credentials_notify['notify_times'] = notify_times + 1
                            credentials_notify['last_notify_time'] = current_millis
                    else:
                        self.wechat.send_msg(u'请重新安装证书')
                        credentials_notify['notify_times'] = 1
                        credentials_notify['last_notify_time'] = current_millis
                else:
                    credentials_notify.clear()
                time.sleep(1)
            self.logger.info(u'第%d次轮询结束' % rounds)
            minute = datetime.now().minute
            if (28 <= minute <= 33) or (0 <= minute <= 3) or (58 <= minute <= 59):  # 整点附近加快刷新频率
                randint = random.randint(3, 4)
            else:
                randint = random.randint(3, 5)
            self.logger.info(u'暂停%d秒...' % randint)
            time.sleep(randint)
            rounds = rounds + 1


if __name__ == '__main__':
    QianKa().execute()
