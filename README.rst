django-sequences
################

The problem
===========

Django's default, implicit primary keys aren't guaranteed to be sequential.

If a transaction inserts a row and then is rolled back, the sequence counter
isn't rolled back for performance reasons, creating a gap in primary keys.

This can cause compliance issues for some use cases such as accounting.

This risk isn't well known. Since most transactions succeed, values look
sequential. Gaps will only be revealed by audits.

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

django-sequences is compatible with Django 1.11 (LTS), 2.0 and 2.1.

Install django-sequences::

    $ pip install django-sequences

Add it to the list of applications in your project's settings::

    INSTALLED_APPS += ['sequences.apps.SequencesConfig']

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

Sequences can loop::

    >>> get_next_value('seconds', initial_value=0, reset_value=60)

When the sequence reaches ``reset_value``, it restarts at ``initial_value``.
In other works, it generates ``reset_value - 2``, ``reset_value - 1``,
``initial_value``, ``initial_value + 1``, etc. In that case, each call to
``get_next_value`` must provide ``initial_value`` and ``reset_value``.

Database transactions that call ``get_next_value`` for a given sequence are
serialized. In other words, when you call ``get_next_value`` in a database
transaction, other callers which attempt to get a value from the same sequence
will block until the transaction completes, either with a commit or a rollback.
You should keep such transactions short to minimize the impact on performance.

(This is why databases default to a faster behavior that may create gaps.)

Passing ``nowait=True`` will cause ``get_next_value`` to raise an exception
instead of blocking. This will rarely be useful. Also it doesn't work for the
first call. (Arguably this is a bug. Patches welcome.)

Calls to ``get_next_value`` for distinct sequences don't interact with one
another.

Finally, passing ``using='...'`` allows selecting the database on which the
current sequence value is stored. When this parameter isn't provided, the
current value is stored in the default database for writing to models of the
``sequences`` application. See "Multiple databases" below for details.

To sum up, the complete signature of ``get_next_value`` is::

    get_next_value(sequence_name='default', initial_value=1, reset_value=None,
                   *, nowait=False, using=None)

Under the hood, it relies on the database's transactional integrity to
guarantee that each value will be returned exactly once.

Contributing
============

You can run tests with::

    $ make test

If you'd like to contribute, please open an issue or a pull request on GitHub!

Database support
================

django-sequences is tested on PostgreSQL, MySQL, Oracle, and SQLite.

MySQL only supports the ``nowait`` parameter when it's MariaDB ≥ 8.0.1.

Applications that will only ever be deployed with an SQLite database don't
need django-sequences because SQLite's ``INTEGER PRIMARY KEY AUTOINCREMENT``
fields are guaranteed to be sequential.

Multiple databases
==================

Since django-sequences relies on the database to guarantee transactional
integrity, the current value for a given sequence must be stored in the same
database as models containing generated values.

In a project that uses multiple databases, you must write a suitable database
router to create tables for the ``sequences`` application on all databases
storing models containing sequential numbers.

Each database has its own namespace: a sequence with the same name stored in
two databases will have independent counters in each database.

Changelog
=========

2.3
---

* Tested on MySQL, SQLite and Oracle.
* Optimized performance on MySQL.

2.2
---

* Optimized performance on PostgreSQL ≥ 9.5.

2.1
---

* Provide looping sequences with ``reset_value``.

2.0
---

* Add support for multiple databases.
* Add translations.
* ``nowait`` becomes keyword-only argument.
* Drop support for Python 2.

1.0
---

* Initial stable release.
