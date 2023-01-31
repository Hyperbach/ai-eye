from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class AiEyeAdminMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return user.is_aieye_admin


class UserFilterViewMixin:
    user_field = "user"

    def get_queryset(self):
        return super().get_queryset().filter(**{self.user_field: self.request.user})
