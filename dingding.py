# -*-coding:utf-8-*-
import httplib
import json

from logger import Logger

logger = Logger('dingding').logger


def notify(msg=''):
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
        logger.exception(e)
        return False
