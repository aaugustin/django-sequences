from django.db import connections, router, transaction


POSTGRESQL_UPSERT = """
        INSERT INTO sequences_sequence (name, last)
             VALUES (%s, %s)
        ON CONFLICT (name)
      DO UPDATE SET last = sequences_sequence.last + 1
          RETURNING last;
"""

MYSQL_UPSERT = """
        INSERT INTO sequences_sequence (name, last)
             VALUES (%s, %s)
   ON DUPLICATE KEY
             UPDATE last = sequences_sequence.last + 1
"""

SELECT = """
             SELECT last
               FROM sequences_sequence
              WHERE name = %s
"""


def get_next_value(
        sequence_name='default', initial_value=1, reset_value=None,
        *, nowait=False, using=None):
    """
    Return the next value for a given sequence.

    """
    # Inner import because models cannot be imported before their application.
    from .models import Sequence

    if reset_value is not None:
        assert initial_value < reset_value

    if using is None:
        using = router.db_for_write(Sequence)

    connection = connections[using]

    if (
        connection.vendor == 'postgresql'
        # connection.features.is_postgresql_9_5 when dropping Django 1.11.
        and getattr(connection, 'pg_version', 0) >= 90500
        and reset_value is None
        and not nowait
    ):

        # PostgreSQL ≥ 9.5 supports "upsert".
        # This is about 3x faster as the naive implementation.

        with connection.cursor() as cursor:
            cursor.execute(POSTGRESQL_UPSERT, [sequence_name, initial_value])
            last, = cursor.fetchone()
        return last

    elif (
        connection.vendor == 'mysql'
        and reset_value is None
        and not nowait
    ):

        # MySQL supports "upsert" but not "returning".
        # This is about 2x faster as the naive implementation.

        with transaction.atomic(using=using, savepoint=False):
            with connection.cursor() as cursor:
                cursor.execute(MYSQL_UPSERT, [sequence_name, initial_value])
                cursor.execute(SELECT, [sequence_name])
                last, = cursor.fetchone()
        return last

    else:

        # Default, ORM-based implementation for all other cases.

        with transaction.atomic(using=using, savepoint=False):
            sequence, created = (
                Sequence.objects
                        .select_for_update(nowait=nowait)
                        .get_or_create(name=sequence_name,
                                       defaults={'last': initial_value})
            )

            if not created:
                sequence.last += 1
                if reset_value is not None and sequence.last >= reset_value:
                    sequence.last = initial_value
                sequence.save()

            return sequence.last
