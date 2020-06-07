# Usage:
# DJANGO_SETTINGS_MODULE=tests.postgresql_settings python -m django migrate
# DJANGO_SETTINGS_MODULE=tests.postgresql_settings python benchmark.py

import threading
import time

import django
from django.db import connection

from sequences import get_next_value

django.setup()

# Reinitialize sequence
get_next_value(initial_value=0, reset_value=1)

LOOPS = 500
THREADS = 20
VALUES = []

def get_values():
    for _ in range(LOOPS):
        # Add `reset_value=10001` to use the ORM-based, non-optimized implementation.
        VALUES.append(get_next_value(reset_value=10001))
    connection.close()

threads = [threading.Thread(target=get_values) for _ in range(THREADS)]

t0 = time.perf_counter()

for thread in threads:
    thread.start()

for thread in threads:
    thread.join()

t1 = time.perf_counter()

assert set(VALUES) == set(range(1, LOOPS * THREADS + 1))

print("{} loops x {} threads in {:.2f} seconds = {:.0f} values / second"
      .format(LOOPS, THREADS, t1 - t0, LOOPS * THREADS / (t1 - t0)))
