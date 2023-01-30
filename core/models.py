from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser, Group

from core.enums import UserGroupType


class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Users require an email field')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class AiEyeUsersManager(models.Manager):
    def get_queryset(self):
        return (
            super().get_queryset()
            .filter(groups__name=UserGroupType.AIEYE_USERS)
            .order_by('-date_joined')
        )


class User(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()
    aieye_users_objects = AiEyeUsersManager()

    def __str__(self):
        return str(self.email)

    def _is_in_group(self, user_group_type: UserGroupType):
        return self.groups.filter(name__in=[
            user_group_type.name,
        ]).exists()

    @property
    def is_aieye_admin(self):
        return self._is_in_group(UserGroupType.AIEYE_ADMINS)

    @property
    def is_aieye_user(self):
        return self._is_in_group(UserGroupType.AIEYE_USERS)

    def set_aieye_users_role(self):
        group = Group.objects.get(name=UserGroupType.AIEYE_USERS.name)
        self.groups.add(group)
