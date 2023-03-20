from django.contrib.auth import get_user_model

import factory
from core.enums import UserGroupType
from core.models import OpenAIKey, PublicToken

from tests import AIEYE_ADMIN_PASSWORD, AIEYE_USER_PASSWORD

User = get_user_model()


class PublicTokenFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PublicToken

    key = factory.Sequence(lambda n: "publictoken%d" % n)


class OpenAIKeyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OpenAIKey

    owner = factory.Iterator(
        User.objects.filter(groups__name=UserGroupType.AIEYE_ADMINS)
    )
    key = factory.Sequence(lambda n: "openaikey%d" % n)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Faker("email")


class AiEyeUserFactory(UserFactory):
    password = factory.PostGenerationMethodCall("set_password", AIEYE_USER_PASSWORD)

    @factory.post_generation
    def add_to_aieye_users_group(self, create, extracted, **kwargs):
        if not create:
            return
        self.set_aieye_users_role()


class AiEyeAdminFactory(UserFactory):
    password = factory.PostGenerationMethodCall("set_password", AIEYE_ADMIN_PASSWORD)

    @factory.post_generation
    def add_to_aieye_admin_group(self, create, extracted, **kwargs):
        if not create:
            return
        self.set_aieye_admin_role()
