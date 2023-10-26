from django.conf import settings
from rest_framework import permissions

from meetings.models import GroupUser


class QueryPermission(permissions.BasePermission):
    """查询权限"""

    def has_permission(self, request, view):
        token = request.GET.get('token')
        if token and token == settings.QUERY_TOKEN:
            return True
        else:
            return False


class MaintainerPermission(permissions.IsAuthenticated):
    """Maintainer权限"""
    message = '需要Maintainer权限！！！'

    def has_permission(self, request, view):
        if request.user.is_anonymous:
            return False
        if GroupUser.objects.filter(user_id=request.user.id):
            return True

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)