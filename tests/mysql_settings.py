import os

from .settings import *  # noqa

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "HOST": os.environ.get("SEQUENCES_MYSQL_HOST", ""),
        "NAME": os.environ.get("SEQUENCES_MYSQL_NAME", "sequences"),
        "USER": os.environ.get("SEQUENCES_MYSQL_USER", "sequences"),
        "PASSWORD": os.environ.get("SEQUENCES_MYSQL_PASSWORD", "sequences"),
    },
}
