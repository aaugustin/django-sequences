import threading
import time

from django.db import OperationalError, connection, transaction
from django.test import TestCase, TransactionTestCase

from . import get_next_value


class SingleConnectionTestsMixin(object):

    def test_defaults(self):
        self.assertEqual(get_next_value(), 1)
        self.assertEqual(get_next_value(), 2)
        self.assertEqual(get_next_value(), 3)

    def test_sequence_name(self):
        self.assertEqual(get_next_value('cases'), 1)
        self.assertEqual(get_next_value('cases'), 2)
        self.assertEqual(get_next_value('invoices'), 1)
        self.assertEqual(get_next_value('invoices'), 2)

    def test_initial_value(self):
        self.assertEqual(get_next_value('customers', initial_value=1000), 1000)
        self.assertEqual(get_next_value('customers', initial_value=1000), 1001)
        self.assertEqual(get_next_value('customers'), 1002)

    def test_reset_value(self):
        self.assertEqual(get_next_value('reference', 0, reset_value=2), 0)
        self.assertEqual(get_next_value('reference', 0, reset_value=2), 1)
        self.assertEqual(get_next_value('reference', 0, 2), 0)
        self.assertEqual(get_next_value('reference', 0, 2), 1)

    def test_reset_value_smaller_than_initial_value(self):
        with self.assertRaises(AssertionError):
            get_next_value('error', initial_value=1, reset_value=1)


class SingleConnectionInAutocommitTests(SingleConnectionTestsMixin,
                                        TransactionTestCase):
    pass


class SingleConnectionInTransactionTests(SingleConnectionTestsMixin,
                                         TestCase):
    pass


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
            with transaction.atomic():
                output.append(('one', 'begin'))
                value = get_next_value()
                output.append(('one', value))
                time.sleep(0.2)
                output.append(('one', 'commit'))
            connection.close()

        def two(output):
            time.sleep(0.1)
            with transaction.atomic():
                output.append(('two', 'begin'))
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
            with transaction.atomic():
                output.append(('one', 'begin'))
                value = get_next_value()
                output.append(('one', value))
                time.sleep(0.2)
                output.append(('one', 'commit'))
            connection.close()

        def two(output):
            time.sleep(0.1)
            with transaction.atomic():
                output.append(('two', 'begin'))
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
            with transaction.atomic():
                output.append(('one', 'begin'))
                value = get_next_value()
                output.append(('one', value))
                time.sleep(0.2)
                transaction.set_rollback(True)
                output.append(('one', 'rollback'))
            connection.close()

        def two(output):
            time.sleep(0.1)
            with transaction.atomic():
                output.append(('two', 'begin'))
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
            with transaction.atomic():
                output.append(('one', 'begin'))
                value = get_next_value()
                output.append(('one', value))
                time.sleep(0.2)
                transaction.set_rollback(True)
                output.append(('one', 'rollback'))
            connection.close()

        def two(output):
            time.sleep(0.1)
            with transaction.atomic():
                output.append(('two', 'begin'))
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

    def test_first_access_nowait(self):

        def one(output):
            with transaction.atomic():
                value = get_next_value()
                output.append(('one', value))
                time.sleep(0.5)
            connection.close()

        # One might expect an OperationalError here, but PostgreSQL doesn't
        # appear to report an error in this case.

        def two(output):
            time.sleep(0.1)
            with transaction.atomic():
                value = get_next_value(nowait=True)
                output.append(('two', value))
            connection.close()

        expected = [
            ('one', 1),
            ('two', 2),
        ]

        self.assertSequence(one, two, expected)

    def test_later_access_nowait(self):

        get_next_value()

        def one(output):
            with transaction.atomic():
                value = get_next_value()
                output.append(('one', value))
                time.sleep(0.5)
            connection.close()

        def two(output):
            time.sleep(0.1)
            with self.assertRaises(OperationalError):
                with transaction.atomic():
                    value = get_next_value(nowait=True)
                    output.append(('two', value))   # shouldn't be reached
            output.append(('two', 'exc'))
            connection.close()

        expected = [
            ('one', 2),
            ('two', 'exc'),
        ]

        self.assertSequence(one, two, expected)

    def test_first_access_to_different_sequences(self):

        def one(output):
            with transaction.atomic():
                output.append(('one', 'begin'))
                value = get_next_value('one')
                output.append(('one', value))
                time.sleep(0.2)
                output.append(('one', 'commit'))
            connection.close()

        def two(output):
            time.sleep(0.1)
            with transaction.atomic():
                output.append(('two', 'begin'))
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
            with transaction.atomic():
                output.append(('one', 'begin'))
                value = get_next_value('one')
                output.append(('one', value))
                time.sleep(0.2)
                output.append(('one', 'commit'))
            connection.close()

        def two(output):
            time.sleep(0.1)
            with transaction.atomic():
                output.append(('two', 'begin'))
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
