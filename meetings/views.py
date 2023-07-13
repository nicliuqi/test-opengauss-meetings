import datetime
import json
import logging
import math
import requests
import secrets
import yaml
from django.conf import settings
from django.middleware.csrf import get_token
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.filters import SearchFilter
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, CreateModelMixin, UpdateModelMixin, RetrieveModelMixin, \
    DestroyModelMixin
from multiprocessing import Process
from rest_framework.response import Response
from meetings.send_email import sendmail
from meetings.models import Meeting, Video, User, Group, Record
from meetings.serializers import MeetingsSerializer, MeetingUpdateSerializer, MeetingDeleteSerializer, \
    MeetingDetailSerializer, GroupsSerializer, AllMeetingsSerializer
from meetings.utils import cryptos
from meetings.permissions import QueryPermission
from meetings.utils import drivers

logger = logging.getLogger('log')


def IdentifyUser(request):
    """
    Identify user by decrypting AES encoding
    :param request: request object
    :return: user_id
    """
    access_token = request.COOKIES.get('access_token')
    if not access_token:
        return JsonResponse({'code': 400, 'msg': '请求头中缺少认证信息'})
    if not isinstance(access_token, str):
        return JsonResponse({'code': 400, 'msg': 'Bad Request'})
    if len(access_token) != 48:
        return JsonResponse({'code': 400, 'msg': 'Bad Request'})
    text, iv = access_token[:32], access_token[32:]
    user_id = int(cryptos.decrypt(text, iv.encode('utf-8')))
    return user_id


def refresh_token(user_id):
    iv = secrets.token_hex(8)
    text = cryptos.encrypt(str(user_id), iv.encode('utf-8'))
    access_token = text + iv
    return access_token


def refresh_cookie(response, access_token):
    response.delete_cookie('access_token')
    now_time = datetime.datetime.now()
    expire = now_time + settings.COOKIE_EXPIRE
    response.set_cookie('access_token', access_token, expires=expire, secure=True, httponly=True, samesite='strict')
    return response


class GiteeAuthView(GenericAPIView, ListModelMixin):
    """
    Gitee Auth
    """

    def get(self, request):
        client_id = settings.GITEE_OAUTH_CLIENT_ID
        redirect_url = settings.GITEE_OAUTH_REDIRECT
        response = {
            "client_id": client_id,
            "redirect_url": redirect_url
        }
        return JsonResponse(response)


class GiteeBackView(GenericAPIView, ListModelMixin):
    """
    Request user info through auth code and save info
    """

    def get(self, request):
        code = request.GET.get('code', None)
        client_id = settings.GITEE_OAUTH_CLIENT_ID
        client_secret = settings.GITEE_OAUTH_CLIENT_SECRET
        redirect_uri = settings.GITEE_OAUTH_REDIRECT
        r = requests.post(
            'https://gitee.com/oauth/token?grant_type=authorization_code&code={}&client_id={}&redirect_uri={}&client_secret={}'.format(
                code, client_id, redirect_uri, client_secret))
        if r.status_code == 200:
            access_token = r.json()['access_token']
            r = requests.get('https://gitee.com/api/v5/user?access_token={}'.format(access_token))
            if r.status_code == 200:
                gid = r.json()['id']
                gitee_id = r.json()['login']
                name = r.json()['name']
                avatar = r.json()['avatar_url']
                if not User.objects.filter(gid=gid):
                    User.objects.create(gid=gid, gitee_id=gitee_id, name=name, avatar=avatar)
                else:
                    User.objects.filter(gid=gid).update(gitee_id=gitee_id, name=name, avatar=avatar)
                response = redirect(settings.REDIRECT_HOME_PAGE)
                user_id = User.objects.get(gid=gid).id
                iv = secrets.token_hex(8)
                access_token = cryptos.encrypt(str(user_id), iv.encode('utf-8'))
                now_time = datetime.datetime.now()
                expire = now_time + settings.COOKIE_EXPIRE
                response.set_cookie('access_token', access_token + iv, expires=expire, secure=True, httponly=True, samesite='strict')
                request.META['CSRF_COOKIE'] = get_token(self.request)
                return response
        else:
            return JsonResponse(r.json())


