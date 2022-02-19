import os

from .settings import *  # noqa

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": os.environ.get("SEQUENCES_POSTGRESQL_HOST", ""),
        "NAME": os.environ.get("SEQUENCES_POSTGRESQL_NAME", "sequences"),
        "USER": os.environ.get("SEQUENCES_POSTGRESQL_USER", "sequences"),
        "PASSWORD": os.environ.get("SEQUENCES_POSTGRESQL_PASSWORD", "sequences"),
    },
}
