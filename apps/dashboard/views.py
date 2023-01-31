from typing import List

from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views import View, generic

from core.forms import UserCreateForm
from core.mixins import AiEyeAdminMixin, UserFilterViewMixin
from core.models import OpenAIKey

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


class OpenAIKeysBaseView(AiEyeAdminMixin, UserFilterViewMixin, View):
    model = OpenAIKey
    fields: List[str] = ["__all__"]
    success_url = reverse_lazy("dashboard:openaikeys")


class OpenAIKeysListView(OpenAIKeysBaseView, generic.ListView):
    """View to list all OpenAIKeys linked with current Admin user."""

    template_name = "dashboard/openaikeys/list.html"


class OpenAIKeysCreateView(OpenAIKeysBaseView, generic.CreateView):
    """View to create a new OpenAIKey linked with current Admin user"""

    fields = ["key"]
    template_name = "dashboard/openaikeys/create.html"

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.user = self.request.user
        return super().form_valid(form)


class OpenAIKeysUpdateView(OpenAIKeysBaseView, generic.UpdateView):
    """View to update an OpenAIKeys linked with current Admin user"""

    fields = ["key"]
    template_name = "dashboard/openaikeys/update.html"


class OpenAIKeysDeleteView(OpenAIKeysBaseView, generic.DeleteView):  # type: ignore
    """View to delete an OpenAIKeys linked with current Admin user"""

    template_name = "dashboard/openaikeys/delete.html"
