from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError


class LoginForm(AuthenticationForm):
    def clean(self):
        cleaned_data = super().clean()

        user = self.get_user()
        if user is None or not (user.is_aieye_admin or user.is_aieye_user):
            raise ValidationError(
                "Insufficient privileges",
                code="wrong_role",
            )

        return cleaned_data
