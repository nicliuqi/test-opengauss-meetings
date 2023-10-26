import datetime
import logging
import os
import sys
import time
import traceback
from bilibili_api import video, Verify
from django.conf import settings
from django.core.management import BaseCommand
from obs import ObsClient
from meetings.models import Record

logger = logging.getLogger('log')


class Command(BaseCommand):
    def handle(self, *args, **options):
        # 从OBS查询对象
        access_key_id = settings.ACCESS_KEY_ID
        secret_access_key = settings.SECRET_ACCESS_KEY
        endpoint = settings.OBS_ENDPOINT
        bucketName = settings.OBS_BUCKETNAME
        if not access_key_id or not secret_access_key or not endpoint or not bucketName:
            logger.error('losing required arguments for ObsClient')
            sys.exit(1)
        obs_client = ObsClient(access_key_id=access_key_id,
                               secret_access_key=secret_access_key,
                               server='https://%s' % endpoint)
        objs = obs_client.listObjects(bucketName=bucketName)['body']['contents']
        # 遍历
        if len(objs) == 0:
            logger.info('OBS中无对象')
            return
        for obj in objs:
            # 获取对象的地址
            object_key = obj['key']
            if not object_key.endswith('.mp4'):
                continue
            # 获取对象的metadata
            metadata = obs_client.getObjectMetadata(bucketName, object_key)
            metadata_dict = {x: y for x, y in metadata['header']}
            # 如果bvid不在metadata_dict中，则下载视频并上传视频至B站
            if 'bvid' in metadata_dict:
                logger.info('{}已在B站上传，跳过'.format(object_key))
            else:
                logger.info('{}尚未上传至B站，开始下载'.format(object_key))
                # 从OBS下载视频到本地临时目录
                videoFile = os.path.join('/tmp', os.path.basename(object_key))
                imageFile = videoFile.replace('.mp4', '.png')
                if os.path.exists(videoFile):
                    os.remove(videoFile)
                if os.path.exists(imageFile):
                    os.remove(imageFile)
                taskNum = 5
                partSize = 10 * 1024 * 1024
                enableCheckpoint = True
                try:
                    # 下载视频
                    resp = obs_client.downloadFile(bucketName, object_key, videoFile, partSize, taskNum,
                                                   enableCheckpoint)
                    if resp.status < 300:
                        try:
                            # 下载封面
                            img_object_key = object_key.replace('.mp4', '.png')
                            try:
                                resp2 = obs_client.downloadFile(bucketName, img_object_key, imageFile, partSize, taskNum,
                                                                enableCheckpoint)
                                if resp2.status < 300:
                                    # 将下载的视频上传至B站
                                    topic = metadata_dict['meeting_topic']
                                    mid = metadata_dict['meeting_id']
                                    community = metadata_dict['community']
                                    record_start = metadata_dict['record_start']
                                    sig = metadata_dict['sig']
                                    date = (datetime.datetime.strptime(record_start.replace('T', ' ').replace('Z', ''),
                                                                       "%Y-%m-%d %H:%M:%S") + datetime.timedelta(
                                        hours=8)).strftime('%Y-%m-%d')
                                    res = upload(topic, date, videoFile, imageFile, mid, sig, community)
                                    try:
                                        if not Record.objects.filter(mid=mid, platform='bilibili'):
                                            Record.objects.create(mid=mid, platform='bilibili')
                                    except Exception as e:
                                        logger.error(e)
                                    # 修改metadata
                                    bvid = res['bvid']
                                    agenda = metadata_dict['agenda'] if 'agenda' in metadata_dict else ''
                                    record_end = metadata_dict['record_end']
                                    download_url = metadata_dict['download_url']
                                    total_size = metadata_dict['total_size']
                                    attenders = metadata_dict['attenders']
                                    metadata = {
                                        "meeting_id": mid,
                                        "meeting_topic": topic,
                                        "community": community,
                                        "sig": sig,
                                        "agenda": agenda,
                                        "record_start": record_start,
                                        "record_end": record_end,
                                        "download_url": download_url,
                                        "total_size": total_size,
                                        "attenders": attenders,
                                        "bvid": bvid
                                    }
                                    try:
                                        resp3 = obs_client.setObjectMetadata(bucketName, object_key, metadata)
                                        if resp3.status < 300:
                                            logger.info('{}: metadata修改成功'.format(object_key))
                                        else:
                                            logger.error('errorCode', resp3.errorCode)
                                            logger.error('errorMessage', resp3.errorMessage)
                                    except:
                                        logger.error(traceback.format_exc())
                                    # 休眠30s避免上传间隔过短
                                    time.sleep(30)
                                else:
                                    logger.error('errorCode', resp2.errorCode)
                                    logger.error('errorMessage', resp2.errorMessage)
                            except Exception as e2:
                                logger.error(e2)
                        except:
                            logger.error(traceback.format_exc())
                    else:
                        logger.error('errorCode', resp.errorCode)
                        logger.error('errorMessage', resp.errorMessage)
                except:
                    logger.error(traceback.format_exc())


def upload(topic, date, videoFile, imageFile, mid, sig, community):
    """上传视频到b站"""
    sessdata = settings.SESSDATA
    bili_jct = settings.BILI_JCT
    if not sessdata or not bili_jct:
        logger.error('both sessdata and bili_jct required, please check!')
        sys.exit(1)
    verify = Verify(sessdata, bili_jct)
    # 上传视频
    filename = video.video_upload(videoFile, verify=verify)
    logger.info('meeting {}: B站上传视频'.format(mid))
    # 上传封面
    cover_url = video.video_cover_upload(imageFile, verify=verify)
    logger.info('meeting {}: B站上传封面'.format(mid))
    # 提交投稿
    data = {
        "copyright": 1,
        "cover": cover_url,
        "desc": "openGauss meeting record for {}".format(sig),
        "desc_format_id": 0,
        "dynamic": "",
        "interactive": 0,
        "no_reprint": 1,
        "subtitles": {
            "lan": "",
            "open": 0
        },
        "tag": "{}, community, recordings, 会议录像".format(community),
        "tid": 124,
        "title": topic + " (" + date + ")",
        "videos": [
            {
                "desc": "recordings download from OBS",
                "filename": os.path.basename(filename),
                "title": "P1"
            }
        ]
    }
    result = video.video_submit(data, verify=verify)
    logger.info('meeting {}: B站提交视频'.format(mid))
    # 返回bv号和av号
    logger.info('meeting {}: 视频提交成功！生成的bvid为{}'.format(mid, result['bvid']))
    return result

