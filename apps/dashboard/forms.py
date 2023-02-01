from django import forms
from django.contrib.auth import get_user_model

from core.models import PublicToken

UserModel = get_user_model()


class CreateUserForm(forms.ModelForm):
    class Meta:
        model = UserModel
        fields = ["email", "password"]


class CreatePublicTokenForm(forms.ModelForm):
    key = forms.CharField(required=False)

    def save(self, *args, **kwargs):
        key = self.cleaned_data.get("key", None)
        if key:
            self.instance.key = key
        return super().save(*args, **kwargs)

    class Meta:
        model = PublicToken
        exclude = ["key", "is_active"]
