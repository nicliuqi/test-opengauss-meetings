import logging
import os
import stat
import yaml
from meetings.models import Group
from django.core.management.base import BaseCommand


logger = logging.getLogger('log')

class Command(BaseCommand):
    def handle(self, *args, **options):
        os.system('test -d meetings/tc && rm -rf meetings/tc')
        os.system('cd meetings; git clone https://gitee.com/opengauss/tc.git')
        with open('meetings/tc/sigs.yaml', 'r') as f:
            content = yaml.safe_load(f)
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
            if Group.objects.filter(name=sig_name):
                Group.objects.filter(name=sig_name).update(members=sig['sponsors'])
                logger.info('Update sig: {}'.format(sig_name))
                logger.info({'sig': sig_name, 'members': sig['sponsors']})
            else:
                Group.objects.create(name=sig_name, members=sig['sponsors'])
                logger.info('Create sig: {}'.format(sig_name))
                logger.info({'sig': sig_name, 'members': sig['sponsors']})
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
        if not Group.objects.filter(name='TC'):
            Group.objects.create(name='TC', members=sig['sponsors'])
            logger.info('Create sig: TC')
        else:
            Group.objects.filter(name='TC').update(members=sig['sponsors'])
            logger.info('Update sig: TC')
        flags = os.O_CREAT | os.O_WRONLY
        modes = stat.S_IWUSR
        with os.fdopen(os.open('share/openGauss_sigs.yaml', flags, modes), 'w') as f:
            yaml.dump(sigs, f, default_flow_style=False)
