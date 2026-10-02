import os

from .settings import *  # noqa

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ.get("SEQUENCES_POSTGRESQL_HOST", "127.0.0.1"),
        "PORT": os.environ.get("SEQUENCES_POSTGRESQL_PORT", "5432"),
        "NAME": os.environ.get("SEQUENCES_POSTGRESQL_NAME", "sequences"),
        "USER": os.environ.get("SEQUENCES_POSTGRESQL_USER", "sequences"),
        "PASSWORD": os.environ.get("SEQUENCES_POSTGRESQL_PASSWORD", "sequences"),
    },
}
