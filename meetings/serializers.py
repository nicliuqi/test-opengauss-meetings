from rest_framework.serializers import ModelSerializer
from meetings.models import Meeting, User, Group
from rest_framework import serializers


class MeetingsSerializer(ModelSerializer):
    class Meta:
        model = Meeting
        fields = ['topic', 'sponsor', 'group_name', 'date', 'start', 'end', 'etherpad', 'agenda', 'emaillist', 'user_id']
        extra_kwargs = {
            'mid': {'read_only': True},
            'join_url': {'read_only': True},
            'group_name': {'required': True}
        }


class MeetingUpdateSerializer(ModelSerializer):
    class Meta:
        model = Meeting
        fields = ['mid', 'topic', 'sponsor', 'group_name', 'date', 'start', 'end']


class MeetingDeleteSerializer(ModelSerializer):
    class Meta:
        model = Meeting
        fields = ['mid']


class MeetingDetailSerializer(ModelSerializer):
    class Meta:
        model = Meeting
        fields = ['id', 'mid', 'topic', 'sponsor', 'group_name', 'date', 'start', 'end', 'etherpad', 'agenda',
                  'join_url', 'emaillist', 'mplatform']


class GroupsSerializer(ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']


class AllMeetingsSerializer(ModelSerializer):
    class Meta:
        model = Meeting
        fields = '__all__'
