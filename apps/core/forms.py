from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.forms import EmailField

UserModel = get_user_model()


class UserCreateForm(UserCreationForm):
    class Meta:
        model = UserModel
        fields = ("email", "first_name", "last_name")
        field_classes = {"email": EmailField}


class LoginForm(AuthenticationForm):
    def clean(self):
        cleaned_data = super().clean()

        user = self.get_user()
        if not user.is_aieye_admin:
            raise ValidationError(
                "Insufficient privileges",
                code="wrong_role",
            )

        return cleaned_data
