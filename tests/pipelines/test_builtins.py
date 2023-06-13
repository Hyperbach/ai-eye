import json
from django.test import TestCase
from funcs.builtins import add, subtract, multiply, divide, length, append, remove, sort, uppercase, lowercase, concat, now
from datetime import datetime, timedelta


class BuiltinFunctionTests(TestCase):

    def test_functions(self):
        # Test math functions
        self.assertEqual(add("1", "2"), '{"result": 3.0}')
        self.assertEqual(subtract("4", "2"), '{"result": 2.0}')
        self.assertEqual(multiply("3", "3"), '{"result": 9.0}')
        self.assertEqual(divide("10", "2"), '{"result": 5.0}')
        self.assertEqual(divide("10", "0"), '{"error": "Division by zero"}')

        # Test string functions
        self.assertEqual(length("hello"), '{"result": 5}')
        self.assertEqual(uppercase("hello"), '{"result": "HELLO"}')
        self.assertEqual(lowercase("HELLO"), '{"result": "hello"}')
        self.assertEqual(concat("hello", " world"), '{"result": "hello world"}')

        # Test list functions
        self.assertEqual(append('["a", "b", "c"]', '"d"'), '{"result": ["a", "b", "c", "d"]}')
        self.assertEqual(remove('["a", "b", "c"]', '"b"'), '{"result": ["a", "c"]}')
        self.assertEqual(sort('["c", "b", "a"]'), '{"result": ["a", "b", "c"]}')

    def test_now_function(self):
        now_result = now()
        now_json = json.loads(now_result)

        # Check if result key exists in the response
        self.assertIn("result", now_json)

        # Parse datetime from the result
        result_datetime = datetime.fromisoformat(now_json["result"])

        # Check if the result datetime is close to the current datetime
        # (account for possible small delays between function execution and test)
        self.assertTrue(datetime.now() - result_datetime < timedelta(seconds=1))
