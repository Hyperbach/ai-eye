from django.contrib.auth import get_user_model
from django.urls import reverse_lazy
from django.views import View, generic

from core.forms import UserCreateForm
from core.mixins import AiEyeAdminMixin
from core.models import OpenAIKey, PublicToken
from dashboard.forms import PublicTokenCreateForm, PublicTokenUpdateForm

User = get_user_model()


class UserCreateView(AiEyeAdminMixin, generic.CreateView):
    template_name = "dashboard/users/create.html"
    form_class = UserCreateForm
    success_url = reverse_lazy("dashboard:users")


class UserListView(AiEyeAdminMixin, generic.ListView):
    template_name = "dashboard/users/list.html"

    def get_queryset(self):
        return User.aieye_users_objects.order_by("-date_created")


class OpenAIKeysBaseView(AiEyeAdminMixin, View):
    success_url = reverse_lazy("dashboard:openaikeys")

    def get_queryset(self):
        return OpenAIKey.objects.filter(owner=self.request.user).order_by(
            "-date_created"
        )


class OpenAIKeysListView(OpenAIKeysBaseView, generic.ListView):
    fields = "__all__"
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


class PublicTokensFormMixin:
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["openaikey"].queryset = OpenAIKey.objects.filter(
            owner=self.request.user
        )
        form.fields["user"].queryset = User.aieye_users_objects
        return form


class PublicTokensBaseViewMixin(AiEyeAdminMixin):
    success_url = reverse_lazy("dashboard:publictokens")

    def get_queryset(self):
        return PublicToken.objects.filter(
            openaikey__owner=self.request.user
        ).prefetch_related("user", "openaikey")


class PublicTokensListView(PublicTokensBaseViewMixin, generic.ListView):
    fields = "__all__"
    template_name = "dashboard/publictokens/list.html"
    ordering = ["-date_created"]


class PublicTokensCreateView(
    PublicTokensFormMixin, PublicTokensBaseViewMixin, generic.CreateView
):
    template_name = "dashboard/publictokens/create.html"
    form_class = PublicTokenCreateForm


class PublicTokensUpdateView(
    PublicTokensFormMixin, PublicTokensBaseViewMixin, generic.UpdateView
):
    template_name = "dashboard/publictokens/update.html"
    form_class = PublicTokenUpdateForm


class PublicTokensDeleteView(PublicTokensBaseViewMixin, generic.DeleteView):  # type: ignore[misc]
    template_name = "dashboard/publictokens/delete.html"
