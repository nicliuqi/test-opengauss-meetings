import unicodedata
from django.db import models


class MyAbstractBaseUser(models.Model):
    EMAIL_FIELD = None
    is_active = True

    REQUIRED_FIELDS = []

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.USERNAME_FIELD = None

    def __str__(self):
        return self.get_username()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def get_username(self):
        """Return the username for this User."""
        return str(self.USERNAME_FIELD)

    def clean(self):
        setattr(self, self.USERNAME_FIELD, self.normalize_username(self.get_username()))

    def natural_key(self):
        return (self.get_username(),)

    @property
    def is_anonymous(self):
        """
        Always return False. This is a way of comparing User objects to
        anonymous users.
        """
        return False

    @property
    def is_authenticated(self):
        """
        Always return True. This is a way to tell if the user has been
        authenticated in templates.
        """
        return True

    @classmethod
    def get_email_field_name(cls):
        try:
            return cls.EMAIL_FIELD
        except AttributeError:
            return 'email'

    @classmethod
    def normalize_username(cls, username):
        return unicodedata.normalize('NFKC', username) if isinstance(username, str) else username


class User(MyAbstractBaseUser):
    """用户表"""
    USERNAME_FIELD = 'id'

    gitee_id = models.CharField(verbose_name='GiteeID', max_length=100)
    signature = models.CharField(verbose_name='签名', max_length=255, blank=True, null=True)
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True, null=True, blank=True)
    last_login = models.DateTimeField(verbose_name='上次登录时间', auto_now=True, null=True, blank=True)


class Group(models.Model):
    """SIG组表"""
    name = models.CharField(verbose_name='sig组名称', max_length=50)
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True, null=True, blank=True)


class GroupUser(models.Model):
    """组与用户表"""
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('group', 'user')



class Meeting(models.Model):
    """会议表"""
    topic = models.CharField(verbose_name='会议主题', max_length=128)
    community = models.CharField(verbose_name='社区', max_length=40, null=True, blank=True)
    group_name = models.CharField(verbose_name='SIG组', max_length=40, null=True, blank=True)
    sponsor = models.CharField(verbose_name='发起人', max_length=20)
    avatar = models.CharField(verbose_name='发起人头像', max_length=255, null=True, blank=True)
    date = models.CharField(verbose_name='会议日期', max_length=30)
    start = models.CharField(verbose_name='会议开始时间', max_length=30)
    end = models.CharField(verbose_name='会议结束时间', max_length=30)
    duration = models.IntegerField(verbose_name='会议时长', null=True, blank=True)
    agenda = models.TextField(verbose_name='议程', default='', null=True, blank=True)
    etherpad = models.CharField(verbose_name='etherpad', max_length=255, null=True, blank=True)
    emaillist = models.TextField(verbose_name='邮件列表', null=True, blank=True)
    host_id = models.EmailField(verbose_name='host_id', null=True, blank=True)
    mid = models.CharField(verbose_name='会议id', max_length=20)
    timezone = models.CharField(verbose_name='时区', max_length=50, null=True, blank=True)
    password = models.CharField(verbose_name='密码', max_length=128, null=True, blank=True)
    start_url = models.TextField(verbose_name='开启会议url', null=True, blank=True)
    join_url = models.CharField(verbose_name='进入会议url', max_length=128, null=True, blank=True)
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True, null=True, blank=True)
    is_delete = models.SmallIntegerField(verbose_name='是否删除', choices=((0, '否'), (1, '是')), default=0)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    group = models.ForeignKey(Group, on_delete=models.DO_NOTHING)
    mplatform = models.CharField(verbose_name='第三方会议平台', max_length=20, null=True, blank=True, default='zoom')
    sequence = models.IntegerField(verbose_name='序列号', default=0)


class Video(models.Model):
    """会议记录表"""
    mid = models.CharField(verbose_name='会议id', max_length=12)
    topic = models.CharField(verbose_name='会议名称', max_length=50)
    community = models.CharField(verbose_name='社区', max_length=40, null=True, blank=True)
    group_name = models.CharField(verbose_name='所属sig组', max_length=50)
    agenda = models.TextField(verbose_name='会议简介', null=True, blank=True)
    attenders = models.TextField(verbose_name='参会人', null=True, blank=True)
    start = models.CharField(verbose_name='记录开始时间', max_length=30, null=True, blank=True)
    end = models.CharField(verbose_name='记录结束时间', max_length=30, null=True, blank=True)
    total_size = models.IntegerField(verbose_name='总文件大小', null=True, blank=True)
    download_url = models.CharField(verbose_name='下载地址', max_length=255, null=True, blank=True)
    replay_url = models.CharField(verbose_name='回放地址', max_length=255, null=True, blank=True)
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True, null=True, blank=True)


class Record(models.Model):
    """录像表"""
    mid = models.CharField(verbose_name='会议id', max_length=12)
    platform = models.CharField(verbose_name='平台', max_length=50)
    url = models.CharField(verbose_name='播放地址', max_length=255, null=True, blank=True)
    thumbnail = models.CharField(verbose_name='缩略图', max_length=255, null=True, blank=True)
