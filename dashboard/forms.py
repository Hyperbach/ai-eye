from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.forms import ModelForm

UserModel = get_user_model()


class LoginForm(AuthenticationForm):

    def clean(self):
        cleaned_data = super().clean()

        user: UserModel = self.get_user()
        if not user.is_aieye_admin:
            raise ValidationError(
                "Insufficient privileges",
                code="wrong_role",
            )

        return cleaned_data


class CreateUserForm(ModelForm):

    class Meta:
        model = UserModel
        fields = ['email', 'password']
