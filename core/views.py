from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.views import View

from dashboard.forms import LoginForm


def index_view(request):
    if not request.user.is_authenticated:
        return redirect("core:login")
    return redirect("dashboard:index")


class LoginFormView(View):
    form_class = LoginForm
    template_name = "core/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("dashboard:index")

        form = self.form_class(None)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = self.form_class(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("dashboard:index")

        return render(request, self.template_name, {"form": form})
