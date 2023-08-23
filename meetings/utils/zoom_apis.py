import datetime
import logging
import json
import random
import requests
from django.conf import settings

logger = logging.getLogger('log')


def createMeeting(date, start, end, topic, host, record):
    start_time = (datetime.datetime.strptime(date + start, '%Y-%m-%d%H:%M') - datetime.timedelta(hours=8)).strftime(
        '%Y-%m-%dT%H:%M:%SZ')
    end_time = (datetime.datetime.strptime(date + end, '%Y-%m-%d%H:%M') - datetime.timedelta(hours=8)).strftime(
        '%Y-%m-%dT%H:%M:%SZ')
    duration = int((datetime.datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%SZ') -
                    datetime.datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%SZ')).seconds / 60)
    password = str(random.randint(100000, 999999))
    headers = {
        "content-type": "application/json",
        "authorization": "Bearer {}".format(settings.ZOOM_TOKEN)
    }
    payload = {
        'start_time': start_time,
        'duration': duration,
        'topic': topic,
        'password': password,
        'settings': {
            'waiting_room': False,
            'auto_recording': record,
            'join_before_host': True,
            'jbh_time': 5
        }
    }
    url = "https://api.zoom.us/v2/users/{}/meetings".format(host)
    response = requests.post(url, data=json.dumps(payload), headers=headers)
    resp_dict = {}
    if response.status_code != 201:
        return response.status_code, resp_dict
    resp_dict['mid'] = response.json()['id']
    resp_dict['start_url'] = response.json()['start_url']
    resp_dict['join_url'] = response.json()['join_url']
    resp_dict['host_id'] = response.json()['host_id']
    return response.status_code, resp_dict


def updateMeeting(mid, date, start, end, topic, record):
    # start_time拼接
    if int(start.split(':')[0]) >= 8:
        start_time = date + 'T' + ':'.join([str(int(start.split(':')[0]) - 8), start.split(':')[1], '00Z'])
    else:
        d = datetime.datetime.strptime(date, '%Y-%m-%d') - datetime.timedelta(days=1)
        d2 = datetime.datetime.strftime(d, '%Y-%m-%d %H%M%S')[:10]
        start_time = d2 + 'T' + ':'.join([str(int(start.split(':')[0]) + 16), start.split(':')[1], '00Z'])
    # 计算duration
    duration = (int(end.split(':')[0]) - int(start.split(':')[0])) * 60 + (
            int(end.split(':')[1]) - int(start.split(':')[1]))

    # 准备好调用zoom api的data
    new_data = {'settings': {}, 'start_time': start_time, 'duration': duration, 'topic': topic}
    new_data['settings']['waiting_room'] = False
    new_data['settings']['auto_recording'] = record
    headers = {
        "content-type": "application/json",
        "authorization": "Bearer {}".format(settings.ZOOM_TOKEN)
    }
    url = "https://api.zoom.us/v2/meetings/{}".format(mid)
    # 发送patch请求，修改会议
    response = requests.patch(url, data=json.dumps(new_data), headers=headers)
    return response.status_code


def cancelMeeting(mid):
    url = "https://api.zoom.us/v2/meetings/{}".format(mid)
    headers = {
        "authorization": "Bearer {}".format(settings.ZOOM_TOKEN)
    }
    response = requests.request("DELETE", url, headers=headers)
    return response.status_code


def getParticipants(mid):
    url = "https://api.zoom.us/v2/past_meetings/{}/participants?page_size=300".format(mid)
    headers = {
        "authorization": "Bearer {}".format(settings.ZOOM_TOKEN)}
    logger.info(url)
    logger.info(headers)
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        total_records = r.json()['total_records']
        participants = r.json()['participants']
        resp = {'total_records': total_records, 'participants': participants}
        return r.status_code, resp
    else:
        return r.status_code, r.json()
