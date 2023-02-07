from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import OpenAIKey

User = get_user_model()


class Log(models.Model):
    api_type = models.CharField(max_length=50)
    endpoint = models.CharField(max_length=100)
    parameters = models.TextField(db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    api_key = models.ForeignKey(OpenAIKey, on_delete=models.CASCADE)
    response = models.TextField()
    cache_hit = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.api_type} {self.endpoint} {self.parameters}"

    class Meta:
        verbose_name = _("Log")
        verbose_name_plural = _("Logs")
