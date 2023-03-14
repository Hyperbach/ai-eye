from django.db import models


class LogMessage(models.Model):
    LEVEL_CHOICES = (
        ("debug", "Debug"),
        ("info", "Info"),
        ("warning", "Warning"),
        ("error", "Error"),
        ("critical", "Critical"),
    )

    level = models.CharField(max_length=10, choices=LEVEL_CHOICES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    meta_info = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.level}: {self.message}"
