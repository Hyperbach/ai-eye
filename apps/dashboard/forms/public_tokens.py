from django import forms

from core.models import PublicToken


class PublicTokenForm(forms.ModelForm):
    key = forms.CharField(required=False)
    field_order = ["user", "openaikey", "togetheraikey", "key", "is_active"]

    def save(self, *args, **kwargs):
        key = self.cleaned_data.get("key", None)
        if key:
            self.instance.key = key
        return super().save(*args, **kwargs)

    class Meta:
        model = PublicToken
        fields = "__all__"


class PublicTokenCreateForm(PublicTokenForm):
    class Meta(PublicTokenForm.Meta):
        exclude = ["is_active"]


class PublicTokenUpdateForm(PublicTokenForm):
    pass
