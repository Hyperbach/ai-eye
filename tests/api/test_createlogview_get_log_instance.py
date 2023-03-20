from collections import OrderedDict

from django.test import TestCase

from api.models import Log
from api.views import CreateLogViewSet

from tests.factories import AiEyeAdminFactory, AiEyeUserFactory, OpenAIKeyFactory


class CreateLogViewSetTestCase(TestCase):
    def setUp(self):
        self.aieye_admin = AiEyeAdminFactory.create()
        self.openaikey = OpenAIKeyFactory.create(owner=self.aieye_admin)
        self.aieye_user = AiEyeUserFactory.create()

        # create a test Log object with some prepared parameters
        self.prepared_parameters = {"b": 2, "a": 1, "c": 3}
        self.log_instance = Log.objects.create(
            endpoint="v1/completions",
            parameters=self.prepared_parameters,
            response="test response",
            cache_hit=False,
            api_key=self.openaikey,
            user=self.aieye_user,
        )

    def test_get_log_instance(self):
        view = CreateLogViewSet()
        view.request = None
        view.format_kwarg = None
        view.kwargs = {"endpoint": "v1/completions"}

        # check that the `get_log_instance` finds an existing record
        log_instance = view.get_log_instance(self.prepared_parameters)
        self.assertEqual(log_instance, self.log_instance)

        # check that an order or parameters doesn't affect the `get_log_instance` behaviour
        sorted_keys = sorted(self.prepared_parameters.keys())
        items_list = [(k, self.prepared_parameters[k]) for k in sorted_keys]
        prepared_parameters_in_another_order = OrderedDict(items_list)
        log_instance = view.get_log_instance(prepared_parameters_in_another_order)
        self.assertEqual(log_instance, self.log_instance)

        # check that the `get_log_instance` doesn't find records with non-existent parameters
        non_existent_prepared_parameters = {"x": "y"}
        log_instance = view.get_log_instance(non_existent_prepared_parameters)
        self.assertIsNone(log_instance)
