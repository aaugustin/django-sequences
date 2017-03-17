from django.db import router, transaction


def get_next_value(
        sequence_name='default', initial_value=1,
        *, nowait=False, using=None):
    """
    Return the next value for a given sequence.

    """
    # Inner import because models cannot be imported before their application.
    from .models import Sequence

    if using is None:
        using = router.db_for_write(Sequence)

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

    with transaction.atomic(using=using, savepoint=False):
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
