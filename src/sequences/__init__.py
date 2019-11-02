from django.db import connections, router, transaction

SELECT = """
             SELECT last
               FROM {db_table}
              WHERE name = %s
"""

POSTGRESQL_UPSERT = """
        INSERT INTO {db_table} (name, last)
             VALUES (%s, %s)
        ON CONFLICT (name)
      DO UPDATE SET last = {db_table}.last + 1
          RETURNING last;
"""

MYSQL_UPSERT = """
        INSERT INTO {db_table} (name, last)
             VALUES (%s, %s)
   ON DUPLICATE KEY
             UPDATE last = {db_table}.last + 1
"""


def get_last_value(
    sequence_name='default',
    *,
    using=None
):
    """
    Return the last value for a given sequence.

    """
    # Inner import because models cannot be imported before their application.
    from .models import Sequence

    if using is None:
        using = router.db_for_read(Sequence)

    connection = connections[using]
    db_table = connection.ops.quote_name(Sequence._meta.db_table)

    with connection.cursor() as cursor:
        cursor.execute(
            SELECT.format(db_table=db_table),
            [sequence_name]
        )
        result = cursor.fetchone()

    return None if result is None else result[0]


def get_next_value(
    sequence_name='default',
    initial_value=1,
    reset_value=None,
    *,
    nowait=False,
    using=None
):
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
    db_table = connection.ops.quote_name(Sequence._meta.db_table)

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
            cursor.execute(
                POSTGRESQL_UPSERT.format(db_table=db_table),
                [sequence_name, initial_value]
            )
            result = cursor.fetchone()

        return result[0]

    elif (
        connection.vendor == 'mysql'
        and reset_value is None
        and not nowait
    ):

        # MySQL supports "upsert" but not "returning".
        # This is about 2x faster as the naive implementation.

        with transaction.atomic(using=using, savepoint=False):
            with connection.cursor() as cursor:
                cursor.execute(
                    MYSQL_UPSERT.format(db_table=db_table),
                    [sequence_name, initial_value]
                )
                cursor.execute(
                    SELECT.format(db_table=db_table),
                    [sequence_name]
                )
                result = cursor.fetchone()

        return result[0]

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


class Sequence:
    """
    Generate a gapless sequence of integer values.

    """
    def __init__(
        self,
        sequence_name='default',
        initial_value=1,
        reset_value=None,
        *,
        using=None
    ):
        if reset_value is not None:
            assert initial_value < reset_value
        self.sequence_name = sequence_name
        self.initial_value = initial_value
        self.reset_value = reset_value
        self.using = using

    def get_last_value(
        self,
    ):
        """
        Return the last value of the sequence.

        """
        return get_last_value(
            self.sequence_name,
            using=self.using,
        )

    def get_next_value(
        self,
        *,
        nowait=False
    ):
        """
        Return the next value of the sequence.

        """
        return get_next_value(
            self.sequence_name,
            self.initial_value,
            self.reset_value,
            nowait=nowait,
            using=self.using,
        )

    def __iter__(self):
        return self

    def __next__(self):
        return self.get_next_value()
