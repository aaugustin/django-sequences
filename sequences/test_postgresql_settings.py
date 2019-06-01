import os

from .test_settings import *  # noqa

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('SEQUENCES_POSTGRESQL_NAME', 'sequences'),
        'USER': os.environ.get('SEQUENCES_POSTGRESQL_USER', 'sequences'),
        'PASSWORD': os.environ.get(
            'SEQUENCES_POSTGRESQL_PASSWORD', 'sequences'),
    },
}
