from django.shortcuts import render


def handler404(request, exc):
    return render(request, "dashboard/errors/404.html", status=404)


def handler500(request):
    return render(request, "dashboard/errors/500.html")
