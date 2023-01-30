from django.db import models


class UserGroupType(models.TextChoices):
    AIEYE_ADMINS = "AIEYE_ADMINS", "Admins"
    AIEYE_USERS = "AIEYE_USERS", "Users"
