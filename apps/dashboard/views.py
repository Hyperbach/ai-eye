from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views import generic

from core.forms import UserCreateForm
from core.mixins import AiEyeAdminMixin

UserModel = get_user_model()


class UserCreateView(AiEyeAdminMixin, generic.CreateView):
    template_name = "dashboard/users/create.html"
    form_class = UserCreateForm
    success_url = reverse_lazy("dashboard:users")

    def form_valid(self, form):
        """If the form is valid, save the associated model."""
        self.object = form.save()
        # attach new user to the role `UserGroupType.AIEYE_USERS`
        self.object.set_aieye_users_role()

        return HttpResponseRedirect(self.get_success_url())


class UserListView(AiEyeAdminMixin, generic.ListView):
    model = UserModel
    template_name = "dashboard/users/list.html"

    def get_queryset(self):
        return self.model.aieye_users_objects.all()
