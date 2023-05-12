from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class AiEyeAdminMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_aieye_admin


class AiEyeAdminOrUserMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_aieye_admin or user.is_aieye_user
