from typing import List

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import Group, PermissionsMixin
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

import rest_framework.authtoken.models

from .enums import UserGroupType


class TimestampMixin(models.Model):
    date_created = models.DateTimeField(_("date created"), auto_now_add=True)
    date_updated = models.DateTimeField(_("date updated"), auto_now=True)

    class Meta:
        abstract = True


class IsActiveMixin(models.Model):
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this object should be treated as active. "
            "Unselect this instead of deleting objects."
        ),
    )

    class Meta:
        abstract = True


class CustomUserManager(BaseUserManager):
    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users require an email field")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class AiEyeUsersManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(groups__name=UserGroupType.AIEYE_USERS)


class User(AbstractBaseUser, PermissionsMixin, TimestampMixin, IsActiveMixin):  # type: ignore[misc]

    email = models.EmailField(_("email address"), unique=True)
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: List[str] = []

    objects = CustomUserManager()
    aieye_users_objects = AiEyeUsersManager()

    def __str__(self):
        return str(self.email)

    def _is_in_group(self, user_group_type: UserGroupType):
        return self.groups.filter(
            name__in=[
                user_group_type.name,
            ]
        ).exists()

    @property
    def is_aieye_admin(self):
        return self._is_in_group(UserGroupType.AIEYE_ADMINS)

    @property
    def is_aieye_user(self):
        return self._is_in_group(UserGroupType.AIEYE_USERS)

    def set_aieye_users_role(self):
        group = Group.objects.get(name=UserGroupType.AIEYE_USERS.name)
        self.groups.add(group)


UserModel = get_user_model()


class OpenAIKey(TimestampMixin, IsActiveMixin):
    # an owner (AIEYE_ADMIN user), who issued this OpenAIKey. One owner can issue several OpenAIKeys
    owner = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        help_text=_(
            "Designates a user who issued this OpenAI key. It's supposed to be an AIEYE_ADMIN user"
        ),
    )
    key = models.CharField(max_length=255, db_index=True, unique=True)
    users = models.ManyToManyField(
        UserModel, related_name="openaikeys", through="PublicToken"
    )

    def __str__(self):
        return self.key

    class Meta:
        verbose_name = _("OpenAI key")
        verbose_name_plural = _("OpenAI keys")


class PublicToken(rest_framework.authtoken.models.Token, TimestampMixin, IsActiveMixin):
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    openaikey = models.ForeignKey(OpenAIKey, on_delete=models.CASCADE)
    key = models.CharField(
        _("Key"),
        max_length=40,
        db_index=True,
        unique=True,
        validators=[MinLengthValidator(40), MaxLengthValidator(40)],
    )
    created = None

    def __str__(self):
        return self.key

    class Meta:
        unique_together = (("user", "openaikey"),)
        verbose_name = _("Public token")
        verbose_name_plural = _("Public tokens")
