# See https://code.djangoproject.com/wiki/OracleTestSetup

import os

from .test_settings import *  # noqa

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.oracle',
        'NAME': os.environ.get('SEQUENCES_ORACLE_NAME', '127.0.0.1:1521/orcl'),
        'USER': os.environ.get('SEQUENCES_ORACLE_USER', 'sequences'),
        'PASSWORD': os.environ.get('SEQUENCES_ORACLE_PASSWORD', 'sequences'),

    },
}
