from django.conf import settings
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken
from meetings.models import User
from meetings.utils import crypto_gcm


def make_signature(access_token):
    signature = make_password(access_token, settings.SECRET_KEY)
    return signature


def refresh_access(user):
    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)
    encrypt_access = make_signature(access)
    User.objects.filter(id=user.id).update(signature=encrypt_access)
    return access


def encrypt(plaintext):
    return crypto_gcm.aes_gcm_encrypt(plaintext, settings.AES_GCM_SECRET, settings.AES_GCM_IV)


def decrypt(ciphertext):
    return crypto_gcm.aes_gcm_decrypt(ciphertext, settings.AES_GCM_SECRET)