class LogoutView(GenericAPIView):
    """
    Log out
    """
    def get(self, request):
        response = JsonResponse({'code': 200, 'msg': 'OK'})
        response.delete_cookie('access_token')
        response.delete_cookie(settings.CSRF_COOKIE_NAME)
        return response


class UserInfoView(GenericAPIView):
    """
    Get login user info
    """

    def get(self, request, *args, **kwargs):
        try:
            user_id = IdentifyUser(request)
            if not User.objects.filter(id=user_id):
                return JsonResponse({'code': 400, 'msg': 'The user does not exist'})
            user = User.objects.get(id=user_id)
            gitee_id = user.gitee_id
            with open('share/openGauss_sigs.yaml', 'r') as f:
                sigs = yaml.safe_load(f)
            self_sigs = []
            for sig in sigs:
                if gitee_id in sig['sponsors']:
                    self_sigs.append(sig['name'])
            data = {
                'user': {
                    'id': user.id,
                    'gitee_id': gitee_id
                },
                'sigs': self_sigs
            }
            return JsonResponse({'code': 200, 'msg': 'userinfo', 'data': data})
        except Exception as e:
            logger.error(e)
            return JsonResponse({'code': 400, 'msg': 'access_token错误', 'en_msg': 'Invalid access_token'})


