from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View, generic
from django.views.generic import TemplateView

from api.models import Log
from core.forms import UserCreateForm
from core.mixins import AiEyeAdminMixin, AiEyeAdminOrUserMixin
from core.models import OpenAIKey, PublicToken
from dashboard.forms import PublicTokenCreateForm, PublicTokenUpdateForm
from pipelines.forms import PipelineCreateForm
from pipelines.models import BuiltinFunction, PipelineSource, Prompt

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
        return (
            PublicToken.objects.filter(openaikey__owner=self.request.user)
            .prefetch_related("user", "openaikey")
            .order_by("-date_created")
        )


class PublicTokensListView(PublicTokensBaseViewMixin, generic.ListView):
    fields = "__all__"
    template_name = "dashboard/publictokens/list.html"


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


class CachesBaseViewMixin(AiEyeAdminMixin):
    success_url = reverse_lazy("dashboard:caches")

    def get_queryset(self):
        return Log.objects.prefetch_related("user", "api_key").order_by("-timestamp")


class CachesListView(CachesBaseViewMixin, generic.ListView):
    fields = "__all__"
    template_name = "dashboard/caches/list.html"


class CachesDeleteView(CachesBaseViewMixin, generic.DeleteView):  # type: ignore[misc]
    template_name = "dashboard/caches/delete.html"


class CachesDeleteAllView(AiEyeAdminMixin, generic.FormView):
    template_name = "dashboard/caches/delete_all.html"
    success_url = reverse_lazy("dashboard:caches")

    form_class = forms.Form

    def form_valid(self, form):
        Log.objects.all().delete()
        return super().form_valid(form)


class PromptBaseView(AiEyeAdminOrUserMixin, View):
    success_url = reverse_lazy("dashboard:prompts")

    def get_queryset(self):
        user = self.request.user
        qs = Prompt.objects
        if user.is_aieye_user:
            qs = qs.filter(owner=user)

        return qs.order_by("-date_created")


class PromptListView(PromptBaseView, generic.ListView):
    fields = "__all__"
    template_name = "dashboard/prompts/list.html"


class PromptCreateView(PromptBaseView, generic.CreateView):
    fields = ["name", "body", "description"]
    template_name = "dashboard/prompts/create.html"

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.owner = self.request.user
        return super().form_valid(form)


class PromptDeleteView(PromptBaseView, generic.DeleteView):  # type: ignore[misc]
    template_name = "dashboard/prompts/delete.html"


class PromptUpdateView(PromptBaseView, generic.UpdateView):
    fields = ["name", "body", "description"]
    template_name = "dashboard/prompts/update.html"


class BuiltinFunctionBaseView(AiEyeAdminMixin, View):
    success_url = reverse_lazy("dashboard:builtins")

    def get_queryset(self):
        return BuiltinFunction.objects.order_by("-date_created")


class BuiltinFunctionListView(AiEyeAdminOrUserMixin, generic.ListView):
    fields = "__all__"
    template_name = "dashboard/builtins/list.html"

    def get_queryset(self):
        return BuiltinFunction.objects.order_by("-date_created")


class BuiltinFunctionCreateView(BuiltinFunctionBaseView, generic.CreateView):
    fields = ["name", "description"]
    template_name = "dashboard/builtins/create.html"

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.owner = self.request.user
        return super().form_valid(form)


class BuiltinFunctionDeleteView(BuiltinFunctionBaseView, generic.DeleteView):  # type: ignore[misc]
    template_name = "dashboard/builtins/delete.html"


class BuiltinFunctionUpdateView(BuiltinFunctionBaseView, generic.UpdateView):
    fields = ["name", "description"]
    template_name = "dashboard/builtins/update.html"


class PipelineSourceBaseView(AiEyeAdminOrUserMixin, View):
    success_url = reverse_lazy("dashboard:pipelines")

    def get_queryset(self):
        user = self.request.user
        qs = PipelineSource.objects
        if user.is_aieye_user:
            qs = qs.filter(owner=user)

        return qs.order_by("-date_created")


class PipelineSourceListView(PipelineSourceBaseView, generic.ListView):
    fields = "__all__"
    template_name = "dashboard/pipelines/list.html"


class PipelineSourceCreateView(PipelineSourceBaseView, generic.CreateView):
    template_name = "dashboard/pipelines/create.html"
    form_class = PipelineCreateForm
    success_url = reverse_lazy("dashboard:pipelines")

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.owner = self.request.user
        return super().form_valid(form)


class PipelineSourceUpdateView(PipelineSourceBaseView, generic.UpdateView):
    form_class = PipelineCreateForm
    template_name = "dashboard/pipelines/update.html"


class PipelineSourceDeleteView(PipelineSourceBaseView, generic.DeleteView):  # type: ignore[misc]
    template_name = "dashboard/pipelines/delete.html"


class PipelineSourceExecuteView(AiEyeAdminOrUserMixin, TemplateView):
    template_name = "dashboard/pipelines/execute.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        qs = PipelineSource.objects
        if user.is_aieye_user:
            qs = qs.filter(owner=user)

        pipelines = qs.order_by("-date_created")
        openaikeys = (
            OpenAIKey.objects.filter(
                Q(owner=user) | Q(users__in=[user]), is_active=True
            )
            .distinct()
            .order_by("-date_created")
        )

        context.update({"pipelines": pipelines, "openaikeys": openaikeys})
        if selected_pipeline := kwargs.get("id"):
            context.update({"selected_pipeline": selected_pipeline})

        return context


def index(request):
    if request.user.is_authenticated:
        if request.user.is_aieye_admin:
            return redirect("dashboard:users")
        else:
            return redirect("dashboard:prompts")
    else:
        return redirect("access:login")
