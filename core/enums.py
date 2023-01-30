from enum import Enum

from django.db import models


# class UsersGroupType(Enum):
#
#     AIEYE_ADMINS = "AIEYE_ADMINS",
#     AIEYE_USERS = "AIEYE_USERS",


class UserGroupType(models.TextChoices):
    AIEYE_ADMINS = "AIEYE_ADMINS", "Admins"
    AIEYE_USERS = "AIEYE_USERS", "Users"

