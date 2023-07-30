django-sequences
################

By default, Django gives each model an auto-incrementing integer primary key.
These primary keys look like they generate a continuous sequence of integers.

However, this behavior isn't guaranteed.

If a transaction inserts a row and then is rolled back, the sequence counter
isn't rolled back for performance reasons, creating a gap in primary keys.

Such gaps may happen on all databases natively supported by Django:

* `PostgreSQL <https://www.postgresql.org/docs/current/datatype-numeric.html#DATATYPE-SERIAL>`_
* `MariaDB <https://mariadb.com/kb/en/auto_increment/#missing-values>`_ / MySQL
* `Oracle <https://docs.oracle.com/en/database/oracle/oracle-database/21/sqlrf/CREATE-SEQUENCE.html>`_
* `SQLite <https://sqlite.org/autoinc.html#the_autoincrement_keyword>`_

They may also happen on most databases supported via third-party backends.

This can cause compliance issues for some use cases such as accounting.

This risk isn't well known. Since most transactions succeed, values look
sequential. Gaps will only be revealed by audits.

django-sequences solves this problem with a ``get_next_value`` function
designed to be used as follows:

.. code:: python

    from django.db import transaction
    from sequences import get_next_value
    from invoices.models import Invoice

    with transaction.atomic():
        Invoice.objects.create(number=get_next_value("invoice_numbers"))

Or, if you'd rather use an object-oriented API:

.. code:: python

    from django.db import transaction
    from sequences import Sequence
    from invoices.models import Invoice

    invoice_numbers = Sequence("invoice_numbers")

    with transaction.atomic():
        Invoice.objects.create(number=next(invoice_numbers))

``get_next_value`` relies on the database's transactional integrity to ensure
that each value is returned exactly once. As a consequence, **the guarantees
of django-sequences apply only if you call** ``get_next_value`` **and save its
return value to the database within the same transaction!**

Table of contents
=================

* `Getting started`_
* `API`_
* `Database support`_
* `Multiple databases`_
* `Isolation levels`_
* `Contributing`_
* `Releasing`_
* `Changelog`_

Getting started
===============

django-sequences is tested with Django 3.2 (LTS), 4.0, 4.1, and 4.2.
It is also tested with all database backends built-in to Django: MySQL/MariaDB,
Oracle, PostgreSQL and SQLite.

It is released under the BSD license, like Django itself.

Install django-sequences:

.. code:: shell-session

    $ pip install django-sequences

Add it to the list of applications in your project's settings:

.. code:: python

    INSTALLED_APPS = [
        ...,
        "sequences.apps.SequencesConfig",
        ...
    ]

Run migrations:

.. code:: shell-session

    $ django-admin migrate

API
===

``get_next_value``
------------------

.. code:: pycon

    >>> from sequences import get_next_value

This function generates a gapless sequence of integer values:

.. code:: pycon

    >>> get_next_value()
    1
    >>> get_next_value()
    2
    >>> get_next_value()
    3

It supports multiple independent sequences:

.. code:: pycon

    >>> get_next_value("cases")
    1
    >>> get_next_value("cases")
    2
    >>> get_next_value("invoices")
    1
    >>> get_next_value("invoices")
    2

The first value defaults to 1. It can be customized:

.. code:: pycon

    >>> get_next_value("customers", initial_value=1000)  # pro growth hacking

The ``initial_value`` parameter only matters when ``get_next_value`` is called
for the first time for a given sequence — assuming the corresponding database
transaction gets committed; as discussed above, if the transaction is rolled
back, the generated value isn't consumed. It's also possible to initialize a
sequence in a data migration and not use ``initial_value`` in actual code.

Sequences can loop:

.. code:: pycon

    >>> get_next_value("seconds", initial_value=0, reset_value=60)

When the sequence reaches ``reset_value``, it restarts at ``initial_value``.
In other words, it generates ``reset_value - 2``, ``reset_value - 1``,
``initial_value``, ``initial_value + 1``, etc. In that case, each call to
``get_next_value`` must provide ``initial_value`` when it isn't the default
and ``reset_value``.