class CreateMeetingView(GenericAPIView, CreateModelMixin):
    """
    Create a meeting
    """
    serializer_class = MeetingsSerializer
    queryset = Meeting.objects.all()

    def post(self, request, *args, **kwargs):
        try:
            user_id = IdentifyUser(request)
        except:
            return JsonResponse({'code': 401, 'msg': '用户未认证', 'en_msg': 'Unauthorised'})
        data = self.request.data
        platform = data['platform'] if 'platform' in data else 'zoom'
        platform = platform.lower()
        host_dict = settings.OPENGAUSS_MEETING_HOSTS[platform]
        date = data['date']
        start = data['start']
        end = data['end']
        topic = data['topic']
        sponsor = data['sponsor']
        group_name = data['group_name']
        etherpad = data['etherpad'] if 'etherpad' in data else None
        if not etherpad:
            etherpad = 'https://etherpad.opengauss.org/p/{}-meetings'.format(group_name)
        community = data['community'] if 'community' in data else 'opengauss'
        emaillist = data['emaillist'] if 'emaillist' in data else None
        summary = data['agenda'] if 'agenda' in data else None
        record = data['record'] if 'record' in data else None
        try:
            group_id = Group.objects.get(name=group_name).id
        except Exception:
            logger.error('Invalid group_name')
            return JsonResponse({'code': 400, 'msg': '错误的SIG组名', 'en_msg': 'Invalid SIG name'})
        if User.objects.get(id=user_id).gitee_id not in Group.objects.get(name=group_name).members:
            logger.error('user is not member of {}'.format(group_name))
            return JsonResponse(
                {'code': 400, 'msg': '用户未在该组', 'en_msg': 'The user is not member of {}'.format(group_name)})
        start_time = ' '.join([date, start])
        if start_time < datetime.datetime.now().strftime('%Y-%m-%d %H:%M'):
            logger.warning('The start time should not be earlier than the current time.')
            return JsonResponse({'code': 1005, 'msg': '请输入正确的开始时间',
                                 'en_msg': 'The start time should not be earlier than the current time'})
        if start >= end:
            logger.warning('The end time must be greater than the start time.')
            return JsonResponse(
                {'code': 1001, 'msg': '请输入正确的结束时间', 'en_msg': 'The end time must be greater than the start time'})
        if date > (datetime.datetime.today() + datetime.timedelta(days=14)).strftime('%Y-%m-%d'):
            logger.warning('The date is more than 14.')
            return JsonResponse({'code': 1002, 'msg': '预定时间不能超过当前14天', 'en_msg': 'The scheduled time cannot exceed 14'})
        start_search = datetime.datetime.strftime(
            (datetime.datetime.strptime(start, '%H:%M') - datetime.timedelta(minutes=30)),
            '%H:%M')
        end_search = datetime.datetime.strftime(
            (datetime.datetime.strptime(end, '%H:%M') + datetime.timedelta(minutes=30)),
            '%H:%M')
        # 查询待创建的会议与现有的预定会议是否冲突
        unavailable_host_id = []
        available_host_id = []
        meetings = Meeting.objects.filter(is_delete=0, date=date, end__gt=start_search, start__lt=end_search).values()
        try:
            for meeting in meetings:
                host_id = meeting['host_id']
                unavailable_host_id.append(host_id)
            logger.info('unavilable_host_id:{}'.format(unavailable_host_id))
        except KeyError:
            pass
        host_list = list(host_dict.keys())
        logger.info('host_list:{}'.format(host_list))
        for host_id in host_list:
            if host_id not in unavailable_host_id:
                available_host_id.append(host_id)
        logger.info('avilable_host_id:{}'.format(available_host_id))
        if len(available_host_id) == 0:
            logger.warning('暂无可用host')
            return JsonResponse({'code': 1000, 'msg': '时间冲突，请调整时间预定会议', 'en_msg': 'Schedule time conflict'})
        # 从available_host_id中随机生成一个host_id,并在host_dict中取出
        host_id = secrets.choice(available_host_id)
        host = host_dict[host_id]
        logger.info('host_id:{}'.format(host_id))
        logger.info('host:{}'.format(host))

        status, content = drivers.createMeeting(platform, date, start, end, topic, host, record)
        if status not in [200, 201]:
            return JsonResponse({'code': 400, 'msg': 'Bad Request'})
        mid = content['mid']
        start_url = content['start_url']
        join_url = content['join_url']
        host_id = content['host_id']
        timezone = content['timezone'] if 'timezone' in content else 'Asia/Shanghai'

        # 数据库生成数据
        Meeting.objects.create(
            mid=mid,
            topic=topic,
            community=community,
            sponsor=sponsor,
            group_name=group_name,
            date=date,
            start=start,
            end=end,
            etherpad=etherpad,
            emaillist=emaillist,
            timezone=timezone,
            agenda=summary,
            host_id=host_id,
            join_url=join_url,
            start_url=start_url,
            user_id=user_id,
            group_id=group_id,
            mplatform=platform
        )
        logger.info('{} has created a meeting which mid is {}.'.format(data['sponsor'], mid))
        logger.info('meeting info: {},{}-{},{}'.format(date, start, end, topic))
        # 如果开启录制功能，则在Video表中创建一条数据
        if record == 'cloud':
            Video.objects.create(
                mid=mid,
                topic=topic,
                community=community,
                group_name=group_name,
                agenda=summary
            )
            logger.info('meeting {} was created with auto recording.'.format(mid))
        # 发送email
        sequence = Meeting.objects.get(mid=mid).sequence
        m = {
            'mid': mid,
            'topic': topic,
            'date': date,
            'start': start,
            'end': end,
            'join_url': join_url,
            'sig_name': group_name,
            'toaddrs': emaillist,
            'platform': platform,
            'etherpad': etherpad,
            'summary': summary,
            'sequence': sequence
        }
        p1 = Process(target=sendmail, args=(m, record))
        p1.start()
        Meeting.objects.filter(mid=mid).update(sequence=sequence + 1)

        # 返回请求数据
        access_token = refresh_token(user_id)
        resp = {'code': 201, 'msg': '创建成功', 'en_msg': 'Schedule meeting successfully'}
        meeting_id = Meeting.objects.get(mid=mid).id
        resp['id'] = meeting_id
        resp['access_token'] = access_token
        response = JsonResponse(resp)
        refresh_cookie(response, access_token)
        request.META['CSRF_COOKIE'] = get_token(request)
        return response


