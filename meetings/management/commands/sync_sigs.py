import logging
import os
import yaml
from meetings.models import Group, User, GroupUser
from django.core.management.base import BaseCommand

from meetings.utils.common import encrypt

logger = logging.getLogger('log')

class Command(BaseCommand):
    def handle(self, *args, **options):
        os.system('test -d meetings/tc && rm -rf meetings/tc')
        os.system('cd meetings; git clone https://gitee.com/opengauss/tc.git')
        with open('meetings/tc/sigs.yaml', 'r') as f:
            content = yaml.safe_load(f)
        res = []
        sigs = []
        for sig in content['sigs']:
            sig_name = sig['name']
            sig['sponsors'] = []
            with open('meetings/tc/sigs/{}/OWNERS'.format(sig_name), 'r') as f:
                owners = yaml.safe_load(f)
            for maintainer in owners['maintainers']:
                sig['sponsors'].append(maintainer)
            for committer in owners['committers']:
                sig['sponsors'].append(committer)
            del sig['repositories']
            sigs.append(sig)
        with open('meetings/tc/OWNERS', 'r') as f:
            owners = yaml.safe_load(f)
        sig = {}
        sig['name'] = 'TC'
        sig['sponsors'] = []
        for maintainer in owners['maintainers']:
            sig['sponsors'].append(maintainer)
        for commiiter in owners['committers']:
            sig['sponsors'].append(commiiter)
        sigs.append(sig)
        for sig in sigs:
            if not Group.objects.filter(name=sig['name']):
                Group.objects.create(name=sig['name'])
            group_id = Group.objects.get(name=sig['name']).id
            members = sig['sponsors']
            for member in members:
                encrypt_gitee_id = encrypt(member)
                if not User.objects.filter(gitee_id=encrypt_gitee_id):
                    continue
                user = User.objects.get(gitee_id=encrypt_gitee_id)
                if not GroupUser.objects.filter(group_id=group_id, user_id=user.id):
                    GroupUser.objects.create(group_id=group_id, user_id=user.id)
                    res.append((group_id, user.id))
        for gu in GroupUser.objects.all().values():
            if (gu.get('group_id'), gu.get('user_id')) not in res:
                gu.delete()