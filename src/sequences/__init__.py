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
      DO UPDATE SET last = {db_table}.last + %s
          RETURNING last;
"""

MYSQL_UPSERT = """
        INSERT INTO {db_table} (name, last)
             VALUES (%s, %s)
   ON DUPLICATE KEY
             UPDATE last = {db_table}.last + %s
"""

DELETE = """
             DELETE
               FROM {db_table}
              WHERE name = %s
"""


def get_last_value(
    sequence_name="default",
    *,
    using=None,
):
    """
    Return the last value for a sequence.

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
            [sequence_name],
        )
        result = cursor.fetchone()

    return None if result is None else result[0]


def get_next_value(
    sequence_name="default",
    initial_value=1,
    reset_value=None,
    batch=None,
    *,
    nowait=False,
    using=None,
):
    """
    Return the next value for a sequence.

    """
    # Inner import because models cannot be imported before their application.
    from .models import Sequence

    if reset_value is not None:
        if initial_value >= reset_value:
            raise ValueError("reset_value must be greater than initial_value")

    if batch is None:
        increment = 1
    else:
        if reset_value is not None:
            raise ValueError("reset_value and batch are incompatible")
        increment = batch
        initial_value = initial_value + increment - 1

    if using is None:
        using = router.db_for_write(Sequence)

    connection = connections[using]
    db_table = connection.ops.quote_name(Sequence._meta.db_table)

    if connection.vendor == "postgresql" and reset_value is None and not nowait:
        # PostgreSQL ≥ 9.5 supports "upsert".
        # This is about 3x faster as the naive implementation.

        with connection.cursor() as cursor:
            cursor.execute(
                POSTGRESQL_UPSERT.format(db_table=db_table),
                [sequence_name, initial_value, increment],
            ),
            result = cursor.fetchone()

        next_value = result[0]

    elif connection.vendor == "mysql" and reset_value is None and not nowait:
        # MySQL supports "upsert" but not "returning".
        # This is about 2x faster as the naive implementation.

        with transaction.atomic(using=using, savepoint=False):
            with connection.cursor() as cursor:
                cursor.execute(
                    MYSQL_UPSERT.format(db_table=db_table),
                    [sequence_name, initial_value, increment],
                )
                cursor.execute(
                    SELECT.format(db_table=db_table),
                    [sequence_name],
                )
                result = cursor.fetchone()

        next_value = result[0]

    else:
        # Default, ORM-based implementation for all other cases.

        with transaction.atomic(using=using, savepoint=False):
            sequences = Sequence.objects.select_for_update(nowait=nowait)
            sequence, created = sequences.get_or_create(
                name=sequence_name,
                defaults={"last": initial_value},
            )

            if not created:
                sequence.last += increment
                if reset_value is not None and sequence.last >= reset_value:
                    sequence.last = initial_value
                sequence.save()

            next_value = sequence.last

    if batch is None:
        return next_value
    else:
        return range(next_value - increment + 1, next_value + 1)


def delete(
    sequence_name="default",
    *,
    using=None,
):
    """
    Delete a sequence.

    """
    # Inner import because models cannot be imported before their application.
    from .models import Sequence

    if using is None:
        using = router.db_for_write(Sequence)

    connection = connections[using]
    db_table = connection.ops.quote_name(Sequence._meta.db_table)

    with connection.cursor() as cursor:
        cursor.execute(
            DELETE.format(db_table=db_table),
            [sequence_name],
        )
        return bool(cursor.rowcount)


class Sequence:
    """
    Generate a gapless sequence of integer values.

    """

    def __init__(
        self,
        sequence_name="default",
        initial_value=1,
        reset_value=None,
        *,
        using=None,
    ):
        self.sequence_name = sequence_name
        self.initial_value = initial_value
        self.reset_value = reset_value
        self.using = using

    def get_last_value(self):
        """
        Return the last value of the sequence.

        """
        return get_last_value(
            self.sequence_name,
            using=self.using,
        )

    def get_next_value(self, batch=None, *, nowait=False):
        """
        Return the next value of the sequence.

        """
        return get_next_value(
            self.sequence_name,
            self.initial_value,
            self.reset_value,
            batch,
            nowait=nowait,
            using=self.using,
        )

    def delete(self):
        """
        Delete the sequence.

        """
        return delete(
            self.sequence_name,
            using=self.using,
        )

    def __iter__(self):
        return self

    def __next__(self):
        return self.get_next_value()
