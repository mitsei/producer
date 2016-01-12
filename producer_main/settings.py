# Django settings for VideoSearch project.
# From NB: https://github.com/nbproject/nbproject/blob/master/apps/settings.py
from os.path import abspath, dirname, basename
import os
from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS

FN_CREDENTIALS = "settings_credentials.py"
def msg_credentials():
    msg = "*** Please edit the %s file with the required settings for authentication. ***" %(FN_CREDENTIALS, )
    stars = "*" * len(msg)
    return "\n\n%s\n%s\n%s\n\n" %(stars, msg, stars)

try:
    import settings_credentials
except ImportError:
    from os.path import dirname, abspath
    import shutil
    thisdir = dirname(abspath(__file__))
    shutil.copy2("%s/%s.skel" % (thisdir, FN_CREDENTIALS), "%s/%s" % (thisdir, FN_CREDENTIALS))
    print msg_credentials()
    exit(1)

DEBUG = settings_credentials.__dict__.get("DEBUG", False)
TEST = settings_credentials.__dict__.get("TEST", False)
PIPELINE_ENABLED = settings_credentials.__dict__.get("PIPELINE_ENABLED", False)
TEMPLATE_DEBUG = DEBUG
ADMINS = settings_credentials.__dict__.get("ADMINS", ())
MANAGERS = ADMINS
SERVERNAME = settings_credentials.__dict__.get("SERVERNAME", "localhost")
HTTP_PORT = settings_credentials.__dict__.get("HTTP_PORT", "80")
CRON_EMAIL = settings_credentials.__dict__.get("CRON_EMAIL", "no@one.com")
DATABASES = settings_credentials.DATABASES

# For logging
LOGGING = settings_credentials.__dict__.get('LOGGING')

# For Amazon S3
S3_PUBLIC_KEY = settings_credentials.__dict__.get('S3_PUBLIC_KEY')
S3_PRIVATE_KEY = settings_credentials.__dict__.get('S3_PRIVATE_KEY')
S3_BUCKET = settings_credentials.__dict__.get('S3_BUCKET')

S3_TEST_PUBLIC_KEY = settings_credentials.__dict__.get('S3_TEST_PUBLIC_KEY')
S3_TEST_PRIVATE_KEY = settings_credentials.__dict__.get('S3_TEST_PRIVATE_KEY')
S3_TEST_BUCKET = settings_credentials.__dict__.get('S3_TEST_BUCKET')

CLOUDFRONT_PUBLIC_KEY = settings_credentials.__dict__.get('CLOUDFRONT_PUBLIC_KEY')
CLOUDFRONT_PRIVATE_KEY = settings_credentials.__dict__.get('CLOUDFRONT_PRIVATE_KEY')
CLOUDFRONT_DISTRO = settings_credentials.__dict__.get('CLOUDFRONT_DISTRO')
CLOUDFRONT_DISTRO_ID = settings_credentials.__dict__.get('CLOUDFRONT_DISTRO_ID')
CLOUDFRONT_SIGNING_KEYPAIR_ID = settings_credentials.__dict__.get('CLOUDFRONT_SIGNING_KEYPAIR_ID')
CLOUDFRONT_SIGNING_PRIVATE_KEY_FILE = settings_credentials.__dict__.get('CLOUDFRONT_SIGNING_PRIVATE_KEY_FILE')

# For static and media files
MEDIA_ROOT = settings_credentials.__dict__.get('MEDIA_ROOT')
MEDIA_URL = settings_credentials.__dict__.get('MEDIA_URL')
STATIC_ROOT = settings_credentials.__dict__.get('STATIC_ROOT')
STATIC_URL = settings_credentials.__dict__.get('STATIC_URL')

# For logging in
LOGIN_URL = settings_credentials.__dict__.get('LOGIN_URL')

# For MC3 Configuration
MC3_HOST = settings_credentials.__dict__.get('MC3_HOST')

#For functional tests
SELENIUM_WEBDRIVER = settings_credentials.__dict__.get('SELENIUM_WEBDRIVER')

# For allowed hosts (Django 1.5+, Debug = False)
ALLOWED_HOSTS = settings_credentials.__dict__.get('ALLOWED_HOSTS')

# Additional locations of static files
STATICFILES_DIRS = settings_credentials.__dict__.get('STATICFILES_DIRS')

