import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('SEQUENCES_DATABASE_NAME', 'sequences'),
        'USER': os.environ.get('SEQUENCES_DATABASE_NAME', 'sequences'),
        'PASSWORD': os.environ.get('SEQUENCES_DATABASE_NAME', 'sequences'),
    },
}

INSTALLED_APPS = ['sequences']

SECRET_KEY = 'whatever'
