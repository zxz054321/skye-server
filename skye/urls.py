from django.urls import path

from . import views

urlpatterns = [
    path("csrf", views.csrf),
    # authentication
    path("register", views.register),
    path("login", views.login),
    path("logout", views.logout),
    path("user", views.get_user),
    # business
    path("ask", views.ask),
    path("invitation-code", views.get_invitation_code),
    path("invitees", views.get_invitees),
    path("redeem", views.redeem),
    path("balance", views.get_balance),
]
