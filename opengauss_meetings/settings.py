"""
Django settings for opengauss_meetings project.

Generated by 'django-admin startproject' using Django 3.1.4.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""
import datetime
import time
import os
from datetime import timedelta
from pathlib import Path
import subprocess
import sys
import yaml


CONFIG_PATH = os.getenv('CONFIG_PATH')
XARMOR_CONF = os.getenv('XARMOR_CONF')
if not os.path.exists(CONFIG_PATH):
    sys.exit()
with open(CONFIG_PATH, 'r') as f:
    content = yaml.safe_load(f)
DEFAULT_CONF = content
if sys.argv[0] == 'uwsgi':
    os.remove(CONFIG_PATH)
    if os.path.basename(XARMOR_CONF) in os.listdir():
        os.remove(os.path.basename(XARMOR_CONF))

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

from meetings.utils.zoom_apis import getOauthToken
ZOOM_TOKEN = getOauthToken()

GITEE_OAUTH_CLIENT_ID = DEFAULT_CONF.get('GITEE_OAUTH_CLIENT_ID', '')

GITEE_OAUTH_CLIENT_SECRET = DEFAULT_CONF.get('GITEE_OAUTH_CLIENT_SECRET', '')

GITEE_OAUTH_REDIRECT = DEFAULT_CONF.get('GITEE_OAUTH_REDIRECT', '')

REDIRECT_HOME_PAGE = DEFAULT_CONF.get('REDIRECT_HOME_PAGE', '')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = DEFAULT_CONF.get('SECRET_KEY', '')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'meetings.apps.MeetingsConfig',
    'rest_framework',
    'drf_yasg',
    'corsheaders',
]

CORS_ALLOW_METHODS = (
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'OPTIONS'
)
CORS_ALLOW_HEADERS = (
    'XMLHttpRequest',
    'X_FILENAME',
    'accept-encoding',
    'content-type',
    'Authorization',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'Pragma',
)
CORS_ALLOW_CREDENTIALS = True

CORS_ORIGIN_ALLOW_ALL = True

SESSION_COOKIE_HTTPONLY = True

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'opengauss_meetings.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')]
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'opengauss_meetings.wsgi.application'

# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'opengauss_meetings',
        'USER': DEFAULT_CONF.get('DB_USER', 'root'),
        'PASSWORD': DEFAULT_CONF.get('DB_PASSWORD', '123456'),
        'HOST': DEFAULT_CONF.get('DB_HOST', '127.0.0.1'),
        'PORT': DEFAULT_CONF.get('DB_PORT', '3306'),
    }
}

OPENGAUSS_MEETING_HOSTS = {
    'zoom': {
        DEFAULT_CONF.get('ZOOM_HOST_FIRST', ''): DEFAULT_CONF.get('ZOOM_ACCOUNT_FIRST', ''),
        DEFAULT_CONF.get('ZOOM_HOST_SECOND', ''): DEFAULT_CONF.get('ZOOM_ACCOUNT_SECOND', '')
    },
    'welink': {
        DEFAULT_CONF.get('WELINK_HOST_1', ''): DEFAULT_CONF.get('WELINK_HOST_1', '')
    }
}

WELINK_HOSTS = {
    DEFAULT_CONF.get('WELINK_HOST_1', ''): {
        'account': DEFAULT_CONF.get('WELINK_HOST_1_ACCOUNT', ''),
        'pwd': DEFAULT_CONF.get('WELINK_HOST_1_PWD', '')
    }
}

# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = False

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

STATIC_URL = '/static/'

cur_path = os.path.dirname(os.path.realpath(__file__))  # log_path是存放日志的路径

log_path = os.path.join(os.path.dirname(cur_path), 'logs')

if not os.path.exists(log_path): os.mkdir(log_path)  # 如果不存在这个logs文件夹，就自动创建一个

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        # 日志格式
        'standard': {
            'format': '[%(asctime)s] [%(filename)s:%(lineno)d] [%(module)s:%(funcName)s] '
                      '[%(levelname)s]- %(message)s'},
        'simple': {  # 简单格式
            'format': '%(levelname)s %(message)s'
        },
    },
    # 过滤
    'filters': {
    },
    # 定义具体处理日志的方式
    'handlers': {
        # 默认记录所有日志
        'default': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(log_path, 'all-{}.log'.format(time.strftime('%Y-%m-%d'))),
            'maxBytes': 1024 * 1024 * 5,  # 文件大小
            'backupCount': 5,  # 备份数
            'formatter': 'standard',  # 输出格式
            'encoding': 'utf-8',  # 设置默认编码，否则打印出来汉字乱码
        },
        # 输出错误日志
        'error': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(log_path, 'error-{}.log'.format(time.strftime('%Y-%m-%d'))),
            'maxBytes': 1024 * 1024 * 5,  # 文件大小
            'backupCount': 5,  # 备份数
            'formatter': 'standard',  # 输出格式
            'encoding': 'utf-8',  # 设置默认编码
        },
        # 控制台输出
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
        # 输出info日志
        'info': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(log_path, 'info-{}.log'.format(time.strftime('%Y-%m-%d'))),
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 5,
            'formatter': 'standard',
            'encoding': 'utf-8',  # 设置默认编码
        },
    },
    # 配置用哪几种 handlers 来处理日志
    'loggers': {
        # 类型 为 django 处理所有类型的日志， 默认调用
        'django': {
            'handlers': ['default', 'console'],
            'level': 'INFO',
            'propagate': False
        },
        # log 调用时需要当作参数传入
        'log': {
            'handlers': ['error', 'info', 'console', 'default'],
            'level': 'INFO',
            'propagate': True
        },
    }
}

GMAIL_USERNAME = DEFAULT_CONF.get('GMAIL_USERNAME', '')
GMAIL_PASSWORD = DEFAULT_CONF.get('GMAIL_PASSWORD', '')
SMTP_SERVER_HOST = DEFAULT_CONF.get('SMTP_SERVER_HOST', '')
SMTP_SERVER_PORT = 25
CSRF_COOKIE_NAME = 'meeting-csrftoken'
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = 'strict'
COOKIE_EXPIRE = timedelta(minutes=30)
ACCESS_TOKEN_NAME = 'meeting-accesstoken'

