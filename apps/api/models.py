from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import OpenAIKey

UserModel = get_user_model()


class Log(models.Model):
    api_type = models.CharField(max_length=50)
    endpoint = models.CharField(max_length=100)
    method = models.CharField(max_length=10)
    parameters = models.TextField()
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    api_key = models.ForeignKey(OpenAIKey, on_delete=models.CASCADE)
    response = models.TextField()
    cache_hit = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)
    expire_time = models.DateTimeField()

    def __str__(self):
        return f"{self.api_type} {self.endpoint} {self.method} {self.parameters}"

    class Meta:
        verbose_name = _("Log")
        verbose_name_plural = _("Logs")
