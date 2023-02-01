from typing import List

from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views import View, generic

from core.forms import UserCreateForm
from core.mixins import AiEyeAdminMixin, OwnerFilterViewMixin
from core.models import OpenAIKey, PublicToken, User
from dashboard.forms import CreatePublicTokenForm

UserModel = get_user_model()


class UserCreateView(AiEyeAdminMixin, generic.CreateView):
    template_name = "dashboard/users/create.html"
    form_class = UserCreateForm
    success_url = reverse_lazy("dashboard:users")

    def form_valid(self, form):
        """If the form is valid, save the associated model."""
        self.object: User = form.save()
        # attach new owner to the role `UserGroupType.AIEYE_USERS`
        self.object.set_aieye_users_role()

        return HttpResponseRedirect(self.get_success_url())


class UserListView(AiEyeAdminMixin, generic.ListView):
    model = UserModel
    template_name = "dashboard/users/list.html"

    def get_queryset(self):
        return self.model.aieye_users_objects.all()


class OpenAIKeysBaseView(AiEyeAdminMixin, OwnerFilterViewMixin, View):
    model = OpenAIKey
    fields: List | str = "__all__"
    success_url = reverse_lazy("dashboard:openaikeys")


class OpenAIKeysListView(OpenAIKeysBaseView, generic.ListView):
    template_name = "dashboard/openaikeys/list.html"


class OpenAIKeysCreateView(OpenAIKeysBaseView, generic.CreateView):
    fields = ["key"]
    template_name = "dashboard/openaikeys/create.html"

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.owner = self.request.user
        return super().form_valid(form)


class OpenAIKeysUpdateView(OpenAIKeysBaseView, generic.UpdateView):
    fields = ["key", "is_active"]
    template_name = "dashboard/openaikeys/update.html"


class OpenAIKeysDeleteView(OpenAIKeysBaseView, generic.DeleteView):  # type: ignore[misc]
    template_name = "dashboard/openaikeys/delete.html"


class PublicTokensBaseView(AiEyeAdminMixin, View):
    model = PublicToken
    fields: List | str = "__all__"
    success_url = reverse_lazy("dashboard:publictokens")


class PublicTokensListView(PublicTokensBaseView, generic.ListView):
    template_name = "dashboard/publictokens/list.html"


class PublicTokensCreateView(PublicTokensBaseView, generic.CreateView):
    fields = None
    template_name = "dashboard/publictokens/create.html"
    form_class = CreatePublicTokenForm


class PublicTokensUpdateView(PublicTokensBaseView, generic.UpdateView):
    """View to update an OpenAIKeys linked with current Admin owner"""

    fields = ["key", "is_active"]
    template_name = "dashboard/publictokens/update.html"


class PublicTokensDeleteView(PublicTokensBaseView, generic.DeleteView):  # type: ignore[misc]
    template_name = "dashboard/publictokens/delete.html"
