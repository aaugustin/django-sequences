from django.db import connections, router, transaction


UPSERT_QUERY = """
    INSERT INTO sequences_sequence (name, last)
         VALUES (%s, %s)
    ON CONFLICT (name)
  DO UPDATE SET last = sequences_sequence.last + 1
      RETURNING last
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

    if (getattr(connection, 'pg_version', 0) >= 90500
            and reset_value is None and not nowait):

        # PostgreSQL ≥ 9.5 supports "upsert".

        with connection.cursor() as cursor:
            cursor.execute(UPSERT_QUERY, [sequence_name, initial_value])
            last, = cursor.fetchone()
        return last

    else:

        # Other databases require making more database queries.

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
