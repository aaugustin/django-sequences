import itertools
import threading
import time
import unittest

from django.db import DatabaseError, connection, transaction
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature

from . import Sequence, get_last_value, get_next_value


class SingleConnectionTestsMixin(object):

    def test_functions_defaults(self):
        self.assertEqual(get_last_value(), None)
        self.assertEqual(get_next_value(), 1)
        self.assertEqual(get_last_value(), 1)
        self.assertEqual(get_next_value(), 2)
        self.assertEqual(get_last_value(), 2)
        self.assertEqual(get_next_value(), 3)

    def test_functions_sequence_name(self):
        self.assertEqual(get_last_value('cases'), None)
        self.assertEqual(get_next_value('cases'), 1)
        self.assertEqual(get_last_value('cases'), 1)
        self.assertEqual(get_next_value('cases'), 2)
        self.assertEqual(get_last_value('invoices'), None)
        self.assertEqual(get_next_value('invoices'), 1)
        self.assertEqual(get_last_value('invoices'), 1)
        self.assertEqual(get_next_value('invoices'), 2)

    def test_functions_initial_value(self):
        self.assertEqual(get_next_value('customers', initial_value=1000), 1000)
        self.assertEqual(get_next_value('customers', initial_value=1000), 1001)
        self.assertEqual(get_next_value('customers'), 1002)
        self.assertEqual(get_next_value('customers'), 1003)

    def test_functions_reset_value(self):
        self.assertEqual(get_next_value('reference', reset_value=3), 1)
        self.assertEqual(get_next_value('reference', reset_value=3), 2)
        self.assertEqual(get_next_value('reference', reset_value=3), 1)
        self.assertEqual(get_next_value('reference', reset_value=3), 2)
        self.assertEqual(get_next_value('reference', 1, 3), 1)
        self.assertEqual(get_next_value('reference', 1, 3), 2)
        self.assertEqual(get_next_value('reference', 1, 3), 1)
        self.assertEqual(get_next_value('reference', 1, 3), 2)

    def test_functions_reset_value_smaller_than_initial_value(self):
        with self.assertRaises(AssertionError):
            get_next_value('error', initial_value=1, reset_value=1)

    def test_class_defaults(self):
        seq = Sequence()
        self.assertEqual(seq.get_last_value(), None)
        self.assertEqual(seq.get_next_value(), 1)
        self.assertEqual(seq.get_last_value(), 1)
        self.assertEqual(seq.get_next_value(), 2)
        self.assertEqual(seq.get_last_value(), 2)
        self.assertEqual(seq.get_next_value(), 3)

    def test_class_iter(self):
        seq = Sequence(initial_value=0)
        self.assertEqual(list(itertools.islice(seq, 5)), list(range(5)))

    def test_class_next(self):
        seq = Sequence(initial_value=0)
        for value in range(5):
            self.assertEqual(next(seq), value)

    def test_class_sequence_name(self):
        cases_seq = Sequence('cases')
        invoices_seq = Sequence('invoices')
        self.assertEqual(cases_seq.get_last_value(), None)
        self.assertEqual(cases_seq.get_next_value(), 1)
        self.assertEqual(cases_seq.get_last_value(), 1)
        self.assertEqual(cases_seq.get_next_value(), 2)
        self.assertEqual(invoices_seq.get_last_value(), None)
        self.assertEqual(invoices_seq.get_next_value(), 1)
        self.assertEqual(invoices_seq.get_last_value(), 1)
        self.assertEqual(invoices_seq.get_next_value(), 2)

    def test_class_initial_value(self):
        customers_seq = Sequence('customers', initial_value=1000)
        self.assertEqual(customers_seq.get_next_value(), 1000)
        self.assertEqual(customers_seq.get_next_value(), 1001)

    def test_class_reset_value(self):
        reference_seq = Sequence('reference', reset_value=3)
        self.assertEqual(reference_seq.get_next_value(), 1)
        self.assertEqual(reference_seq.get_next_value(), 2)
        self.assertEqual(reference_seq.get_next_value(), 1)
        self.assertEqual(reference_seq.get_next_value(), 2)

    def test_class_reset_value_smaller_than_initial_value(self):
        with self.assertRaises(AssertionError):
            Sequence('error', initial_value=1, reset_value=1)


