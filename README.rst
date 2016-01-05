django-sequences
################

The problem
===========

On PostgreSQL, ``SERIAL`` columns aren't guaranteed to be sequential.

If a transaction inserts a row and then is rolled back, the sequence counter
isn't rolled back for performance reasons, creating a gap in the sequence.

Django's default, implicit primary keys are backed by ``SERIAL`` columns.
Usually they're sequential but this problem can create unexpected gaps.

This is a problem for some use cases such as accounting.

The solution
============

django-sequences provides just one function, ``get_next_value``, which is
designed to be used as follows::

    from django.db import transaction

    from sequences import get_next_value

    from invoices.models import Invoice

    with transaction.atomic():
        Invoice.objects.create(number=get_next_value('invoice_numbers'))

**The guarantees of django-sequences only apply if you call** ``get_next_value``
**and save its return value to the database within the same transaction!**

Installation
============

Install django-sequences::

    $ pip install django-sequences

Add it to the list of applications in your project's settings::

    INSTALLED_APPS += ['sequences']

Run migrations::

    $ django-admin migrate

API
===

``get_next_value`` generates a gap-less sequence of integer values::

    >>> get_next_value()
    1
    >>> get_next_value()
    2
    >>> get_next_value()
    3

It supports multiple independent sequences::

    >>> get_next_value('cases')
    1
    >>> get_next_value('cases')
    2
    >>> get_next_value('invoices')
    1
    >>> get_next_value('invoices')
    2

The first value defaults to 1. It can be customized::

    >>> get_next_value('customers', initial_value=1000)  # pro growth hacking

The ``initial_value`` parameter only matters when ``get_next_value`` is called
for the first time for a given sequence — assuming the corresponding database
transaction gets committed; as discussed above, if the transaction is rolled
back, the generated value isn't consumed. It's also possible to initialize a
sequence in a data migration and not use ``initial_value`` in actual code.

Database transactions that call ``get_next_value`` for a given sequence are
serialized. In other words, when you call ``get_next_value`` in a database
transaction, other callers which attempt to get a value from the same sequence
will block until the transaction completes, either with a commit or a rollback.
You should keep such transactions short to minimize the impact on performance.

Passing ``nowait=True`` will cause ``get_next_value`` to raise an exception
instead of blocking. This will rarely be useful. Also it doesn't work for the
first call. (Arguably this is a bug. Patches welcome.)

Calls to ``get_next_value`` for different sequences don't interact with one
another.

To sum up, the complete signature of ``get_next_value`` is::

    get_next_value(sequence_name='default', initial_value=1, nowait=False)

Under the hood, it relies on PostgreSQL's transactional integrity to guarantee
that each value will be returned exactly once.

Contributing
============

You can run tests with::

    $ make test

If you'd like to contribute, please open an issue or a pull request on GitHub!

Other databases
===============

``INTEGER PRIMARY KEY AUTOINCREMENT`` fields on SQLite don't have this problem.

The author doesn't know if this problem can happens on MySQL or Oracle. If it
does, then the current implementation of django-sequences should work. If you
test this, please open an issue on GitHub to report your findings. Note that
MySQL won't support the ``nowait`` parameter.

Changelog
=========

1.0
---

* Initial stable release.
