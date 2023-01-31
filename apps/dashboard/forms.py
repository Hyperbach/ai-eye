from django.contrib.auth import get_user_model
from django.forms import ModelForm

UserModel = get_user_model()


class CreateUserForm(ModelForm):
    class Meta:
        model = UserModel
        fields = ["email", "password"]