# because dlkit runtime needs all these fields, even if I don't use them...
MC3_HANDCAR_APP_KEY = settings_credentials.__dict__.get('MC3_HANDCAR_APP_KEY')
MC3_DEMO_HANDCAR_APP_KEY = settings_credentials.__dict__.get('MC3_DEMO_HANDCAR_APP_KEY')
MC3_DEV_HANDCAR_APP_KEY = settings_credentials.__dict__.get('MC3_DEV_HANDCAR_APP_KEY')
DLKIT_MONGO_DB_PREFIX = settings_credentials.__dict__.get('DLKIT_MONGO_DB_PREFIX')
MONGO_HOST_URI = settings_credentials.__dict__.get('MONGO_HOST_URI')
DLKIT_AUTHORITY = settings_credentials.__dict__.get('DLKIT_AUTHORITY')
DLKIT_MONGO_DB_INDEXES = settings_credentials.__dict__.get('DLKIT_MONGO_DB_INDEXES')
DLKIT_MONGO_KEYWORD_FIELDS = settings_credentials.__dict__.get('DLKIT_MONGO_KEYWORD_FIELDS')
WEBSOCKET_EXCHANGE = settings_credentials.__dict__.get('WEBSOCKET_EXCHANGE', '')  # needs to match spec in node_modules/server.js...should migrate to environment variable at some point

CELERY_ALWAYS_EAGER = settings_credentials.__dict__.get('CELERY_ALWAYS_EAGER', False)
CELERY_EAGER_PROPAGATES_EXCEPTIONS = settings_credentials.__dict__.get('CELERY_EAGER_PROPAGATES_EXCEPTIONS', False)
BROKER_URL = settings_credentials.__dict__.get('BROKER_URL', '')
CELERY_RESULT_BACKEND = settings_credentials.__dict__.get('CELERY_RESULT_BACKEND', '')
CELERY_RESULT_PERSISTENT = settings_credentials.__dict__.get('CELERY_RESULT_PERSISTENT', True)
CELERY_IGNORE_RESULT = settings_credentials.__dict__.get('CELERY_IGNORE_RESULT', '')

RABBITMQ_USER = settings_credentials.__dict__.get('RABBITMQ_USER', '')
RABBITMQ_PWD = settings_credentials.__dict__.get('RABBITMQ_PWD', True)
RABBITMQ_VHOST = settings_credentials.__dict__.get('RABBITMQ_VHOST', '')

ENABLE_NOTIFICATIONS = settings_credentials.__dict__.get('ENABLE_NOTIFICATIONS', False)
ENABLE_OBJECTIVE_FACETS = settings_credentials.__dict__.get('ENABLE_OBJECTIVE_FACETS', False)
FORCE_TLSV1 = settings_credentials.__dict__.get('FORCE_TLSV1', False)

if "default" not in DATABASES or "PASSWORD" not in DATABASES["default"] or DATABASES["default"]["PASSWORD"]=="":
    print msg_credentials()
    exit(1)

# PROJECT_PATH avoids using a hard-coded path that must be changed with every server deployment
PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))

ABS_PATH_TO_FILES = os.path.abspath(os.path.join(PROJECT_PATH, os.pardir))

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
    'compressor.finders.CompressorFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '5#75$niX*(DSFh1fc!5%nzbn9o_!2tijqih*6uyomtb+bjlq$^n!ww'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

if DEBUG:
    MIDDLEWARE_CLASSES = (
        'corsheaders.middleware.CorsMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.auth.middleware.RemoteUserMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        # Uncomment the next line for simple clickjacking protection:
        # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
        'producer.middleware.ProfilerMiddleware',
    )
else:
    MIDDLEWARE_CLASSES = (
        'corsheaders.middleware.CorsMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.auth.middleware.RemoteUserMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.gzip.GZipMiddleware',
        # Uncomment the next line for simple clickjacking protection:
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
    )


AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'django.contrib.auth.backends.RemoteUserBackend',
)

ROOT_URLCONF = 'producer_main.urls'

# Python dotted path to the WSGI application used by Django's runserver.
# WSGI_APPLICATION = 'resource_bank.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    ABS_PATH_TO_FILES+'/templates',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'assessments',
    'grading',
    'learning',
    'producer',
    'repository',
    'ui',
    'utilities',
    'south',
    'rest_framework',
    'dlkit_django',
    'dlkit',
    'corsheaders',
    'compressor',
    'records'
)

SOUTH_TESTS_MIGRATE = False

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
       'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    )
}

SESSION_SERIALIZER='django.contrib.sessions.serializers.JSONSerializer'

TEMPLATE_CONTEXT_PROCESSORS += ("django.core.context_processors.request",)

SESSION_SAVE_EVERY_REQUEST = True

# Django CORS from:
# https://github.com/ottoyiu/django-cors-headers/
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_HEADERS = (
    'x-api-proxy',
    'content-type',
    'accept',
    'origin'
)

# sacrifice SEO to support non-slash frameworks like Angular
# http://stackoverflow.com/questions/1596552/django-urls-without-a-trailing-slash-do-not-redirect
APPEND_SLASH = False
