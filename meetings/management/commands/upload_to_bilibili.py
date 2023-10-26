import datetime
import logging
import os
import sys
from django.conf import settings
from django.core.management import BaseCommand
from obs import ObsClient
from meetings.models import Record
from meetings.utils.bili_apis import upload_video

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
        objs = []
        mark = None
        while True:
            obs_objs = obs_client.listObjects(bucketName, marker=mark, max_keys=1000)
            if obs_objs.status < 300:
                index = 1
                for content in obs_objs.body.contents:
                    objs.append(content)
                    index += 1
                if obs_objs.body.is_truncated:
                    mark = obs_objs.body.next_marker
                else:
                    break
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
                # 下载视频
                res1 = obs_client.downloadFile(bucketName, object_key, videoFile, partSize, taskNum, enableCheckpoint)
                if res1.status > 300:
                    logger.error('Fail to download target video: {}'.format(object_key))
                    logger.error('errorCode', res1.errorCode)
                    logger.error('errorMessage', res1.errorMessage)
                    continue
                # 下载封面
                img_object_key = object_key.replace('.mp4', '.png')
                res2 = obs_client.downloadFile(bucketName, img_object_key, imageFile, partSize, taskNum,
                                               enableCheckpoint)
                if res2.status > 300:
                    logger.error('Fail to download target thumbnail: {}'.format(img_object_key))
                    logger.error('errorCode', res2.errorCode)
                    logger.error('errorMessage', res2.errorMessage)
                    continue
                # 上传视频至B站
                topic = metadata_dict.get('meeting_topic')
                mid = metadata_dict.get('meeting_id')
                community = metadata_dict.get('community')
                record_start = metadata_dict.get('record_start')
                sig = metadata_dict.get('sig')
                date = (datetime.datetime.strptime(record_start.replace('T', ' ').replace('Z', ''), "%Y-%m-%d %H:%M:%S")
                        + datetime.timedelta(hours=8)).strftime('%Y-%m-%d')
                meeting_info = {
                    'desc': 'community meeting recording for {}'.format(sig),
                    'tag': '{}, community, recordings, 会议录像'.format(community),
                    'title': topic + ' (' + date + ')'
                }
                res = upload_video(meeting_info, videoFile, imageFile)
                if isinstance(res, dict) and 'bvid' in res.keys():
                    bvid = res['bvid']
                    logger.info('meeting {}: 视频提交成功！生成的bvid为{}'.format(mid, bvid))
                    if not Record.objects.filter(mid=mid, platform='bilibili'):
                        Record.objects.create(mid=mid, platform='bilibili')
                    # 修改metadata
                    agenda = metadata_dict.get('agenda')
                    record_end = metadata_dict.get('record_end')
                    download_url = metadata_dict.get('download_url')
                    total_size = metadata_dict.get('total_size')
                    attenders = metadata_dict.get('attenders')
                    metadata = {
                        'meeting_id': mid,
                        'meeting_topic': topic,
                        'community': community,
                        'sig': sig,
                        'agenda': agenda,
                        'record_start': record_start,
                        'record_end': record_end,
                        'download_url': download_url,
                        'total_size': total_size,
                        'attenders': attenders,
                        'bvid': bvid
                    }
                    resp3 = obs_client.setObjectMetadata(bucketName, object_key, metadata)
                    if resp3.status < 300:
                        logger.info('{}: metadata修改成功'.format(object_key))
                    else:
                        logger.error('Fail to update metadata of {}'.format(object_key))
                        logger.error('errorCode', resp3.errorCode)
                        logger.error('errorMessage', resp3.errorMessage)