class SingleConnectionInAutocommitTests(SingleConnectionTestsMixin,
                                        TransactionTestCase):
    pass


class SingleConnectionInTransactionTests(SingleConnectionTestsMixin,
                                         TestCase):
    pass


@unittest.skipIf(
    connection.vendor == 'sqlite',
    "SQLite doesn't support concurrent writes"
)
class ConcurrencyTests(TransactionTestCase):

    def assertSequence(self, one, two, expected):
        actual = []
        thread_one = threading.Thread(target=one, args=(actual,))
        thread_two = threading.Thread(target=two, args=(actual,))
        thread_one.start()
        thread_two.start()
        thread_one.join(timeout=1)
        thread_two.join(timeout=1)
        self.assertEqual(actual, expected)

    def test_first_access_with_commit(self):

        def one(output):
            output.append(('one', 'begin'))
            with transaction.atomic():
                value = get_next_value()
                output.append(('one', value))
                time.sleep(0.2)
                output.append(('one', 'commit'))
            connection.close()

        def two(output):
            time.sleep(0.1)
            output.append(('two', 'begin'))
            with transaction.atomic():
                value = get_next_value()
                output.append(('two', value))
                output.append(('two', 'commit'))
            connection.close()

        expected = [
            ('one', 'begin'),
            ('one', 1),
            ('two', 'begin'),
            ('one', 'commit'),
            ('two', 2),
            ('two', 'commit'),
        ]

        self.assertSequence(one, two, expected)

    def test_later_access_with_commit(self):

        get_next_value()

        def one(output):
            output.append(('one', 'begin'))
            with transaction.atomic():
                value = get_next_value()
                output.append(('one', value))
                time.sleep(0.2)
                output.append(('one', 'commit'))
            connection.close()

        def two(output):
            time.sleep(0.1)
            output.append(('two', 'begin'))
            with transaction.atomic():
                value = get_next_value()
                output.append(('two', value))
                output.append(('two', 'commit'))
            connection.close()

        expected = [
            ('one', 'begin'),
            ('one', 2),
            ('two', 'begin'),
            ('one', 'commit'),
            ('two', 3),
            ('two', 'commit'),
        ]

        self.assertSequence(one, two, expected)

    def test_first_access_with_rollback(self):

        def one(output):
            output.append(('one', 'begin'))
            with transaction.atomic():
                value = get_next_value()
                output.append(('one', value))
                time.sleep(0.2)
                transaction.set_rollback(True)
                output.append(('one', 'rollback'))
            connection.close()

        def two(output):
            time.sleep(0.1)
            output.append(('two', 'begin'))
            with transaction.atomic():
                value = get_next_value()
                output.append(('two', value))
                output.append(('two', 'commit'))
            connection.close()

        expected = [
            ('one', 'begin'),
            ('one', 1),
            ('two', 'begin'),
            ('one', 'rollback'),
            ('two', 1),
            ('two', 'commit'),
        ]

        self.assertSequence(one, two, expected)

    def test_later_access_with_rollback(self):

        get_next_value()

        def one(output):
            output.append(('one', 'begin'))
            with transaction.atomic():
                value = get_next_value()
                output.append(('one', value))
                time.sleep(0.2)
                transaction.set_rollback(True)
                output.append(('one', 'rollback'))
            connection.close()

        def two(output):
            time.sleep(0.1)
            output.append(('two', 'begin'))
            with transaction.atomic():
                value = get_next_value()
                output.append(('two', value))
                output.append(('two', 'commit'))
            connection.close()

        expected = [
            ('one', 'begin'),
            ('one', 2),
            ('two', 'begin'),
            ('one', 'rollback'),
            ('two', 2),
            ('two', 'commit'),
        ]

        self.assertSequence(one, two, expected)

    @skipUnlessDBFeature('has_select_for_update_nowait')
    def test_first_access_nowait(self):

        def one(output):
            output.append(('one', 'begin'))
            with transaction.atomic():
                value = get_next_value()
                output.append(('one', value))
                time.sleep(0.5)
                output.append(('one', 'commit'))
            connection.close()

        # SELECT ... FOR UPDATE doesn't select any row to lock. In this case,
        # behavior depends on the database (and perhaps the isolation level).

        if connection.vendor != 'mysql':

            def two(output):
                time.sleep(0.1)
                with transaction.atomic():
                    output.append(('two', 'begin'))
                    value = get_next_value(nowait=True)
                    output.append(('two', value))
                    output.append(('two', 'commit'))
                connection.close()

            expected = [
                ('one', 'begin'),
                ('one', 1),
                ('two', 'begin'),
                ('one', 'commit'),
                ('two', 2),
                ('two', 'commit'),
            ]

        else:

            def two(output):
                time.sleep(0.1)
                with self.assertRaises(DatabaseError):
                    with transaction.atomic():
                        output.append(('two', 'begin'))
                        value = get_next_value(nowait=True)
                        output.append(('two', value))   # shouldn't be reached
                connection.close()

            expected = [
                ('one', 'begin'),
                ('one', 1),
                ('two', 'begin'),
                ('one', 'commit'),
            ]

        self.assertSequence(one, two, expected)

    @skipUnlessDBFeature('has_select_for_update_nowait')
    def test_later_access_nowait(self):

        get_next_value()

        def one(output):
            output.append(('one', 'begin'))
            with transaction.atomic():
                value = get_next_value()
                output.append(('one', value))
                time.sleep(0.5)
                output.append(('one', 'commit'))
            connection.close()

        def two(output):
            time.sleep(0.1)
            output.append(('two', 'begin'))
            with self.assertRaises(DatabaseError):
                with transaction.atomic():
                    value = get_next_value(nowait=True)
                    output.append(('two', value))   # shouldn't be reached
            connection.close()

        expected = [
            ('one', 'begin'),
            ('one', 2),
            ('two', 'begin'),
            ('one', 'commit'),
        ]

        self.assertSequence(one, two, expected)

    def test_first_access_to_different_sequences(self):

        def one(output):
            output.append(('one', 'begin'))
            with transaction.atomic():
                value = get_next_value('one')
                output.append(('one', value))
                time.sleep(0.2)
                output.append(('one', 'commit'))
            connection.close()

        def two(output):
            time.sleep(0.1)
            output.append(('two', 'begin'))
            with transaction.atomic():
                value = get_next_value('two')
                output.append(('two', value))
                output.append(('two', 'commit'))
            connection.close()

        expected = [
            ('one', 'begin'),
            ('one', 1),
            ('two', 'begin'),
            ('two', 1),
            ('two', 'commit'),
            ('one', 'commit'),
        ]

        self.assertSequence(one, two, expected)

    def test_later_access_to_different_sequences(self):

        get_next_value('one')
        get_next_value('two')

        def one(output):
            output.append(('one', 'begin'))
            with transaction.atomic():
                value = get_next_value('one')
                output.append(('one', value))
                time.sleep(0.2)
                output.append(('one', 'commit'))
            connection.close()

        def two(output):
            time.sleep(0.1)
            output.append(('two', 'begin'))
            with transaction.atomic():
                value = get_next_value('two')
                output.append(('two', value))
                output.append(('two', 'commit'))
            connection.close()

        expected = [
            ('one', 'begin'),
            ('one', 2),
            ('two', 'begin'),
            ('two', 2),
            ('two', 'commit'),
            ('one', 'commit'),
        ]

        self.assertSequence(one, two, expected)
