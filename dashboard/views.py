from django.contrib.auth import get_user_model, login
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View, generic

from core.forms import UserCreateForm
from core.mixins import AiEyeAdminMixin
from dashboard.forms import LoginForm

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
    template_name = "dashboard/index.html"

    def get_queryset(self):
        return self.model.aieye_users_objects.all()


class LoginFormView(View):
    form_class = LoginForm
    template_name = "dashboard/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("index")

        form = self.form_class(None)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = self.form_class(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("index")

        return render(request, self.template_name, {"form": form})