class UpdateMeetingView(GenericAPIView, UpdateModelMixin, DestroyModelMixin, RetrieveModelMixin):
    """
    Update a meeting
    """
    serializer_class = MeetingUpdateSerializer
    queryset = Meeting.objects.filter(is_delete=0)

    def put(self, request, *args, **kwargs):
        if request.COOKIES.get('csrftoken') != request.headers.get('X-Csrftoken'):
            return HttpResponse('403 Forbidden')
        # 鉴权
        try:
            user_id = IdentifyUser(request)
        except:
            return JsonResponse({'code': 401, 'msg': '用户未认证', 'en_msg': 'Unauthorised'})
        mid = self.kwargs.get('mid')
        if not Meeting.objects.filter(user_id=user_id, mid=mid, is_delete=0):
            return JsonResponse({'code': 404, 'msg': '会议不存在', 'en_msg': 'The meeting does not exist'})

        # 获取data
        data = self.request.data
        topic = data['topic']
        sponsor = data['sponsor']
        date = data['date']
        start = data['start']
        end = data['end']
        group_name = data['group_name']
        community = 'opengauss'
        summary = data['agenda'] if 'agenda' in data else None
        emaillist = data['emaillist'] if 'emaillist' in data else None
        record = data['record'] if 'record' in data else None
        etherpad = data['etherpad'] if 'etherpad' in data else 'https://etherpad.opengauss.org/p/{}-meetings'.format(
            group_name)
        group_id = Group.objects.get(name=group_name).id

        # 根据时间判断冲突
        start_time = ' '.join([date, start])
        if start_time < datetime.datetime.now().strftime('%Y-%m-%d %H:%M'):
            logger.warning('The start time should not be earlier than the current time.')
            return JsonResponse({'code': 1005, 'msg': '请输入正确的开始时间',
                                 'en_msg': 'The start time should not be earlier than the current time'})
        if start >= end:
            logger.warning('The end time must be greater than the start time.')
            return JsonResponse(
                {'code': 1001, 'msg': '请输入正确的结束时间', 'en_msg': 'The end time must be greater than the start time'})
        start_search = datetime.datetime.strftime(
            (datetime.datetime.strptime(start, '%H:%M') - datetime.timedelta(minutes=30)),
            '%H:%M')
        end_search = datetime.datetime.strftime(
            (datetime.datetime.strptime(end, '%H:%M') + datetime.timedelta(minutes=30)),
            '%H:%M')
        # 查询待创建的会议与现有的预定会议是否冲突
        meeting = Meeting.objects.get(mid=mid)
        host_id = meeting.host_id
        if Meeting.objects.filter(date=date, is_delete=0, host_id=host_id, end__gt=start_search, start__lt=end_search).exclude(mid=mid):
            logger.info('会议冲突！主持人在{}-{}已经创建了会议'.format(start_search, end_search))
            return JsonResponse({'code': 400, 'msg': '会议冲突！主持人在{}-{}已经创建了会议'.format(start_search, end_search),
                                 'en_msg': 'Schedule time conflict'})
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

        update_topic = '[Update] ' + topic
        status = drivers.updateMeeting(mid, date, start, end, update_topic, record)
        if status not in [200, 204]:
            return JsonResponse({'code': 400, 'msg': '修改会议失败', 'en_msg': 'Fail to update.'})

        # 数据库更新数据
        Meeting.objects.filter(mid=mid).update(
            topic=topic,
            sponsor=sponsor,
            group_name=group_name,
            date=date,
            start=start,
            end=end,
            etherpad=etherpad,
            emaillist=emaillist,
            agenda=summary,
            user_id=user_id,
            group_id=group_id
        )
        logger.info('{} has updated a meeting which mid is {}.'.format(sponsor, mid))
        logger.info('meeting info: {},{}-{},{}'.format(date, start, end, topic))
        # 如果开启录制功能，则在Video表中创建一条数据
        if not Video.objects.filter(mid=mid) and record == 'cloud':
            Video.objects.create(
                mid=mid,
                topic=topic,
                community=community,
                group_name=group_name,
                agenda=summary
            )
            logger.info('meeting {} was created with auto recording.'.format(mid))
        if Video.objects.filter(mid=mid) and record != 'cloud':
            Video.objects.filter(mid=mid).delete()
            logger.info('remove video obj of meeting {}'.format(mid))
        join_url = Meeting.objects.get(mid=mid).join_url
        platform = Meeting.objects.get(mid=mid).mplatform
        sequence = Meeting.objects.get(mid=mid).sequence
        m = {
            'mid': mid,
            'topic': update_topic,
            'date': date,
            'start': start,
            'end': end,
            'join_url': join_url,
            'sig_name': group_name,
            'toaddrs': emaillist,
            'platform': platform,
            'etherpad': etherpad,
            'summary': summary,
            'sequence': sequence
        }
        p1 = Process(target=sendmail, args=(m, record))
        p1.start()
        Meeting.objects.filter(mid=mid).update(sequence=sequence + 1)
        # 返回请求数据
        access_token = refresh_token(user_id)
        resp = {'code': 204, 'msg': '修改成功', 'en_msg': 'Update successfully', 'id': mid, 'access_token': access_token}
        response = JsonResponse(resp)
        refresh_cookie(response, access_token)
        request.META['CSRF_COOKIE'] = get_token(request)
        return response


