from django.test import TestCase

from pipelines.services.functions_manager import FunctionsManager


class TestFunctionsManager(TestCase):
    def setUp(self):
        parent_package_name = ".".join(__name__.split(".")[:-1])
        test_files_package_name = f"{parent_package_name}.test_files"

        FunctionsManager.FUNCS_PACKAGE_NAME = test_files_package_name
        FunctionsManager._instance = None

    def test_is_builtin_function(self):
        fm = FunctionsManager()
        self.assertTrue(fm.is_builtin_function("builtin_foo"))
        self.assertTrue(fm.is_builtin_function("builtin_bar"))

        self.assertFalse(fm.is_builtin_function("smth"))

    def test_user_module_functions(self):
        fm = FunctionsManager()
        func_names = fm.get_func_names()
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
