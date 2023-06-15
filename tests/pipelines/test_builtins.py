from datetime import datetime, timedelta

from django.test import TestCase

from funcs.builtins import (
    add,
    append,
    concat,
    divide,
    length,
    lowercase,
    multiply,
    now,
    remove,
    sort,
    subtract,
    uppercase,
)


class BuiltinFunctionTests(TestCase):
    def test_functions(self):
        # Test math functions
        self.assertEqual(add("1", "2"), "3")
        self.assertEqual(subtract("4", "2"), "2")
        self.assertEqual(multiply("3", "3"), "9")
        self.assertEqual(divide("10", "2"), "5.0")

        with self.assertRaises(Exception):
            divide("10", "0")

        # Additional test for adding integer and float strings
        self.assertEqual(add("3", "2.0"), "5.0")
        self.assertEqual(add("2.0", "3"), "5.0")

        # Test string functions
        self.assertEqual(length("hello"), "5")
        self.assertEqual(uppercase("hello"), "HELLO")
        self.assertEqual(lowercase("HELLO"), "hello")
        self.assertEqual(concat("hello", " world"), "hello world")

        # Test list functions
        self.assertEqual(append('["a", "b", "c"]', '"d"'), '["a", "b", "c", "d"]')
        self.assertEqual(remove('["a", "b", "c"]', '"b"'), '["a", "c"]')
        self.assertEqual(sort('["c", "b", "a"]'), '["a", "b", "c"]')

    def test_now_function(self):
        now_result = now()

        # Parse datetime from the result
        result_datetime = datetime.fromisoformat(now_result)

        # Check if the result datetime is close to the current datetime
        # (account for possible small delays between function execution and test)
        self.assertTrue(datetime.now() - result_datetime < timedelta(seconds=1))

    def test_idempotency_and_chainability(self):
        x = '["c", "b", "a"]'
        y = "2"
        z = "3"

        # Check idempotency for sort
        self.assertEqual(sort(x), sort(sort(x)))
        self.assertEqual(sort(lst=x), sort(lst=sort(lst=x)))

        # Check chainability for add
        self.assertEqual(add(y, add(y, z)), "7")