class DeleteMeetingView(GenericAPIView, UpdateModelMixin):
    """
    Cancel a meeting
    """
    serializer_class = MeetingDeleteSerializer
    queryset = Meeting.objects.filter(is_delete=0)

    def delete(self, request, *args, **kwargs):
        # 鉴权
        try:
            user_id = IdentifyUser(request)
        except:
            return JsonResponse({'code': 401, 'msg': '用户未认证', 'en_msg': 'Unauthorised'})
        mid = self.kwargs.get('mid')
        if not Meeting.objects.filter(user_id=user_id, mid=mid, is_delete=0):
            return JsonResponse({'code': 404, 'msg': '会议不存在', 'en_msg': 'The meeting does not exist'})
        drivers.cancelMeeting(mid)
        # 数据库软删除数据
        Meeting.objects.filter(mid=mid).update(is_delete=1)
        user = User.objects.get(id=user_id)
        logger.info('{} has canceled meeting {}'.format(user.gitee_id, mid))
        from meetings.utils.send_cancel_email import sendmail
        meeting = Meeting.objects.get(mid=mid)
        date = meeting.date
        start = meeting.start
        end = meeting.end
        toaddrs = meeting.emaillist
        topic = '[Cancel] ' + meeting.topic
        sig_name = meeting.group_name
        platform = meeting.mplatform
        platform = platform.replace('zoom', 'Zoom').replace('welink', 'WeLink')
        sequence = meeting.sequence
        m = {
            'mid': mid,
            'date': date,
            'start': start,
            'end': end,
            'toaddrs': toaddrs,
            'topic': topic,
            'sig_name': sig_name,
            'platform': platform,
            'sequence': sequence
        }
        sendmail(m)
        Meeting.objects.filter(mid=mid).update(sequence=sequence + 1)
        access_token = refresh_token(user_id)
        response = JsonResponse({'code': 204, 'msg': '已删除会议{}'.format(mid), 'en_msg': 'Delete successfully',
                                 'access_token': access_token})
        refresh_cookie(response, access_token)
        request.META['CSRF_COOKIE'] = get_token(request)
        return response


