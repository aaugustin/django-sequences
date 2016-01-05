"""
Sequential (gap-less) values generation on PostgreSQL.

SERIAL fields aren't guaranteed to be sequential. If a transaction attempts to
insert a row and then is rolled back, the sequence counter isn't rolled back,
for performance reasons, creating a gap in the sequence. This is a problem for
some use cases such as accounting.

INTEGER PRIMARY KEY AUTOINCREMENT fields on SQLite don't exhibit this problem.
The author doesn't know if it happens on MySQL or Oracle and didn't research
whether this application would solve it.

"""

from django.db import router, transaction


def get_next_value(sequence_name="default", initial_value=1, nowait=False):
    """
    Return the next value for a given sequence.

    All database transactions that call this function will be serialized.
    Keep such transactions short to minimize the impact or performance.
    Pass nowait=False if you'd rather get an exception than wait when
    something else holds the lock.

    """
    # Inner import because models cannot be imported before their application.
    from .models import Sequence

    # The current implementation makes two SQL queries (plus two for creating
    # and releasing a savepoint when the sequence is created). The same effect
    # could be achieved with a single query on PostgreSQL >= 9.5:
    #
    #   INSERT INTO sequences_sequence (name, last)
    #        VALUES (E'default', 1)
    #   ON CONFLICT (name)
    # DO UPDATE SET last = sequences_sequence.last + 1
    #     RETURNING last;
    #
    # That version would be more elegant and perhaps slightly faster. But it
    # involves PostgreSQL-specific syntax and requires a version of PostgreSQL
    # which isn't widely available yet. It could be implemented only when the
    # database supports it, based on django.db.connections[using].pg_version.

    with transaction.atomic(using=router.db_for_write(Sequence),
                            savepoint=False):
        sequence, created = (
            Sequence.objects
                    .select_for_update(nowait=nowait)
                    .get_or_create(name=sequence_name,
                                   defaults={'last': initial_value})
        )
        if not created:
            sequence.last += 1
            sequence.save()
        return sequence.last
