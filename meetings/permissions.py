from django.conf import settings
from rest_framework import permissions


class QueryPermission(permissions.BasePermission):
    """查询权限"""

    def has_permission(self, request, view):
        token = request.GET.get('token')
        if token and token == settings.DEFAULT_CONF.get('QUERY_TOKEN'):
            return True
        else:
            return False

