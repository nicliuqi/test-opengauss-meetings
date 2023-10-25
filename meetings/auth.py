from django.utils.translation import ugettext_lazy as _
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.state import User
from meetings.utils.common import make_signature
from meetings.models import User as MUser


class CustomAuthentication(JWTAuthentication):
    """
    CustomAuthentication override get_user
    """

    def get_user(self, validated_token):
        """
        Attempts to find and return a user using the given validated token.
        """
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError:
            raise InvalidToken(_('Token contained no recognizable user identification'))

        if not MUser.objects.filter(id=user_id):
            raise AuthenticationFailed(_('User not found'), code='user_not_found')
        user = MUser.objects.get(id=user_id)
        token = make_signature(validated_token)
        if MUser.objects.get(id=user_id).signature != str(token):
            raise InvalidToken(_('Token has expired'))

        return user
