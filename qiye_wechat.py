# -*-coding=utf-8-*-

import httplib
import json
import sqlite3
import time

from logger import Logger

logger = Logger('qiye_wechat').logger

corp_id = ''
agent_id = ''
secret = ''
header = {"Host": "qyapi.weixin.qq.com",
          "Connection": "keep-alive",
          "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"}


def get_access_token():
    conn = sqlite3.connect('master.db')
    cursor = conn.cursor()
    sql = "SELECT * FROM t_access_token WHERE STATUS=1 ORDER BY ID DESC;"
    row = cursor.execute(sql).fetchone()
    cursor.close()
    conn.close()
    if valid_token(row):
        return row[1]
    else:
        access_token, expire_in = get_access_token_from_wechat()
        if access_token is None:
            raise Exception('get access token from wechat failure')
        save_access_token(access_token, expire_in)
        return access_token


def valid_token(row):
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


def get_access_token_from_wechat():
    try:
        url = 'https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=%s&corpsecret=%s' % (corp_id, secret)
        conn = httplib.HTTPSConnection("qyapi.weixin.qq.com")
        conn.request(method='GET', url=url, headers=header)
        response = conn.getresponse()
        resp_str = response.read()
        json_str = json.loads(resp_str)
        return json_str['access_token'], json_str['expires_in']
    except Exception, e:
        print 'error occurred: ' + unicode(repr(e))
        return None, None


def save_access_token(token='', expire_in=7200, status=1):
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

def send(msg=''):
    access_token = get_access_token()
    body = {
        "touser": "@all",
        "toparty": "",
        "totag": "",
        "msgtype": "text",
        "agentid": agent_id,
        "text": {
            "content": msg
        },
        "safe": 0
    }
    json_body = json.dumps(body).encode('utf-8')
    url = 'https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=%s' % access_token
    conn = httplib.HTTPSConnection("qyapi.weixin.qq.com")
    conn.request(method='POST', url=url, body=json_body, headers=header)
    response = conn.getresponse()
    resp_str = response.read()
    json_str = json.loads(resp_str)
    logger.info(u'企业微信发通知结果：%s' % json_str['errmsg'])
