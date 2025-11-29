"""
Django settings for myproject project.
"""

import os
from pathlib import Path

from decouple import config

# --- Base directory ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Security ---
DEBUG = True
ALLOWED_HOSTS = ['*']

# --- Installed apps ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'myapp',  # your app
]

# --- Middleware ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',  # session support
    'whitenoise.middleware.WhiteNoiseMiddleware',  # <-- add this
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # auth
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'myproject.urls'

# --- Templates ---
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],  # you can leave empty because APP_DIRS=True
        'APP_DIRS': True,  # Django will search myapp/templates automatically
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


WSGI_APPLICATION = 'myproject.wsgi.application'

# --- Database ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# --- Password validators ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- Internationalization ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# --- Static files ---
STATIC_URL = '/static/'

# --- Default primary key field type ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- Authentication settings ---
LOGIN_URL = '/login/' 
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# --- Email backend for dev/testing ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = ''       # your Gmail address
EMAIL_HOST_PASSWORD = ''     # see step 2 below


# --- Session settings ---
SESSION_COOKIE_AGE = 1209600         # 2 weeks in seconds
SESSION_EXPIRE_AT_BROWSER_CLOSE = False



# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'myapp/static'),
]

STATIC_URL = '/static/'

# Local static files (for development)
STATICFILES_DIRS = [
    BASE_DIR / 'myapp' / 'static',
]

# Collected static files (for production)
STATIC_ROOT = BASE_DIR / 'staticfiles'

EMAIL_BACKEND = "emails.resend_backend.ResendEmailBackend"
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

SECRET_KEY = config("SECRET_KEY")
STRIPE_PUBLIC_KEY = config("STRIPE_PUBLIC_KEY")
STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY")
RESEND_API_KEY = config("RESEND_API_KEY")
MYHOSTEMAIL = config("MYHOSTEMAIL")
CSRF_TRUSTED_ORIGINS = [
    config('RAILWAY_PUBLIC_URL'),
]
