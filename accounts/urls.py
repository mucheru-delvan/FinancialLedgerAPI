from django.urls import path

from accounts.views import MyAccountView


urlpatterns = [
    path("me/", MyAccountView.as_view(), name="my-account"),
]