from django.urls import path
from accounts.views import *

urlpatterns = [
    path("auth/connect/", auth_connect, name="oauth_connect"),
    path("auth/callback/", callback, name="oauth_callback"),
    path("auth/tokens/", tokens, name="oauth_tokens"),
    path('auth/login/', LoginView.as_view(), name='login'),

]