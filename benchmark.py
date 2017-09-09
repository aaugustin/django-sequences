# Usage:
# PYTHONPATH=. DJANGO_SETTINGS_MODULE=sequences.test_postgresql_settings django-admin migrate
# PYTHONPATH=. DJANGO_SETTINGS_MODULE=sequences.test_postgresql_settings python benchmark.py

import threading
import time

import django
from django.db import connection

from sequences import get_next_value

django.setup()

LOOPS = 500
THREADS = 20

def get_values():
    for _ in range(LOOPS):
        # Add `reset_value=1000` to use SELECT + UPDATE instead of INSERT ON CONFLICT.
        get_next_value()
    connection.close()

threads = [threading.Thread(target=get_values) for _ in range(THREADS)]

t0 = time.perf_counter()

for thread in threads:
    thread.start()

for thread in threads:
    thread.join()

t1 = time.perf_counter()

print("{} loops x {} threads in {:.2f} seconds = {:.0f} values / second"
      .format(LOOPS, THREADS, t1 - t0, LOOPS * THREADS / (t1 - t0)))
