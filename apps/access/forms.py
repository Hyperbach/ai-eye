from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from core.models import User


class LoginForm(AuthenticationForm):
    def clean(self):
        cleaned_data = super().clean()

        user: User = self.get_user()
        if not user.is_aieye_admin:
            raise ValidationError(
                "Insufficient privileges",
                code="wrong_role",
            )

        return cleaned_data
