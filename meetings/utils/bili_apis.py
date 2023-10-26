from bilibili_api import Credential, sync, video_uploader
from bilibili_api.user import User
from django.conf import settings


def get_credential():
    return Credential(settings.SESSDATA, settings.BILI_JCT)


def get_user(uid, credential):
    return User(uid, credential)


def get_all_bvids(user):
    bvids = []
    pn = 1
    while True:
        res = sync(user.get_videos(pn=pn))
        if len(res.get('list').get('vlist')) == 0:
            break
        for video in res['list']['vlist']:
            bvid = video.get('bvid')
            if bvid not in bvids:
                bvids.append(bvid)
        pn += 1
    return bvids


def upload_video(meeting_info, video_path, thumbnail_path):
    tag = meeting_info.get('tag')
    title = meeting_info.get('title')
    desc = meeting_info.get('desc')
    credential = Credential(sessdata=settings.SESSDATA, bili_jct=settings.BILI_JCT)
    page = video_uploader.VideoUploadPage(path=video_path, title=title, description=desc)
    meta = {
        'copyright': 1,
        'desc': desc,
        'desc_format_id': 0,
        'dynamic': '',
        'interactive': 0,
        'no_reprint': 1,
        'subtitles': {
            'lan': '',
            'open': 0
        },
        'tag': tag,
        'tid': 124,
        'title': title
    }
    uploader = video_uploader.VideoUploader([page], meta, credential, cover=thumbnail_path)
    res = sync(uploader.start())
    return res