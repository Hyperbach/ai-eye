from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

UserModel = get_user_model()


class AiEyeAdminMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        user: UserModel = self.request.user
        return user.is_aieye_admin
