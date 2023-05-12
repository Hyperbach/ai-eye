from django.test import TestCase

from pipelines.services.functions_manager import FunctionsManager


class TestFunctionsManager(TestCase):
    @classmethod
    def setUpTestData(cls):
        parent_package_name = ".".join(__name__.split(".")[:-1])
        test_files_package_name = f"{parent_package_name}.test_files"
        FunctionsManager.FUNCS_PACKAGE_NAME = test_files_package_name

    def setUp(self):
        self.fm = FunctionsManager()

    def test_is_builtin_function(self):
        self.assertTrue(self.fm.is_builtin_function("builtin_foo"))
        self.assertTrue(self.fm.is_builtin_function("builtin_bar"))

        self.assertFalse(self.fm.is_builtin_function("custom_a_foo"))

    def test_get_func_names(self):
        func_names = self.fm.get_func_names()
        self.assertCountEqual(
            func_names,
            [
                "builtin_foo",
                "builtin_bar",
                "custom_a_foo",
                "custom_a_fred",
                "custom_b_foo",
                "custom_b_fred",
            ],
        )

    def test_get_arity_of_function(self):
        self.assertEqual(2, self.fm.get_arity_of_function("builtin_foo"))

        with self.assertRaises(Exception):
            self.fm.get_arity_of_function("non_existent_fn")

    def test_get_arg_name_by_index(self):
        self.assertEqual("x", self.fm.get_arg_name_by_index("builtin_foo", 0))
        self.assertEqual("y", self.fm.get_arg_name_by_index("builtin_foo", 1))

        with self.assertRaises(Exception):
            self.fm.get_arg_name_by_index("builtin_foo", 2)
            self.fm.get_arg_name_by_index("non_existent_fn", 1)

    def test_call_builtin_function(self):
        result = self.fm.call_builtin_function("builtin_foo", x=1, y=2)
        self.assertEqual("builtin_foo 1 2", result)

        with self.assertRaises(Exception):
            _ = self.fm.call_builtin_function("builtin_foo", z=3)
            _ = self.fm.call_builtin_function("non_existent_fn")
