import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SECRET_KEY = os.environ.get('SECRET_KEY', 'not secret key')

DEBUG = True

DOMAIN = os.environ.get('DOMAIN', 'localhost')

ALLOWED_HOSTS = [DOMAIN, 'www.' + DOMAIN]

INSTALLED_APPS = [
    'ffpasta',
    'ckeditor',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ffpasta.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'testoviny/templates')]
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

WSGI_APPLICATION = 'wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'data/db.sqlite3'),
    }
}

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

LANGUAGE_CODE = 'cs'

TIME_ZONE = 'Europe/Prague'

USE_I18N = True

USE_L10N = True
USE_THOUSAND_SEPARATOR = True

USE_TZ = False

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Custom',
        'toolbar_Custom': [
            ['Styles', 'Format', 'FontSize', 'Bold', 'Italic', 'Underline', 'Strike',
             'RemoveFormat', 'PasteText','Redo', 'Undo', 'Link', 'Unlink', 'Anchor'],
            ['NumberedList', 'BulletedList', 'Outdent', 'Indent', 'Blockquote'],
            ['JustifyLeft', 'JustifyCenter', 'JustifyRight'],
            ['Image', 'Flash', 'Table', 'HorizontalRule', 'Smiley', 'SpecialChar'],
            ['TextColor', 'BGColor'],
            ['Source'],
        ]
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = True
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'email_host')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'email_host_user')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'email_host_password')
EMAIL_PORT = 25

LOGIN_URL = '/prihlaseni/'
LOGIN_REDIRECT_URL = '/objednavky/'

IDOKLAD_API_URL = 'https://app.idoklad.cz/developer'
IDOKLAD_AUTH_URL = 'https://app.idoklad.cz/identity/server/connect/token'
IDOKLAD_CLIENT_ID = os.environ.get('IDOKLAD_CLIENT_ID', 'not client id')
IDOKLAD_CLIENT_SECRET = os.environ.get('IDOKLAD_CLIENT_SECRET', 'not client secret')

FB_APP_ID = os.environ.get('FB_APP_ID', None)