**Database transactions that call** ``get_next_value`` **for a given sequence
are serialized.** As a consequence, when you call ``get_next_value`` in a
database transaction, other callers trying to get a value from the same
sequence block until the transaction completes, either with a commit or a
rollback. You should keep such transactions short to minimize the impact on
performance.

This is why databases default to a faster behavior that may create gaps.

Passing ``nowait=True`` makes ``get_next_value`` raise an exception instead of
blocking in this scenario. This is rarely useful. Also it doesn't work for the
first call. (This is a bug but it's harmless and hard to fix.)

Calls to ``get_next_value`` for distinct sequences don't interact with one
another.

Finally, passing ``using="..."`` allows selecting the database on which the
current sequence value is stored. When this parameter isn't provided, it
defaults to the default database for writing models of the ``sequences``
application. See `Multiple databases`_ for details.

To sum up, the complete signature of ``get_next_value`` is:

.. code:: python

    get_next_value(
        sequence_name="default",
        initial_value=1,
        reset_value=None,
        *,
        nowait=False,
        using=None,
    )

``get_last_value``
------------------

.. code:: pycon

    >>> from sequences import get_last_value

This function returns the last value generated by a sequence:

.. code:: pycon

    >>> get_last_value()
    None
    >>> get_next_value()
    1
    >>> get_last_value()
    1
    >>> get_next_value()
    2
    >>> get_last_value()
    2

If the sequence hasn't generated a value yet, ``get_last_value`` returns
``None``.

It supports independent sequences like ``get_next_value``:

.. code:: pycon

    >>> get_next_value("cases")
    1
    >>> get_last_value("cases")
    1
    >>> get_next_value("invoices")
    1
    >>> get_last_value("invoices")
    1

It accepts ``using="..."`` for selecting the database on which the current
sequence value is stored, defaulting to the default database for reading
models of the ``sequences`` application.

The complete signature of ``get_last_value`` is:

.. code:: python

    get_last_value(
        sequence_name="default",
        *,
        using=None,
    )

``get_last_value`` **is a convenient and fast way to tell how many values a
sequence generated but it makes no guarantees.** Concurrent calls to
``get_next_value`` may produce unexpected results of ``get_last_value``.

``Sequence``
------------

.. code:: pycon

    >>> from sequences import Sequence

(not to be confused with ``sequences.models.Sequence``, a private API)

This class stores parameters for a sequence and provides ``get_next_value``
and ``get_last_value`` methods:

.. code:: pycon

    >>> claim_ids = Sequence("claims")
    >>> claim_ids.get_next_value()
    1
    >>> claim_ids.get_next_value()
    2
    >>> claim_ids.get_last_value()
    2

This reduces the risk of errors when the same sequence is used in multiple
places.

Instances of ``Sequence`` are also infinite iterators:

.. code:: pycon

    >>> next(claim_ids)
    3
    >>> next(claim_ids)
    4

The complete API is:

.. code:: python

    Sequence(
        sequence_name="default",
        initial_value=1,
        reset_value=None,
        *,
        using=None,
    )

    Sequence.get_next_value(
        self,
        *,
        nowait=False,
    )

    Sequence.get_last_value(
        self,
    )

All parameters have the same meaning as in the ``get_next_value`` and
``get_last_value`` functions.

Examples
========

Per-date sequences
------------------

If you want independent sequences per day, month, or year, use the appropriate
date fragment in the sequence name. For example:

.. code:: python

    from django.utils import timezone
    from sequences import get_next_value

    # Per-day sequence
    get_next_value(f"books-{timezone.now().date().isoformat()}")
    # Per-year sequence
    get_next_value(f"prototocol-{timezone.now().year}")

The above calls will result in separate sequences like ``books-2023-03-15``
or ``protocol-2022``, respectively.

Database support
================

django-sequences is tested on PostgreSQL, MariaDB / MySQL, Oracle, and SQLite.

MySQL only supports the ``nowait`` parameter from version 8.0.1.
MariaDB only supports ``nowait`` from version 10.3.

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

Isolation levels
================

Since django-sequences relies on the database's transactional integrity, using
a non-default transaction isolation level requires special care.

* **read uncommitted:** django-sequences cannot work at this isolation level.

  Indeed, concurrent transactions can create gaps, as in this scenario:

  * Transaction A reads N and writes N + 1;
  * Transaction B reads N + 1 (dirty read) and writes N + 2;
  * Transaction A is rolled back;
  * Transaction B is committed;
  * N + 1 is a gap.

  The read uncommitted isolation level doesn't provide sufficient guarantees.
  It will never be supported.

* **read committed:** django-sequences works best at this isolation level,
  like Django itself.

* **repeatable read:** django-sequences also works at this isolation level,
  provided your code handles serialization failures and retries transactions.

  This requirement isn't specific to django-sequences. It's generally needed
  when running at the repeatable read isolation level.

  Here's a scenario where only one of two concurrent transactions can
  complete on PostgreSQL:

  * Transaction A reads N and writes N + 1;
  * Transaction B attemps to read; it must wait until transaction A completes;
  * Transaction A is committed;
  * Transaction B is aborted.

  On PostgreSQL, serialization failures are reported as: ``OperationalError:
  could not serialize access due to concurrent update``.

  On MySQL, they result in: ``OperationalError: (1213, 'Deadlock found when
  trying to get lock; try restarting transaction')``.

  Concurrent transactions initializing the same sequence are also vulnerable,
  although that's hardly ever a problem in practice.

  On PostgreSQL, this manifests as ``IntegrityError: duplicate key value
  violates unique constraint "sequences_sequence_pkey"``.

* **serializable:** the situation is identical to the repeatable read level.

  SQLite always runs at the serializable isolation level. Serialization
  failures result in: ``OperationalError: database is locked``.

Contributing
============

Prepare a development environment:

* Install Poetry_.
* Run ``poetry install``.
* Run ``poetry shell`` to load the development environment.

Prepare testing databases:

* Install PostgreSQL, MariaDB, and Oracle.
* Create a database called ``sequences``, owned by a user called ``sequences``
  with password ``sequences``, with permissions to create a ``test_sequences``
  test database. You may override these values with environment variables; see
  ``tests/*_settings.py`` for details.

Make changes:

* Make changes to the code, tests, or docs.
* Run ``make style`` and fix any flake8 violations.
* Run ``make test`` to run the set suite on all databases.

Iterate until you're happy.

Check quality and submit your changes:

* Install tox_.
* Run ``tox`` to test on all Python and Django versions and all databases.
* Submit a pull request.

.. _Poetry: https://python-poetry.org/
.. _tox: https://tox.readthedocs.io/

Releasing
=========

Increment version number X.Y in ``pyproject.toml``.

Commit, tag, and push the change:

.. code:: shell-session

    $ git commit -m "Bump version number".
    $ git tag X.Y
    $ git push
    $ git push --tags

Build and publish the new version:

.. code:: shell-session

    $ poetry build
    $ poetry publish

Changelog
=========

2.8
---

* No significant changes.

2.7
---

* Sequence values can go up to ``2 ** 63 - 1`` instead of ``2 ** 31 - 1``
  previously. The exact limit depends on the database backend.

  Migration ``0002_alter_sequence_last.py`` changes the field storing sequence
  values from ``PositiveIntegerField`` to ``PositiveBigIntegerField``. Running
  it requires an exclusive lock on the table, which prevents other operations,
  including reads.

  If you have many distinct sequences, e.g. if you create one sequence per user
  and you have millions of users, review how the migration will affect your app
  before running it or skip it with ``migrate --fake``.

2.6
---

* Improve documentation.

2.5
---

* Fix Japanese and Turkish translations.
* Restore compatibility with Python 3.5.
* Support relabeling the ``sequences`` app with a custom ``AppConfig``.

2.4
---

* Add the ``get_last_value`` function.
* Add the ``Sequence`` class.

2.3
---

* Optimize performance on MySQL.
* Test on MySQL, SQLite and Oracle.

2.2
---

* Optimize performance on PostgreSQL ≥ 9.5.

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
