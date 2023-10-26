import binascii
from django.core.management.base import BaseCommand
from meetings.models import User
from meetings.utils.common import decrypt, encrypt


class Command(BaseCommand):
    def handle(self, *args, **options):
        users = User.objects.all().values()
        for user in users:
            gitee_id = user.gitee_id
            try:
                decrypt(gitee_id)
                continue
            except (binascii.Error, ValueError):
                encrypt_gitee_id = encrypt(gitee_id)
                User.objects.filter(gitee_id=gitee_id).update(gitee_id=encrypt_gitee_id)