class MeetingDetailView(GenericAPIView, RetrieveModelMixin):
    """
    Meeting detail
    """
    serializer_class = MeetingDetailSerializer
    queryset = Meeting.objects.filter(is_delete=0)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class GroupsView(GenericAPIView, ListModelMixin):
    """
    Groups info
    """
    serializer_class = GroupsSerializer
    queryset = Group.objects.all()

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class MeetingsDataView(GenericAPIView, ListModelMixin):
    """
    Calendar data
    """
    queryset = Meeting.objects.filter(is_delete=0).order_by('start')
    filter_backends = [SearchFilter]
    search_fields = ['group_name']

    def get(self, request, *args, **kwargs):
        self.queryset = self.queryset.filter(
            date__gte=(datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d'),
            date__lte=(datetime.datetime.now() + datetime.timedelta(days=14)).strftime('%Y-%m-%d'))
        sig_name = self.request.GET.get('group')
        if Group.objects.filter(name=sig_name):
            self.queryset = self.queryset.filter(group_name=sig_name)
        queryset = self.filter_queryset(self.get_queryset()).values()
        tableData = []
        date_list = []
        for query in queryset:
            date_list.append(query.get('date'))
        date_list = sorted(list(set(date_list)))
        if Group.objects.filter(name=sig_name):
            for date in date_list:
                tableData.append(
                    {
                        'date': date,
                        'timeData': [{
                            'id': meeting.id,
                            'mid': meeting.mid,
                            'group_name': meeting.group_name,
                            'startTime': meeting.start,
                            'endTime': meeting.end,
                            'duration': math.ceil(float(meeting.end.replace(':', '.'))) - math.floor(
                                float(meeting.start.replace(':', '.'))),
                            'duration_time': meeting.start.split(':')[0] + ':00' + '-' + str(
                                math.ceil(float(meeting.end.replace(':', '.')))) + ':00',
                            'name': meeting.topic,
                            'creator': meeting.sponsor,
                            'detail': meeting.agenda,
                            'url': User.objects.get(id=meeting.user_id).avatar,
                            'join_url': meeting.join_url,
                            'meeting_id': meeting.mid,
                            'etherpad': meeting.etherpad,
                            'record': True if Record.objects.filter(mid=meeting.mid) else False,
                            'platform': meeting.mplatform,
                            'video_url': '' if not Record.objects.filter(mid=meeting.mid, platform='bilibili') else
                            Record.objects.filter(mid=meeting.mid, platform='bilibili').values()[0]['url']
                        } for meeting in Meeting.objects.filter(is_delete=0, date=date, group_name=sig_name)]
                    }
                )
            return Response({'tableData': tableData})
        for date in date_list:
            tableData.append(
                {
                    'date': date,
                    'timeData': [{
                        'id': meeting.id,
                        'mid': meeting.mid,
                        'group_name': meeting.group_name,
                        'startTime': meeting.start,
                        'endTime': meeting.end,
                        'duration': math.ceil(float(meeting.end.replace(':', '.'))) - math.floor(
                            float(meeting.start.replace(':', '.'))),
                        'duration_time': meeting.start.split(':')[0] + ':00' + '-' + str(
                            math.ceil(float(meeting.end.replace(':', '.')))) + ':00',
                        'name': meeting.topic,
                        'creator': meeting.sponsor,
                        'detail': meeting.agenda,
                        'url': User.objects.get(id=meeting.user_id).avatar,
                        'join_url': meeting.join_url,
                        'meeting_id': meeting.mid,
                        'etherpad': meeting.etherpad,
                        'record': True if Record.objects.filter(mid=meeting.mid) else False,
                        'platform': meeting.mplatform,
                        'video_url': '' if not Record.objects.filter(mid=meeting.mid, platform='bilibili') else
                        Record.objects.filter(mid=meeting.mid, platform='bilibili').values()[0]['url']
                    } for meeting in Meeting.objects.filter(is_delete=0, date=date)]
                })
        return Response({'tableData': tableData})


class AllMeetingsView(GenericAPIView, ListModelMixin):
    """
    List all meetings
    """
    serializer_class = AllMeetingsSerializer
    queryset = Meeting.objects.all()
    filter_backends = [SearchFilter]
    search_fields = ['group_name', 'sponsor', 'date']
    permission_classes = (QueryPermission,)

    def get(self, request, *args, **kwargs):
        is_delete = self.request.GET.get('delete')
        if is_delete and is_delete in ['0', '1']:
            self.queryset = self.queryset.filter(is_delete=int(is_delete))
        return self.list(request, *args, **kwargs)


class ParticipantsView(GenericAPIView, RetrieveModelMixin):
    """
    List all participants info of a meeting
    """
    permission_classes = (QueryPermission,)

    def get(self, request, *args, **kwargs):
        mid = kwargs.get('mid')
        status, res = drivers.getParticipants(mid)
        if status == 200:
            return JsonResponse(res)
        else:
            resp = JsonResponse(res)
            resp.status_code = 400
            return resp
